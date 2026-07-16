# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ResadeTresoreriePrevisionnel(models.Model):
    """
    Prévisionnel de trésorerie RESADE (Carnet F – Module 03, P-TB-02 B.4
    étape 3, formulaire RESADE-F-TB-02-02, horizons 30/60/90 jours).

    Un enregistrement = une période (mois) de prévision, avec :
      - le solde de départ (repris des soldes comptables réels des journaux
        banque/caisse Odoo au 1er jour de la période) ;
      - les lignes d'entrées attendues (décaissements bailleurs à venir) ;
      - les lignes de sorties attendues (engagements resade_budget non
        encore réalisés : FEB en cours, marchés en exécution, missions
        approuvées non clôturées) ;
      - le solde prévisionnel de fin de période.
    """
    _name = 'resade.tresorerie.previsionnel'
    _description = 'Prévisionnel de trésorerie mensuel RESADE'
    _inherit = ['mail.thread']
    _order = 'periode desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau', copy=False)
    code_document = fields.Char(
        string='Code document', default='RESADE-F-TB-02-02', readonly=True,
        help="Référence officielle du formulaire selon le Carnet F."
    )
    periode = fields.Date(string='Date de référence (aujourd\'hui du calcul)', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )

    solde_depart = fields.Monetary(
        string='Solde de départ (réel, comptable)', currency_field='currency_id',
        help="Somme des soldes comptables des journaux banque/caisse Odoo au "
             "début de la période (calculée automatiquement)."
    )

    ligne_entree_ids = fields.One2many(
        'resade.tresorerie.previsionnel.ligne', 'previsionnel_id',
        string='Entrées attendues', domain=[('type_ligne', '=', 'entree')]
    )
    ligne_sortie_ids = fields.One2many(
        'resade.tresorerie.previsionnel.ligne', 'previsionnel_id',
        string='Sorties attendues', domain=[('type_ligne', '=', 'sortie')]
    )

    total_entrees = fields.Monetary(
        string='Total entrées attendues', compute='_compute_totaux', store=True,
        currency_field='currency_id'
    )
    total_sorties = fields.Monetary(
        string='Total sorties attendues', compute='_compute_totaux', store=True,
        currency_field='currency_id'
    )
    solde_prevu_fin = fields.Monetary(
        string='Solde prévisionnel de fin de période', compute='_compute_totaux',
        store=True, currency_field='currency_id'
    )
    # ── Horizons réglementaires fixes P-TB-02 B.4 étape 3 : 30/60/90 jours ──
    solde_j30 = fields.Monetary(
        string='Solde prévisionnel à J+30', compute='_compute_horizons', store=True,
        currency_field='currency_id'
    )
    solde_j60 = fields.Monetary(
        string='Solde prévisionnel à J+60', compute='_compute_horizons', store=True,
        currency_field='currency_id'
    )
    solde_j90 = fields.Monetary(
        string='Solde prévisionnel à J+90', compute='_compute_horizons', store=True,
        currency_field='currency_id'
    )
    alerte_tension = fields.Boolean(
        string='⚠️ Tension de trésorerie prévue', compute='_compute_totaux', store=True,
        help="Activé si le solde prévisionnel de fin de période est négatif "
             "ou inférieur au seuil de sécurité défini par le CAF."
    )
    seuil_securite = fields.Monetary(
        string='Seuil de sécurité de trésorerie', currency_field='currency_id',
        help="Montant minimal de trésorerie disponible souhaité (fonds de "
             "roulement de sécurité)."
    )

    valide_caf = fields.Boolean(string='Validé par le CAF', default=False, tracking=True)
    date_validation = fields.Date(string='Date de validation CAF')
    note = fields.Text(string='Commentaires / mesures correctives envisagées')

    @api.depends('solde_depart', 'ligne_entree_ids.montant', 'ligne_sortie_ids.montant', 'seuil_securite')
    def _compute_totaux(self):
        for rec in self:
            rec.total_entrees = sum(rec.ligne_entree_ids.mapped('montant'))
            rec.total_sorties = sum(rec.ligne_sortie_ids.mapped('montant'))
            rec.solde_prevu_fin = rec.solde_depart + rec.total_entrees - rec.total_sorties
            rec.alerte_tension = rec.solde_prevu_fin < (rec.seuil_securite or 0.0)

    @api.depends('solde_depart', 'periode', 'ligne_entree_ids.montant', 'ligne_entree_ids.date_prevue',
                 'ligne_sortie_ids.montant', 'ligne_sortie_ids.date_prevue')
    def _compute_horizons(self):
        for rec in self:
            if not rec.periode:
                rec.solde_j30 = rec.solde_j60 = rec.solde_j90 = rec.solde_depart
                continue
            for horizon, field_name in ((30, 'solde_j30'), (60, 'solde_j60'), (90, 'solde_j90')):
                limite = rec.periode + relativedelta(days=horizon)
                entrees = sum(rec.ligne_entree_ids.filtered(
                    lambda l: l.date_prevue and l.date_prevue <= limite
                ).mapped('montant'))
                sorties = sum(rec.ligne_sortie_ids.filtered(
                    lambda l: l.date_prevue and l.date_prevue <= limite
                ).mapped('montant'))
                rec[field_name] = rec.solde_depart + entrees - sorties

    def action_calculer_solde_depart(self):
        """Reprend automatiquement le solde comptable réel des journaux
        banque/caisse Odoo (aucune saisie manuelle)."""
        for rec in self:
            journaux = self.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', self.env.company.id),
            ])
            rec.solde_depart = sum(journaux.mapped('resade_solde_comptable'))

    def action_charger_sorties_engagements(self):
        """
        Alimente automatiquement les sorties attendues à partir des
        engagements budgétaires en cours (resade.budget.ligne.montant_engage)
        qui ne sont pas encore réalisés — remplace une saisie manuelle des
        FEB / marchés / missions en cours.
        """
        for rec in self:
            rec.ligne_sortie_ids.filtered(lambda l: l.origine == 'auto_engagement').unlink()
            lignes = self.env['resade.budget.ligne'].search([('montant_engage', '>', 0)])
            vals = []
            for ligne in lignes:
                vals.append((0, 0, {
                    'type_ligne': 'sortie',
                    'origine': 'auto_engagement',
                    'libelle': _('Engagement en cours – %s') % ligne.name,
                    'montant': ligne.montant_engage,
                    'ligne_budgetaire_id': ligne.id,
                    'date_prevue': rec.periode,
                }))
            if vals:
                rec.ligne_sortie_ids = vals
            rec.message_post(body=_(
                "Sorties attendues rechargées depuis les engagements budgétaires en cours (%d ligne(s))."
            ) % len(vals))

    def action_valider_caf(self):
        self.ensure_one()
        self.write({'valide_caf': True, 'date_validation': fields.Date.today()})
        self.message_post(body=_("Prévisionnel de trésorerie validé par le CAF."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                periode = vals.get('periode') or fields.Date.today()
                vals['name'] = 'PREV-TRESO-%s' % (
                    periode.strftime('%Y-%m') if hasattr(periode, 'strftime') else periode
                )
        return super().create(vals_list)


class ResadeTresoreriePrevisionnelLigne(models.Model):
    _name = 'resade.tresorerie.previsionnel.ligne'
    _description = 'Ligne de prévisionnel de trésorerie'

    previsionnel_id = fields.Many2one(
        'resade.tresorerie.previsionnel', string='Prévisionnel', ondelete='cascade'
    )
    type_ligne = fields.Selection([
        ('entree', 'Entrée attendue'),
        ('sortie', 'Sortie attendue'),
    ], string='Type', required=True, default='sortie')
    origine = fields.Selection([
        ('manuelle', 'Saisie manuelle'),
        ('auto_engagement', 'Engagement budgétaire (auto)'),
        ('bailleur', 'Décaissement bailleur attendu'),
    ], string='Origine', default='manuelle')
    libelle = fields.Char(string='Libellé', required=True)
    montant = fields.Monetary(string='Montant', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(related='previsionnel_id.currency_id', store=True)
    date_prevue = fields.Date(string='Date prévue')
    ligne_budgetaire_id = fields.Many2one('resade.budget.ligne', string='Ligne budgétaire liée')
    projet_bailleur_id = fields.Many2one(
        'resade.budget.projet.bailleur', string='Projet bailleur concerné'
    )
