# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeTresoreriePrevision(models.Model):
    """
    Prévisionnel de décaissements RESADE – Carnet C, section Trésorerie.

    Agrège automatiquement, à date de génération, tous les décaissements
    engagés (double signature obtenue ou dossier complet) mais pas encore
    exécutés/comptabilisés dans Odoo Accounting, issus de :
      - resade.marche.paiement (paiements fournisseurs)
      - resade.marche.honoraires (paiements honoraires consultants)

    Objectif : donner au CAF une visibilité sur le besoin de trésorerie à
    court terme, en complément de la Position de trésorerie (soldes réels).
    """
    _name = 'resade.tresorerie.prevision'
    _description = 'Prévisionnel de Décaissements RESADE'
    _inherit = ['mail.thread']
    _order = 'date_generation desc'

    name = fields.Char(string='Référence', required=True, readonly=True,
                        default=lambda self: _('Nouveau'), copy=False)
    date_generation = fields.Datetime(
        string='Date de génération', default=fields.Datetime.now, readonly=True
    )
    genere_par = fields.Many2one('res.users', string='Généré par', readonly=True)

    ligne_ids = fields.One2many(
        'resade.tresorerie.prevision.ligne', 'prevision_id', string='Décaissements prévus'
    )
    nb_lignes = fields.Integer(string='Nb décaissements prévus', compute='_compute_totaux', store=True)
    total_previsionnel = fields.Monetary(
        string='Total prévisionnel à décaisser', compute='_compute_totaux', store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    note = fields.Text(string='Analyse / mesures proposées (CAF)')

    @api.depends('ligne_ids.montant')
    def _compute_totaux(self):
        for rec in self:
            rec.nb_lignes = len(rec.ligne_ids)
            rec.total_previsionnel = sum(rec.ligne_ids.mapped('montant'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resade.tresorerie.prevision'
                ) or _('Nouveau')
        return super().create(vals_list)

    def action_generer(self):
        """Recalcule le prévisionnel à partir des dossiers de paiement marché
        (fournisseurs + honoraires consultants) pas encore comptabilisés."""
        for rec in self:
            rec.ligne_ids.unlink()
            lignes_vals = []

            Paiement = self.env['resade.marche.paiement']
            paiements = Paiement.search([
                ('statut', 'in', ('complet', 'signe')),
            ])
            for p in paiements:
                lignes_vals.append((0, 0, {
                    'source': 'marche_paiement',
                    'origine_res_id': p.id,
                    'objet': p.marche_id.objet,
                    'fournisseur': p.marche_id.fournisseur_id.name or '',
                    'montant': p.montant,
                    'date_prevue': p.date_creation,
                }))

            Honoraires = self.env['resade.marche.honoraires']
            honoraires = Honoraires.search([
                ('statut', 'in', ('verifie', 'signe')),
            ])
            for h in honoraires:
                lignes_vals.append((0, 0, {
                    'source': 'marche_honoraires',
                    'origine_res_id': h.id,
                    'objet': f"{h.marche_id.objet} – Tranche {h.num_tranche}",
                    'fournisseur': h.marche_id.fournisseur_id.name or '',
                    'montant': h.montant_net,
                    'date_prevue': fields.Date.today(),
                }))

            rec.write({
                'ligne_ids': lignes_vals,
                'date_generation': fields.Datetime.now(),
                'genere_par': self.env.uid,
            })
            rec.message_post(body=_(
                "📋 Prévisionnel régénéré – %s décaissement(s) en attente, total : %s %s"
            ) % (rec.nb_lignes, '{:,.0f}'.format(rec.total_previsionnel), rec.currency_id.name or ''))


class ResadeTresoreriePrevisionLigne(models.Model):
    _name = 'resade.tresorerie.prevision.ligne'
    _description = 'Ligne de Décaissement Prévisionnel'
    _order = 'date_prevue'

    prevision_id = fields.Many2one(
        'resade.tresorerie.prevision', string='Prévisionnel', ondelete='cascade', required=True
    )
    source = fields.Selection([
        ('marche_paiement', 'Paiement fournisseur (marché)'),
        ('marche_honoraires', 'Honoraires consultant (marché)'),
    ], string='Origine', required=True)
    origine_res_id = fields.Integer(string='ID enregistrement source')
    objet = fields.Char(string='Objet')
    fournisseur = fields.Char(string='Fournisseur / Consultant')
    montant = fields.Monetary(string='Montant prévu', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='prevision_id.currency_id', string='Devise'
    )
    date_prevue = fields.Date(string='Date prévue')

    def action_voir_dossier(self):
        """Ouvre le dossier de paiement source (fournisseur ou honoraires)."""
        self.ensure_one()
        model = (
            'resade.marche.paiement' if self.source == 'marche_paiement'
            else 'resade.marche.honoraires'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dossier de paiement'),
            'res_model': model,
            'view_mode': 'form',
            'res_id': self.origine_res_id,
        }
