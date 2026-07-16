# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeBudgetProjetBailleur(models.Model):
    """
    Processus P-EAB-02 : Élaboration des budgets de projets bailleurs
    Manuel RESADE - Carnet C - Module 01

    Circuit (Manuel B.6 / B.8) :
    1. Analyse canevas bailleur (CAF + Chef dépt. Partenariat)  -> analyse
    2. Cadrage interne et estimation des coûts (DE+Chef dépt.)   -> cadrage
    3. Construction du budget en devise (CAF)                    -> construction
    4. Validation interne (DE)                                   -> valide
    5. Soumission avec la proposition technique                  -> soumis
    6. Négociation avec le bailleur (si nécessaire)               -> negociation
    7. Intégration dans la comptabilité analytique (signature)    -> integre
    """
    _name = 'resade.budget.projet.bailleur'
    _description = 'Budget de Projet Bailleur RESADE (P-EAB-02)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Intitulé du projet', required=True, tracking=True)
    budget_annuel_id = fields.Many2one('resade.budget.annuel', string='Budget annuel de rattachement')
    bailleur_name = fields.Char(string='Bailleur / PTF', required=True, tracking=True)
    chef_departement_id = fields.Many2one('hr.employee', string='Chef Département Partenariat')

    # ─────────────────────────────────────────────
    # DEVISE / MONTANTS (B.5 structure type budget projet)
    # ─────────────────────────────────────────────
    currency_id = fields.Many2one('res.currency', string='Devise du bailleur', required=True)
    taux_change_bceao = fields.Float(string='Taux de change BCEAO appliqué', default=0.0)

    montant_personnel = fields.Monetary(string='Personnel (direct)', currency_field='currency_id')
    montant_terrain = fields.Monetary(string='Activités de terrain', currency_field='currency_id')
    montant_publication = fields.Monetary(string='Publication et dissémination', currency_field='currency_id')
    montant_equipements = fields.Monetary(string='Équipements et matériels', currency_field='currency_id')
    montant_couts_directs = fields.Monetary(
        string='Total coûts directs', compute='_compute_montants', store=True, currency_field='currency_id'
    )
    taux_overhead_pct = fields.Float(string='Taux frais de gestion / overhead (%)', default=15.0, tracking=True)
    montant_overhead = fields.Monetary(
        string='Frais de gestion (overhead)', compute='_compute_montants', store=True, currency_field='currency_id'
    )
    taux_imprevus_pct = fields.Float(string='Taux imprévus (%, max 5%)', default=5.0)
    montant_imprevus = fields.Monetary(
        string='Imprévus', compute='_compute_montants', store=True, currency_field='currency_id'
    )
    montant_audit = fields.Monetary(string="Audit de projet (si requis par bailleur)", currency_field='currency_id')
    montant_total = fields.Monetary(
        string='TOTAL BUDGET PROJET', compute='_compute_montants', store=True, currency_field='currency_id'
    )

    @api.depends(
        'montant_personnel', 'montant_terrain', 'montant_publication', 'montant_equipements',
        'taux_overhead_pct', 'taux_imprevus_pct', 'montant_audit'
    )
    def _compute_montants(self):
        for rec in self:
            couts_directs = (
                rec.montant_personnel + rec.montant_terrain
                + rec.montant_publication + rec.montant_equipements
            )
            rec.montant_couts_directs = couts_directs
            rec.montant_overhead = couts_directs * (rec.taux_overhead_pct or 0.0) / 100.0
            rec.montant_imprevus = couts_directs * (rec.taux_imprevus_pct or 0.0) / 100.0
            rec.montant_total = couts_directs + rec.montant_overhead + rec.montant_imprevus + (rec.montant_audit or 0.0)

    # ─────────────────────────────────────────────
    # SOUMISSION / NÉGOCIATION
    # ─────────────────────────────────────────────
    date_soumission = fields.Date(string='Date de soumission au bailleur')
    document_budget_devise = fields.Many2many(
        'ir.attachment', 'budget_projet_bailleur_pj_rel', string='Budget projet (RESADE-F-EAB-02-01)'
    )
    commentaire_negociation = fields.Text(string='Commentaire / demandes de révision du bailleur')

    # ─────────────────────────────────────────────
    # INTÉGRATION ANALYTIQUE (étape 7 — démarrage projet)
    # ─────────────────────────────────────────────
    code_analytique = fields.Char(string='Code analytique SAGE (RESADE-F-EAB-02-02)')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Compte analytique Odoo')
    date_ouverture_code = fields.Date(string='Date ouverture code analytique')
    date_signature_convention = fields.Date(string='Date de signature de la convention')
    document_repartition_panier = fields.Many2many(
        'ir.attachment', 'budget_projet_bailleur_pj_panier_rel',
        string='Document de répartition du panier commun (RESADE-F-CR-02-04)'
    )

    # Ligne budgétaire générée pour suivi (P-ESB-01/02)
    ligne_budgetaire_id = fields.Many2one(
        'resade.budget.ligne', string='Ligne budgétaire de suivi générée', readonly=True
    )

    state = fields.Selection([
        ('analyse', '🔍 Analyse canevas bailleur'),
        ('cadrage', '📐 Cadrage interne'),
        ('construction', '🧮 Construction budget'),
        ('valide', '✅ Validé (DE)'),
        ('soumis', '📤 Soumis au bailleur'),
        ('negociation', '🤝 Négociation'),
        ('integre', '🔗 Intégré (code analytique ouvert)'),
    ], string='État', default='analyse', tracking=True, copy=False)

    note_interne = fields.Text(string='Note interne')


    # ─────────────────────────────────────────────
    # ACTIONS DU WORKFLOW (P-EAB-02)
    # ─────────────────────────────────────────────


    def action_analyser(self):
        """
        Étape 1 : Analyse du canevas budgétaire du bailleur.
        Lecture des instructions, identification des contraintes.
        """
        for rec in self:
            # Vérifier que le bailleur est renseigné
            if not rec.bailleur_name:
                raise UserError(_(
                    "Veuillez renseigner le nom du bailleur avant de passer à l'étape suivante."
                ))
            rec.write({'state': 'cadrage'})
        return True

    def action_cadrer(self):
        """
        Étape 2 : Cadrage interne du projet et estimation des coûts.
        Le DE et le Chef de département valident le périmètre.
        """
        for rec in self:
            # Vérifier que les champs de base sont renseignés
            if not rec.name:
                raise UserError(_("Veuillez renseigner l'intitulé du projet."))
            if not rec.bailleur_name:
                raise UserError(_("Veuillez renseigner le bailleur."))
            rec.write({'state': 'construction'})
        return True

    def action_construire(self):
        """
        Étape 3 : Construction du budget complet en devise.
        Inclut l'overhead (minimum 15%) et les imprévus.
        """
        for rec in self:
            # Vérifier que les montants sont renseignés
            if rec.montant_total == 0:
                raise UserError(_(
                    "Le budget total est à 0. Veuillez renseigner les montants "
                    "(personnel, terrain, publication, équipements) avant de valider."
                ))
            # Vérifier le taux d'overhead minimum (15%)
            if rec.taux_overhead_pct < 15.0:
                raise UserError(_(
                    "Le taux de frais de gestion (overhead) est inférieur au minimum institutionnel "
                    "de 15%% (Manuel P-EAB-02, B.3).\n"
                    "Taux actuel : %s%%\n"
                    "Veuillez ajuster ou obtenir une dérogation du DE et du CA."
                ) % rec.taux_overhead_pct)
            # Vérifier le taux d'imprévus (maximum 5%)
            if rec.taux_imprevus_pct > 5.0:
                raise UserError(_(
                    "Le taux d'imprévus dépasse le maximum autorisé de 5%%.\n"
                    "Taux actuel : %s%%\n"
                    "Veuillez ajuster."
                ) % rec.taux_imprevus_pct)
            rec.write({'state': 'valide'})
        return True

    def action_valider_de(self):
        """Étape 4 : Validation par le DE, puis passage direct à l'état soumis."""
        for rec in self:
            if rec.taux_overhead_pct < 15.0:
                raise UserError(_(
                    "Le taux de frais de gestion (overhead) est inférieur au minimum institutionnel "
                    "de 15%% (Manuel P-EAB-02, B.3). Toute dérogation nécessite l'approbation du DE et du CA."
                ))
            rec.write({'state': 'soumis'})


    def action_soumettre(self):
        for rec in self:
            if not rec.document_budget_devise:
                raise UserError(_("Veuillez joindre le budget en devise avant soumission au bailleur."))
            rec.write({
                'state': 'soumis',
                'date_soumission': rec.date_soumission or fields.Date.context_today(rec),
            })

    def action_negocier(self):
        for rec in self:
            rec.write({'state': 'negociation'})

    def action_integrer(self):
        """Étape 7 : ouverture du code analytique + génération de la ligne budgétaire de suivi."""
        for rec in self:
            if not rec.code_analytique:
                raise UserError(_(
                    "Veuillez renseigner le code analytique SAGE avant d'intégrer le projet "
                    "(Manuel P-EAB-02, étape 7 — délai cible 5 jours après signature)."
                ))
            
            taux_conversion = rec.taux_change_bceao if rec.taux_change_bceao and rec.taux_change_bceao > 0 else 1.0
            montant_fcfa = rec.montant_total * taux_conversion

            ligne = rec.ligne_budgetaire_id
            if not ligne:
                ligne = self.env['resade.budget.ligne'].create({
                    'name': _('Projet bailleur : %s') % rec.name,
                    'budget_annuel_id': rec.budget_annuel_id.id if rec.budget_annuel_id else False,
                    'rubrique': 'budget_projets',
                    'code_analytique': rec.code_analytique,
                    'analytic_account_id': rec.analytic_account_id.id if rec.analytic_account_id else False,
                    'montant_prevu': montant_fcfa,
                    'ressource_confirmee': True,
                    'note': _('Généré automatiquement depuis le budget projet bailleur %s (montant original : %.2f %s)') 
                        % (rec.name, rec.montant_total, rec.currency_id.name),
                    })
            rec.write({
                'state': 'integre',
                'date_ouverture_code': rec.date_ouverture_code or fields.Date.context_today(rec),
                'ligne_budgetaire_id': ligne.id,
            })
