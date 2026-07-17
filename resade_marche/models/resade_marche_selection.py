import secrets

from odoo import models, fields, api, _
from odoo.http import UserError


class ResadeMarcheListeCourte(models.Model):
    """
    P-PTM-02 – Consultation restreinte
    Manuel RESADE Carnet D Module 02 étape 2 :
    Liste courte de 3 à 5 fournisseurs présélectionnés invités à soumissionner.
    """
    _name = 'resade.marche.liste.courte'
    _description = 'Liste courte – Consultation restreinte (P-PTM-02)'
    _order = 'marche_id, sequence'

    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', required=True, ondelete='cascade'
    )
    sequence = fields.Integer(string='N°', default=10)
    fournisseur_id = fields.Many2one(
        'resade.fournisseur', string='Fournisseur', required=True
    )
    raison_selection = fields.Char(
        string='Motif de présélection',
        help='Critères ayant justifié l\'inclusion dans la liste courte'
    )
    lettre_invitation_envoyee = fields.Boolean(
        string='Lettre d\'invitation envoyée', default=False
    )
    date_invitation = fields.Date(string='Date envoi invitation')
    offre_recue = fields.Boolean(string='Offre reçue', default=False)
    date_reception_offre = fields.Date(string='Date réception offre')
    note_interne = fields.Char(string='Note')
    offre_id = fields.Many2one('resade.marche.offre', string='Offre déposée', readonly=True)
   

    # nouveaux

    token = fields.Char(
        string='Jeton d\'invitation',
        default=lambda self: __import__('secrets').token_urlsafe(32),
        readonly=True, copy=False
    )
    email_contact = fields.Char(
        related='fournisseur_id.email', string='Email de contact'
    )
    state = fields.Selection([
        ('preselectionne', 'Présélectionné'),
        ('invite', 'Invité (lien envoyé)'),
        ('offre_recue', 'Offre reçue'),
        ('decline', 'A décliné'),
    ], default='preselectionne', string='Statut', tracking=True)
    # ── FIN NOUVEAUX CHAMPS ──

    
    
    

    _sql_constraints = [
        ('token_unique', 'unique(token)', 'Le jeton d\'invitation doit être unique.'),
    ]

    def action_envoyer_invitation(self):
        """Envoie le lien unique d'invitation au fournisseur."""
        for rec in self:
            if not rec.email_contact:
                raise UserError(_("Aucun email pour ce fournisseur."))
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/marche/consultation/{rec.token}"
            # Template email à créer
            template = self.env.ref('resade_marche.mail_template_invitation_consultation', raise_if_not_found=False)
            if template:
                template.with_context(invitation_url=url).send_mail(rec.id, force_send=True,
                                                                    email_values={'email_to': rec.email_contact})
            rec.write({
                'state': 'invite',
                'lettre_invitation_envoyee': True,
                'date_invitation': fields.Date.today(),
            })
    
    def action_revoquer_invitation(self):
        """Révoque l'invitation (régénère un nouveau token)."""
        for rec in self:
            rec.write({
                'token': secrets.token_urlsafe(32),
                'state': 'preselectionne',
                'date_invitation': False,
                'lettre_invitation_envoyee': False,
            })


class ResadeMarcheGrilleEval(models.Model):
    """
    P-PTM-04 / P-PTM-05 – Grille d'évaluation des offres
    Manuel RESADE Carnet D Module 02 étape 5 (consultant individuel)
    et étape 5 (services spécialisés recherche).
    Pondération par défaut 80% technique / 20% financier (consultants).
    """
    _name = 'resade.marche.grille.eval'
    _description = 'Grille évaluation des offres (P-PTM-04 / P-PTM-05)'
    _order = 'marche_id, sequence'

    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', required=True, ondelete='cascade'
    )
    sequence = fields.Integer(string='N°', default=10)
    fournisseur_id = fields.Many2one(
        'resade.fournisseur', string='Soumissionnaire', required=True
    )

    # Scores techniques (sur 100)
    score_experience = fields.Float(
        string='Expérience générale (/20)', digits=(5, 2), default=0.0
    )
    score_competences = fields.Float(
        string='Compétences spécifiques (/30)', digits=(5, 2), default=0.0
    )
    score_methodologie = fields.Float(
        string='Méthodologie proposée (/30)', digits=(5, 2), default=0.0
    )
    score_references = fields.Float(
        string='Références missions similaires (/20)', digits=(5, 2), default=0.0
    )
    score_technique_total = fields.Float(
        string='Score technique total (/100)',
        compute='_compute_scores', store=True, digits=(5, 2)
    )

    # Score financier (sur 100 – offre la moins disante = 100)
    montant_offre = fields.Monetary(
        string='Montant offre financière',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='marche_id.currency_id', store=True
    )
    score_financier = fields.Float(
        string='Score financier (/100)',
        digits=(5, 2), default=0.0,
        help='Calculer selon la formule : (Offre min / Offre soumissionnaire) × 100'
    )

    # Score global pondéré
    score_global = fields.Float(
        string='Score global pondéré (/100)',
        compute='_compute_scores', store=True, digits=(5, 2)
    )
    retenu = fields.Boolean(string='Offre retenue', default=False)
    observations = fields.Text(string='Observations / Justification')

    @api.depends('score_experience', 'score_competences',
                 'score_methodologie', 'score_references',
                 'score_financier', 'marche_id.poids_technique_pct',
                 'marche_id.poids_financier_pct')
    def _compute_scores(self):
        for rec in self:
            tech = (
                rec.score_experience
                + rec.score_competences
                + rec.score_methodologie
                + rec.score_references
            )
            rec.score_technique_total = min(tech, 100.0)
            poids_t = rec.marche_id.poids_technique_pct or 80.0
            poids_f = rec.marche_id.poids_financier_pct or 20.0
            total_poids = poids_t + poids_f
            if total_poids > 0:
                rec.score_global = (
                    rec.score_technique_total * (poids_t / total_poids)
                    + rec.score_financier * (poids_f / total_poids)
                )
            else:
                rec.score_global = 0.0
