# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeTresorerieConversionDevise(models.Model):
    """
    Décision de conversion des fonds en devise étrangère (USD/EUR) reçus
    d'un bailleur — P-TB-02 B.4 étape 4 : « Dès réception d'un financement
    en devise, le CAF évalue la conversion BCEAO ; décide avec le DE du
    calendrier optimal de conversion pour limiter le risque de change. »
    """
    _name = 'resade.tresorerie.conversion.devise'
    _description = 'Décision de conversion de devise – P-TB-02'
    _inherit = ['mail.thread']
    _order = 'date_reception desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau', copy=False)
    journal_id = fields.Many2one(
        'account.journal', string='Compte en devise', required=True,
        domain=[('resade_devise_etrangere', '=', True)]
    )
    devise_id = fields.Many2one('res.currency', string='Devise reçue', required=True)
    projet_bailleur_id = fields.Many2one('resade.budget.projet.bailleur', string='Projet bailleur concerné')

    date_reception = fields.Date(string='Date de réception des fonds', default=fields.Date.today, required=True)
    montant_devise = fields.Float(string='Montant reçu (en devise)', required=True)
    taux_bceao_reference = fields.Float(
        string='Taux BCEAO de référence à la réception',
        help="Taux de change officiel BCEAO constaté à la date de réception."
    )
    montant_xof_estime = fields.Monetary(
        string='Contre-valeur FCFA estimée', currency_field='currency_xof_id',
        compute='_compute_montant_xof', store=True
    )
    currency_xof_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
    )

    decision = fields.Selection([
        ('conversion_immediate', 'Conversion immédiate'),
        ('conversion_differee', 'Conversion différée (attente meilleur taux)'),
        ('conservation_devise', 'Conservation en devise (dépenses prévues en devise)'),
    ], string='Décision de conversion')
    justification = fields.Text(string='Justification de la décision (risque de change)')
    caf_id = fields.Many2one('hr.employee', string='Proposé par (CAF)')
    de_id = fields.Many2one('hr.employee', string='Décidé avec (DE)')
    date_decision = fields.Date(string='Date de la décision')
    date_conversion_effective = fields.Date(string='Date de conversion effective (si applicable)')
    taux_conversion_effectif = fields.Float(string='Taux de conversion effectivement appliqué')

    statut = fields.Selection([
        ('a_decider', 'À décider'),
        ('decide', 'Décision actée'),
        ('converti', 'Conversion effectuée'),
    ], string='Statut', default='a_decider', tracking=True)

    @api.depends('montant_devise', 'taux_bceao_reference')
    def _compute_montant_xof(self):
        for rec in self:
            rec.montant_xof_estime = (rec.montant_devise or 0.0) * (rec.taux_bceao_reference or 0.0)

    def action_acter_decision(self):
        self.ensure_one()
        self.write({
            'statut': 'decide',
            'date_decision': fields.Date.today(),
            'de_id': self.de_id.id or self.env.user.employee_id.id,
        })
        self.message_post(body=_("Décision de conversion actée conjointement CAF + DE : %s.") % (
            dict(self._fields['decision'].selection).get(self.decision, '')
        ))

    def action_marquer_converti(self):
        self.ensure_one()
        self.write({'statut': 'converti', 'date_conversion_effective': fields.Date.today()})
        self.message_post(body=_("Conversion effectuée au taux de %.4f.") % (self.taux_conversion_effectif or 0.0))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = 'DEVISE-%s' % fields.Date.today().strftime('%Y%m%d')
        return super().create(vals_list)
