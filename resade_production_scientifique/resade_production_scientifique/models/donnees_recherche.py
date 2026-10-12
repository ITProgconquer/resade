# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DonneesRecherche(models.Model):
    """
    Processus P-CI-03 : Gestion des données de recherche
    Carnet I — Module 01 — RESADE
    Conforme aux principes FAIR (Findable, Accessible, Interoperable, Reusable)
    """
    _name = 'resade.donnees.recherche'
    _description = 'Données de Recherche (P-CI-03)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Code Jeu de données',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
    )
    titre = fields.Char(string='Titre / Description', required=True, tracking=True)
    etude_id = fields.Many2one(
        'resade.etude.enquete',
        string='Étude source',
        required=True,
        tracking=True,
    )
    protocole_id = fields.Many2one(
        'resade.protocole.recherche',
        string='Protocole',
        related='etude_id.protocole_id',
        store=True,
    )

    # ─── Responsable (gestionnaire de données) ───────────────────────────────
    gestionnaire_id = fields.Many2one(
        'hr.employee',
        string='Gestionnaire des données (CSI)',
        required=True,
        tracking=True,
    )
    investigateur_id = fields.Many2one(
        'hr.employee',
        string='Investigateur Principal (PI)',
        related='etude_id.investigateur_principal_id',
        store=True,
    )

    # ─── Caractéristiques des données ────────────────────────────────────────
    type_donnees = fields.Selection([
        ('quantitatif', 'Données quantitatives (bases, registres)'),
        ('qualitatif', 'Données qualitatives (entretiens, focus groups)'),
        ('mixte', 'Données mixtes'),
        ('biologique', 'Échantillons biologiques'),
        ('image', 'Images / Vidéos'),
        ('geo', 'Données géospatiales'),
        ('autre', 'Autre'),
    ], string='Type de données', required=True)
    format_fichier = fields.Char(string='Format(s) de fichier (ex. .csv, .dta, .xlsx)')
    taille_base = fields.Char(string='Taille / Volume estimé')
    nb_observations = fields.Integer(string="Nombre d'observations")

    # ─── Dates ────────────────────────────────────────────────────────────────
    date_creation = fields.Date(
        string='Date de création',
        default=fields.Date.today,
        required=True,
    )
    date_derniere_mise_a_jour = fields.Date(string='Dernière mise à jour')
    date_archivage = fields.Date(string="Date d'archivage")

    # ─── Plan de gestion des données (DMP) ───────────────────────────────────
    dmp_redige = fields.Boolean(
        string='DMP (Data Management Plan) rédigé ?',
        default=False,
        tracking=True,
    )
    dmp_fichier = fields.Binary(string='Fichier DMP')
    dmp_filename = fields.Char()

    # ─── Stockage & Sécurité ─────────────────────────────────────────────────
    lieu_stockage = fields.Selection([
        ('sharepoint', 'SharePoint RESADE (GED)'),
        ('serveur_local', 'Serveur local sécurisé'),
        ('cloud_prive', 'Cloud privé (accès restreint)'),
        ('outil_collecte', 'Plateforme de collecte (KoBo/ODK)'),
        ('autre', 'Autre'),
    ], string='Lieu de stockage principal', required=True)
    chiffrement = fields.Boolean(string='Données chiffrées / anonymisées ?', default=True)
    acces_restreint = fields.Boolean(string='Accès restreint (données personnelles) ?', default=True)
    responsable_archivage_id = fields.Many2one('hr.employee', string='Responsable archivage (AECD-D)')

    # ─── Partage & Publication ────────────────────────────────────────────────
    partage_prevu = fields.Boolean(string='Partage externe prévu ?', default=False)
    conditions_partage = fields.Text(string='Conditions de partage / Licence')
    depot_externe = fields.Char(
        string='Référentiel de dépôt externe (Zenodo, OSF, etc.)',
    )
    doi_dataset = fields.Char(string='DOI du jeu de données')

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('collecte', 'En cours de collecte'),
        ('nettoyage', 'Nettoyage / Validation'),
        ('analyse', "En cours d'analyse"),
        ('archive', 'Archivé'),
        ('publie', 'Publié / Accessible'),
        ('detruit', 'Détruit (selon protocole)'),
    ], string='Statut', default='collecte', tracking=True)

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.donnees.recherche') or _('Nouveau')
        return super().create(vals_list)

    def action_archiver(self):
        self.write({'state': 'archive', 'date_archivage': fields.Date.today()})
