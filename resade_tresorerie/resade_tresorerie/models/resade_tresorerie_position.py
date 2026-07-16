# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeTresoreriePosition(models.Model):
    """
    Position de trésorerie RESADE – Carnet C, section Trésorerie et Banque.

    Photo, à une date donnée, du solde de chaque compte bancaire / caisse
    (account.journal de type bank/cash), calculée à partir des écritures
    comptables réelles d'Odoo Accounting Enterprise (account.move.line).

    Ne remplace pas le rapprochement bancaire natif : c'est une couche de
    lecture/pilotage institutionnel au-dessus.
    """
    _name = 'resade.tresorerie.position'
    _description = 'Position de Trésorerie RESADE (snapshot bancaire)'
    _inherit = ['mail.thread']
    _order = 'date_generation desc'

    name = fields.Char(string='Référence', required=True, readonly=True,
                        default=lambda self: _('Nouveau'), copy=False)
    date_generation = fields.Datetime(
        string='Date de génération', default=fields.Datetime.now, readonly=True
    )
    genere_par = fields.Many2one('res.users', string='Généré par', readonly=True)

    ligne_ids = fields.One2many(
        'resade.tresorerie.position.ligne', 'position_id', string='Comptes bancaires / caisses'
    )
    nb_comptes = fields.Integer(string='Nb comptes', compute='_compute_totaux', store=True)
    total_disponible = fields.Monetary(
        string='Trésorerie disponible totale', compute='_compute_totaux', store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    note = fields.Text(string='Observations / analyse CAF')

    @api.depends('ligne_ids.solde')
    def _compute_totaux(self):
        for rec in self:
            rec.nb_comptes = len(rec.ligne_ids)
            rec.total_disponible = sum(rec.ligne_ids.mapped('solde'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resade.tresorerie.position'
                ) or _('Nouveau')
        return super().create(vals_list)

    def action_generer(self):
        """Recalcule les soldes de tous les journaux bancaires/caisses de la société,
        à partir des écritures comptables Odoo réelles (account.move.line postées)."""
        for rec in self:
            rec.ligne_ids.unlink()
            journaux = self.env['account.journal'].search([
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', self.env.company.id),
            ])
            lignes_vals = []
            for journal in journaux:
                account = journal.default_account_id
                solde = 0.0
                if account:
                    lines = self.env['account.move.line'].search([
                        ('account_id', '=', account.id),
                        ('parent_state', '=', 'posted'),
                    ])
                    solde = sum(lines.mapped('balance'))
                lignes_vals.append((0, 0, {
                    'journal_id': journal.id,
                    'compte_id': account.id if account else False,
                    'solde': solde,
                }))
            rec.write({
                'ligne_ids': lignes_vals,
                'date_generation': fields.Datetime.now(),
                'genere_par': self.env.uid,
            })
            rec.message_post(body=_(
                "📊 Position de trésorerie régénérée – %s compte(s), disponible total : %s %s"
            ) % (rec.nb_comptes, '{:,.0f}'.format(rec.total_disponible), rec.currency_id.name or ''))


class ResadeTresoreriePositionLigne(models.Model):
    _name = 'resade.tresorerie.position.ligne'
    _description = 'Ligne de Position de Trésorerie (par compte bancaire/caisse)'
    _order = 'journal_id'

    position_id = fields.Many2one(
        'resade.tresorerie.position', string='Position', ondelete='cascade', required=True
    )
    journal_id = fields.Many2one('account.journal', string='Journal bancaire/caisse', required=True)
    compte_id = fields.Many2one('account.account', string='Compte comptable lié')
    solde = fields.Monetary(string='Solde (comptabilité)', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='position_id.currency_id', string='Devise'
    )
