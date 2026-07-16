# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAnalyticLineMission(models.Model):
    """Ajout du lien vers la mission sur les écritures analytiques GFIC"""
    _inherit = 'account.analytic.line'

    resade_mission_id = fields.Many2one(
        'resade.mission',
        string='Ordre de Mission',
        readonly=True,
        ondelete='set null',
        help='Mission RESADE à l\'origine de cette écriture analytique (P-GMD-03 – GFIC)'
    )
