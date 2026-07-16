from odoo import models, fields, api


class WizardSeuilsMarche(models.TransientModel):
    """
    Wizard d'information sur les seuils de passation des marchés RESADE
    Carnet D Module 01 – P-CIP-02 : Mise à jour des seuils de passation
    Les seuils sont définis dans le Manuel RESADE Volume 2 et ne changent
    qu'après décision du Conseil d'Administration.
    """
    _name = 'wizard.seuils.marche'
    _description = 'Référentiel des seuils de passation RESADE (P-CIP-02)'

    # Seuils en lecture seule – conformes au Manuel RESADE Carnet D, B.6
    seuil_entente_directe = fields.Monetary(
        string='Entente directe / Gré à gré (P-PTM-01)',
        default=2_000_000, readonly=True, currency_field='currency_id'
    )
    seuil_consultation_min = fields.Monetary(
        string='Consultation restreinte – seuil min (P-PTM-02)',
        default=2_000_001, readonly=True, currency_field='currency_id'
    )
    seuil_consultation_max = fields.Monetary(
        string='Consultation restreinte – seuil max (P-PTM-02)',
        default=10_000_000, readonly=True, currency_field='currency_id'
    )
    seuil_aoo_min = fields.Monetary(
        string='Appel d\'offres ouvert – seuil min (P-PTM-03)',
        default=10_000_001, readonly=True, currency_field='currency_id'
    )
    seuil_aoo_max = fields.Monetary(
        string='Appel d\'offres ouvert – seuil max (P-PTM-03)',
        default=50_000_000, readonly=True, currency_field='currency_id'
    )
    seuil_aoo_majeur = fields.Monetary(
        string='AOO majeur + ANO bailleur – au-delà de (P-PTM-03)',
        default=50_000_000, readonly=True, currency_field='currency_id'
    )
    seuil_cam = fields.Monetary(
        string='Seuil de convocation CAM (P-CIP-01)',
        default=2_000_000, readonly=True, currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )
    note = fields.Text(
        string='Note',
        default=(
            "Seuils définis dans le Manuel de Procédures RESADE – Volume 2, "
            "Carnet D Module 01 (P-CIP-01 et P-CIP-02) – Version 2.0 – 2026.\n\n"
            "Toute mise à jour des seuils doit faire l'objet d'une décision du "
            "Conseil d'Administration et d'une révision du Manuel de Procédures."
        ),
        readonly=True
    )

    def action_fermer(self):
        return {'type': 'ir.actions.act_window_close'}
