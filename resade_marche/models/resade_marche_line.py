from odoo import models, fields, api


class ResadeMarcheLine(models.Model):
    _name = 'resade.marche.line'
    _description = 'Ligne de dépense / Lot du marché'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    marche_id = fields.Many2one(
        'resade.marche', string='Marché', ondelete='cascade', required=True
    )
    designation = fields.Char(string='Désignation', required=True)
    unite = fields.Char(string='Unité', default='Forfait')
    quantite = fields.Float(string='Quantité', default=1.0)
    prix_unitaire_estime = fields.Monetary(string='PU estimé', currency_field='currency_id')
    prix_unitaire_retenu = fields.Monetary(string='PU retenu', currency_field='currency_id')
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)
    montant_estime = fields.Monetary(
        string='Montant estimé', compute='_compute_montants', store=True, currency_field='currency_id'
    )
    montant_retenu = fields.Monetary(
        string='Montant retenu', compute='_compute_montants', store=True, currency_field='currency_id'
    )
    note = fields.Char(string='Observations')

    @api.depends('quantite', 'prix_unitaire_estime', 'prix_unitaire_retenu')
    def _compute_montants(self):
        for line in self:
            line.montant_estime = line.quantite * line.prix_unitaire_estime
            line.montant_retenu = line.quantite * line.prix_unitaire_retenu


class ResadeMarcheOffre(models.Model):
    """Offre reçue lors du dépouillement – Carnet D Module 02"""
    _name = 'resade.marche.offre'
    _description = "Offre reçue d'un fournisseur / prestataire"
    _order = 'rang_classement, id'

    marche_id = fields.Many2one(
        'resade.marche', string='Marché', ondelete='cascade', required=True
    )
    fournisseur_id = fields.Many2one(
        'resade.fournisseur', string='Fournisseur / Prestataire', required=True
    )
    date_reception = fields.Date(string='Date réception', default=fields.Date.today)
    note_technique = fields.Float(string='Note technique /100')
    montant_financier = fields.Monetary(string='Montant offre', currency_field='currency_id')
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)
    conforme = fields.Boolean(string='Offre conforme', default=True)
    motif_non_conformite = fields.Text(string='Motif non-conformité')
    rang_classement = fields.Integer(string='Rang classement', default=0)
    retenue = fields.Boolean(string='Offre retenue', default=False)
    note_analyse = fields.Text(string='Analyse')
    conflict_interet = fields.Boolean(string="Conflit d'intérêt déclaré", default=False)
    note_conflit = fields.Text(string='Nature du conflit')
    membre_cam_concerne = fields.Char(string='Membre CAM concerné')
    recuse = fields.Boolean(string='Membre récusé', default=False)
    delai_execution = fields.Integer(string='Délai d\'exécution proposé (jours)')
    note_soumission = fields.Text(string='Note de soumission du fournisseur')
    ip_soumission = fields.Char(string='IP de soumission', readonly=True)
    pj_offre = fields.Many2many('ir.attachment', 'offre_pj_rel', string='Documents de l\'offre')

    nom_fournisseur_tmp = fields.Char(string='Nom fournisseur (AOO)')
    email_fournisseur_tmp = fields.Char(string='Email fournisseur (AOO)')
