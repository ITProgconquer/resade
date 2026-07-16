# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeTauxPerdiem(models.Model):
    _name = 'resade.taux.perdiem'
    _description = 'Grille des taux de per diem et indemnités – RESADE-F-GMD-01-05'
    _order = 'zone, annee desc'

    name = fields.Char(
        string='Libellé', required=True,
        compute='_compute_name', store=True
    )
    zone = fields.Selection([
        ('ouaga',        'Ouagadougou (même jour)'),
        ('interieur_bf', 'Intérieur BF (nuitée)'),
        ('cedeao',       'Région CEDEAO / sous-saharienne'),
        ('international','International (hors CEDEAO)'),
    ], string='Zone / Type', required=True)

    annee = fields.Integer(
        string='Année de référence',
        default=lambda self: fields.Date.today().year,
        required=True
    )
    perdiem_journalier = fields.Monetary(
        string='Per diem journalier (FCFA)',
        currency_field='currency_id'
    )
    plafond_hebergement = fields.Monetary(
        string='Plafond hébergement / nuit (FCFA)',
        currency_field='currency_id'
    )
    indemnite_deplacement = fields.Monetary(
        string='Indemnité de déplacement local (FCFA)',
        currency_field='currency_id'
    )
    taux_carburant_km = fields.Float(
        string='Taux carburant (FCFA/km)',
        help='Taux de remboursement carburant par kilomètre'
    )
    reference_pnud = fields.Char(
        string='Référence PNUD/DSA',
        help='Référence DSA PNUD si applicable (missions internationales – Manuel NEX 2022 §6.2.3)'
    )
    note = fields.Text(string='Notes / Conditions particulières')
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('zone', 'annee')
    def _compute_name(self):
        zone_labels = dict(self._fields['zone'].selection)
        for rec in self:
            rec.name = '%s – %s' % (zone_labels.get(rec.zone, ''), rec.annee)
