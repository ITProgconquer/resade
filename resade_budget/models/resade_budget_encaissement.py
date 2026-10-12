from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

class ResadeBudgetEncaissement(models.Model):
    """
    Encaissement lié à une ligne budgétaire de type RECETTE.
    Pendant du décaissement : quand RESADE reçoit de l'argent (cotisation,
    subvention, don...), on l'enregistre ici et ça met à jour le montant_realise
    de la ligne budgétaire ET ça génère l'écriture comptable.
    """
    _name = 'resade.budget.encaissement'
    _description = 'Encaissement sur ligne budgétaire de recette'
    _inherit = ['mail.thread']
    _order = 'date_encaissement desc'

    name = fields.Char(string='Référence', readonly=True, default='Nouveau')
    date_encaissement = fields.Date(string='Date d\'encaissement', default=fields.Date.today)
    ligne_budgetaire_id = fields.Many2one(
        'resade.budget.ligne', 
        string='Ligne budgétaire (recette)',
        domain="[('rubrique', '=', 'ressources'), ('budget_annuel_id.state', 'in', ['approuve_ca', 'diffuse'])]",
        required=True
    )
    montant = fields.Monetary(string='Montant encaissé', required=True)
    journal_id = fields.Many2one(
        'account.journal', string='Journal de trésorerie', required=True,
        help='Journal bancaire ou de caisse où l\'argent est déposé'
    )
    description = fields.Char(string='Description')
    account_move_id = fields.Many2one('account.move', string='Écriture comptable', readonly=True)
    currency_id = fields.Many2one(related='ligne_budgetaire_id.currency_id')
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('encaisse', 'Encaissé'),
    ], default='brouillon', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.budget.encaissement') or 'ENC-001'
        return super().create(vals_list)

    def action_encaisser(self):
        """Enregistre l'encaissement, génère l'écriture comptable et met à jour la ligne."""
        for rec in self:
            if not rec.ligne_budgetaire_id.account_id:
                raise UserError(_(
                    "La ligne budgétaire « %s » n'a pas de compte comptable configuré."
                ) % rec.ligne_budgetaire_id.name)

            # Générer l'écriture comptable
            move = self.env['account.move'].sudo().create({
                'move_type': 'entry',
                'journal_id': rec.journal_id.id,
                'date': rec.date_encaissement,
                'ref': rec.name,
                'line_ids': [
                    (0, 0, {
                        'name': rec.description or rec.name,
                        'account_id': rec.journal_id.default_account_id.id,  # Banque/Caisse
                        'debit': rec.montant,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': rec.description or rec.name,
                        'account_id': rec.ligne_budgetaire_id.account_id.id,  # Compte de recette
                        'debit': 0.0,
                        'credit': rec.montant,
                    }),
                ],
            })
            move.action_post()

            # Mettre à jour la ligne budgétaire
            rec.ligne_budgetaire_id.constater_encaissement(rec.montant)

            rec.write({
                'state': 'encaisse',
                'account_move_id': move.id,
            })