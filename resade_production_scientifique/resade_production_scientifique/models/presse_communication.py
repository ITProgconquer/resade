# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PresseCommunication(models.Model):
    """
    Processus P-CI-10 : Relations presse et communication externe
    Carnet I — Module 03 : Communication Institutionnelle — RESADE
    """
    _name = 'resade.presse.communication'
    _description = 'Relations Presse & Communication Externe (P-CI-10)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_publication desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Code Communication',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    titre = fields.Char(string='Titre / Sujet', required=True, tracking=True)

    type_action = fields.Selection([
        ('communique_presse', 'Communiqué de presse'),
        ('interview', 'Interview / Déclaration'),
        ('article_presse', 'Article presse (couverture média)'),
        ('post_reseaux_sociaux', 'Publication réseaux sociaux'),
        ('newsletter', 'Newsletter RESADE'),
        ('rapport_annuel', 'Rapport annuel'),
        ('video_documentaire', 'Vidéo / Documentaire'),
        ('infographie', 'Infographie'),
        ('autre', 'Autre'),
    ], string="Type d'action", required=True)

    canal = fields.Selection([
        ('presse_ecrite', 'Presse écrite'),
        ('radio', 'Radio'),
        ('tv', 'Télévision'),
        ('web', 'Web / Site Internet'),
        ('reseaux_sociaux', 'Réseaux sociaux'),
        ('email', 'Email / Newsletter'),
        ('autre', 'Autre'),
    ], string='Canal de diffusion', required=True)

    # ─── Responsables ────────────────────────────────────────────────────────
    responsable_id = fields.Many2one(
        'hr.employee',
        string='Responsable Communication (RC)',
        required=True,
        tracking=True,
    )
    approbateur_id = fields.Many2one(
        'hr.employee',
        string='Approbateur (DE)',
        tracking=True,
    )

    # ─── Dates ────────────────────────────────────────────────────────────────
    date_creation = fields.Date(
        string='Date de création',
        default=fields.Date.today,
        required=True,
    )
    date_approbation = fields.Date(string="Date d'approbation DE")
    date_publication = fields.Date(string='Date de publication / Diffusion')

    # ─── Contenu ─────────────────────────────────────────────────────────────
    contenu = fields.Text(string='Contenu / Message clé')
    public_cible = fields.Char(string='Public cible')
    organe_presse = fields.Char(string='Organe de presse / Média / Plateforme')
    journaliste_contact = fields.Char(string='Contact journaliste / Médias')

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('revue', 'En revue interne'),
        ('approuve', 'Approuvé par DE'),
        ('publie', 'Publié / Diffusé'),
        ('archive', 'Archivé'),
    ], string='Statut', default='brouillon', tracking=True)

    # ─── Fichiers ─────────────────────────────────────────────────────────────
    document = fields.Binary(string='Document (communiqué, article...)')
    document_filename = fields.Char()
    image_principale = fields.Binary(string='Visuel / Image principale')
    image_filename = fields.Char()

    # ─── Retombées ────────────────────────────────────────────────────────────
    retombees = fields.Text(string='Retombées presse / Réactions')
    url_diffusion = fields.Char(string='URL de publication')
    portee_estimee = fields.Integer(string='Portée estimée (nb. de personnes touchées)')

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.presse.communication') or _('Nouveau')
        return super().create(vals_list)

    def action_soumettre_revue(self):
        self.state = 'revue'

    def action_approuver(self):
        self.write({
            'state': 'approuve',
            'date_approbation': fields.Date.today(),
        })

    def action_publier(self):
        self.write({
            'state': 'publie',
            'date_publication': fields.Date.today(),
        })
