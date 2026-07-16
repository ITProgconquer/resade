# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeTresorerieCaisseDecaissement(models.Model):
    """
    Décaissement de petite caisse — P-TB-01, étapes B.4.1 et règles B.3.

    Règles réglementaires appliquées automatiquement :
      - Aucun décaissement sans pièce justificative signée (B.3) ;
      - Décaissement > plafond unitaire (50 000 FCFA) → INTERDIT, doit passer
        par virement bancaire ;
      - Décaissement > seuil DE (20 000 FCFA) → autorisation DE obligatoire
        en plus du CAF ;
      - Le solde de caisse ne peut jamais devenir négatif (B.3) ;
      - Toute opération est enregistrée immédiatement (B.4 étape 3) — ici,
        directement comme écriture réelle dans le journal de caisse Odoo.
    """
    _name = 'resade.tresorerie.caisse.decaissement'
    _description = 'Décaissement de petite caisse – P-TB-01'
    _inherit = ['mail.thread']
    _order = 'date_demande desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau', copy=False)
    journal_id = fields.Many2one(
        'account.journal', string='Caisse', required=True,
        domain=[('type', '=', 'cash')]
    )
    currency_id = fields.Many2one(related='journal_id.currency_id', store=True)
    date_demande = fields.Date(string='Date de la demande', default=fields.Date.today, required=True)
    beneficiaire_id = fields.Many2one('res.partner', string='Bénéficiaire', required=True)
    motif = fields.Char(string='Motif du décaissement', required=True)
    montant = fields.Monetary(string='Montant demandé', currency_field='currency_id', required=True)

    piece_justificative = fields.Binary(string='Pièce justificative (reçu, facture, OM)', attachment=True)
    piece_justificative_nom = fields.Char(string='Nom du fichier')

    # Seuils recopiés du journal au moment de la demande, pour traçabilité
    plafond_unitaire = fields.Monetary(
        related='journal_id.resade_plafond_decaissement_unitaire', string='Plafond unitaire autorisé'
    )
    seuil_autorisation_de = fields.Monetary(
        related='journal_id.resade_seuil_autorisation_de', string='Seuil autorisation DE'
    )
    autorisation_de_requise = fields.Boolean(
        string='Autorisation DE requise', compute='_compute_autorisation_de_requise', store=True
    )

    statut = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('autorise_caf', 'Autorisé CAF'),
        ('autorise_de', 'Autorisé DE'),
        ('decaisse', 'Décaissé (comptabilisé)'),
        ('rejete', 'Rejeté'),
    ], string='Statut', default='brouillon', tracking=True)

    caf_id = fields.Many2one('hr.employee', string='Autorisé par (CAF)')
    de_id = fields.Many2one('hr.employee', string='Autorisé par (DE)')
    date_decaissement = fields.Date(string='Date effective du décaissement')
    account_move_id = fields.Many2one('account.move', string='Écriture comptable (Odoo)', readonly=True, copy=False)
    motif_rejet = fields.Char(string='Motif de rejet')

    @api.depends('montant', 'seuil_autorisation_de')
    def _compute_autorisation_de_requise(self):
        for rec in self:
            rec.autorisation_de_requise = rec.montant > (rec.seuil_autorisation_de or 0.0)

    @api.constrains('montant', 'journal_id')
    def _check_plafond_unitaire(self):
        for rec in self:
            if rec.journal_id and rec.montant > (rec.journal_id.resade_plafond_decaissement_unitaire or 0.0):
                raise UserError(_(
                    "Montant refusé : %s dépasse le plafond de décaissement unitaire en "
                    "caisse (%s). Ce paiement doit obligatoirement passer par virement "
                    "bancaire – P-TB-01 B.3."
                ) % ('{:,.0f}'.format(rec.montant), '{:,.0f}'.format(rec.journal_id.resade_plafond_decaissement_unitaire)))

    def action_demander_autorisation_caf(self):
        self.ensure_one()
        if not self.piece_justificative:
            raise UserError(_(
                "Aucun décaissement de caisse sans pièce justificative signée par le "
                "bénéficiaire – P-TB-01 B.3."
            ))
        self._check_solde_disponible()
        self.write({'statut': 'autorise_caf', 'caf_id': self.env.user.employee_id.id})
        self.message_post(body=_("Décaissement autorisé par le CAF."))
        if self.autorisation_de_requise:
            self.message_post(body=_(
                "Montant > %s : autorisation du Directeur Exécutif requise avant décaissement."
            ) % '{:,.0f}'.format(self.seuil_autorisation_de))

    def action_autoriser_de(self):
        self.ensure_one()
        if self.statut != 'autorise_caf':
            raise UserError(_("L'autorisation du CAF est requise avant celle du DE."))
        self.write({'statut': 'autorise_de', 'de_id': self.env.user.employee_id.id})
        self.message_post(body=_("Décaissement autorisé par le Directeur Exécutif."))

    def action_rejeter(self):
        self.ensure_one()
        if not self.motif_rejet:
            raise UserError(_("Renseignez le motif de rejet."))
        self.write({'statut': 'rejete'})
        self.message_post(body=_("Décaissement rejeté : %s") % self.motif_rejet)

    def _check_solde_disponible(self):
        """P-TB-01 B.3 : interdiction de caisse négative."""
        self.ensure_one()
        solde = self.journal_id.resade_solde_comptable
        if self.montant > solde:
            raise UserError(_(
                "Décaissement refusé : le solde de caisse disponible (%s) est "
                "insuffisant pour ce montant (%s). Le solde de caisse ne peut "
                "jamais devenir négatif – P-TB-01 B.3."
            ) % ('{:,.0f}'.format(solde), '{:,.0f}'.format(self.montant)))

    def action_decaisser(self):
        """
        Enregistrement immédiat de l'opération (P-TB-01 B.4 étape 1/3) :
        génère l'écriture réelle dans le journal de caisse Odoo.
        """
        self.ensure_one()
        statut_requis = 'autorise_de' if self.autorisation_de_requise else 'autorise_caf'
        if self.statut != statut_requis:
            raise UserError(_(
                "Autorisation(s) manquante(s) avant décaissement (CAF%s requise)."
            ) % (' + DE' if self.autorisation_de_requise else ''))
        self._check_solde_disponible()

        compte_charge = self.env['account.account'].search([
            ('account_type', '=', 'expense'), ('company_ids', 'in', self.env.company.id)
        ], limit=1)
        if not compte_charge:
            raise UserError(_("Aucun compte de charge configuré dans la Comptabilité Odoo."))

        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date_demande,
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'name': self.motif,
                    'account_id': compte_charge.id,
                    'partner_id': self.beneficiaire_id.id,
                    'debit': self.montant,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': self.motif,
                    'account_id': self.journal_id.default_account_id.id,
                    'partner_id': self.beneficiaire_id.id,
                    'debit': 0.0,
                    'credit': self.montant,
                }),
            ],
        })
        move.action_post()
        self.write({
            'statut': 'decaisse',
            'account_move_id': move.id,
            'date_decaissement': fields.Date.today(),
        })
        self.message_post(body=_("Décaissement enregistré – écriture Odoo %s.") % move.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.tresorerie.caisse.decaissement')
                    or 'DEC-CAISSE-001'
                )
        return super().create(vals_list)
