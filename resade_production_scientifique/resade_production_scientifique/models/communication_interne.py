# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CommunicationInterne(models.Model):
    """
    Processus P-CI-06 : Communication interne (réunions, groupes de travail, rapports)
    Carnet I — Module 03 : Communication Institutionnelle — RESADE
    """
    _name = 'resade.communication.interne'
    _description = 'Communication Interne (P-CI-06)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reunion desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Code Communication',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    objet = fields.Char(string='Objet / Titre', required=True, tracking=True)

    type_communication = fields.Selection([
        ('reunion_codir', 'Réunion CODIR'),
        ('reunion_equipe', "Réunion d'équipe"),
        ('groupe_travail', 'Groupe de travail'),
        ('rapport_activites', "Rapport d'activités"),
        ('note_interne', 'Note interne'),
        ('circular', 'Circulaire'),
        ('formation_interne', 'Formation interne'),
        ('autre', 'Autre'),
    ], string='Type', required=True)

    # ─── RACI ────────────────────────────────────────────────────────────────
    animateur_id = fields.Many2one(
        'hr.employee',
        string='Animateur / Responsable (RC)',
        required=True,
        tracking=True,
    )
    participants_ids = fields.Many2many(
        'hr.employee',
        'com_interne_participant_rel',
        'com_id', 'employee_id',
        string='Participants',
    )

    # ─── Dates ────────────────────────────────────────────────────────────────
    date_reunion = fields.Datetime(
        string='Date / Heure',
        required=True,
        default=fields.Datetime.now,
    )
    duree_heures = fields.Float(string='Durée (heures)', digits=(4, 2))
    lieu = fields.Char(string='Lieu / Lien de connexion')

    # ─── Ordre du jour ────────────────────────────────────────────────────────
    ordre_du_jour = fields.Text(string='Ordre du jour')
    decisions = fields.Text(string='Décisions prises')
    points_action = fields.Text(string="Points d'action (qui fait quoi, quand)")

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('planifie', 'Planifié'),
        ('tenu', 'Tenu'),
        ('pv_redige', 'PV rédigé'),
        ('pv_approuve', 'PV approuvé / Diffusé'),
    ], string='Statut', default='planifie', tracking=True)

    # ─── Documents ───────────────────────────────────────────────────────────
    pv = fields.Binary(string='Procès-verbal (PV)')
    pv_filename = fields.Char()
    support_presentation = fields.Binary(string='Support de présentation')
    support_filename = fields.Char()
    liste_presence = fields.Binary(string='Liste de présence')
    liste_presence_filename = fields.Char()
    diffuse = fields.Boolean(string='PV diffusé aux participants ?', default=False)
    date_diffusion = fields.Date(string='Date de diffusion du PV')

    notes = fields.Text(string='Notes complémentaires')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.communication.interne') or _('Nouveau')
        return super().create(vals_list)

    def action_marquer_tenu(self):
        self.state = 'tenu'

    def action_pv_redige(self):
        self.state = 'pv_redige'

    def action_pv_approuve(self):
        self.write({
            'state': 'pv_approuve',
            'diffuse': True,
            'date_diffusion': fields.Date.today(),
        })
