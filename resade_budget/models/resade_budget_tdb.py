# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeBudgetTdb(models.Model):
    """
    Processus P-ESB-02 : Suivi budgétaire mensuel et reporting interne
    Manuel RESADE - Carnet C - Module 02

    Tableau de bord mensuel consolidé (RESADE-F-ESB-02-01) : budget vs
    exécution par rubrique institutionnelle ET par projet, avec analyse
    des écarts > 10% (Manuel §B.3 / B.5).
    """
    _name = 'resade.budget.tdb'
    _description = 'Tableau de Bord Budgétaire Mensuel RESADE (P-ESB-02)'
    _inherit = ['mail.thread']
    _order = 'mois desc'

    name = fields.Char(string='Désignation', compute='_compute_name', store=True)
    mois = fields.Date(string='Mois concerné', required=True, default=fields.Date.context_today)
    budget_annuel_id = fields.Many2one('resade.budget.annuel', string='Budget annuel de référence', required=True)

    date_extraction_sage = fields.Date(string='Date extraction SAGE (J+5)')
    sage_complet = fields.Boolean(string='Saisies SAGE complètes pour le mois (AC)', default=False)

    ligne_analyse_ids = fields.One2many('resade.budget.tdb.ligne', 'tdb_id', string="Lignes d'analyse")
    nb_ecarts_significatifs = fields.Integer(
        string='Nb lignes avec écart > 10%', compute='_compute_ecarts', store=True
    )

    commentaire_analyse = fields.Text(string='Analyse des écarts et mesures correctives proposées (CAF)')
    instructions_de = fields.Text(string='Instructions du DE (mesures correctives décidées)')

    valide_par_de = fields.Boolean(string='Validé par le DE', default=False, tracking=True)
    date_validation_de = fields.Date(string='Date de validation DE')
    date_diffusion_departements = fields.Date(string='Date de diffusion aux chefs de département')

    rapport_trimestriel = fields.Boolean(
        string='Inclus dans le rapport trimestriel CA', default=False
    )
    document_tdb = fields.Many2many('ir.attachment', 'budget_tdb_pj_rel', string='TDB (RESADE-F-ESB-02-01)')

    state = fields.Selection([
        ('extraction', '📊 Extraction SAGE'),
        ('production', '🧮 Production TDB'),
        ('analyse', '🔍 Analyse des écarts'),
        ('valide', '✅ Validé (DE)'),
        ('diffuse', '📤 Diffusé'),
    ], string='État', default='extraction', tracking=True, copy=False)

    @api.depends('mois')
    def _compute_name(self):
        for rec in self:
            rec.name = _('TDB %s') % (rec.mois.strftime('%B %Y') if rec.mois else '?')

    @api.depends('ligne_analyse_ids.ecart_pct')
    def _compute_ecarts(self):
        for rec in self:
            rec.nb_ecarts_significatifs = len(
                rec.ligne_analyse_ids.filtered(lambda l: abs(l.ecart_pct) > 10.0)
            )

    def action_generer_lignes(self):
        """Génère automatiquement les lignes d'analyse à partir des lignes du budget annuel."""
        for rec in self:
            rec.ligne_analyse_ids.unlink()
            for ligne in rec.budget_annuel_id.ligne_ids:
                self.env['resade.budget.tdb.ligne'].create({
                    'tdb_id': rec.id,
                    'ligne_budgetaire_id': ligne.id,
                    'montant_prevu': ligne.montant_prevu,
                    'montant_realise_cumul': ligne.montant_realise,
                })
            rec.state = 'production'

    def action_marquer_analyse(self):
        for rec in self:
            rec.state = 'analyse'

    def action_valider_de(self):
        for rec in self:
            rec.write({
                'state': 'valide',
                'valide_par_de': True,
                'date_validation_de': rec.date_validation_de or fields.Date.context_today(rec),
            })

    def action_diffuser(self):
        for rec in self:
            rec.write({
                'state': 'diffuse',
                'date_diffusion_departements': rec.date_diffusion_departements or fields.Date.context_today(rec),
            })


class ResadeBudgetTdbLigne(models.Model):
    """Ligne d'analyse du tableau de bord : budget vs réalisé + écart."""
    _name = 'resade.budget.tdb.ligne'
    _description = "Ligne d'analyse TDB Budgétaire"

    tdb_id = fields.Many2one('resade.budget.tdb', string='Tableau de bord', ondelete='cascade')
    ligne_budgetaire_id = fields.Many2one('resade.budget.ligne', string='Ligne budgétaire', required=True)
    rubrique = fields.Selection(related='ligne_budgetaire_id.rubrique', string='Rubrique')
    montant_prevu = fields.Monetary(string='Budget prévu', currency_field='currency_id')
    montant_realise_cumul = fields.Monetary(string='Réalisé cumulé', currency_field='currency_id')
    currency_id = fields.Many2one(related='ligne_budgetaire_id.currency_id', string='Devise')
    ecart_montant = fields.Monetary(
        string='Écart (montant)', compute='_compute_ecart', store=True, currency_field='currency_id'
    )
    ecart_pct = fields.Float(string='Écart (%)', compute='_compute_ecart', store=True)
    commentaire = fields.Char(string='Commentaire explicatif (si écart > 10%)')

    @api.depends('montant_prevu', 'montant_realise_cumul')
    def _compute_ecart(self):
        for rec in self:
            rec.ecart_montant = rec.montant_prevu - rec.montant_realise_cumul
            rec.ecart_pct = (
                (rec.ecart_montant / rec.montant_prevu * 100.0) if rec.montant_prevu else 0.0
            )


class ResadeBudgetRapportTrimestriel(models.Model):
    """Rapport de performance budgétaire trimestriel destiné au CA — RESADE-F-ESB-02-02."""
    _name = 'resade.budget.rapport.trimestriel'
    _description = 'Rapport de Performance Budgétaire Trimestriel (P-ESB-02, RESADE-F-ESB-02-02)'
    _order = 'annee desc, trimestre desc'

    budget_annuel_id = fields.Many2one('resade.budget.annuel', string='Budget annuel', required=True)
    annee = fields.Integer(string='Exercice', related='budget_annuel_id.annee', store=True)
    trimestre = fields.Selection([
        ('1', 'T1'), ('2', 'T2'), ('3', 'T3'), ('4', 'T4'),
    ], string='Trimestre', required=True)

    tdb_mensuel_ids = fields.Many2many('resade.budget.tdb', string='TDB mensuels inclus')
    synthese_execution = fields.Text(string="Synthèse de l'exécution")
    alertes_risques = fields.Text(string='Alertes et risques financiers identifiés')
    previsions_fin_exercice = fields.Text(string="Prévisions de fin d'exercice")
    recommandations = fields.Text(string='Recommandations')

    soumis_au_ca = fields.Boolean(string='Soumis au CA', default=False)
    date_soumission_ca = fields.Date(string='Date de soumission au CA')
    document_rapport = fields.Many2many(
        'ir.attachment', 'budget_rapport_trim_pj_rel', string='Rapport (RESADE-F-ESB-02-02)'
    )

    def action_soumettre_ca(self):
        for rec in self:
            rec.write({
                'soumis_au_ca': True,
                'date_soumission_ca': rec.date_soumission_ca or fields.Date.context_today(rec),
            })
