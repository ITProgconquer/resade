# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadePartenaireProjet(models.Model):
    """
    P-EST-03 : Gestion des partenaires et sous-traitants sur les projets
    Formulaires : F-EST-03-01 à F-EST-03-08
    """
    _name = 'resade.partenaire.projet'
    _description = 'Partenaire / Sous-traitant – P-EST-03 (F-EST-03-01 à 08)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'type_engagement, name'

    name = fields.Char(string='Nom du partenaire / sous-traitant', required=True)
    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True, ondelete='cascade'
    )
    type_engagement = fields.Selection([
        ('partenaire',    '🤝 Partenaire (MoU – F-EST-03-02)'),
        ('sous_traitant', '📄 Sous-traitant (Subaward – F-EST-03-03)'),
        ('prestataire',   '🔧 Prestataire de services'),
        ('co_pi',         '🔬 Co-PI / Institution de recherche (Consortium)'),
    ], string='Type d\'engagement', required=True, tracking=True)

    pays = fields.Char(string='Pays / Localisation')
    contact_principal = fields.Char(string='Contact principal (nom, poste)')
    email_contact = fields.Char(string='Email')
    telephone_contact = fields.Char(string='Téléphone')

    # ── Due diligence F-EST-03-01 ──
    due_diligence_juridique = fields.Boolean(
        string='Due diligence juridique réalisée', tracking=True,
        help='Vérification statuts, agréments, représentant légal'
    )
    due_diligence_financiere = fields.Boolean(
        string='Due diligence financière réalisée', tracking=True,
        help='États financiers, capacité de gestion, expérience grants GFGP'
    )
    due_diligence_operationnelle = fields.Boolean(
        string='Due diligence opérationnelle réalisée', tracking=True,
        help='Capacités opérationnelles, équipe, matériel'
    )
    due_diligence_ethique = fields.Boolean(
        string='Due diligence éthique réalisée', tracking=True,
        help='Politique éthique, intégrité, conformité Déclaration d\'Helsinki'
    )
    fiche_due_diligence_ids = fields.Many2many(
        'ir.attachment',
        'resade_part_dd_rel', 'part_id', 'att_id',
        string='Fiche due diligence (F-EST-03-01)'
    )
    due_diligence_concluante = fields.Boolean(
        string='Due diligence concluante',
        compute='_compute_due_diligence', store=True
    )

    # ── Accord signé ──
    type_accord = fields.Selection([
        ('mou',       'MoU (F-EST-03-02)'),
        ('subaward',  'Subaward Agreement NIH 15.2 (F-EST-03-03)'),
        ('contrat',   'Contrat de prestation'),
    ], string='Type d\'accord', tracking=True)
    date_signature_accord = fields.Date(
        string='Date de signature accord', tracking=True
    )
    date_fin_accord = fields.Date(string='Date fin accord')
    accord_signe_ids = fields.Many2many(
        'ir.attachment',
        'resade_part_accord_rel', 'part_id', 'att_id',
        string='Accord signé (MoU / Subaward)'
    )
    montant_subaward = fields.Monetary(
        string='Montant Subaward (FCFA)',
        currency_field='currency_id',
        help='Budget transféré à ce sous-traitant (NIH GPS 15.2 obligatoire si sub-recipient)'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='projet_id.currency_id', store=True
    )

    # ── Suivi exécution ──
    date_kickoff_partenaire = fields.Date(
        string='Date réunion de lancement avec partenaire'
    )
    pv_kickoff_ids = fields.Many2many(
        'ir.attachment',
        'resade_part_koff_rel', 'part_id', 'att_id',
        string='PV de réunion de lancement'
    )

    # ── Évaluation de performance F-EST-03-04 ──
    evaluation_ids = fields.One2many(
        'resade.evaluation.partenaire', 'partenaire_id',
        string='Évaluations de performance (F-EST-03-04)'
    )
    score_moyen_performance = fields.Float(
        string='Score moyen performance (/5)',
        compute='_compute_score_moyen', store=True
    )

    # ── Gestion incidents F-EST-03-07 ──
    incident_ids = fields.One2many(
        'resade.incident.partenaire', 'partenaire_id',
        string='Plans de correction d\'incidents (F-EST-03-07)'
    )

    # ── COPIL F-EST-03-06 ──
    copil_ids = fields.One2many(
        'resade.copil', 'partenaire_id',
        string='PV de Comités de Pilotage (F-EST-03-06)'
    )

    # ── État ──
    state = fields.Selection([
        ('identification',  '🔍 Identification'),
        ('due_diligence',   '🔬 Due diligence en cours'),
        ('negociation',     '📋 Négociation accord'),
        ('actif',           '✅ Actif / Accord signé'),
        ('suspendu',        '⚠️ Suspendu'),
        ('cloture',         '🏁 Clôturé'),
        ('resilie',         '❌ Résilié'),
    ], string='Statut', default='identification', tracking=True)

    # ────────────────────────────────────────
    # COMPUTED
    # ────────────────────────────────────────
    @api.depends(
        'due_diligence_juridique', 'due_diligence_financiere',
        'due_diligence_operationnelle', 'due_diligence_ethique'
    )
    def _compute_due_diligence(self):
        for rec in self:
            rec.due_diligence_concluante = all([
                rec.due_diligence_juridique,
                rec.due_diligence_financiere,
                rec.due_diligence_operationnelle,
                rec.due_diligence_ethique,
            ])

    @api.depends('evaluation_ids.score_global')
    def _compute_score_moyen(self):
        for rec in self:
            if rec.evaluation_ids:
                rec.score_moyen_performance = sum(
                    e.score_global for e in rec.evaluation_ids
                ) / len(rec.evaluation_ids)
            else:
                rec.score_moyen_performance = 0.0

    # ────────────────────────────────────────
    # WORKFLOW
    # ────────────────────────────────────────
    def action_lancer_due_diligence(self):
        self.ensure_one()
        self.write({'state': 'due_diligence'})
        self.message_post(
            body=_('🔬 Due diligence démarrée. '
                   '4 volets : juridique, financier, opérationnel, éthique '
                   '(F-EST-03-01 / GFGP Module 1).')
        )

    def action_valider_due_diligence(self):
        self.ensure_one()
        if not self.due_diligence_concluante:
            raise UserError(
                _('Les 4 volets de la due diligence doivent être complétés '
                  'avant de passer à la négociation (F-EST-03-01).')
            )
        self.write({'state': 'negociation'})
        self.message_post(
            body=_('✅ Due diligence concluante. Négociation de l\'accord démarrée.')
        )

    def action_accord_signe(self):
        self.ensure_one()
        if self.state != 'negociation':
            raise UserError(_('L\'accord doit être en négociation.'))
        if not self.accord_signe_ids:
            raise UserError(
                _('Joignez l\'accord signé (MoU F-EST-03-02 ou '
                  'Subaward F-EST-03-03) avant de valider.')
            )
        self.write({
            'state': 'actif',
            'date_signature_accord': self.date_signature_accord or fields.Date.today(),
        })
        self.message_post(
            body=_('✅ Accord signé le %s. Partenaire actif. '
                   'Réunion de lancement à planifier.') % self.date_signature_accord
        )

    def action_suspendre(self):
        self.ensure_one()
        self.write({'state': 'suspendu'})
        self.message_post(
            body=_('⚠️ Partenaire/sous-traitant suspendu. '
                   'Plan de correction à déclencher (F-EST-03-07).')
        )

    def action_resilier(self):
        self.ensure_one()
        self.write({'state': 'resilie'})
        self.message_post(
            body=_('❌ Accord résilié. Décision DE formalisée.')
        )


class ResadeEvaluationPartenaire(models.Model):
    """F-EST-03-04 : Grille d'évaluation de performance partenaire"""
    _name = 'resade.evaluation.partenaire'
    _description = 'Évaluation Performance Partenaire – F-EST-03-04'
    _order = 'date_evaluation desc'

    partenaire_id = fields.Many2one(
        'resade.partenaire.projet', string='Partenaire', required=True, ondelete='cascade'
    )
    date_evaluation = fields.Date(
        string='Date d\'évaluation', default=fields.Date.today, required=True
    )
    trimestre = fields.Selection([
        ('T1', 'T1'), ('T2', 'T2'), ('T3', 'T3'), ('T4', 'T4')
    ], string='Trimestre')
    note_qualite_scientifique = fields.Integer(string='Qualité scientifique /5', default=0)
    note_respect_delais = fields.Integer(string='Respect des délais /5', default=0)
    note_conformite_financiere = fields.Integer(string='Conformité financière /5', default=0)
    note_communication = fields.Integer(string='Qualité communication /5', default=0)
    note_conformite_ethique = fields.Integer(string='Conformité éthique /5', default=0)
    score_global = fields.Float(
        string='Score global /5',
        compute='_compute_score', store=True
    )
    commentaires = fields.Text(string='Commentaires et observations')
    actions_correctives = fields.Text(string='Actions correctives recommandées')
    evalue_par_id = fields.Many2one(
        'res.users', string='Évalué par',
        default=lambda self: self.env.user
    )

    @api.depends(
        'note_qualite_scientifique', 'note_respect_delais',
        'note_conformite_financiere', 'note_communication', 'note_conformite_ethique'
    )
    def _compute_score(self):
        for rec in self:
            total = (
                rec.note_qualite_scientifique
                + rec.note_respect_delais
                + rec.note_conformite_financiere
                + rec.note_communication
                + rec.note_conformite_ethique
            )
            rec.score_global = total / 5


class ResadeIncidentPartenaire(models.Model):
    """F-EST-03-07 : Plan de correction d'incident"""
    _name = 'resade.incident.partenaire'
    _description = 'Incident Partenaire – Plan de Correction F-EST-03-07'
    _inherit = ['mail.thread']

    partenaire_id = fields.Many2one(
        'resade.partenaire.projet', required=True, ondelete='cascade'
    )
    name = fields.Char(string='Description de l\'incident', required=True)
    date_detection = fields.Date(
        string='Date de détection', default=fields.Date.today
    )
    type_incident = fields.Selection([
        ('technique',    'Non-conformité technique'),
        ('financier',    'Non-conformité financière'),
        ('ethique',      'Manquement éthique'),
        ('securite',     'Incident sécurité'),
        ('conflit',      'Conflit / Litige'),
    ], string='Type d\'incident', required=True)
    description_complete = fields.Text(string='Description détaillée')
    mesures_correctives = fields.Text(string='Plan de correction (actions, délais, responsables)')
    date_echeance_correction = fields.Date(string='Échéance correction')
    state = fields.Selection([
        ('ouvert',      '🔴 Ouvert'),
        ('en_cours',    '🟡 En cours de correction'),
        ('resolu',      '🟢 Résolu'),
        ('escalade',    '⚠️ Escalade DE / Résiliation'),
    ], string='Statut', default='ouvert', tracking=True)


class ResadeCopil(models.Model):
    """F-EST-03-06 : PV de Comité de Pilotage (COPIL)"""
    _name = 'resade.copil'
    _description = 'PV COPIL – F-EST-03-06'

    partenaire_id = fields.Many2one(
        'resade.partenaire.projet', string='Partenaire', ondelete='cascade'
    )
    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True, ondelete='cascade'
    )
    name = fields.Char(string='Intitulé du COPIL', required=True)
    date_copil = fields.Date(
        string='Date du COPIL', default=fields.Date.today, required=True
    )
    participants = fields.Text(string='Liste des participants')
    ordre_du_jour = fields.Html(string='Ordre du jour')
    compte_rendu = fields.Html(string='Compte-rendu / Décisions actées')
    actions_ids = fields.One2many(
        'resade.copil.action', 'copil_id', string='Plan d\'actions'
    )
    pv_signe_ids = fields.Many2many(
        'ir.attachment', string='PV signé'
    )


class ResadeCopilAction(models.Model):
    """Actions issues du COPIL"""
    _name = 'resade.copil.action'
    _description = 'Action COPIL'

    copil_id = fields.Many2one('resade.copil', required=True, ondelete='cascade')
    name = fields.Char(string='Action', required=True)
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    echeance = fields.Date(string='Échéance')
    state = fields.Selection([
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('fait',    'Fait'),
    ], string='Statut', default='a_faire')
