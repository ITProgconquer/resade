# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EtudeEnquete(models.Model):
    """
    Processus P-CI-02 : Conduite des études et enquêtes terrain
    Carnet I — Module 01 : Processus de Recherche — RESADE
    """
    _name = 'resade.etude.enquete'
    _description = 'Étude / Enquête Terrain (P-CI-02)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'
    _rec_name = 'reference'

    # ─── Identification ───────────────────────────────────────────────────────
    reference = fields.Char(
        string='Code Étude',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    titre = fields.Char(string="Titre de l'étude", required=True, tracking=True)
    protocole_id = fields.Many2one(
        'resade.protocole.recherche',
        string='Protocole de référence',
        required=True,
        tracking=True,
        domain=[('state', '=', 'valide')],
    )
    projet_id = fields.Many2one(
        'project.project',
        string='Projet rattaché',
        related='protocole_id.projet_id',
        store=True,
    )

    # ─── RACI ────────────────────────────────────────────────────────────────
    investigateur_principal_id = fields.Many2one(
        'hr.employee',
        string='Investigateur Principal (PI)',
        required=True,
        tracking=True,
    )
    coordinateur_terrain_id = fields.Many2one(
        'hr.employee',
        string='Coordinateur terrain',
    )
    equipe_terrain_ids = fields.Many2many(
        'hr.employee',
        'etude_equipe_terrain_rel',
        'etude_id', 'employee_id',
        string='Équipe terrain',
    )

    # ─── Localisation & Période ───────────────────────────────────────────────
    zone_etude = fields.Char(string='Zone géographique / Sites')
    date_debut = fields.Date(string='Date début terrain', required=True)
    date_fin_prevue = fields.Date(string='Date fin prévue')
    date_fin_reelle = fields.Date(string='Date fin réelle')

    # ─── Type d'étude ────────────────────────────────────────────────────────
    type_etude = fields.Selection([
        ('quantitatif', 'Quantitatif'),
        ('qualitatif', 'Qualitatif'),
        ('mixte', 'Méthodes mixtes'),
        ('experimental', 'Expérimental / Essai'),
        ('longitudinal', 'Longitudinal / Cohorte'),
        ('transversal', 'Transversal'),
        ('autre', 'Autre'),
    ], string="Type d'étude")
    taille_echantillon = fields.Integer(string='Taille échantillon prévu')
    taille_echantillon_reel = fields.Integer(string='Taille échantillon réel')

    # ─── Collecte de données ─────────────────────────────────────────────────
    outil_collecte = fields.Selection([
        ('kobo', 'KoBoToolbox'),
        ('odk', 'ODK Collect'),
        ('paper', 'Papier / PAPI'),
        ('capi', 'CAPI (tablette)'),
        ('autre', 'Autre'),
    ], string='Outil de collecte')
    consentement_eclaire = fields.Boolean(
        string='Consentement éclairé obtenu ?',
        default=False,
        tracking=True,
    )

    # ─── Statut ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('preparation', 'Préparation'),
        ('en_cours', 'Collecte en cours'),
        ('saisie', 'Saisie / Nettoyage données'),
        ('analyse', 'Analyse'),
        ('rapport', 'Rédaction rapport'),
        ('termine', 'Terminée'),
        ('suspendue', 'Suspendue'),
    ], string='Statut', default='preparation', tracking=True, required=True)

    # ─── Avancement ──────────────────────────────────────────────────────────
    taux_avancement = fields.Float(
        string="Taux de progression (%)",
        digits=(5, 1),
        default=0.0,
        tracking=True,
    )
    difficultes = fields.Text(string='Difficultés / Obstacles rencontrés')
    mesures_correctives = fields.Text(string='Mesures correctives')
    autres = fields.Text(string='Autres outils à préciser')

    # ─── Documents ───────────────────────────────────────────────────────────
    guide_entretien = fields.Binary(string="Guide d'entretien / Questionnaire")
    guide_entretien_filename = fields.Char()
    rapport_terrain = fields.Binary(string='Rapport terrain préliminaire')
    rapport_terrain_filename = fields.Char()
    # ─── Données liées ───────────────────────────────────────────────────────
    donnees_count = fields.Integer(
        string='Jeux de données',
        compute='_compute_donnees_count',
    )

    sais_net=fields.Html(string="Saisie et Nettoyage des données", placeholder="Saisie et nettoyage des données...")
    analyse_upl=fields.Html(string="Analyse des données", placeholder="Analyse des données...")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.etude.enquete') or _('Nouveau')
        return super().create(vals_list)

    def _compute_donnees_count(self):
        for rec in self:
            rec.donnees_count = self.env['resade.donnees.recherche'].search_count(
                [('etude_id', '=', rec.id)])

    # ─── Workflow ────────────────────────────────────────────────────────────
    def action_demarrer(self):
        self.ensure_one()
        if not self.consentement_eclaire:
            raise UserError(_("Le consentement éclairé doit être confirmé avant le démarrage de la collecte."))
        self.state = 'en_cours'

    def action_saisie(self):
        self.state = 'saisie'

    def action_analyser(self):
        self.state = 'analyse'

    def action_rediger_rapport(self):
        self.state = 'rapport'

    def action_suspendre(self):
        self.state = 'suspendue'

    def action_reprendre(self):
        self.state = 'en_cours'

    def action_terminer(self):
        self.write({'state': 'termine', 'date_fin_reelle': fields.Date.today()})

    def action_voir_donnees(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Données — %s') % self.titre,
            'res_model': 'resade.donnees.recherche',
            'view_mode': 'list,form',
            'domain': [('etude_id', '=', self.id)],
            'context': {'default_etude_id': self.id},
        }
