# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeBudgetFeb(models.Model):
    """
    Processus P-ESB-01 : Engagement des dépenses et niveaux d'autorisation
    Manuel RESADE - Carnet C - Module 02

    LA FEB (Fiche d'Expression des Besoins) est le document PIVOT institutionnel
    de tout engagement de dépense chez RESADE (Manuel §B.2 : "Aucun paiement ne
    peut être effectué sans FEB validée préalablement").

    Ce modèle est le référentiel GÉNÉRIQUE institutionnel (toute dépense, quelle
    que soit son origine). Le module resade_marche possède déjà son propre modèle
    resade.marche.feb, plus spécialisé pour les dossiers de marché (avec ses
    propres champs CAM, seuils de passation, etc.) — les deux peuvent coexister :
    - resade.marche.feb reste le document opérationnel du dossier marché
    - resade.budget.feb (ce modèle) est utilisé pour les dépenses HORS marché
      formel (missions, frais courants, achats < seuil) ET peut être lié en
      Many2one optionnel depuis resade.marche.feb pour bénéficier de la
      VÉRIFICATION RÉELLE de disponibilité de crédit (au lieu du simple
      visa déclaratif actuel).

    Circuit (Manuel B.7 / B.8) :
    1. Rédaction et soumission de la FEB (Demandeur)        -> soumise
    2. Visa budgétaire du CAF (vérif. disponibilité crédit)  -> visee_caf
    3. Autorisation de dépense (DE ou délégué)               -> autorisee
    4. Lancement procédure d'achat (si applicable)           -> en_cours
    5. Réception et certification                            -> receptionnee
    6. Constitution dossier de paiement                       -> dossier_complet
    7. Paiement et comptabilisation (double signature)        -> payee
    """
    _name = 'resade.budget.feb'
    _description = "Fiche d'Expression des Besoins RESADE (P-ESB-01)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_creation desc'

    name = fields.Char(string='Réf. FEB', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    # ─────────────────────────────────────────────
    # B.6 : CONTENU OBLIGATOIRE DE LA FEB
    # ─────────────────────────────────────────────
    demandeur_id = fields.Many2one(
        'hr.employee', string='Demandeur', required=True, tracking=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    )
    departement = fields.Char(string='Département / Service demandeur')
    date_creation = fields.Date(string='Date de la demande', default=fields.Date.context_today, required=True)
    date_besoin = fields.Date(string='Date de besoin souhaitée')

    nature_besoin = fields.Text(string='Nature du besoin (description précise)', required=True)
    justification = fields.Text(string='Justification (motif et nécessité)', required=True)
    quantite_specifications = fields.Text(string='Quantité et spécifications techniques')

    montant_estime = fields.Monetary(string='Montant estimé', currency_field='currency_id', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False) or self.env.company.currency_id
    )
    source_estimation = fields.Char(string="Source de l'estimation")

    # Imputation budgétaire — le VRAI lien vers la structure budgétaire
    ligne_budgetaire_id = fields.Many2one(
        'resade.budget.ligne', string='Ligne budgétaire (imputation)', tracking=True,
        domain="[('budget_annuel_id.state', 'in', ['approuve_ca', 'diffuse'])]"
    )
    montant_disponible_ligne = fields.Monetary(
        related='ligne_budgetaire_id.montant_disponible', string='Disponible sur la ligne', readonly=True
    )

    fournisseur_suggere = fields.Char(string='Fournisseur(s) suggéré(s) (informatif)')

    # Lien optionnel vers un dossier marché (resade_marche), si la dépense
    # bascule en procédure formelle de passation (Carnet D)
    marche_ref = fields.Char(
        string='Réf. dossier marché lié (si applicable)',
        help="Renseigner la référence du dossier marché resade_marche une fois la procédure d'achat lancée."
    )
    mission_ref = fields.Char(
        string='Réf. ordre de mission lié (si applicable)',
        help="Renseigner la référence de l'OM resade_mission si la dépense concerne une mission."
    )

    # ─────────────────────────────────────────────
    # CIRCUIT DE VALIDATION (B.5 / B.8 du Manuel)
    # ─────────────────────────────────────────────
    chef_dept_id = fields.Many2one('hr.employee', string='Chef de département')
    date_visa_chef = fields.Date(string='Date visa chef de département')

    caf_valideur_id = fields.Many2one('res.users', string='Visé CAF par', readonly=True)
    date_visa_caf = fields.Datetime(string='Date visa CAF', readonly=True)
    credit_reserve = fields.Boolean(string='Crédit réservé sur la ligne', default=False, readonly=True)

    seuil_delegation = fields.Selection([
        ('de', 'Directeur Exécutif'),
        ('delegue', 'Délégué (selon matrice des délégations RESADE-F-OP-03-01)'),
    ], string="Niveau d'autorisation requis", default='de')
    autorise_par_id = fields.Many2one('res.users', string='Autorisé par', readonly=True)
    date_autorisation = fields.Datetime(string="Date d'autorisation", readonly=True)

    motif_refus = fields.Text(string='Motif de refus / rejet')

    # ─────────────────────────────────────────────
    # ÉTAPES 4-7 : ACHAT / RÉCEPTION / PAIEMENT
    # ─────────────────────────────────────────────
    pv_reception = fields.Many2many('ir.attachment', 'budget_feb_pj_pvr_rel', string='PV de réception')
    facture_certifiee = fields.Many2many('ir.attachment', 'budget_feb_pj_facture_rel', string='Facture certifiée')
    document_feb_signee = fields.Many2many('ir.attachment', 'budget_feb_pj_signee_rel', string='FEB signée (scan)',domain="[('res_model', '=', 'resade.budget.feb')]")

    date_paiement = fields.Date(string='Date de paiement')
    montant_paye_reel = fields.Monetary(string='Montant réellement payé', currency_field='currency_id')
    paye_par_de = fields.Boolean(string='Signature DE (double signature)', default=False)
    paye_par_caf = fields.Boolean(string='Signature CAF (double signature)', default=False)
    reference_ecriture_sage = fields.Char(string='Référence écriture SAGE')

    state = fields.Selection([
        ('brouillon', '📝 Brouillon'),
        ('soumise', '📥 Soumise'),
        ('visee_caf', '💰 Visée CAF (crédit réservé)'),
        ('autorisee', '✅ Autorisée (DE)'),
        ('en_cours', '🛒 Procédure achat en cours'),
        ('receptionnee', '📦 Réceptionnée / certifiée'),
        ('dossier_complet', '📁 Dossier de paiement complet'),
        ('payee', '💵 Payée (clôturée)'),
        ('rejetee', '❌ Rejetée'),
    ], string='Statut FEB', default='brouillon', tracking=True, copy=False)

    delai_traitement_jours = fields.Float(
        string='Délai soumission → autorisation (jours)', compute='_compute_delai', store=True
    )
    delai_depasse = fields.Boolean(
        string='Délai dépassé (> 5 j ouvrables)', compute='_compute_delai', store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.budget.feb') or _('Nouveau')
        records = super().create(vals_list)
        records._sync_attachments()
        return records

    
    def _sync_attachments(self):
        for record in self:
            if record.document_feb_signee:
                record.document_feb_signee.write({
                    'res_model': 'resade.budget.feb',
                    'res_id': record.id,    
                })


    def write(self, vals):
        result = super().write(vals)
        if 'document_feb_signee' in vals:
            self._sync_attachments()
        return result

    @api.depends('date_creation', 'date_autorisation')
    def _compute_delai(self):
        for rec in self:
            rec.delai_traitement_jours = 0.0
            rec.delai_depasse = False
            if rec.date_creation and rec.date_autorisation:
                debut = fields.Datetime.from_string(str(rec.date_creation) + ' 00:00:00')
                delta = rec.date_autorisation - debut
                jours = delta.total_seconds() / 86400.0
                rec.delai_traitement_jours = jours
                rec.delai_depasse = jours > 5.0

    # ─────────────────────────────────────────────
    # ACTIONS DU WORKFLOW
    # ─────────────────────────────────────────────
    def action_soumettre(self):
        for rec in self:
            if not rec.justification or not rec.nature_besoin:
                raise UserError(_("La nature du besoin et la justification sont obligatoires avant soumission."))
            rec.write({'state': 'soumise'})

    def action_viser_caf(self):
        """
        Étape 2 : VRAIE vérification de disponibilité budgétaire (et non plus
        une simple case à cocher). Réserve (engage) le crédit sur la ligne.
        """
        for rec in self:
            if not rec.ligne_budgetaire_id:
                raise UserError(_("Veuillez sélectionner la ligne budgétaire d'imputation avant le visa CAF."))
            rec.ligne_budgetaire_id.reserver_credit(rec.montant_estime)
            rec.write({
                'state': 'visee_caf',
                'caf_valideur_id': self.env.user.id,
                'date_visa_caf': fields.Datetime.now(),
                'credit_reserve': True,
            })

    def action_autoriser(self):
        """Étape 3 : autorisation DE (ou délégué selon la matrice des délégations)."""
        for rec in self:
            if rec.state != 'visee_caf':
                raise UserError(_("La FEB doit d'abord être visée par le CAF (disponibilité budgétaire)."))
            rec.write({
                'state': 'autorisee',
                'autorise_par_id': self.env.user.id,
                'date_autorisation': fields.Datetime.now(),
            })

    def action_lancer_achat(self):
        for rec in self:
            rec.write({'state': 'en_cours'})

    def action_receptionner(self):
        for rec in self:
            if not rec.pv_reception or not rec.facture_certifiee:
                raise UserError(_(
                    "Le PV de réception et la facture certifiée sont obligatoires avant cette étape "
                    "(Manuel P-ESB-01, étape 5)."
                ))
            rec.write({'state': 'receptionnee'})

    def action_constituer_dossier(self):
        for rec in self:
            rec.write({'state': 'dossier_complet'})

    def action_payer(self):
        """Étape 7 : paiement (double signature DE+CAF obligatoire) + solde du crédit engagé."""
        for rec in self:
            if not (rec.paye_par_de and rec.paye_par_caf):
                raise UserError(_(
                    "Le paiement nécessite la double signature DE et CAF (Manuel P-ESB-01, étape 7)."
                ))
            montant_reel = rec.montant_paye_reel or rec.montant_estime
            if rec.credit_reserve and rec.ligne_budgetaire_id:
                rec.ligne_budgetaire_id.constater_realisation(rec.montant_estime, montant_reel)
            rec.write({
                'state': 'payee',
                'date_paiement': rec.date_paiement or fields.Date.context_today(rec),
                'montant_paye_reel': montant_reel,
            })

    def action_rejeter(self):
        for rec in self:
            if not rec.motif_refus:
                raise UserError(_("Merci de renseigner le motif de rejet."))
            if rec.credit_reserve and rec.ligne_budgetaire_id:
                rec.ligne_budgetaire_id.liberer_credit(rec.montant_estime)
            rec.write({'state': 'rejetee', 'credit_reserve': False})
