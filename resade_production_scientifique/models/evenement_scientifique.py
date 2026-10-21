# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EvenementScientifique(models.Model):
    """
    Processus P-CI-07 : Participation aux événements scientifiques
    Processus P-CI-09 : Organisation d'événements scientifiques
    Carnet I — Module 03 : Communication Institutionnelle — RESADE
    """
    _name = 'resade.evenement.scientifique'
    _description = 'Événement Scientifique (P-CI-07/09)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Code Événement',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    titre = fields.Char(string="Titre / Nom de l'événement", required=True, tracking=True)

    # ─── Type ────────────────────────────────────────────────────────────────
    type_evenement = fields.Selection([
        ('conference', 'Conférence internationale'),
        ('seminaire', 'Séminaire scientifique'),
        ('atelier', 'Atelier (Workshop)'),
        ('cafe_debat', 'Café-débat'),
        ('webinaire', 'Webinaire'),
        ('forum', 'Forum / Symposium'),
        ('formation', 'Formation / Renforcement de capacités'),
        ('autre', 'Autre'),
    ], string="Type d'événement", required=True)

    mode_participation = fields.Selection([
        ('organisation', 'RESADE organise'),
        ('participation', 'RESADE participe'),
        ('co_organisation', 'Co-organisation'),
    ], string='Mode', required=True, tracking=True)

    # ─── Responsables ────────────────────────────────────────────────────────
    responsable_id = fields.Many2one(
        'hr.employee',
        string='Responsable RESADE (RC / CDP)',
        required=True,
        tracking=True,
    )
    participants_internes_ids = fields.Many2many(
        'hr.employee',
        'evenement_participant_rel',
        'evenement_id', 'employee_id',
        string='Participants RESADE',
    )
    nb_participants_externes = fields.Integer(string='Nb. participants externes attendus')

    # ─── Dates & Lieu ─────────────────────────────────────────────────────────
    date_debut = fields.Date(string='Date de début', required=True, tracking=True)
    date_fin = fields.Date(string='Date de fin')
    lieu = fields.Char(string='Lieu')
    pays = fields.Many2one('res.country', string='Pays')
    en_ligne = fields.Boolean(string='En ligne / Virtuel ?', default=False)
    url_evenement = fields.Char(string="URL / Lien d'accès")

    # ─── Contenu RESADE ──────────────────────────────────────────────────────
    titre_communication = fields.Char(string='Titre de la communication RESADE')
    type_communication = fields.Selection([
        ('oral', 'Présentation orale'),
        ('poster', 'Poster'),
        ('keynote', 'Keynote / Conférencier invité'),
        ('moderation', 'Modération'),
        ('panel', 'Participation à un panel'),
        ('autre', 'Autre'),
    ], string='Type de contribution')
    resume_communication = fields.Html(string='Résumé de la communication', help='Résumé de la communication soumise ou présentée à l\'événement')

    # ─── Financement ─────────────────────────────────────────────────────────
    budget_estime = fields.Float(string='Budget estimé (FCFA)')
    source_financement = fields.Char(string='Source de financement')
    frais_inscription = fields.Float(string="Frais d'inscription (FCFA)")

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('planifie', 'Planifié'),
        ('inscription', 'Inscription / Préparation'),
        ('confirme', 'Confirmé'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
    ], string='Statut', default='planifie', tracking=True, required=True)

    # ─── Compte-rendu ────────────────────────────────────────────────────────
    compte_rendu = fields.Text(string='Compte-rendu / Rapport de participation')
    presentation_fichier = fields.Binary(string='Fichier présentation (PPT/PDF)')
    presentation_filename = fields.Char()
    certificat = fields.Binary(string='Certificat de participation')
    certificat_filename = fields.Char()

    # ─── Diffusion ────────────────────────────────────────────────────────────
    diffusion_interne = fields.Boolean(string='Compte-rendu diffusé en interne ?')
    diffusion_site_web = fields.Boolean(string='Publié sur le site web RESADE ?')
    lien_enregistrement = fields.Char(string='Lien enregistrement / Rediffusion')

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.evenement.scientifique') or _('Nouveau')
        return super().create(vals_list)

    def action_confirmer(self):
        self.state = 'confirme'

    def action_demarrer(self):
        self.state = 'en_cours'

    def action_terminer(self):
        self.state = 'termine'

    def action_annuler(self):
        self.state = 'annule'
