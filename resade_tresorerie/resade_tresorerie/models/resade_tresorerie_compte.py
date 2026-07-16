# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountJournalResade(models.Model):
    """
    Extension du journal Odoo (account.journal) — PAS de réinvention de la
    gestion bancaire : on s'appuie sur les journaux banque/caisse natifs
    d'Odoo Accounting Enterprise (relevés, synchronisation bancaire,
    rapprochement). On ajoute uniquement les attributs institutionnels
    RESADE nécessaires à la traçabilité bailleurs et au contrôle interne.
    """
    _inherit = 'account.journal'

    resade_type_fonds = fields.Selection([
        ('propre', 'Fonds propres RESADE'),
        ('restreint', 'Fonds restreint (projet bailleur)'),
        ('caisse_menue', 'Caisse menue dépense'),
    ], string='Type de fonds (RESADE)',
        help="Nature des fonds transitant par ce compte — exigence de "
             "traçabilité des fonds restreints vis-à-vis des bailleurs "
             "(Carnet F – P-TB-02 B.3).")

    resade_projet_bailleur_id = fields.Many2one(
        'resade.budget.projet.bailleur', string='Projet bailleur rattaché',
        help="Si ce compte est dédié à un projet bailleur (fonds restreint), "
             "précisez le projet. Laisser vide pour un compte de fonds propres."
    )

    resade_signataire_1_id = fields.Many2one(
        'hr.employee', string='1er signataire autorisé',
        help='Généralement le Directeur Exécutif (DE).'
    )
    resade_signataire_2_id = fields.Many2one(
        'hr.employee', string='2e signataire autorisé',
        help='Généralement le Chargé Administratif et Financier (CAF).'
    )
    resade_double_signature_obligatoire = fields.Boolean(
        string='Double signature obligatoire sur ce compte', default=True
    )

    resade_plafond_caisse = fields.Monetary(
        string='Plafond de caisse (si caisse menue)',
        currency_field='currency_id', default=150000,
        help="P-TB-01 B.3 : plafond permanent de la petite caisse. "
             "Valeur réglementaire RESADE : 150 000 FCFA."
    )
    resade_plafond_decaissement_unitaire = fields.Monetary(
        string='Plafond par décaissement (caisse)',
        currency_field='currency_id', default=50000,
        help="P-TB-01 B.3 : au-delà de ce montant par opération, le paiement "
             "doit obligatoirement passer par virement bancaire, pas par la caisse. "
             "Valeur réglementaire RESADE : 50 000 FCFA."
    )
    resade_seuil_autorisation_de = fields.Monetary(
        string='Seuil déclenchant autorisation DE',
        currency_field='currency_id', default=20000,
        help="P-TB-01 B.4 étape 1 : au-delà de ce montant, l'autorisation du "
             "Directeur Exécutif est requise en plus de celle du CAF. "
             "Valeur réglementaire RESADE : 20 000 FCFA."
    )
    resade_seuil_reconstitution = fields.Monetary(
        string='Seuil déclenchant la reconstitution',
        currency_field='currency_id', default=30000,
        help="P-TB-01 B.11 risque 1 : en-dessous de ce solde, la reconstitution "
             "de la caisse doit être déclenchée. Valeur réglementaire RESADE : 30 000 FCFA."
    )
    resade_devise_etrangere = fields.Boolean(
        string='Compte en devise étrangère (USD/EUR)',
        help="P-TB-02 B.3 : à cocher pour un compte en devise, afin d'activer "
             "le suivi des décisions de conversion BCEAO."
    )

    resade_solde_comptable = fields.Monetary(
        string='Solde comptable actuel', compute='_compute_resade_solde',
        currency_field='currency_id'
    )

    @api.depends('default_account_id')
    def _compute_resade_solde(self):
        """Solde réel du compte, calculé directement depuis les écritures
        comptables Odoo (account.move.line) — jamais de ressaisie manuelle."""
        for journal in self:
            solde = 0.0
            if journal.default_account_id:
                lines = self.env['account.move.line'].search([
                    ('account_id', '=', journal.default_account_id.id),
                    ('parent_state', '=', 'posted'),
                    ('company_id', '=', journal.company_id.id),
                ])
                solde = sum(lines.mapped('balance'))
            journal.resade_solde_comptable = solde
