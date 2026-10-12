# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BibliothequeEnLigne(models.Model):
    """
    Processus P-CI-08 : Gestion du site web et de la bibliothèque en ligne
    Carnet I — Module 03 : Communication Institutionnelle — RESADE
    """
    _name = 'resade.bibliotheque'
    _description = 'Bibliothèque en ligne / Production documentaire (P-CI-08)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_publication desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Code Document',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    titre = fields.Char(string='Titre', required=True, tracking=True)
    sous_titre = fields.Char(string='Sous-titre')

    # ─── Type de document ────────────────────────────────────────────────────
    type_document = fields.Selection([
        ('article_publie', 'Article publié (peer-reviewed)'),
        ('note_politique', 'Note de politique (Policy Brief)'),
        ('rapport_recherche', 'Rapport de recherche'),
        ('rapport_projet', 'Rapport de projet'),
        ('these', 'Thèse / Mémoire'),
        ('communication', 'Communication (conférence)'),
        ('working_paper', 'Working Paper / Preprint'),
        ('manuel', 'Manuel / Guide'),
        ('fiche_bonne_pratique', 'Fiche de bonne pratique'),
        ('autre', 'Autre'),
    ], string='Type de document', required=True)

    # ─── Auteurs / Responsable ────────────────────────────────────────────────
    auteur_principal_id = fields.Many2one('hr.employee', string='Auteur principal RESADE')
    auteurs_txt = fields.Char(string='Auteurs (texte libre)')
    responsable_publication_id = fields.Many2one(
        'hr.employee',
        string='Responsable publication / Communication (RC)',
        tracking=True,
    )

    # ─── Source / Lien ────────────────────────────────────────────────────────
    article_id = fields.Many2one(
        'resade.article.scientifique',
        string='Article source',
    )
    soumission_id = fields.Many2one(
        'resade.soumission.revue',
        string='Soumission source',
    )
    doi = fields.Char(string='DOI')
    url_externe = fields.Char(string='URL externe (revue, HAL, Zenodo...)')
    url_site_resade = fields.Char(string='URL sur site RESADE')

    # ─── Dates ────────────────────────────────────────────────────────────────
    date_publication = fields.Date(
        string='Date de publication',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    annee = fields.Integer(
        string='Année',
        compute='_compute_annee',
        store=True,
    )

    # ─── Classification ──────────────────────────────────────────────────────
    thematique_ids = fields.Many2many(
        'resade.thematique',
        string='Thématiques',
    )
    mots_cles = fields.Char(string='Mots-clés')
    langue = fields.Selection([
        ('fr', 'Français'),
        ('en', 'Anglais'),
        ('fr_en', 'Bilingue'),
    ], string='Langue', default='fr')
    open_access = fields.Boolean(string='Open Access ?', default=True)

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('a_publier', 'À publier'),
        ('publie', 'Publié'),
        ('archive', 'Archivé'),
    ], string='Statut', default='brouillon', tracking=True)

    # ─── Visibilité site ──────────────────────────────────────────────────────
    visible_site = fields.Boolean(
        string='Visible sur le site RESADE ?',
        default=False,
        tracking=True,
    )
    featured = fields.Boolean(string='Mise en avant (featured) ?', default=False)

    # ─── Fichier ─────────────────────────────────────────────────────────────
    fichier = fields.Binary(string='Fichier (PDF)')
    fichier_filename = fields.Char()
    couverture = fields.Binary(string='Image de couverture')
    couverture_filename = fields.Char()

    resume = fields.Text(string='Résumé / Abstract')
    notes = fields.Text(string='Notes internes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.bibliotheque') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('date_publication')
    def _compute_annee(self):
        for rec in self:
            rec.annee = rec.date_publication.year if rec.date_publication else 0

    def action_publier(self):
        self.write({'state': 'publie', 'visible_site': True})

    def action_archiver(self):
        self.write({'state': 'archive', 'visible_site': False})


class ResadeThematique(models.Model):
    """Thématiques de recherche RESADE (tag)"""
    _name = 'resade.thematique'
    _description = 'Thématique de recherche RESADE'
    _order = 'name'

    name = fields.Char(string='Thématique', required=True)
    code = fields.Char(string='Code')
    color = fields.Integer(string='Couleur')
    description = fields.Text(string='Description')
