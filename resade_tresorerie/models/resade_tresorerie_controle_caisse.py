# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeTresorerieControleCaisse(models.Model):
    """
    Contrôle physique hebdomadaire de la caisse par le CAF — P-TB-01 B.4
    étape 4 / formulaire RESADE-F-TB-01-02.

    KPI associé : taux de contrôles hebdomadaires réalisés (cible ≥ 90%),
    écart maximum constaté (cible 0 FCFA).
    """
    _name = 'resade.tresorerie.controle.caisse'
    _description = 'Contrôle physique hebdomadaire de caisse – RESADE-F-TB-01-02'
    _inherit = ['mail.thread']
    _order = 'date_controle desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau', copy=False)
    journal_id = fields.Many2one(
        'account.journal', string='Caisse contrôlée', required=True,
        domain=[('type', '=', 'cash')]
    )
    currency_id = fields.Many2one(related='journal_id.currency_id', store=True)
    date_controle = fields.Date(string='Date du contrôle', default=fields.Date.today, required=True)
    caf_controleur_id = fields.Many2one('hr.employee', string='CAF contrôleur', required=True)

    solde_journal = fields.Monetary(
        string='Solde du journal de caisse (Odoo)', currency_field='currency_id',
        compute='_compute_solde_journal', store=True
    )
    espece_physique_comptee = fields.Monetary(
        string='Espèces physiques comptées', currency_field='currency_id', required=True
    )
    ecart = fields.Monetary(
        string='Écart constaté', compute='_compute_ecart', store=True, currency_field='currency_id'
    )
    observations = fields.Text(string='Observations / constat')

    @api.depends('journal_id')
    def _compute_solde_journal(self):
        for rec in self:
            rec.solde_journal = rec.journal_id.resade_solde_comptable if rec.journal_id else 0.0

    @api.depends('espece_physique_comptee', 'solde_journal')
    def _compute_ecart(self):
        for rec in self:
            rec.ecart = (rec.espece_physique_comptee or 0.0) - (rec.solde_journal or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.tresorerie.controle.caisse')
                    or 'CTRL-CAISSE-001'
                )
        recs = super().create(vals_list)
        for rec in recs:
            if abs(rec.ecart) > 0.01:
                rec.message_post(body=_(
                    "⚠️ Écart constaté lors du contrôle physique de caisse : %s. "
                    "À documenter et transmettre au DE (P-TB-01 B.11 – risque de détournement)."
                ) % '{:,.0f}'.format(rec.ecart))
        return recs

    @api.model
    def _cron_alerte_controle_manquant(self):
        """Alerte si aucun contrôle n'a été réalisé depuis plus de 7 jours sur
        une caisse active — appuie le KPI 'Taux de contrôles hebdomadaires'."""
        caisses = self.env['account.journal'].search([('type', '=', 'cash')])
        for caisse in caisses:
            dernier = self.search([('journal_id', '=', caisse.id)], order='date_controle desc', limit=1)
            if not dernier or (fields.Date.today() - dernier.date_controle).days > 7:
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('account.journal'),
                    'res_id': caisse.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('Contrôle hebdomadaire de caisse en retard'),
                    'note': _(
                        "Aucun contrôle physique de la caisse « %s » depuis plus de "
                        "7 jours – P-TB-01 exige un contrôle hebdomadaire."
                    ) % caisse.name,
                    'user_id': self.env.user.id,
                })
