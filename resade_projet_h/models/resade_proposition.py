# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeProposition(models.Model):
    """
    P-MRV-02 : Rédaction et soumission des propositions techniques et financières
    Formulaires : F-MRV-02-01 à F-MRV-02-08
    """
    _name = 'resade.proposition'
    _description = 'Proposition de Financement – RESADE P-MRV-02'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_limite_soumission asc, name'

    # ── Identification ──
    name = fields.Char(string='Titre de la proposition', required=True, tracking=True)
    ref = fields.Char(
        string='Référence', default=lambda self: _('Nouveau'),
        copy=False, readonly=True
    )
    opportunite_id = fields.Many2one(
        'resade.opportunite', string='Opportunité source (F-MRV-01-01)',
        required=True, tracking=True, ondelete='restrict'
    )
    bailleur = fields.Char(
        string='Bailleur', related='opportunite_id.bailleur', store=True
    )

    # ── Arbitrage GO/NO-GO F-MRV-02-01 ──
    fiche_arbitrage_gonogo = fields.Html(
        string='Fiche d\'arbitrage GO/NO-GO (F-MRV-02-01)',
        help='Analyse coûts/bénéfices, capacités disponibles, alignement stratégique PS RESADE'
    )
    decision_gonogo = fields.Selection([
        ('go',    '✅ GO – On candidate'),
        ('no_go', '❌ NO-GO – On ne candidate pas'),
        ('en_attente', '⏳ En attente de décision'),
    ], string='Décision GO/NO-GO', default='en_attente', tracking=True)
    date_decision_gonogo = fields.Datetime(
        string='Date décision GO/NO-GO', readonly=True
    )
    decide_par_de_id = fields.Many2one(
        'res.users', string='Décidé par (DE)', readonly=True
    )

    # ── Équipe de rédaction ──
    pi_id = fields.Many2one(
        'hr.employee', string='Principal Investigator (PI)',
        help='Pilote scientifique de la proposition – désigné par le CDP'
    )
    cdp_id = fields.Many2one(
        'hr.employee', string='Chef Département Partenariat (CDP)',
        help='Superviseur du processus – coordonne les propositions en parallèle'
    )
    co_pi_ids = fields.Many2many(
        'hr.employee',
        'resade_prop_copi_rel', 'prop_id', 'emp_id',
        string='Co-PI / Co-Investigateurs pressentis',
        help='Experts internes et partenaires co-signataires de la proposition'
    )
    reviewer_ids = fields.Many2many(
        'hr.employee',
        'resade_prop_reviewer_rel', 'prop_id', 'emp_id',
        string='Reviewers internes (pairs scientifiques)',
        help='Pairs non impliqués dans la rédaction – revue qualité F-MRV-02-05'
    )

    # ── Dates ──
    date_limite_soumission = fields.Date(
        string='Date limite de soumission', required=True, tracking=True
    )
    date_go = fields.Date(string='Date décision GO')
    date_soumission_effective = fields.Date(
        string='Date de soumission effective', readonly=True
    )
    delai_jours = fields.Integer(
        string='Jours restants avant deadline',
        compute='_compute_delai'
    )

    # ── Contenu scientifique (P-MRV-02 étapes 3-4) ──
    theory_of_change = fields.Html(
        string='Theory of Change (ToC)',
        help='Logique d\'intervention : problème → activités → résultats → impact. '
             'Standard EuropeAid PCM obligatoire.'
    )
    logframe = fields.Html(
        string='Cadre logique (Logframe)',
        help='Matrice 4×4 : objectifs – résultats – activités – indicateurs. '
             'Aligné sur le dispositif MELA de RESADE.'
    )
    resume_technique = fields.Html(
        string='Résumé technique / Abstract',
        help='Résumé de max 500 mots selon format bailleur'
    )
    note_conceptuelle = fields.Html(
        string='Note conceptuelle (Concept Note – F-MRV-02-02)',
        help='Trame standardisée pour les appels en deux étapes (LOI → Full proposal)'
    )
    proposition_complete = fields.Html(
        string='Proposition technique complète (F-MRV-02-03)',
        help='Sections : Contexte – Problématique – Méthodologie – Plan de travail '
             '– Équipe – Impact – Budget'
    )

    # ── Budget (F-MRV-02-04) ──
    montant_sollicite = fields.Monetary(
        string='Montant sollicité (total)',
        currency_field='currency_id', tracking=True
    )
    montant_couts_indirects = fields.Monetary(
        string='Coûts indirects / Overhead',
        currency_field='currency_id',
        help='Coûts institutionnels RESADE : % défini dans la clé de répartition P-CD-03'
    )
    taux_overhead = fields.Float(
        string='Taux overhead (%)',
        help='Taux de coûts indirects négocié avec le bailleur (standard GFGP Module 3)'
    )
    cofinancement = fields.Monetary(
        string='Cofinancement apporté par RESADE',
        currency_field='currency_id'
    )
    duree_projet_mois = fields.Integer(string='Durée du projet (mois)')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    budget_excel_ids = fields.Many2many(
        'ir.attachment',
        'resade_prop_budget_rel', 'prop_id', 'att_id',
        string='Budget détaillé Excel (F-MRV-02-04)'
    )

    # ── Revue qualité interne F-MRV-02-05 ──
    revue_qualite_faite = fields.Boolean(
        string='Revue qualité interne réalisée (F-MRV-02-05)',
        tracking=True,
        help='Check-list des critères de qualité remplie par les reviewers internes'
    )
    rapport_revue_qualite = fields.Html(
        string='Rapport de revue qualité (F-MRV-02-05)',
        help='Observations des reviewers, corrections demandées, validation finale'
    )
    conformite_administrative = fields.Boolean(
        string='Conformité administrative vérifiée (J-3)',
        tracking=True,
        help='Chargé DPMR : documents annexes obligatoires, limites bailleur, formats'
    )

    # ── Soumission ──
    portail_soumission = fields.Char(
        string='Portail de soumission',
        help='Ex: NIH eRA Commons, Gates Fluxx, EDCTP Grants Portal...'
    )
    accuse_reception = fields.Char(
        string='N° accusé de réception bailleur'
    )
    lettre_engagement_de_ids = fields.Many2many(
        'ir.attachment',
        'resade_prop_lettre_rel', 'prop_id', 'att_id',
        string='Lettre d\'engagement institutionnel (DE signé – F-MRV-02-06)'
    )

    # ── Post-soumission ──
    decision_bailleur = fields.Selection([
        ('en_attente',  '⏳ En attente'),
        ('acceptee',    '✅ Acceptée → P-CD-01'),
        ('rejetee',     '❌ Rejetée → Capitalisation P-CC-02'),
        ('liste_att',   '⚠️ Liste d\'attente'),
        ('clarifs',     '🔄 Clarifications demandées'),
    ], string='Décision du bailleur', default='en_attente', tracking=True)
    date_decision_bailleur = fields.Date(
        string='Date de la décision bailleur'
    )
    note_capitalisation = fields.Html(
        string='Note de capitalisation post-décision (F-MRV-02-08)',
        help='Enseignements tirés (succès ou rejet) pour alimenter les propositions futures '
             'et le processus P-CC-02'
    )

    # ── Registre des propositions F-MRV-02-07 ──
    state = fields.Selection([
        ('brouillon',      '📝 Brouillon'),
        ('gonogo_valide',  '✅ GO/NO-GO validé'),
        ('en_redaction',   '✍️ En rédaction'),
        ('revue_qualite',  '🔬 Revue qualité'),
        ('validation_de',  '📋 Validation DE'),
        ('soumise',        '📤 Soumise'),
        ('acceptee',       '🎉 Acceptée'),
        ('rejetee',        '❌ Rejetée'),
        ('no_go',          '🚫 NO-GO'),
    ], string='Statut', default='brouillon', tracking=True, copy=False)

    projet_id = fields.Many2one(
        'resade.projet', string='Projet créé', readonly=True,
        help='Projet créé automatiquement dans P-CD-01 après acceptation'
    )

    # ── Documents ──
    document_ids = fields.Many2many(
        'ir.attachment',
        'resade_prop_doc_rel', 'prop_id', 'att_id',
        string='Autres documents joints (annexes, CV, MoU partenaires...)'
    )

    # ────────────────────────────────────────
    # COMPUTED
    # ────────────────────────────────────────
    @api.depends('date_limite_soumission')
    def _compute_delai(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_limite_soumission:
                rec.delai_jours = (rec.date_limite_soumission - today).days
            else:
                rec.delai_jours = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', _('Nouveau')) == _('Nouveau'):
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'resade.proposition'
                ) or _('Nouveau')
        return super().create(vals_list)

    # ────────────────────────────────────────
    # WORKFLOW
    # ────────────────────────────────────────
    def action_valider_gonogo(self):
        """DE décide le GO/NO-GO (P-MRV-02 séq. 2)"""
        self.ensure_one()
        if not self.fiche_arbitrage_gonogo:
            raise UserError(
                _('Renseignez la fiche d\'arbitrage GO/NO-GO (F-MRV-02-01) '
                  'avant la décision.')
            )
        if self.decision_gonogo == 'no_go':
            self.write({'state': 'no_go'})
            self.message_post(body=_('🚫 Décision NO-GO. Proposition abandonnée.'))
        else:
            self.write({
                'state': 'gonogo_valide',
                'decide_par_de_id': self.env.user.id,
                'date_decision_gonogo': fields.Datetime.now(),
                'decision_gonogo': 'go',
            })
            self.message_post(
                body=_('✅ Décision GO validée par le DE. '
                       'Constitution de l\'équipe de rédaction déclenchée (P-MRV-02 séq. 3-4).')
            )

    def action_lancer_redaction(self):
        """Équipe constituée, rédaction démarrée"""
        self.ensure_one()
        if self.state != 'gonogo_valide':
            raise UserError(_('Le GO/NO-GO doit être validé par le DE.'))
        if not self.pi_id:
            raise UserError(
                _('Désignez le Principal Investigator (PI) avant de lancer la rédaction '
                  '(P-MRV-02 séq. 3).')
            )
        self.write({'state': 'en_redaction'})
        self.message_post(
            body=_('✍️ Rédaction lancée. PI : %s | CDP superviseur : %s') % (
                self.pi_id.name, self.cdp_id.name if self.cdp_id else '—'
            )
        )

    def action_soumettre_revue(self):
        """J-15 : soumission à la revue qualité interne (F-MRV-02-05)"""
        self.ensure_one()
        if self.state != 'en_redaction':
            raise UserError(_('La proposition doit être en cours de rédaction.'))
        if not self.proposition_complete and not self.note_conceptuelle:
            raise UserError(
                _('Rédigez la proposition (F-MRV-02-03) ou la note conceptuelle '
                  '(F-MRV-02-02) avant de soumettre à la revue qualité.')
            )
        if not self.reviewer_ids:
            raise UserError(
                _('Désignez au moins 2 reviewers internes pour la revue qualité '
                  '(P-MRV-02 séq. 10 – J-15 avant deadline).')
            )
        self.write({'state': 'revue_qualite'})
        self.message_post(
            body=_('🔬 Proposition soumise à la revue qualité interne. '
                   'Reviewers : %s') % ', '.join(self.reviewer_ids.mapped('name'))
        )

    def action_valider_revue(self):
        """CDP valide la revue qualité, soumet au DE pour validation finale"""
        self.ensure_one()
        if not self.revue_qualite_faite:
            raise UserError(
                _('Cochez que la revue qualité (F-MRV-02-05) a été réalisée '
                  'et intégrez les corrections avant de valider.')
            )
        self.write({'state': 'validation_de'})
        self.message_post(
            body=_('✅ Revue qualité validée par CDP. '
                   'Soumis au DE pour validation finale et signature '
                   'de la lettre d\'engagement.')
        )

    def action_valider_de_et_soumettre(self):
        """DE valide et signe → Chargé DPMR soumet via portail (J-0)"""
        self.ensure_one()
        if self.state != 'validation_de':
            raise UserError(_('La proposition doit être en attente de validation DE.'))
        if not self.conformite_administrative:
            raise UserError(
                _('Vérifiez la conformité administrative finale (documents annexes, '
                  'limites bailleur) avant soumission – J-3 avant deadline (P-MRV-02 séq. 12).')
            )
        if not self.lettre_engagement_de_ids:
            raise UserError(
                _('Joignez la lettre d\'engagement institutionnel signée par le DE '
                  '(F-MRV-02-06) avant soumission.')
            )
        self.write({
            'state': 'soumise',
            'date_soumission_effective': fields.Date.today(),
        })
        self.message_post(
            body=_('📤 Proposition soumise au bailleur (%s) le %s via %s. '
                   'Accusé de réception : %s. '
                   'Suivi post-soumission déclenché (P-MRV-02 séq. 15).') % (
                self.bailleur,
                self.date_soumission_effective,
                self.portail_soumission or '—',
                self.accuse_reception or '—',
            )
        )

    def action_enregistrer_decision(self):
        """Réception de la décision du bailleur"""
        self.ensure_one()
        if self.state not in ('soumise',):
            raise UserError(_('La proposition doit être soumise.'))
        if self.decision_bailleur == 'acceptee':
            self.write({'state': 'acceptee'})
            self.message_post(
                body=_('🎉 Proposition ACCEPTÉE par %s ! '
                       'Processus P-CD-01 (négociation convention) déclenché. '
                       'Note de capitalisation à produire (F-MRV-02-08).') % self.bailleur
            )
        elif self.decision_bailleur == 'rejetee':
            self.write({'state': 'rejetee'})
            self.message_post(
                body=_('❌ Proposition rejetée par %s. '
                       'Capitalisation des retours en cours (P-CC-02 – F-MRV-02-08).') % self.bailleur
            )
        else:
            self.message_post(
                body=_('🔄 Décision intermédiaire enregistrée : %s') % self.decision_bailleur
            )

    def action_creer_projet(self):
        """Créer le projet Odoo après acceptation → déclenche P-CD-01"""
        self.ensure_one()
        if self.state != 'acceptee':
            raise UserError(
                _('La proposition doit être acceptée par le bailleur '
                  'pour créer un projet (P-CD-01).')
            )
        if self.projet_id:
            raise UserError(_('Un projet existe déjà pour cette proposition.'))
        projet = self.env['resade.projet'].create({
            'name': self.name,
            'proposition_id': self.id,
            'bailleur': self.bailleur,
            'montant_convention': self.montant_sollicite,
            'duree_mois': self.duree_projet_mois,
            'pi_id': self.pi_id.id if self.pi_id else False,
        })
        self.write({'projet_id': projet.id})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouveau Projet',
            'res_model': 'resade.projet',
            'res_id': projet.id,
            'view_mode': 'form',
        }
