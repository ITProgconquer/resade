from odoo import _, api, fields, models
from odoo.exceptions import UserError
class PosPayment(models.Model):
    _inherit = "pos.payment"

    montantcor = fields.Float('Montant corrigé')
    montantsav = fields.Float('Montant sauvegardé')
    def corrigermontant(self):
        if self.montantcor==0:
           raise UserError("Revoir le montant") 
        req1 = "UPDATE pos_payment SET montantsav ="+str(self.amount)+" WHERE id="+str(self.id)+""
        req2 = "UPDATE pos_payment SET amount ="+str(self.montantcor)+" WHERE id="+str(self.id)+""
        self.env.cr.execute(req1)
        self.env.cr.execute(req2)
