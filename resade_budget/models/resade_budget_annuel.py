



    
  
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ResadeBudgetAnnuel(models.Model):
    """
    Processus P-EAB-01 : Élaboration du budget annuel (Plan Opérationnel Annuel - POA)
    Manuel RESADE - Carnet C - Module 01
    Version consolidée - Juillet 2026
    """
    """
    Processus P-EAB-01 : Élaboration du budget annuel (Plan Opérationnel Annuel - POA)
    Manuel RESADE - Carnet C - Module 01

    Circuit (Manuel B.7 / B.8) :
    1. Lancement / note de cadrage (DE+CAF, octobre)         -> cadrage
    2. Soumission budgets départementaux (Chefs dépt.)        -> soumission
    3. Intégration budgets projets bailleurs (CAF)            -> integration
    4. Consolidation / première ébauche (CAF)                 -> consolidation
    5. Arbitrage et équilibrage (DE+CAF)                      -> arbitrage
    6. Validation du projet de budget (DE)                    -> valide_de
    7. Approbation par le CA                                  -> approuve_ca
    8. Présentation AG et diffusion                           -> diffuse
    """

    _name = 'resade.budget.annuel'
    _description = 'Budget Annuel RESADE / POA (P-EAB-01)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'annee desc'

    # ─────────────────────────────────────────────
    # CONTRAINTES D'INTÉGRITÉ
    # ─────────────────────────────────────────────
    _sql_constraints = [
        ('annee_unique', 'unique(annee)',
         "Un budget annuel existe déjà pour cet exercice. Un seul enregistrement par exercice est autorisé."),
    ]

    # ─────────────────────────────────────────────
    # CHAMPS DE BASE
    # ─────────────────────────────────────────────
    name = fields.Char(string='Désignation', compute='_compute_name', store=True)
    annee = fields.Integer(string='Exercice (N+1)', required=True, tracking=True,
                           default=lambda self: fields.Date.context_today(self).year + 1)
    date_debut = fields.Date(string='Date de début', required=True)
    date_fin = fields.Date(string='Date de fin', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False) or self.env.company.currency_id
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 1 : NOTE DE CADRAGE
    # ─────────────────────────────────────────────
    date_cadrage = fields.Date(string='Date de la note de cadrage')
    orientations_strategiques = fields.Text(string='Orientations stratégiques (Plan Stratégique 2026-2030)')
    contraintes_financieres = fields.Text(string='Contraintes financières')
    document_cadrage = fields.Many2many(
        'ir.attachment',                    # Modèle lié
        'budget_annuel_pj_cadrage_rel',     # Table de liaison
        'resade_budget_annuel_id',                 # Colonne qui pointe vers resade.budget.annuel
        'ir_attachment_id',                    # Colonne qui pointe vers ir.attachment
        string='Note de cadrage (RESADE-F-EAB-01-01)',
        domain="[('res_model', '=', 'resade.budget.annuel')]"
    )
    delai_soumission = fields.Date(string='Délai de soumission des départements')

    # ─────────────────────────────────────────────
    # ÉTAPE 5 : ARBITRAGE / ÉQUILIBRE — CALCULÉS AUTOMATIQUEMENT
    # ─────────────────────────────────────────────
    reserve_fonctionnement = fields.Monetary(
        string='Réserve de fonctionnement (3 mois charges fixes)',
        compute='_compute_reserve_provision', store=True, currency_field='currency_id'
    )
    provision_imprevus_pct = fields.Float(string='Taux de provision imprévus (%)', default=5.0)
    provision_imprevus_montant = fields.Monetary(
        string='Provision imprévus (montant)',
        compute='_compute_reserve_provision', store=True, currency_field='currency_id'
    )
    total_recettes = fields.Monetary(
        string='Total recettes prévues', compute='_compute_reserve_provision',
        store=True, currency_field='currency_id'
    )

    total_charges = fields.Monetary(
        string='Total charges (hors recettes)',
        compute='_compute_reserve_provision',
        store=True,
        currency_field='currency_id'
    )

    total_charges_fixes = fields.Monetary(
        string='Total charges fixes', compute='_compute_reserve_provision',
        store=True, currency_field='currency_id'
    )
    budget_equilibre = fields.Boolean(
        string='Budget équilibré', compute='_compute_reserve_provision', store=True
    )
    date_arbitrage = fields.Date(string='Date de l\'arbitrage')
    arbitre_par_id = fields.Many2one('res.users', string='Arbitré par')

    # ─────────────────────────────────────────────
    # ÉTAPE 6/7 : VALIDATION DE / APPROBATION CA
    # ─────────────────────────────────────────────
    valide_par_de_id = fields.Many2one('res.users', string='Validé par (DE)', readonly=True)
    date_validation_de = fields.Datetime(string='Date validation DE', readonly=True)
    approuve_par_ca = fields.Boolean(string='Approuvé par le CA', default=False, tracking=True)
    date_approbation_ca = fields.Date(string="Date d'approbation CA")
    reference_resolution_ca = fields.Char(string="N° résolution CA (RESADE-F-EAB-01-03/RES)")
    document_resolution_ca = fields.Many2many(
        'ir.attachment', 'budget_annuel_pj_resolution_rel',
        string='Résolution CA (scan)',
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 8 : PRÉSENTATION AG / DIFFUSION
    # ─────────────────────────────────────────────
    date_presentation_ag = fields.Date(string="Date de présentation à l'AG")
    valide_ag = fields.Boolean(string="Validé par l'AG", default=False)
    date_diffusion = fields.Date(string='Date de diffusion aux départements')
    document_budget_consolide = fields.Many2many(
        'ir.attachment', 'budget_annuel_pj_consolide_rel',
        string='Budget annuel consolidé (RESADE-F-EAB-01-03)',
    )

    # ─────────────────────────────────────────────
    # LIGNES BUDGÉTAIRES
    # ─────────────────────────────────────────────
    ligne_ids = fields.One2many('resade.budget.ligne', 'budget_annuel_id', string='Lignes budgétaires')
    nb_lignes = fields.Integer(string='Nb lignes', compute='_compute_montants', store=True)
    total_prevu = fields.Monetary(string='Total prévu (toutes lignes)', compute='_compute_montants',
                                  store=True, currency_field='currency_id')
    total_engage = fields.Monetary(string='Total engagé', compute='_compute_montants',
                                   store=True, currency_field='currency_id')
    total_realise = fields.Monetary(string='Total réalisé', compute='_compute_montants',
                                    store=True, currency_field='currency_id')
    total_disponible_hors_reserve = fields.Monetary(
        string='Total disponible hors réserve/provision',
        compute='_compute_montants', store=True, currency_field='currency_id'
    )
    taux_execution = fields.Float(string="Taux d'exécution global (%)", compute='_compute_montants', store=True)

    # ─────────────────────────────────────────────
    # PROJETS BAILLEURS LIÉS (P-EAB-02)
    # ─────────────────────────────────────────────
    projet_bailleur_ids = fields.One2many(
        'resade.budget.projet.bailleur', 'budget_annuel_id', 
        string='Budgets de projets bailleurs'
    )

    can_edit_lines = fields.Boolean(
        string='Peut modifier les lignes',
        compute='_compute_can_edit_lines',
        help="Détermine si l'utilisateur actuel peut modifier les lignes budgétaires"
    )

    # ─────────────────────────────────────────────
    # ÉTAT DU WORKFLOW
    # ─────────────────────────────────────────────
    state = fields.Selection([
        ('cadrage', '📋 Note de cadrage'),
        ('soumission', '📥 Soumission départementale'),
        ('integration', '🔗 Intégration projets bailleurs'),
        ('consolidation', '🧮 Consolidation'),
        ('arbitrage', '⚖️ Arbitrage / équilibrage'),
        ('valide_de', '✅ Validé (DE)'),
        ('approuve_ca', '🏛️ Approuvé (CA)'),
        ('diffuse', '📤 Diffusé (clôturé)'),
    ], string='État', default='cadrage', tracking=True, copy=False)

    note_interne = fields.Text(string='Note interne')

    is_chef_only = fields.Boolean(
        string='Est Chef de Département (non CAF)',
        compute='_compute_is_chef_only',
        help="Détermine si l'utilisateur est Chef de Département sans être CAF"
    )


    # ─────────────────────────────────────────────
    # MÉTHODES DE CALCUL
    # ─────────────────────────────────────────────

    @api.depends('annee')
    def _compute_name(self):
        for rec in self:
            rec.name = _('Budget Annuel %s (POA)') % (rec.annee or '?')

    @api.depends('ligne_ids.montant_prevu', 'ligne_ids.montant_engage', 
                 'ligne_ids.montant_realise', 'reserve_fonctionnement', 
                 'provision_imprevus_montant')
    
    def _compute_montants(self):
        for rec in self:
            lignes = rec.ligne_ids
            rec.nb_lignes = len(lignes)
            
            # Total de TOUTES les lignes (recettes + charges)
            rec.total_prevu = sum(lignes.mapped('montant_prevu')) or 0.0
            rec.total_engage = sum(lignes.mapped('montant_engage')) or 0.0
            rec.total_realise = sum(lignes.mapped('montant_realise')) or 0.0
            
            # Total des CHARGES SEULEMENT (sans les recettes)
            total_charges = sum(lignes.filtered(
                lambda l: l.rubrique != 'ressources'
            ).mapped('montant_prevu')) or 0.0
            
            
            # Disponible = CHARGES - engagé - réalisé - réserve - provision
            rec.total_disponible_hors_reserve = (
                rec.total_recettes                  # ← Charges seulement
                - rec.total_engage
                - rec.total_realise
                - rec.reserve_fonctionnement
                - rec.provision_imprevus_montant
            ) or 0.0
            
            rec.taux_execution = (
                (rec.total_realise / total_charges * 100.0) if total_charges else 0.0
            )

    @api.depends('ligne_ids.montant_prevu', 'ligne_ids.rubrique', 
                 'provision_imprevus_pct', 'total_prevu')
    def _compute_reserve_provision(self):
        """
        Carnet C - rubrique RÉSERVE ET IMPRÉVUS :
        - Réserve de fonctionnement = 3 mois de charges fixes (charges_fixes_annuelles / 12 * 3)
        - Provision pour imprévus = provision_imprevus_pct % du budget total prévu
        - Budget équilibré = recettes prévues >= charges + réserve + provision
        """
        for rec in self:
            lignes = rec.ligne_ids

            
            charges_fixes = sum(lignes.filtered(
                lambda l: l.rubrique == 'charge_fixe').mapped('montant_prevu'))
            
             # 2. Recettes institutionnelles
            recettes_institutionnelles = sum(lignes.filtered(
                lambda l: l.rubrique == 'ressources'
            ).mapped('montant_prevu')) or 0.0

            # 3. Overhead des projets bailleurs intégrés, converti en FCFA
            overhead_bailleurs = 0.0
            for p in rec.projet_bailleur_ids:
                if p.state == 'integre':
                    overhead = p.montant_overhead or 0.0
                    taux = p.taux_change_bceao or 1.0  # Si pas de taux, on suppose 1 (déjà en FCFA)
                    overhead_bailleurs += overhead * taux
                
            
            # 4. Total recettes
            rec.total_recettes = recettes_institutionnelles + overhead_bailleurs
            
            # Total charges = tout SAUF les recettes
            total_charges = sum(lignes.filtered(
                lambda l: l.rubrique != 'ressources'
            ).mapped('montant_prevu'))
            
            rec.total_charges = total_charges or 0.0
            rec.total_charges_fixes = charges_fixes or 0.0
            
            
            # Réserve = 3 mois de charges fixes
            rec.reserve_fonctionnement = (charges_fixes / 12.0) * 3.0 if charges_fixes else 0.0
            
            # Provision = % du budget total
            rec.provision_imprevus_montant = total_charges * (rec.provision_imprevus_pct / 100.0)


            # Vérification de l'équilibre
            total_charges_a_couvrir = (
                total_charges
                + (rec.reserve_fonctionnement or 0.0)
                + (rec.provision_imprevus_montant or 0.0)
            )

            rec.budget_equilibre = (rec.total_recettes or 0.0) >= total_charges_a_couvrir
    

           
    
    def _compute_is_chef_only(self):
        for rec in self:
            user = self.env.user
            is_chef = user.has_group('resade_budget.group_resade_budget_chef_dept')
            is_caf = user.has_group('resade_budget.group_resade_budget_caf')
            rec.is_chef_only = is_chef and not is_caf

    # ─────────────────────────────────────────────
    # ACTIONS DU WORKFLOW
    # ─────────────────────────────────────────────


    def _compute_can_edit_lines(self):
        for rec in self:
            rec.can_edit_lines = (
                rec.state != 'diffuse' and 
                self.env.user.has_group('resade_budget.group_resade_budget_caf')
            )

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_debut > rec.date_fin:
                raise ValidationError(_("La date de début ne peut pas être postérieure à la date de fin."))

    def action_lancer_cadrage(self):
        """
        Étape 1 : Lancement du processus budgétaire avec note de cadrage.
        Réservé au CAF.
        """
        for rec in self:
            if not rec.document_cadrage:
                raise UserError(_(
                    "Veuillez joindre la note de cadrage budgétaire avant de lancer le processus "
                    "(Manuel P-EAB-01, étape 1)."
                ))
            rec.write({
                'state': 'soumission', 
                'date_cadrage': rec.date_cadrage or fields.Date.context_today(rec)
            })

    def action_confirmer_soumissions(self):
        """
        Étape 2 : Confirmation que tous les départements ont soumis leur budget.
        Réservé au CAF.
        """
        for rec in self:
            if not rec.ligne_ids:
                raise UserError(_(
                    "Aucune ligne budgétaire départementale n'a été saisie "
                    "(Manuel P-EAB-01, étape 2)."
                ))
            rec.write({'state': 'integration'})

    def action_integrer_projets(self):
        """
        Étape 3 : Intégration des budgets de projets bailleurs.
        Réservé au CAF.
        Vérifie que les projets sont au bon état avant intégration.
        """
        for rec in self:
            en_cours = rec.projet_bailleur_ids.filtered(
                lambda p: p.state not in ('integre', 'negociation')
            )
            if en_cours:
                raise UserError(_(
                    "Certains budgets de projets bailleurs ne sont ni intégrés ni en négociation "
                    "avancée : %s. Merci de finaliser leur statut avant intégration."
                ) % ', '.join(en_cours.mapped('name')))
            rec.write({'state': 'consolidation'})

    def action_consolider(self):
        """
        Étape 4 : Consolidation du budget.
        Réservé au CAF.
        """
        for rec in self:
            rec.write({'state': 'arbitrage'})

    def action_arbitrer(self):
        """
        Étape 5 : Arbitrage DE.
        Calcule réserve de fonctionnement et provision pour imprévus,
        vérifie l'équilibre du budget.
        Ne change PAS l'état : la validation DE reste une étape distincte.
        """
        for rec in self:
            # Recalculer les montants
            rec._compute_reserve_provision()
            
            # Calculer le total des charges (sans les recettes)
            total_charges = sum(rec.ligne_ids.filtered(
                lambda l: l.rubrique != 'ressources'
            ).mapped('montant_prevu')) or 0.0
            
            # Vérifier l'équilibre
            if not rec.budget_equilibre:
                raise UserError(_(
                    "Budget déséquilibré : les recettes prévues (%.0f %s) ne couvrent pas "
                    "les charges (%.0f) + réserve de fonctionnement (%.0f) + provision pour imprévus (%.0f) "
                    "(besoin total : %.0f %s). Veuillez ajuster les lignes avant de valider."
                ) % (
                    rec.total_recettes, rec.currency_id.name,
                    total_charges, rec.reserve_fonctionnement, rec.provision_imprevus_montant,
                    total_charges + rec.reserve_fonctionnement + rec.provision_imprevus_montant,
                    rec.currency_id.name,
                ))
            
            # Enregistrer l'arbitrage
            rec.write({
                'date_arbitrage': fields.Date.today(),
                'arbitre_par_id': self.env.user.id
            })



    def action_valider_de(self):
        """
        Étape 6 : Validation du projet de budget par le DE.
        Exige que l'arbitrage ait été effectué au préalable.
        """
        for rec in self:
            if rec.state != 'arbitrage':
                raise UserError(_(
                    "Le budget doit être en phase d'arbitrage avant validation par le DE."
                ))
            if not rec.date_arbitrage:
                raise UserError(_(
                    "L'arbitrage doit être effectué avant la validation DE "
                    "(bouton 'Arbitrer / équilibrer')."
                ))
            if not rec.budget_equilibre:
                raise UserError(_(
                    "Le budget n'est pas équilibré. Veuillez l'arbitrer avant validation."
                ))
            rec.write({
                'state': 'valide_de',
                'valide_par_de_id': self.env.user.id,
                'date_validation_de': fields.Datetime.now(),
            })

    def action_approuver_ca(self):
        """
        Étape 7 : Approbation formelle par le Conseil d'Administration.
        """
        for rec in self:
            if not rec.reference_resolution_ca:
                raise UserError(_(
                    "Veuillez renseigner la référence de la résolution du CA avant d'approuver "
                    "(Manuel P-EAB-01, étape 7)."
                ))
            rec.write({
                'state': 'approuve_ca',
                'approuve_par_ca': True,
                'date_approbation_ca': rec.date_approbation_ca or fields.Date.context_today(rec),
            })

    def action_diffuser(self):
        """
        Étape 8 : Présentation AG + diffusion du budget approuvé.
        Vérifie que l'AG a bien validé le budget.
        """
        for rec in self:
            if rec.state != 'approuve_ca':
                raise UserError(_(
                    "Le budget doit être approuvé par le CA avant diffusion."
                ))
            if not rec.valide_ag:
                raise UserError(_(
                    "Le budget doit être présenté et validé par l'Assemblée Générale avant "
                    "diffusion (Manuel P-EAB-01, étape 8)."
                ))
            if not rec.date_presentation_ag:
                raise UserError(_(
                    "La date de présentation à l'AG doit être renseignée avant diffusion."
                ))
            rec.write({
                'state': 'diffuse',
                'date_diffusion': rec.date_diffusion or fields.Date.context_today(rec),
            })

    def action_annuler(self):
        """
        Action d'annulation : permet de revenir à l'étape précédente.
        """
        for rec in self:
            if rec.state == 'diffuse':
                raise UserError(_(
                    "Impossible d'annuler un budget déjà diffusé. Utilisez la procédure de révision."
                ))
            # Revenir à l'étape de cadrage
            rec.write({'state': 'cadrage'})


    def _sync_attachments(self):
        """Synchronise les pièces jointes avec le bon res_model et res_id."""
        for record in self:
            if record.document_cadrage:
                record.document_cadrage.write({
                    'res_model': 'resade.budget.annuel',
                    'res_id': record.id,
                })
            if record.document_resolution_ca:
                record.document_resolution_ca.write({
                    'res_model': 'resade.budget.annuel',
                    'res_id': record.id,
                })
            if record.document_budget_consolide:
                record.document_budget_consolide.write({
                    'res_model': 'resade.budget.annuel',
                    'res_id': record.id,
                })


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_attachments()
        return records

    # ─────────────────────────────────────────────
    # ACTIONS DE NAVIGATION
    # ─────────────────────────────────────────────

    def action_voir_lignes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lignes budgétaires'),
            'res_model': 'resade.budget.ligne',
            'view_mode': 'list,form',
            'domain': [('budget_annuel_id', '=', self.id)],
            'context': {'default_budget_annuel_id': self.id},
        }

    def action_voir_projets_bailleurs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Projets bailleurs'),
            'res_model': 'resade.budget.projet.bailleur',
            'view_mode': 'list,form',
            'domain': [('budget_annuel_id', '=', self.id)],
            'context': {'default_budget_annuel_id': self.id},
        }

    # ─────────────────────────────────────────────
    # SÉCURITÉ : VERROU APRÈS DIFFUSION
    # ─────────────────────────────────────────────

    def write(self, vals):
        """
        Verrou : une fois diffusé, impossible de modifier les champs protégés
        directement — seul le circuit de révision budgétaire (F-ESB-03-01) le permet.
        """
        champs_proteges = {'ligne_ids', 'document_cadrage', 'orientations_strategiques', 
                          'contraintes_financieres', 'provision_imprevus_pct'}
        
        # Vérifier si on essaie de modifier un champ protégé
        if champs_proteges & set(vals.keys()):
            for rec in self:
                if rec.state == 'diffuse' and not self.env.context.get('via_revision'):
                    raise UserError(_(
                        "Ce budget est diffusé et verrouillé. Toute modification des lignes "
                        "budgétaires doit passer par une Révision Budgétaire (F-ESB-03-01)."
                    ))
                
        for budget in self:

            # Si ce n'est pas le CAF
            if not self.env.user.has_group('resade_budget.group_resade_budget_caf'):

                champs_interdits = {
                    'annee',
                    'date_debut',
                    'date_fin',
                    'currency_id',
                    'state',
                    'date_diffusion',
                }

                if champs_interdits.intersection(vals.keys()):
                    raise AccessError(
                        "Le chef de département ne peut pas modifier les informations générales du budget."
                    )
        
        result = super().write(vals)
        if any(f in vals for f in ['document_cadrage', 'document_resolution_ca', 'document_budget_consolide']):
            self._sync_attachments()
        return result
    

    def unlink(self):
        """
        Empêcher la suppression d'un budget diffusé ou approuvé.
        """
        for rec in self:
            if rec.state in ('diffuse', 'approuve_ca'):
                raise UserError(_(
                    "Impossible de supprimer un budget qui a été approuvé ou diffusé."
                ))
        return super().unlink()