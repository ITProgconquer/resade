# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeBudgetRevision(models.Model):
    """
    Processus P-ESB-03 : Révision et réajustement budgétaire
    Manuel RESADE - Carnet C - Module 02

    Niveaux d'approbation (Manuel B.4) :
      - Virement mineur (<=5% d'une ligne, même département) : DE seul
      - Virement significatif (>5% ou entre départements)     : DE + Info CA
      - Révision institutionnelle (>10% budget total)         : DE + Approbation CA
      - Révision projet bailleur (avenant)                    : DE + CA (si seuil) + Accord bailleur
      - Ressources supplémentaires reçues                      : DE + Info CA

    Circuit (Manuel B.5 / B.8) :
    1. Identification du besoin (CAF / Chef dépt.)        -> identifie
    2. Qualification de la modification (CAF)             -> qualifie
    3. Préparation du tableau de modification (CAF)        -> tableau_prepare
    4. Validation selon niveau requis (DE / CA)             -> approuve
    5. Notification bailleur (si applicable)                -> notifie
    6. Mise à jour du budget officiel (CAF)                 -> mis_a_jour
    7. Diffusion et archivage                                -> diffuse
    """
    _name = 'resade.budget.revision'
    _description = 'Révision / Réajustement Budgétaire RESADE (P-ESB-03)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Réf. révision', readonly=True, copy=False, default=lambda self: _('Nouveau'))
    budget_annuel_id = fields.Many2one('resade.budget.annuel', string='Budget annuel concerné', required=True)

    # ─────────────────────────────────────────────
    # ÉTAPE 1-2 : IDENTIFICATION / QUALIFICATION (B.4)
    # ─────────────────────────────────────────────
    type_modification = fields.Selection([
        ('virement_mineur', "Virement de ligne mineur (≤5%, même département) — DE seul"),
        ('virement_significatif', "Virement significatif (>5% ou inter-départements) — DE + Info CA"),
        ('revision_institutionnelle', "Révision institutionnelle (>10% budget total) — DE + Approbation CA"),
        ('avenant_bailleur', "Révision budget projet / avenant bailleur — DE + CA + Accord bailleur"),
        ('ressources_supplementaires', "Ressources supplémentaires reçues — DE + Info CA"),
    ], string='Type de modification', required=True, tracking=True)

    demandeur_id = fields.Many2one('hr.employee', string='Demandeur (CAF / Chef dépt.)', required=True)
    motif = fields.Text(string='Motif / justification du besoin de révision', required=True)
    evenement_declencheur = fields.Char(string='Événement déclencheur')

    niveau_approbation_requis = fields.Char(
        string="Niveau d'approbation requis", compute='_compute_niveau', store=True
    )
    notification_bailleur_requise = fields.Boolean(
        string='Notification bailleur requise', compute='_compute_niveau', store=True
    )

    nature_operation = fields.Selection([
        ('transfert', 'Transfert entre lignes existantes'),
        ('ajout', 'Ajout de ressources / nouvelle ligne'),
    ], string='Nature de l\'opération', compute='_compute_nature_operation', store=True)

    piece_justificative_ids = fields.Many2many(
        'ir.attachment', 'budget_revision_pj_justif_rel',
        string='Pièces justificatives (convention, notification don...)'
    )

    @api.depends('type_modification')
    def _compute_nature_operation(self):
        for rec in self:
            if rec.type_modification == 'ressources_supplementaires':
                rec.nature_operation = 'ajout'
            elif rec.type_modification == 'revision_institutionnelle':
                rec.nature_operation = 'ajout'  # Peut créer de nouvelles lignes
            else:
                rec.nature_operation = 'transfert'

    @api.depends('type_modification')
    def _compute_niveau(self):
        mapping = {
            'virement_mineur': ('Directeur Exécutif seul', False),
            'virement_significatif': ('DE + Information CA (session suivante)', False),
            'revision_institutionnelle': ('DE + Approbation formelle du CA', False),
            'avenant_bailleur': ('DE + CA (si seuil délégation dépassé) + Accord du bailleur', True),
            'ressources_supplementaires': ('DE + Information CA', False),
        }
        for rec in self:
            niveau, notif = mapping.get(rec.type_modification, ('—', False))
            rec.niveau_approbation_requis = niveau
            rec.notification_bailleur_requise = notif

    # ─────────────────────────────────────────────
    # ÉTAPE 3 : TABLEAU DE MODIFICATION (RESADE-F-ESB-03-01)
    # ─────────────────────────────────────────────
    ligne_ids = fields.One2many('resade.budget.revision.ligne', 'revision_id', string='Lignes impactées')
    document_tableau_modification = fields.Many2many(
        'ir.attachment', 'budget_revision_pj_tableau_rel', string='Tableau de modification (RESADE-F-ESB-03-01)'
    )
    

    # ─────────────────────────────────────────────
    # ÉTAPE 4 : VALIDATION
    # ─────────────────────────────────────────────
    approuve_par_de_id = fields.Many2one('res.users', string='Approuvé par (DE)', readonly=True)
    date_approbation_de = fields.Datetime(string='Date approbation DE', readonly=True)
    approuve_par_ca = fields.Boolean(string='Approuvé par le CA', default=False)
    date_approbation_ca = fields.Date(string="Date d'approbation CA")
    reference_decision = fields.Char(string='Réf. décision / résolution (RESADE-F-ESB-03-02)')
    document_decision = fields.Many2many(
        'ir.attachment', 'budget_revision_pj_decision_rel', string='Décision approbation (scan)'
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 5 : NOTIFICATION BAILLEUR
    # ─────────────────────────────────────────────
    date_notification_bailleur = fields.Date(string='Date de notification au bailleur')
    accuse_reception_bailleur = fields.Boolean(string='Accusé de réception du bailleur obtenu', default=False)

    # ─────────────────────────────────────────────
    # ÉTAPE 6-7 : MISE À JOUR / DIFFUSION
    # ─────────────────────────────────────────────
    date_mise_a_jour_sage = fields.Date(string='Date de mise à jour dans SAGE')
    date_diffusion = fields.Date(string='Date de diffusion aux départements')

    state = fields.Selection([
        ('identifie', '🔍 Besoin identifié'),
        ('qualifie', '🏷️ Qualifié'),
        ('tableau_prepare', '📋 Tableau préparé'),
        ('approuve', '✅ Approuvé'),
        ('notifie', '✉️ Bailleur notifié'),
        ('mis_a_jour', '🔄 Budget mis à jour'),
        ('diffuse', '📤 Diffusé (clôturé)'),
    ], string='État', default='identifie', tracking=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.budget.revision') or _('Nouveau')
        return super().create(vals_list)

    def action_qualifier(self):
        for rec in self:
            rec.write({'state': 'qualifie'})

    def action_preparer_tableau(self):
        for rec in self:
            if not rec.ligne_ids:
                raise UserError(_("Veuillez ajouter au moins une ligne impactée avant de préparer le tableau."))
            rec.write({'state': 'tableau_prepare'})

    def action_approuver(self):
        for rec in self:
            if rec.type_modification in ('revision_institutionnelle', 'avenant_bailleur') and not rec.reference_decision:
                raise UserError(_(
                    "Ce type de révision nécessite une approbation formelle du CA : "
                    "veuillez renseigner la référence de la décision/résolution."
                ))
            rec.write({
                'state': 'approuve',
                'approuve_par_de_id': self.env.user.id,
                'date_approbation_de': fields.Datetime.now(),
                'approuve_par_ca': rec.type_modification in (
                    'revision_institutionnelle', 'avenant_bailleur'
                ) or rec.approuve_par_ca,
            })

    def action_notifier_bailleur(self):
        for rec in self:
            rec.write({
                'state': 'notifie',
                'date_notification_bailleur': rec.date_notification_bailleur or fields.Date.context_today(rec),
            })

    def action_mettre_a_jour(self):
        """Étape 6 : applique les modifications + vérifie l'équilibre du budget."""
        for rec in self:
            budget = rec.budget_annuel_id
            
            # Vérification spécifique selon la nature
            if rec.nature_operation == 'transfert':
                total_variation = sum(rec.ligne_ids.mapped('montant_virement'))
                if total_variation != 0:
                    raise UserError(_(
                        "Un transfert doit être à somme nulle : ce qui est retiré d'une ligne "
                        "doit être ajouté à une autre. Écart constaté : %.0f FCFA."
                    ) % total_variation)
            
            if rec.nature_operation == 'ajout':
                if not rec.piece_justificative_ids:
                    raise UserError(_(
                        "Une révision par ajout de ressources doit être justifiée par une pièce "
                        "(convention, notification de don, etc.)."
                    ))
            
            # Appliquer les modifications
            for ligne in rec.ligne_ids:
                if ligne.ligne_origine_id and ligne.montant_virement:
                    ligne.ligne_origine_id.with_context(via_revision=True).write({
                        'montant_prevu': ligne.ligne_origine_id.montant_prevu - ligne.montant_virement,
                    })
                if ligne.ligne_destination_id and ligne.montant_virement:
                    ligne.ligne_destination_id.with_context(via_revision=True).write({
                        'montant_prevu': ligne.ligne_destination_id.montant_prevu + ligne.montant_virement,
                    })
                # Ajout : création d'une nouvelle ligne si pas de destination
                if rec.nature_operation == 'ajout' and ligne.montant_virement and not ligne.ligne_destination_id:
                    self.env['resade.budget.ligne'].create({
                        'name': ligne.nouvelle_ligne_libelle or 'Nouvelle ligne',
                        'budget_annuel_id': budget.id,
                        'rubrique': ligne.nouvelle_ligne_rubrique or 'ressources',
                        'montant_prevu': ligne.montant_virement,
                    })
            
            # Vérifier l'équilibre
            budget.invalidate_recordset()
            budget._compute_montants()
            budget._compute_reserve_provision()
            
            if not budget.budget_equilibre:
                raise UserError(_(
                    "La révision rend le budget déséquilibré.\n\n"
                    "Recettes : %.0f %s\n"
                    "Charges + Réserve + Provision : %.0f %s\n\n"
                    "Veuillez ajuster les lignes avant de valider."
                ) % (
                    budget.total_recettes, budget.currency_id.name,
                    budget.total_charges + budget.reserve_fonctionnement + budget.provision_imprevus_montant,
                    budget.currency_id.name,
                ))
            
            rec.write({
                'state': 'mis_a_jour',
                'date_mise_a_jour_sage': rec.date_mise_a_jour_sage or fields.Date.context_today(rec),
            })

    def action_diffuser(self):
        for rec in self:
            rec.write({
                'state': 'diffuse',
                'date_diffusion': rec.date_diffusion or fields.Date.context_today(rec),
            })


class ResadeBudgetRevisionLigne(models.Model):
    """Ligne du tableau de modification budgétaire : virement d'une ligne à une autre."""
    _name = 'resade.budget.revision.ligne'
    _description = 'Ligne de Révision Budgétaire (virement)'

    revision_id = fields.Many2one('resade.budget.revision', string='Révision', ondelete='cascade')
    ligne_origine_id = fields.Many2one('resade.budget.ligne', string='Ligne origine (crédit retiré)')
    ligne_destination_id = fields.Many2one('resade.budget.ligne', string='Ligne destination (crédit ajouté)')
    montant_virement = fields.Monetary(string='Montant du virement', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='ligne_origine_id.currency_id', string='Devise'
    )
    justification = fields.Char(string='Justification de ce virement')
    nouvelle_ligne_libelle = fields.Char(string='Libellé nouvelle ligne (si ajout)')
    nouvelle_ligne_rubrique = fields.Selection([
        ('ressources', 'RESSOURCES (RECETTES)'),
        ('charges_fixes', 'CHARGES DE STRUCTURE FIXES'),
        ('charges_operationnelles', 'CHARGES OPÉRATIONNELLES'),
        ('budget_projets', 'BUDGET DES PROJETS DE RECHERCHE'),
        ('investissements', 'INVESTISSEMENTS'),
    ], string='Rubrique nouvelle ligne')
