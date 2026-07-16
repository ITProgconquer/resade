# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeTresorerieReconstitution(models.Model):
    """
    Bordereau mensuel de reconstitution de la petite caisse — P-TB-01 B.4
    étapes 5-6 / formulaire RESADE-F-TB-01-03.

    Workflow réel du manuel : AC prépare → CAF vérifie → DE autorise le
    virement de reconstitution → AC enregistre le virement (ici : écriture
    Odoo réelle générée automatiquement).
    """
    _name = 'resade.tresorerie.reconstitution'
    _description = 'Bordereau mensuel de reconstitution de caisse – RESADE-F-TB-01-03'
    _inherit = ['mail.thread']
    _order = 'periode desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau', copy=False)
    journal_caisse_id = fields.Many2one(
        'account.journal', string='Caisse à reconstituer', required=True,
        domain=[('type', '=', 'cash')]
    )
    journal_banque_id = fields.Many2one(
        'account.journal', string='Compte bancaire source du virement', required=True,
        domain=[('type', '=', 'bank')]
    )
    currency_id = fields.Many2one(related='journal_caisse_id.currency_id', store=True)
    periode = fields.Date(string='Mois concerné', required=True, default=fields.Date.today)

    decaissement_ids = fields.Many2many(
        'resade.tresorerie.caisse.decaissement', 'resade_treso_reconst_decaiss_rel',
        'reconstitution_id', 'decaissement_id',
        string='Décaissements du mois inclus',
        domain=[('statut', '=', 'decaisse')]
    )
    montant_total_depenses = fields.Monetary(
        string='Total des dépenses du mois', compute='_compute_montant_total',
        store=True, currency_field='currency_id'
    )
    montant_virement = fields.Monetary(
        string='Montant du virement de reconstitution', currency_field='currency_id',
        help="Égal, par défaut, au total des dépenses justifiées du mois."
    )

    statut = fields.Selection([
        ('brouillon', 'Préparation (AC)'),
        ('verifie_caf', 'Vérifié CAF'),
        ('autorise_de', 'Autorisé DE'),
        ('reconstitue', 'Caisse reconstituée'),
    ], string='Statut', default='brouillon', tracking=True)

    ac_id = fields.Many2one('hr.employee', string='Préparé par (AC)')
    caf_id = fields.Many2one('hr.employee', string='Vérifié par (CAF)')
    de_id = fields.Many2one('hr.employee', string='Autorisé par (DE)')
    date_virement = fields.Date(string='Date effective du virement')
    account_move_id = fields.Many2one('account.move', string='Écriture comptable (Odoo)', readonly=True, copy=False)

    @api.depends('decaissement_ids.montant')
    def _compute_montant_total(self):
        for rec in self:
            rec.montant_total_depenses = sum(rec.decaissement_ids.mapped('montant'))

    def action_soumettre_caf(self):
        self.ensure_one()
        if not self.decaissement_ids:
            raise UserError(_("Aucune dépense justifiée n'est rattachée à ce bordereau."))
        if not self.montant_virement:
            self.montant_virement = self.montant_total_depenses
        self.write({'statut': 'verifie_caf', 'caf_id': self.env.user.employee_id.id})
        self.message_post(body=_("Bordereau de reconstitution vérifié par le CAF, transmis au DE."))

    def action_autoriser_de(self):
        self.ensure_one()
        if self.statut != 'verifie_caf':
            raise UserError(_("La vérification CAF est requise avant l'autorisation DE."))
        self.write({'statut': 'autorise_de', 'de_id': self.env.user.employee_id.id})
        self.message_post(body=_("Virement de reconstitution autorisé par le Directeur Exécutif."))

    def action_enregistrer_virement(self):
        """Génère l'écriture réelle du virement banque -> caisse (P-TB-01 B.4
        étape 6) et marque la caisse comme reconstituée."""
        self.ensure_one()
        if self.statut != 'autorise_de':
            raise UserError(_("L'autorisation du DE est requise avant d'enregistrer le virement."))

        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': self.journal_banque_id.id,
            'date': fields.Date.today(),
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'name': _('Reconstitution caisse %s') % self.journal_caisse_id.name,
                    'account_id': self.journal_caisse_id.default_account_id.id,
                    'debit': self.montant_virement,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': _('Virement de reconstitution'),
                    'account_id': self.journal_banque_id.default_account_id.id,
                    'debit': 0.0,
                    'credit': self.montant_virement,
                }),
            ],
        })
        move.action_post()
        self.write({
            'statut': 'reconstitue',
            'account_move_id': move.id,
            'date_virement': fields.Date.today(),
        })
        self.message_post(body=_("Caisse reconstituée – écriture Odoo %s.") % move.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.tresorerie.reconstitution')
                    or 'RECONST-CAISSE-001'
                )
                vals.setdefault('ac_id', self.env.user.employee_id.id)
        return super().create(vals_list)
