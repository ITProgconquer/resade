# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class ResadeOpportunite(models.Model):
    """
    P-MRV-01 : Veille sur les appels à projets et opportunités de financement
    Formulaires : F-MRV-01-01 à F-MRV-01-07
    """
    _name = 'resade.opportunite'
    _description = 'Opportunité de Financement – RESADE F-MRV-01-01'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_identification desc, name desc'

    # ── Identification ──
    name = fields.Char(
        string='Intitulé de l\'opportunité', required=True, tracking=True
    )
    ref = fields.Char(
        string='Référence interne',
        default=lambda self: _('Nouveau'), copy=False, readonly=True
    )
    bailleur = fields.Char(string='Bailleur / Donateur', required=True, tracking=True)
    type_bailleur = fields.Selection([
        ('multilatéral', 'Multilatéral (ONU, Banque Mondiale...)'),
        ('bilateral',    'Bilatéral (USAID, GIZ, AFD...)'),
        ('fondation',    'Fondation privée (Gates, Wellcome...)'),
        ('gouvernement', 'Gouvernement BF / National'),
        ('autres',       'Autres'),
    ], string='Type de bailleur', required=True)

    # ── Dates & délais ──
    date_identification = fields.Date(
        string='Date d\'identification', default=fields.Date.today, required=True
    )
    date_limite_soumission = fields.Date(
        string='Date limite de soumission', tracking=True
    )
    jours_restants = fields.Integer(
        string='Jours restants', compute='_compute_jours_restants'
    )
    urgence = fields.Selection([
        ('haute',   '🔴 Haute (< 15j)'),
        ('moyenne', '🟡 Moyenne (15-30j)'),
        ('basse',   '🟢 Basse (> 30j)'),
        ('expiree', '⬛ Expirée'),
    ], string='Niveau d\'urgence', compute='_compute_jours_restants', store=True)

    # ── Contenu ──
    description = fields.Text(
        string='Description de l\'opportunité',
        help='Résumé de l\'appel à propositions, axes prioritaires, modalités'
    )
    lien_appel = fields.Char(string='Lien URL de l\'appel à projets')
    axes_thematiques = fields.Many2many(
        'resade.axe.thematique',
        string='Axes thématiques',
        help='Alignement avec les axes de recherche de RESADE et le PNDS 2021-2030'
    )
    zone_geographique = fields.Selection([
        ('burkina',         'Burkina Faso'),
        ('afrique_ouest',   'Afrique de l\'Ouest / CEDEAO'),
        ('afrique',         'Afrique sub-saharienne'),
        ('international',   'International'),
    ], string='Zone géographique')

    # ── Grille de scoring multicritères F-MRV-01-07 ──
    score_alignement_strategique = fields.Integer(
        string='Alignement stratégique (0-5)',
        default=0,
        help='Alignement avec le Plan Stratégique RESADE 2026-2030 et les axes de recherche'
    )
    score_capacite_interne = fields.Integer(
        string='Capacité interne (0-5)',
        default=0,
        help='Disponibilité des RH, compétences techniques requises, charge de travail actuelle'
    )
    score_potentiel_financier = fields.Integer(
        string='Potentiel financier (0-5)',
        default=0,
        help='Montant estimé, durée du financement, coûts indirects autorisés'
    )
    score_faisabilite = fields.Integer(
        string='Faisabilité (0-5)',
        default=0,
        help='Délai de soumission, complexité, partenaires requis, clauses contractuelles'
    )
    score_visibilite = fields.Integer(
        string='Visibilité / Réputation (0-5)',
        default=0,
        help='Impact sur la visibilité scientifique et la crédibilité de RESADE'
    )
    score_total = fields.Integer(
        string='Score total (/25)',
        compute='_compute_score_total', store=True
    )
    seuil_qualification = fields.Integer(
        string='Seuil de qualification',
        default=15,
        help='Score minimum pour qualifier l\'opportunité (défini dans F-MRV-01-07)'
    )
    qualifiee = fields.Boolean(
        string='Qualifiée pour P-MRV-02',
        compute='_compute_score_total', store=True
    )

    # ── Budget estimé ──
    montant_estime = fields.Monetary(
        string='Budget estimé (FCFA)', currency_field='currency_id'
    )
    duree_projet_mois = fields.Integer(string='Durée estimée (mois)')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )

    # ── Workflow ──
    state = fields.Selection([
        ('identifiee',  '🔍 Identifiée'),
        ('en_analyse',  '🔬 En cours d\'analyse'),
        ('qualifiee',   '✅ Qualifiée → P-MRV-02'),
        ('non_retenue', '❌ Non retenue'),
        ('expiree',     '⌛ Expirée'),
    ], string='Statut', default='identifiee', tracking=True)

    # ── Traçabilité RACI ──
    identifie_par_id = fields.Many2one(
        'res.users', string='Identifié par (DPMR)',
        default=lambda self: self.env.user
    )
    valide_par_cdp_id = fields.Many2one(
        'res.users', string='Validé par (CDP)', readonly=True
    )
    date_validation_cdp = fields.Datetime(string='Date validation CDP', readonly=True)
    note_qualification = fields.Text(
        string='Note de qualification / Décision RT + CAF'
    )

    # ── Bordereau de transmission F-MRV-01-02 ──
    transmise_p_mrv02 = fields.Boolean(
        string='Bordereau de transmission émis (F-MRV-01-02)', readonly=True
    )
    date_transmission = fields.Datetime(string='Date transmission vers P-MRV-02', readonly=True)
    proposition_ids = fields.One2many(
        'resade.proposition', 'opportunite_id', string='Propositions liées'
    )
    nb_propositions = fields.Integer(
        string='Nb propositions', compute='_compute_nb_propositions'
    )

    # ── Plan annuel de veille F-MRV-01-04 ──
    plan_veille_id = fields.Many2one(
        'resade.plan.veille', string='Plan annuel de veille (F-MRV-01-04)'
    )

    # ── Pièces jointes ──
    document_appel_ids = fields.Many2many(
        'ir.attachment',
        'resade_opp_doc_rel', 'opp_id', 'att_id',
        string='Documents de l\'appel (PDF, guidelines...)'
    )

    # ────────────────────────────────────────
    # COMPUTED
    # ────────────────────────────────────────
    @api.depends('date_limite_soumission')
    def _compute_jours_restants(self):
        today = date.today()
        for rec in self:
            if rec.date_limite_soumission:
                delta = (rec.date_limite_soumission - today).days
                rec.jours_restants = delta
                if delta < 0:
                    rec.urgence = 'expiree'
                elif delta < 15:
                    rec.urgence = 'haute'
                elif delta <= 30:
                    rec.urgence = 'moyenne'
                else:
                    rec.urgence = 'basse'
            else:
                rec.jours_restants = 0
                rec.urgence = 'basse'

    @api.depends(
        'score_alignement_strategique', 'score_capacite_interne',
        'score_potentiel_financier', 'score_faisabilite', 'score_visibilite',
        'seuil_qualification'
    )
    def _compute_score_total(self):
        for rec in self:
            total = (
                rec.score_alignement_strategique
                + rec.score_capacite_interne
                + rec.score_potentiel_financier
                + rec.score_faisabilite
                + rec.score_visibilite
            )
            rec.score_total = total
            rec.qualifiee = total >= rec.seuil_qualification

    def _compute_nb_propositions(self):
        for rec in self:
            rec.nb_propositions = len(rec.proposition_ids)

    # ────────────────────────────────────────
    # CONTRAINTES
    # ────────────────────────────────────────
    @api.constrains(
        'score_alignement_strategique', 'score_capacite_interne',
        'score_potentiel_financier', 'score_faisabilite', 'score_visibilite'
    )
    def _check_scores(self):
        for rec in self:
            for fname in [
                'score_alignement_strategique', 'score_capacite_interne',
                'score_potentiel_financier', 'score_faisabilite', 'score_visibilite'
            ]:
                val = getattr(rec, fname)
                if not (0 <= val <= 5):
                    raise ValidationError(
                        _('Les scores doivent être entre 0 et 5 (grille F-MRV-01-07).')
                    )

    # ────────────────────────────────────────
    # SÉQUENCE
    # ────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', _('Nouveau')) == _('Nouveau'):
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'resade.opportunite'
                ) or _('Nouveau')
        return super().create(vals_list)

    # ────────────────────────────────────────
    # WORKFLOW
    # ────────────────────────────────────────
    def action_analyser(self):
        self.ensure_one()
        self.write({'state': 'en_analyse'})
        self.message_post(body=_('🔬 Opportunité en cours d\'analyse (grille F-MRV-01-07).'))

    def action_qualifier(self):
        """CDP valide la qualification → bordereau F-MRV-01-02 émis automatiquement"""
        self.ensure_one()
        if self.score_total < self.seuil_qualification:
            raise UserError(
                _('Score insuffisant (%d/%d). Révisez la grille de scoring '
                  'F-MRV-01-07 avant de qualifier.') % (self.score_total, 25)
            )
        if not self.note_qualification:
            raise UserError(
                _('Renseignez la note de qualification / décision RT + CAF '
                  'avant de valider (F-MRV-01-01 B.8 séq. 7).')
            )
        self.write({
            'state': 'qualifiee',
            'valide_par_cdp_id': self.env.user.id,
            'date_validation_cdp': fields.Datetime.now(),
            'transmise_p_mrv02': True,
            'date_transmission': fields.Datetime.now(),
        })
        self.message_post(
            body=_(
                '✅ Opportunité qualifiée (score %d/25). '
                'Bordereau de transmission F-MRV-01-02 émis vers P-MRV-02. '
                'Rédaction de proposition déclenchée.'
            ) % self.score_total
        )

    def action_non_retenir(self):
        self.ensure_one()
        if not self.note_qualification:
            raise UserError(
                _('Précisez le motif de non-sélection dans la note de qualification.')
            )
        self.write({'state': 'non_retenue'})
        self.message_post(
            body=_('❌ Opportunité non retenue. Motif : %s') % self.note_qualification
        )

    def action_creer_proposition(self):
        """Créer une proposition depuis l'opportunité qualifiée"""
        self.ensure_one()
        if self.state != 'qualifiee':
            raise UserError(_('Qualifiez d\'abord l\'opportunité avant de créer une proposition.'))
        proposition = self.env['resade.proposition'].create({
            'name': f'Proposition – {self.name}',
            'opportunite_id': self.id,
            'bailleur': self.bailleur,
            'date_limite_soumission': self.date_limite_soumission,
            'montant_sollicite': self.montant_estime,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle Proposition',
            'res_model': 'resade.proposition',
            'res_id': proposition.id,
            'view_mode': 'form',
        }

    # ────────────────────────────────────────
    # CRON : marquer expirées
    # ────────────────────────────────────────
    @api.model
    def _cron_marquer_expirees(self):
        expirees = self.search([
            ('state', 'in', ['identifiee', 'en_analyse']),
            ('date_limite_soumission', '<', fields.Date.today()),
        ])
        expirees.write({'state': 'expiree'})


class ResadeAxeThematique(models.Model):
    _name = 'resade.axe.thematique'
    _description = 'Axe thématique de recherche RESADE'

    name = fields.Char(string='Axe thématique', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)


class ResadePlanVeille(models.Model):
    """F-MRV-01-04 : Plan annuel de veille"""
    _name = 'resade.plan.veille'
    _description = 'Plan Annuel de Veille – RESADE F-MRV-01-04'
    _inherit = ['mail.thread']
    _order = 'annee desc'

    name = fields.Char(
        string='Libellé', compute='_compute_name', store=True
    )
    annee = fields.Integer(
        string='Année', required=True,
        default=lambda self: fields.Date.today().year
    )
    axes_cibles = fields.Text(
        string='Axes thématiques cibles',
        help='Axes de recherche prioritaires pour la veille (alignement PNDS + PS RESADE)'
    )
    bailleurs_cibles = fields.Text(
        string='Bailleurs cibles',
        help='Liste des PTF prioritaires à cibler pour l\'année'
    )
    seuil_score = fields.Integer(
        string='Seuil de qualification retenu', default=15
    )
    valide_par_de = fields.Boolean(string='Validé par le DE', tracking=True)
    date_validation = fields.Date(string='Date de validation')
    opportunite_ids = fields.One2many(
        'resade.opportunite', 'plan_veille_id', string='Opportunités identifiées'
    )
    nb_opportunites = fields.Integer(
        string='Nb opportunités', compute='_compute_stats'
    )
    nb_qualifiees = fields.Integer(
        string='Nb qualifiées', compute='_compute_stats'
    )
    taux_conversion = fields.Float(
        string='Taux de conversion (%)', compute='_compute_stats'
    )
    note_plan = fields.Html(string='Contenu du plan annuel de veille')
    rapport_trimestriel_ids = fields.One2many(
        'resade.rapport.veille', 'plan_veille_id',
        string='Rapports trimestriels (F-MRV-01-05)'
    )
    document_ids = fields.Many2many(
        'ir.attachment', string='Documents joints (plan, rapports...)'
    )

    @api.depends('annee')
    def _compute_name(self):
        for rec in self:
            rec.name = f'Plan de Veille {rec.annee}'

    @api.depends('opportunite_ids', 'opportunite_ids.state')
    def _compute_stats(self):
        for rec in self:
            total = len(rec.opportunite_ids)
            qualifiees = len(rec.opportunite_ids.filtered(
                lambda o: o.state == 'qualifiee'
            ))
            rec.nb_opportunites = total
            rec.nb_qualifiees = qualifiees
            rec.taux_conversion = (qualifiees / total * 100) if total else 0.0


class ResadeRapportVeille(models.Model):
    """F-MRV-01-05 : Rapport trimestriel de veille"""
    _name = 'resade.rapport.veille'
    _description = 'Rapport Trimestriel de Veille – RESADE F-MRV-01-05'
    _inherit = ['mail.thread']

    name = fields.Char(string='Intitulé', required=True)
    plan_veille_id = fields.Many2one(
        'resade.plan.veille', string='Plan annuel de veille', required=True
    )
    trimestre = fields.Selection([
        ('T1', 'T1 (Jan–Mar)'),
        ('T2', 'T2 (Avr–Jun)'),
        ('T3', 'T3 (Jul–Sep)'),
        ('T4', 'T4 (Oct–Déc)'),
    ], string='Trimestre', required=True)
    date_rapport = fields.Date(
        string='Date du rapport', default=fields.Date.today
    )
    nb_opportunites_identifiees = fields.Integer(
        string='Nb opportunités identifiées'
    )
    nb_opportunites_qualifiees = fields.Integer(
        string='Nb opportunités qualifiées'
    )
    nb_propositions_transmises = fields.Integer(
        string='Nb propositions transmises à P-MRV-02'
    )
    synthese = fields.Html(
        string='Synthèse narrative du trimestre',
        help='Consolidation des activités de veille, tendances bailleurs, ajustements'
    )
    recommandations = fields.Text(
        string='Recommandations pour le trimestre suivant'
    )
    valide_par_cdp = fields.Boolean(string='Validé par CDP', tracking=True)
    document_ids = fields.Many2many('ir.attachment', string='Rapport joint (PDF)')
