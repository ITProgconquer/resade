# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeBudgetLigne(models.Model):
    """
    Ligne budgétaire RESADE — structure conforme au Manuel Carnet C, B.6
    (Structure du budget annuel RESADE / nomenclature SYCEBNL).

    C'est LE référentiel central que consomment :
      - resade.budget.feb (P-ESB-01, ce module) via reserver_credit()
      - à terme : resade.marche.feb (module resade_marche) et
        resade.mission (module resade_mission), pour remplacer la simple
        case "visa budgétaire" par une vraie vérification de crédit
        disponible (Many2one à ajouter dans une prochaine itération de
        ces modules : ligne_budgetaire_id = fields.Many2one
        ('resade.budget.ligne', ...) au lieu du Char actuel).
    """
    _name = 'resade.budget.ligne'
    _description = 'Ligne Budgétaire RESADE (structure SYCEBNL – Manuel Carnet C B.6)'
    _order = 'rubrique, code_sycebnl'

    name = fields.Char(string='Intitulé de la ligne', required=True)
    code_sycebnl = fields.Char(string='Code SYCEBNL', help="Ex : Classe 6 - Charges / Classe 7 - Produits")

    budget_annuel_id = fields.Many2one(
        'resade.budget.annuel', string='Budget annuel', required=True, ondelete='cascade'
    )
    annee = fields.Integer(related='budget_annuel_id.annee', store=True, string='Exercice')
    currency_id = fields.Many2one(related='budget_annuel_id.currency_id', string='Devise')

    # ─────────────────────────────────────────────
    # RUBRIQUE BUDGÉTAIRE (B.6 du Manuel)
    # ─────────────────────────────────────────────
    rubrique = fields.Selection([
        ('ressources', 'RESSOURCES (RECETTES)'),
        ('charges_fixes', 'CHARGES DE STRUCTURE FIXES'),
        ('charges_operationnelles', 'CHARGES OPÉRATIONNELLES'),
        ('budget_projets', 'BUDGET DES PROJETS DE RECHERCHE'),
        ('investissements', 'INVESTISSEMENTS'),
        ('reserve_imprevus', 'RÉSERVE ET IMPRÉVUS'),
    ], string='Rubrique budgétaire', required=True, tracking=True)

    sous_rubrique = fields.Char(
        string='Sous-rubrique',
        help="Ex : Cotisations des membres / Charges de personnel permanent / Frais de mission..."
    )

    # ─────────────────────────────────────────────
    # DÉPARTEMENT / PROJET (canevas budget départemental F-EAB-01-02)
    # ─────────────────────────────────────────────
    departement = fields.Selection([
        ('direction', 'Direction Exécutive'),
        ('operations', 'Département des Opérations'),
        ('partenariat', 'Département du Partenariat'),
        ('pool_support', 'Pool Support'),
        ('pool_rd', 'Pool R&D'),
        ('institutionnel', 'Institutionnel (transversal)'),
    ], string='Département', tracking=True)

    code_analytique = fields.Char(
        string='Code analytique projet (SAGE)',
        help='Code projet ouvert dans SAGE (P-EAB-02, étape 7) — vide pour le budget institutionnel'
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Compte analytique Odoo (optionnel)',
        help="Lien optionnel vers le compte analytique standard Odoo, si la compagnie l'utilise."
    )
    ressource_confirmee = fields.Boolean(
        string='Ressource confirmée (vs conditionnelle)', default=True,
        help="Manuel P-EAB-01 §B.3 : distinction ressources confirmées / conditionnelles"
    )

    # ─────────────────────────────────────────────
    # MONTANTS
    # ─────────────────────────────────────────────
    montant_prevu = fields.Monetary(string='Montant prévu (budget approuvé)', currency_field='currency_id',
                                     required=True, tracking=True)
    montant_engage = fields.Monetary(string='Montant engagé (FEB en cours)', currency_field='currency_id',
                                      default=0.0, readonly=True, tracking=True)
    montant_realise = fields.Monetary(string='Montant réalisé (dépensé)', currency_field='currency_id',
                                       default=0.0, readonly=True, tracking=True)
    montant_disponible = fields.Monetary(
        string='Disponible', compute='_compute_disponible', store=True, currency_field='currency_id'
    )
    taux_consommation = fields.Float(
        string='Taux de consommation (%)', compute='_compute_disponible', store=True
    )
    alerte_seuil = fields.Selection([
        ('ok', 'OK (< 80%)'),
        ('alerte_80', '⚠️ Alerte 80%'),
        ('alerte_95', '🔴 Alerte 95%'),
        ('depasse', '⛔ Dépassé'),
    ], string='Statut de consommation', compute='_compute_disponible', store=True)

    note = fields.Char(string='Justification / note')

    # models/resade_budget_ligne.py

    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        default=lambda self: self.env.user.employee_id.department_id.id,
        readonly=True
    )

    @api.depends('montant_prevu', 'montant_engage', 'montant_realise')
    def _compute_disponible(self):
        for rec in self:
            rec.montant_disponible = rec.montant_prevu - rec.montant_engage - rec.montant_realise
            consomme = rec.montant_engage + rec.montant_realise
            rec.taux_consommation = (consomme / rec.montant_prevu * 100.0) if rec.montant_prevu else 0.0
            if rec.taux_consommation >= 100.0:
                rec.alerte_seuil = 'depasse'
            elif rec.taux_consommation >= 95.0:
                rec.alerte_seuil = 'alerte_95'
            elif rec.taux_consommation >= 80.0:
                rec.alerte_seuil = 'alerte_80'
            else:
                rec.alerte_seuil = 'ok'

    # ─────────────────────────────────────────────
    # POINT D'INTÉGRATION CENTRAL — Manuel P-ESB-01
    # Appelable depuis ce module (FEB RESADE) et, dans une prochaine
    # itération, depuis resade_marche / resade_mission.
    # ─────────────────────────────────────────────
    def reserver_credit(self, montant):
        """
        Vérifie la disponibilité du crédit sur la ligne et réserve (engage)
        le montant si suffisant. Lève une UserError sinon.
        C'est l'équivalent automatisé du "visa budgétaire CAF" du Manuel
        (P-ESB-01, étape 2 : "vérifier la disponibilité des crédits").
        """
        self.ensure_one()
        if montant <= 0:
            raise UserError(_("Le montant à réserver doit être positif."))
        if montant > self.montant_disponible:
            raise UserError(_(
                "Crédit insuffisant sur la ligne budgétaire « %s ».\n"
                "Disponible : %s %s — Montant demandé : %s %s.\n"
                "(Manuel RESADE P-ESB-01 : aucun engagement n'est possible sans disponibilité "
                "de crédit confirmée par le CAF.)"
            ) % (
                self.name, '{:,.0f}'.format(self.montant_disponible), self.currency_id.name or 'FCFA',
                '{:,.0f}'.format(montant), self.currency_id.name or 'FCFA'
            ))
        self.montant_engage += montant
        return True

    def liberer_credit(self, montant):
        """Annule une réservation (ex : FEB rejetée) : restitue le montant engagé."""
        self.ensure_one()
        self.montant_engage = max(0.0, self.montant_engage - montant)
        return True

    def constater_realisation(self, montant_engage_a_solder, montant_reel):
        """
        Au paiement effectif (P-ESB-01 étape 7) : solde le montant engagé et
        constate la dépense réelle (qui peut différer légèrement du montant engagé).
        """
        self.ensure_one()
        self.montant_engage = max(0.0, self.montant_engage - montant_engage_a_solder)
        self.montant_realise += montant_reel
        return True
    


    def action_import_lignes(self):
        """
        Action d'import d'une ligne budgétaire.
        Vérifie que le budget n'est pas verrouillé avant l'import.
        Appelée depuis le formulaire d'import.
        """
        self.ensure_one()

        # Récupérer le budget annuel
        budget_annuel = self.budget_annuel_id

        if not budget_annuel:
            raise UserError(_("Cette ligne doit être rattachée à un budget annuel."))

        # Vérifier que le budget n'est pas verrouillé
        if budget_annuel.state == 'diffuse':
            raise UserError(_(
                "Ce budget est diffusé et verrouillé. "
                "L'import de nouvelles lignes n'est pas autorisé."
            ))

        # Retourner à la liste des lignes du budget
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lignes budgétaires'),
            'res_model': 'resade.budget.ligne',
            'view_mode': 'list,form',
            'domain': [('budget_annuel_id', '=', budget_annuel.id)],
            'context': {'default_budget_annuel_id': budget_annuel.id},
        }
    

    def action_create_ligne(self):
        """
        Action appelée après la création d'une ligne depuis le popup.
        Vérifie que le budget n'est pas verrouillé.
        """
        self.ensure_one()
        if self.budget_annuel_id.state == 'diffuse':
            raise UserError(_("Ce budget est verrouillé. La création de ligne n'est pas autorisée."))
        return {'type': 'ir.actions.act_window_close'}
