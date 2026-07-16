# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeEthiquePlanContinuite(models.Model):
    """
    Processus P-GRI-02 : Plans de mitigation et de continuité des activités
    Manuel RESADE - Carnet J - Module 03 : Gestion des risques institutionnels

    Pour chaque risque du registre (P-GRI-01), définit les mesures préventives
    et correctives, ainsi que les plans de continuité assurant la résilience
    opérationnelle de RESADE en cas d'événement perturbateur majeur.

    Circuit :
    1. Élaboration du plan                 -> elabore
    2. Validation (DE / Comité pilotage)   -> valide
    3. Test du plan (si continuité)        -> teste
    4. Plan actif / en application         -> actif
    """
    _name = 'resade.ethique.plan.continuite'
    _description = "Plan de mitigation / continuité (P-GRI-02)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Réf. plan', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    risque_id = fields.Many2one('resade.ethique.risque', string='Risque associé', required=True, tracking=True)

    type_plan = fields.Selection([
        ('mitigation', 'Plan de mitigation'),
        ('continuite', 'Plan de continuité des activités'),
    ], string='Type de plan', required=True, tracking=True)

    mesures_preventives = fields.Text(string='Mesures préventives')
    mesures_correctives = fields.Text(string='Mesures correctives')

    responsable_id = fields.Many2one('hr.employee', string='Responsable de mise en œuvre', tracking=True)

    date_elaboration = fields.Date(string='Date d\'élaboration', default=fields.Date.context_today)
    date_validation = fields.Date(string='Date de validation')
    date_test = fields.Date(string='Date de test (si applicable)')
    resultat_test = fields.Text(string='Résultat du test')
    date_prochaine_revue = fields.Date(string='Date de prochaine revue')

    state = fields.Selection([
        ('elabore', 'Élaboré'),
        ('valide', 'Validé'),
        ('teste', 'Testé'),
        ('actif', 'Actif'),
    ], string='Statut', default='elabore', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.plan.continuite') or _('Nouveau')
        return super().create(vals_list)

    def action_valider(self):
        self.write({'state': 'valide', 'date_validation': fields.Date.context_today(self)})

    def action_marquer_teste(self):
        self.write({'state': 'teste', 'date_test': fields.Date.context_today(self)})

    def action_activer(self):
        self.write({'state': 'actif'})
