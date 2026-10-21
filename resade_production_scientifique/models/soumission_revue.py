# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SoumissionRevue(models.Model):
    """
    Processus P-CI-05 : Soumission à des revues scientifiques indexées
    Carnet I — Module 02 : Publication Scientifique — RESADE
    """
    _name = 'resade.soumission.revue'
    _description = 'Soumission Revue Scientifique (P-CI-05)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_soumission desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Code Soumission',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    article_id = fields.Many2one(
        'resade.article.scientifique',
        string='Article',
        required=True,
        domain=[('state', 'in', ['valide_interne', 'soumis', 'revision_externe', 'accepte'])],
        tracking=True,
    )
    auteur_correspondant_id = fields.Many2one(
        'hr.employee',
        string='Auteur correspondant',
        related='article_id.auteur_correspondant_id',
        store=True,
    )

    # ─── Revue cible ─────────────────────────────────────────────────────────
    nom_revue = fields.Char(string='Nom de la revue', required=True, tracking=True)
    editeur = fields.Char(string='Éditeur')
    facteur_impact = fields.Float(string="Facteur d'impact (IF)")
    quartile = fields.Selection([
        ('Q1', 'Q1'),
        ('Q2', 'Q2'),
        ('Q3', 'Q3'),
        ('Q4', 'Q4'),
        ('nc', 'Non classé'),
    ], string='Quartile (Scimago/Web of Science)')
    indexee = fields.Selection([
        ('pubmed', 'PubMed / MEDLINE'),
        ('scopus', 'Scopus'),
        ('wos', 'Web of Science'),
        ('african_journals', 'African Journals Online (AJOL)'),
        ('doaj', 'DOAJ (Open Access)'),
        ('autre', 'Autre'),
    ], string='Indexation principale')
    open_access = fields.Boolean(string='Open Access ?', default=False)
    frais_publication = fields.Float(string='Frais de publication (APC) en FCFA')
    url_submission = fields.Char(string='URL portail de soumission')

    # ─── Dates clés ──────────────────────────────────────────────────────────
    date_soumission = fields.Date(
        string='Date de soumission',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    date_accuse_reception = fields.Date(string='Date accusé de réception')
    date_retour_reviewers = fields.Date(string='Date retour reviewers')
    date_resoumission = fields.Date(string='Date re-soumission (révision)')
    date_decision_finale = fields.Date(string='Date décision finale')
    date_publication = fields.Date(string='Date publication en ligne')

    # ─── Identifiants publication ────────────────────────────────────────────
    numero_soumission = fields.Char(string='N° de soumission (Manuscript ID)')
    doi = fields.Char(string="DOI de l'article publié")
    url_publication = fields.Char(string="URL de l'article (en ligne)")
    numero_volume = fields.Char(string='Volume / Numéro / Pages')

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', 'En préparation'),
        ('soumis', 'Soumis — En attente'),
        ('peer_review', 'Peer review en cours'),
        ('revision_demandee', 'Révision majeure demandée'),
        ('revision_mineure', 'Révision mineure demandée'),
        ('accepte', 'Accepté'),
        ('publie', 'Publié'),
        ('rejete', 'Rejeté'),
        ('retire', 'Retiré'),
    ], string='Statut', default='brouillon', tracking=True, required=True)

    # ─── Commentaires reviewers ───────────────────────────────────────────────
    commentaires_reviewers = fields.Text(string='Commentaires reviewers')
    reponse_reviewers = fields.Binary(string='Lettre de réponse aux reviewers')
    reponse_reviewers_filename = fields.Char()

    # ─── Lettre de couverture ────────────────────────────────────────────────
    lettre_couverture = fields.Binary(string='Lettre de couverture (Cover letter)')
    lettre_couverture_filename = fields.Char()
    manuscrit_soumis = fields.Html(string='Manuscrit soumis', help='Contenu du manuscrit soumis à la revue scientifique')
  

    notes = fields.Text(string='Notes / Historique')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.soumission.revue') or _('Nouveau')
        return super().create(vals_list)

    # ─── Workflow ────────────────────────────────────────────────────────────
    def action_soumettre(self):
        self.ensure_one()
        if not self.date_soumission:
            raise UserError(_("Veuillez indiquer la date de soumission."))
        self.state = 'soumis'
        # Mettre à jour l'article
        if self.article_id:
            self.article_id.state = 'soumis'

    def action_revision_demandee(self):
        self.state = 'revision_demandee'

    def action_accepter(self):
        self.ensure_one()
        self.write({'state': 'accepte', 'date_decision_finale': fields.Date.today()})
        if self.article_id:
            self.article_id.state = 'accepte'

    def action_publier(self):
        self.ensure_one()
        self.write({'state': 'publie', 'date_publication': fields.Date.today()})
        if self.article_id:
            self.article_id.state = 'publie'

    def action_rejeter(self):
        self.ensure_one()
        self.write({'state': 'rejete', 'date_decision_finale': fields.Date.today()})
