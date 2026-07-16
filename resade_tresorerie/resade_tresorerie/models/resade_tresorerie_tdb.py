# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class ResadeTresorerieTdb(models.Model):
    """
    Tableau de bord de trésorerie consolidé RESADE.

    Agrège, à la date de génération :
      - les soldes comptables réels de tous les journaux banque/caisse Odoo,
        répartis par type de fonds (propres / restreints par bailleur) ;
      - le total des engagements budgétaires non encore réalisés
        (resade.budget.ligne.montant_engage) ;
      - la trésorerie disponible réelle nette (solde réel – engagements en
        cours), indicateur central pour le CAF et le DE.
    """
    _name = 'resade.tresorerie.tdb'
    _description = 'Tableau de bord trésorerie consolidé'
    _inherit = ['mail.thread']
    _order = 'date_generation desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau')
    date_generation = fields.Datetime(string='Date de génération', readonly=True)
    genere_par = fields.Many2one('res.users', string='Généré par', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )

    solde_total_fonds_propres = fields.Monetary(
        string='Solde total – Fonds propres', currency_field='currency_id', readonly=True
    )
    solde_total_fonds_restreints = fields.Monetary(
        string='Solde total – Fonds restreints (bailleurs)', currency_field='currency_id', readonly=True
    )
    solde_total_general = fields.Monetary(
        string='Solde total général (toutes banques/caisses)', currency_field='currency_id', readonly=True
    )
    total_engagements_budget = fields.Monetary(
        string='Total engagements budgétaires en cours (non réalisés)',
        currency_field='currency_id', readonly=True
    )
    tresorerie_disponible_nette = fields.Monetary(
        string='Trésorerie disponible réelle nette', currency_field='currency_id', readonly=True,
        help="Solde total général – Total des engagements budgétaires en cours. "
             "Indicateur clé : ce qui reste réellement mobilisable une fois "
             "les engagements déjà pris en compte."
    )

    ligne_compte_ids = fields.One2many(
        'resade.tresorerie.tdb.ligne', 'tdb_id', string='Détail par compte', readonly=True
    )

    # ── KPI réglementaires Carnet F (P-TB-01 B.12 / P-TB-02 B.12) ──
    kpi_taux_controle_hebdo = fields.Float(
        string='Taux de contrôles hebdomadaires de caisse réalisés (%)', readonly=True,
        help="Cible réglementaire : ≥ 90%."
    )
    kpi_taux_piece_justificative = fields.Float(
        string='Taux de décaissements caisse avec pièce justificative (%)', readonly=True,
        help="Cible réglementaire : 100%."
    )
    kpi_taux_rapprochement_delai = fields.Float(
        string='Taux de rapprochements produits dans les délais ≤ J+7 (%)', readonly=True,
        help="Cible réglementaire : ≥ 95%."
    )
    kpi_ecart_net_rapprochement = fields.Monetary(
        string='Écart net moyen des rapprochements (période)', currency_field='currency_id', readonly=True,
        help="Cible réglementaire : 0 FCFA."
    )

    note_analyse = fields.Text(string='Analyse et points d’attention CAF')

    def action_generer(self):
        self.ensure_one()
        Journal = self.env['account.journal']
        BudgetLigne = self.env['resade.budget.ligne']

        journaux = Journal.search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.env.company.id),
        ])

        lignes_vals = []
        total_propre = total_restreint = 0.0
        for j in journaux:
            solde = j.resade_solde_comptable
            if j.resade_type_fonds == 'restreint':
                total_restreint += solde
            else:
                total_propre += solde
            lignes_vals.append((0, 0, {
                'journal_id': j.id,
                'solde': solde,
                'type_fonds': j.resade_type_fonds or 'propre',
                'projet_bailleur_id': j.resade_projet_bailleur_id.id if j.resade_projet_bailleur_id else False,
            }))

        total_engagements = sum(BudgetLigne.search([]).mapped('montant_engage'))
        solde_total = total_propre + total_restreint

        kpis = self._compute_kpis_reglementaires()

        self.write({
            'ligne_compte_ids': [(5, 0, 0)] + lignes_vals,
            'solde_total_fonds_propres': total_propre,
            'solde_total_fonds_restreints': total_restreint,
            'solde_total_general': solde_total,
            'total_engagements_budget': total_engagements,
            'tresorerie_disponible_nette': solde_total - total_engagements,
            'genere_par': self.env.uid,
            'date_generation': fields.Datetime.now(),
            **kpis,
        })
        self.message_post(body=_("Tableau de bord de trésorerie recalculé automatiquement."))

    def _compute_kpis_reglementaires(self):
        """KPI Carnet F P-TB-01 B.12 / P-TB-02 B.12, sur les 12 derniers mois glissants."""
        self.ensure_one()
        date_debut = fields.Date.today() - relativedelta(months=12)

        # Taux de contrôles hebdomadaires réalisés (cible réelle : 1/semaine, soit ~52/an -> 4.33/mois)
        controles = self.env['resade.tresorerie.controle.caisse'].search([
            ('date_controle', '>=', date_debut)
        ])
        nb_semaines = 52
        taux_controle = min(100.0, (len(controles) / nb_semaines) * 100.0) if nb_semaines else 0.0

        # Taux de décaissements de caisse avec pièce justificative
        decaissements = self.env['resade.tresorerie.caisse.decaissement'].search([
            ('date_demande', '>=', date_debut), ('statut', '=', 'decaisse')
        ])
        nb_total = len(decaissements)
        nb_avec_piece = len(decaissements.filtered('piece_justificative'))
        taux_piece = (nb_avec_piece / nb_total * 100.0) if nb_total else 100.0

        # Taux de rapprochements produits dans les délais (<= J+7)
        rapprochements = self.env['resade.tresorerie.rapprochement'].search([
            ('periode', '>=', date_debut), ('statut', '=', 'valide_caf')
        ])
        nb_rap = len(rapprochements)
        nb_dans_delai = len(rapprochements.filtered(lambda r: not r.en_retard))
        taux_delai = (nb_dans_delai / nb_rap * 100.0) if nb_rap else 100.0
        ecart_moyen = (sum(rapprochements.mapped('ecart')) / nb_rap) if nb_rap else 0.0

        return {
            'kpi_taux_controle_hebdo': taux_controle,
            'kpi_taux_piece_justificative': taux_piece,
            'kpi_taux_rapprochement_delai': taux_delai,
            'kpi_ecart_net_rapprochement': ecart_moyen,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                today = fields.Date.today()
                vals['name'] = 'TDB-TRESO-%s' % today.strftime('%Y-%m-%d')
        return super().create(vals_list)


class ResadeTresorerieTdbLigne(models.Model):
    _name = 'resade.tresorerie.tdb.ligne'
    _description = 'Ligne détail tableau de bord trésorerie'

    tdb_id = fields.Many2one('resade.tresorerie.tdb', ondelete='cascade')
    journal_id = fields.Many2one('account.journal', string='Compte bancaire / caisse')
    solde = fields.Monetary(string='Solde', currency_field='currency_id')
    currency_id = fields.Many2one(related='tdb_id.currency_id', store=True)
    type_fonds = fields.Selection([
        ('propre', 'Fonds propres'),
        ('restreint', 'Fonds restreint (bailleur)'),
        ('caisse_menue', 'Caisse menue'),
    ], string='Type de fonds')
    projet_bailleur_id = fields.Many2one('resade.budget.projet.bailleur', string='Projet bailleur')
