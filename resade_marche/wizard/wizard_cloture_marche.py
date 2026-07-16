from odoo import models, fields, api, exceptions


class WizardClotureMarche(models.TransientModel):
    """
    Wizard de clôture et archivage du dossier marché
    Carnet D Module 03 – P-DA-02 : Archivage des dossiers de passation
    Carnet E Module 03 : Clôture et archivage du dossier marché
    """
    _name = 'wizard.cloture.marche'
    _description = 'Clôture et archivage du dossier marché (P-DA-02)'

    marche_id = fields.Many2one('resade.marche', string='Dossier marché', readonly=True)
    ref_archivage_ged = fields.Char(
        string='Référence archivage GED',
        help='Référence du dossier dans le système GED (SharePoint / Drive) – P-DA-02',
        required=True
    )
    note_cloture = fields.Text(string='Note de clôture')
    checklist_pv_reception = fields.Boolean(string='PV de réception signé présent')
    checklist_facture = fields.Boolean(string='Facture certifiée (ASF) présente')
    checklist_preuve_paiement = fields.Boolean(string='Preuve de paiement présente')
    checklist_contrat = fields.Boolean(string='Contrat / BC signé présent')
    checklist_offres = fields.Boolean(string='Offres reçues archivées')
    checklist_pv_cam = fields.Boolean(string='PV CAM archivé (si applicable)')
    checklist_rapport_analyse = fields.Boolean(string="Rapport d'analyse archivé")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['marche_id'] = active_id
        return res

    def action_cloturer(self):
        self.ensure_one()
        marche = self.marche_id
        if marche.state not in ['paye', 'annule']:
            raise exceptions.UserError(
                "Le dossier doit être dans l'état 'Payé' ou 'Annulé' "
                "avant la clôture définitive (Carnet E Module 03)."
            )
        manquants = []
        if not self.checklist_pv_reception and marche.state == 'paye':
            manquants.append("PV de réception signé")
        if not self.checklist_facture and marche.state == 'paye':
            manquants.append("Facture certifiée / ASF")
        if not self.checklist_preuve_paiement and marche.state == 'paye':
            manquants.append("Preuve de paiement")
        if manquants:
            raise exceptions.UserError(
                "Documents manquants pour clôturer :\n- " + "\n- ".join(manquants)
            )
        marche.write({
            'dossier_cloture': True,
            'date_cloture': fields.Date.today(),
            'ref_archivage': self.ref_archivage_ged,
            'note_cloture': self.note_cloture,
            'cloture_par': self.env.uid,
            'cloture_date': fields.Datetime.now(),
        })
        marche.message_post(
            body=f"🗂️ Dossier clôturé et archivé (GED : {self.ref_archivage_ged}) – P-DA-02."
        )
        return {'type': 'ir.actions.act_window_close'}
