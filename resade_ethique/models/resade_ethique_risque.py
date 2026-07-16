# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeEthiqueRisque(models.Model):
    """
    Processus P-GRI-01 : Identification et évaluation des risques institutionnels
    Manuel RESADE - Carnet J - Module 03 : Gestion des risques institutionnels

    Registre institutionnel des risques, structuré autour des 19 risques
    identifiés dans le Plan Stratégique 2026-2030 (Tableau 5), enrichi en continu
    par les remontées opérationnelles des départements, les audits annuels et
    les revues périodiques.

    Cotation standard : Criticité = Incidence × Occurrence (échelle 1 à 3 chacune,
    soit une criticité de 1 à 9), conformément au Manuel.
    """
    _name = 'resade.ethique.risque'
    _description = "Risque institutionnel (P-GRI-01)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'criticite desc'

    name = fields.Char(string='Réf. risque', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    intitule_risque = fields.Char(string='Intitulé du risque', required=True, tracking=True)

    categorie = fields.Selection([
        ('financier', 'Financier'),
        ('operationnel', 'Opérationnel'),
        ('reputationnel', 'Réputationnel'),
        ('juridique', 'Juridique / conformité'),
        ('securitaire', 'Sécuritaire'),
        ('sanitaire', 'Sanitaire'),
        ('strategique', 'Stratégique'),
    ], string='Catégorie', required=True, tracking=True)

    description = fields.Text(string='Description du risque')
    origine_ps_2026_2030 = fields.Boolean(string='Issu des 19 risques du Plan Stratégique 2026-2030', default=True)

    incidence = fields.Selection([
        ('1', 'Faible (1)'),
        ('2', 'Modérée (2)'),
        ('3', 'Forte (3)'),
    ], string='Incidence', default='1', required=True, tracking=True)

    occurrence = fields.Selection([
        ('1', 'Faible (1)'),
        ('2', 'Modérée (2)'),
        ('3', 'Forte (3)'),
    ], string='Occurrence', default='1', required=True, tracking=True)

    criticite = fields.Integer(string='Criticité (I × O)', compute='_compute_criticite', store=True, tracking=True)

    proprietaire_id = fields.Many2one('hr.employee', string='Propriétaire du risque', tracking=True)
    date_identification = fields.Date(string="Date d'identification", default=fields.Date.context_today)
    date_derniere_revue = fields.Date(string='Date de dernière revue')
    date_prochaine_revue = fields.Date(string='Date de prochaine revue (semestrielle)')

    plan_ids = fields.One2many('resade.ethique.plan.continuite', 'risque_id', string='Plans de mitigation / continuité')
    nb_plans = fields.Integer(string='Nombre de plans liés', compute='_compute_nb_plans')

    statut = fields.Selection([
        ('actif', 'Actif'),
        ('maitrise', 'Maîtrisé'),
        ('clos', 'Clos'),
    ], string='Statut du risque', default='actif', tracking=True)

    @api.depends('incidence', 'occurrence')
    def _compute_criticite(self):
        for rec in self:
            rec.criticite = int(rec.incidence or 1) * int(rec.occurrence or 1)

    @api.depends('plan_ids')
    def _compute_nb_plans(self):
        for rec in self:
            rec.nb_plans = len(rec.plan_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.risque') or _('Nouveau')
        return super().create(vals_list)

    def action_marquer_maitrise(self):
        self.write({'statut': 'maitrise'})

    def action_cloturer(self):
        self.write({'statut': 'clos'})

    def action_reactiver(self):
        self.write({'statut': 'actif'})
