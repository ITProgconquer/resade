from odoo import models, fields, api, exceptions
from datetime import date


# ═══════════════════════════════════════════════════════
# FEB – FICHE D'EXPRESSION DES BESOINS (P-ESB-01)
# Manuel RESADE – Carnet D – Pièce obligatoire N°1
# Document RESADE-F-PTM-01-01
# Produit par le Demandeur + visé CAF + autorisé DE
# Pièce obligatoire dans TOUT dossier de paiement (P-PL-01 B.4)
# ═══════════════════════════════════════════════════════
class ResadeMarcheFEB(models.Model):
    _name = 'resade.marche.feb'
    _description = 'Fiche Expression des Besoins (FEB) – P-ESB-01'
    _inherit = ['mail.thread']
    _order = 'date_creation desc'

    name = fields.Char(
        string='Ref. FEB', required=True, readonly=True,
        default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marche', ondelete='cascade'
    )

    # Identification
    titre_besoin = fields.Char(string='Intitule du besoin', required=True)
    departement_demandeur = fields.Char(string='Departement / Service demandeur', required=True)
    demandeur_id = fields.Many2one(
        'hr.employee', string='Demandeur',
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
    )
    date_creation = fields.Date(
        string='Date creation', default=fields.Date.today, required=True
    )
    date_besoin = fields.Date(
        string='Date besoin (livraison souhaitee)', required=True
    )

    # Nature du besoin
    type_besoin = fields.Selection([
        ('fourniture', 'Fourniture de biens / materiels'),
        ('service', 'Prestation de services courants'),
        ('consultant', 'Consultance / expertise intellectuelle'),
        ('travaux', 'Travaux'),
        ('formation', 'Formation'),
        ('autre', 'Autre'),
    ], string='Type de besoin', required=True, default='fourniture')

    justification = fields.Text(
        string='Justification du besoin',
        help='Pourquoi ce besoin ? Lien avec les activites du projet / plan de travail ?',
        required=True
    )
    specifications = fields.Text(
        string='Specifications techniques / TDR synthetiques',
        help='Description precise : marque, modele, caracteristiques, ou termes de reference pour services'
    )

    # Budget
    montant_estime = fields.Monetary(
        string='Montant estime (FCFA)', currency_field='currency_id', required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )
    code_analytique = fields.Char(
        string='Code analytique / Code projet',
        help='Code projet SAGE pour imputation budgetaire'
    )
    ligne_budgetaire = fields.Char(
        string='Ligne budgetaire',
        help='Rubrique du budget approbation bailleurs (ex: 3.2 – Equipements de terrain)'
    )

    # Validations
    statut = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('soumise', 'Soumise au chef de departement'),
        ('visee_chef', 'Visee par le chef de departement'),
        ('visee_caf', 'Visee CAF (disponibilite budgetaire confirmee)'),
        ('autorisee', 'Autorisee par le DE'),
        ('rejetee', 'Rejetee'),
    ], string='Statut FEB', default='brouillon', tracking=True)

    chef_dept_id = fields.Many2one('hr.employee', string='Chef de departement valideur')
    date_visa_chef = fields.Date(string='Date visa chef dept')
    caf_valideur_id = fields.Many2one('hr.employee', string='CAF valideur')
    date_visa_caf = fields.Date(string='Date visa CAF')
    de_id = fields.Many2one('hr.employee', string='DE autorisateur')
    date_autorisation_de = fields.Date(string='Date autorisation DE')
    motif_rejet = fields.Text(string='Motif rejet')

    pj_feb = fields.Many2many(
        'ir.attachment', 'feb_pj_rel', string='FEB signee (scan)'
    )

    def action_soumettre(self):
        self.ensure_one()
        if not self.justification or not self.specifications:
            raise exceptions.UserError(
                "La justification et les specifications sont obligatoires avant soumission."
            )
        self.write({'statut': 'soumise'})
        self.message_post(body="FEB soumise au chef de departement.")

    def action_viser_chef(self):
        self.ensure_one()
        self.write({
            'statut': 'visee_chef',
            'date_visa_chef': fields.Date.today(),
        })
        self.message_post(body="FEB visee par le chef de departement.")

    def action_viser_caf(self):
        self.ensure_one()
        self.write({
            'statut': 'visee_caf',
            'date_visa_caf': fields.Date.today(),
        })
        self.message_post(body="FEB visee CAF – disponibilite budgetaire confirmee.")

    def action_autoriser_de(self):
        self.ensure_one()
        self.write({
            'statut': 'autorisee',
            'date_autorisation_de': fields.Date.today(),
        })
        self.message_post(body="FEB autorisee par le Directeur Executif.")

    def action_rejeter(self):
        self.ensure_one()
        if not self.motif_rejet:
            raise exceptions.UserError("Renseignez le motif de rejet.")
        self.write({'statut': 'rejetee'})
        self.message_post(body=f"FEB rejetee : {self.motif_rejet}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.feb')
                    or 'FEB-2026-001'
                )
        return super().create(vals_list)


# ═══════════════════════════════════════════════════════
# P-PL-02 – PAIEMENT HONORAIRES CONSULTANTS
# Manuel RESADE Carnet E Module 02 – B.4/B.5/B.6
# Specificites : paiement par tranches + verification fiscale
# Documents : RESADE-F-PL-02-01 (checklist) + RESADE-F-PL-02-02 (fiche fiscale)
# ═══════════════════════════════════════════════════════
class ResadeMarcheHonoraires(models.Model):
    _name = 'resade.marche.honoraires'
    _description = 'Paiement honoraires consultant – P-PL-02'
    _inherit = ['mail.thread']
    _order = 'marche_id, num_tranche'

    name = fields.Char(
        string='Ref. paiement honoraires', required=True,
        readonly=True, default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marche', ondelete='cascade', required=True
    )
    asf_id = fields.Many2one(
        'resade.marche.asf', string='ASF liee',
        domain="[('marche_id', '=', marche_id)]",
        help='ASF obligatoire et inconditionnelle avant tout paiement – P-PL-02 B.3'
    )

    # Structure paiement par tranches (Manuel B.4)
    num_tranche = fields.Integer(string='N° tranche', default=1)
    type_tranche = fields.Selection([
        ('avance', 'Avance de demarrage (20-30% – si contrat le prevoit)'),
        ('intermediaire', 'Tranche intermediaire (30-40% – sur livrable d etape)'),
        ('solde', 'Solde final (40-70% – sur livrable final valide)'),
        ('unique', 'Paiement unique (contrat a forfait simple)'),
    ], string='Type de tranche', required=True, default='unique')

    pct_tranche = fields.Float(string='% des honoraires totaux')
    montant_brut = fields.Monetary(
        string='Montant brut honoraires', currency_field='currency_id', required=True
    )
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)

    # Verification fiscale (Manuel B.5 – RESADE-F-PL-02-02)
    statut_fiscal_consultant = fields.Selection([
        ('resident_bf', 'Resident fiscal Burkina Faso'),
        ('non_resident', 'Non-resident (expertise internationale)'),
        ('risque_requalification', 'Risque requalification en contrat de travail'),
    ], string='Statut fiscal du consultant', required=True, default='resident_bf')

    retenue_source_applicable = fields.Boolean(
        string='Retenue a la source applicable',
        compute='_compute_retenue_source', store=True
    )
    taux_retenue = fields.Float(
        string='Taux retenue a la source (%)',
        help='Taux DGI Burkina Faso applicable selon statut fiscal et type de prestation'
    )
    montant_retenue = fields.Monetary(
        string='Montant retenue a la source',
        compute='_compute_montants_nets', store=True, currency_field='currency_id'
    )
    montant_net = fields.Monetary(
        string='Montant net a payer',
        compute='_compute_montants_nets', store=True, currency_field='currency_id'
    )
    avis_fiscal_requis = fields.Boolean(
        string='Avis fiscal DGI requis',
        help='Obligatoire pour certaines prestations selon legislation burkinabe (seuil DGI)'
    )
    avis_fiscal_obtenu = fields.Boolean(string='Avis fiscal DGI obtenu', default=False)
    ref_avis_fiscal = fields.Char(string='Ref. avis fiscal DGI')
    fiche_fiscale_etablie = fields.Boolean(
        string='Fiche verification fiscale etablie (RESADE-F-PL-02-02)',
        default=False
    )

    # Double signature DE + CAF (Manuel P-PL-02 B.6 etape 6)
    ordre_virement_prepare = fields.Boolean(
        string='Ordre de virement prepare par CAF', default=False
    )
    signe_caf = fields.Boolean(string='Signe CAF', default=False, tracking=True)
    signe_de = fields.Boolean(string='Signe DE', default=False, tracking=True)
    date_double_signature = fields.Date(string='Date double signature')
    double_signature_ok = fields.Boolean(
        string='Double signature complete (DE + CAF)',
        compute='_compute_double_sig', store=True
    )

    # Execution paiement
    mode_paiement = fields.Selection([
        ('virement', 'Virement bancaire'),
        ('cheque', 'Cheque'),
        ('mobile_money', 'Mobile Money'),
    ], string='Mode de paiement', default='virement')
    reference_virement = fields.Char(string='Reference virement / cheque')
    date_execution = fields.Date(string='Date execution paiement')
    comptabilise_sage = fields.Boolean(
        string='Comptabilise dans SAGE le jour de paiement',
        help='Regle absolue : comptabilisation SAGE le jour meme de l execution – P-PL-01 B.5 etape 6'
    )
    code_analytique_sage = fields.Char(
        string='Code analytique SAGE',
        help='Imputation analytique au code projet correspondant'
    )

    # ─── Intégration Comptabilité Odoo Enterprise ──────
    journal_id = fields.Many2one(
        'account.journal', string='Journal de paiement (banque/caisse)',
        domain="[('type', 'in', ('bank', 'cash'))]"
    )
    move_id = fields.Many2one(
        'account.move', string='Facture consultant (Odoo)', readonly=True, copy=False
    )
    payment_id = fields.Many2one(
        'account.payment', string='Paiement (Odoo)', readonly=True, copy=False
    )

    # Checklist dossier paiement (RESADE-F-PL-02-01)
    cl_asf_presente = fields.Boolean(string='ASF validee presente dans le dossier')
    cl_facture_conforme = fields.Boolean(string='Facture conforme au taux et tranche contractuels')
    cl_contrat_tdr = fields.Boolean(string='Contrat + TDR presents')
    cl_livrable_archive = fields.Boolean(string='Livrable valide archive dans GED')
    cl_fiche_fiscale = fields.Boolean(string='Fiche verification fiscale etablie')
    cl_rib_presente = fields.Boolean(string='RIB consultant present (1er paiement ou modif)')

    dossier_complet = fields.Boolean(
        string='Dossier de paiement complet',
        compute='_compute_dossier_complet', store=True
    )

    statut = fields.Selection([
        ('brouillon', 'En constitution'),
        ('verifie', 'Dossier verifie par CAF'),
        ('signe', 'Double signature obtenue'),
        ('paye', 'Paiement execute'),
        ('comptabilise', 'Comptabilise dans SAGE'),
    ], string='Statut', default='brouillon', tracking=True)

    pj_dossier = fields.Many2many(
        'ir.attachment', 'honoraires_pj_rel',
        string='Pieces justificatives (ASF, facture, fiche fiscale...)'
    )
    note = fields.Text(string='Notes / observations')

    @api.depends('statut_fiscal_consultant')
    def _compute_retenue_source(self):
        for rec in self:
            rec.retenue_source_applicable = (
                rec.statut_fiscal_consultant == 'non_resident'
            )

    @api.depends('montant_brut', 'taux_retenue', 'retenue_source_applicable')
    def _compute_montants_nets(self):
        for rec in self:
            if rec.retenue_source_applicable and rec.taux_retenue:
                rec.montant_retenue = rec.montant_brut * rec.taux_retenue / 100
            else:
                rec.montant_retenue = 0.0
            rec.montant_net = rec.montant_brut - rec.montant_retenue

    @api.depends('signe_caf', 'signe_de')
    def _compute_double_sig(self):
        for rec in self:
            rec.double_signature_ok = rec.signe_caf and rec.signe_de

    @api.depends(
        'cl_asf_presente', 'cl_facture_conforme', 'cl_contrat_tdr',
        'cl_livrable_archive', 'cl_fiche_fiscale', 'cl_rib_presente'
    )
    def _compute_dossier_complet(self):
        for rec in self:
            rec.dossier_complet = all([
                rec.cl_asf_presente, rec.cl_facture_conforme,
                rec.cl_contrat_tdr, rec.cl_livrable_archive,
                rec.cl_fiche_fiscale,
            ])

    def action_verifier_dossier(self):
        self.ensure_one()
        if not self.asf_id:
            raise exceptions.UserError(
                "L ASF est obligatoire et inconditionnelle avant tout paiement "
                "d honoraires – P-PL-02 B.3 risque 1."
            )
        if not self.dossier_complet:
            raise exceptions.UserError(
                "Le dossier de paiement n est pas complet. "
                "Verifiez la checklist RESADE-F-PL-02-01."
            )
        if self.avis_fiscal_requis and not self.avis_fiscal_obtenu:
            raise exceptions.UserError(
                "L avis fiscal DGI est requis et n a pas encore ete obtenu – P-PL-02 B.5."
            )
        self.write({'statut': 'verifie'})
        self.message_post(body="Dossier paiement honoraires verifie par le CAF.")

    def action_signer_caf(self):
        self.ensure_one()
        if self.statut not in ('verifie', 'brouillon'):
            raise exceptions.UserError("Verifiez le dossier avant de signer.")
        self.write({'signe_caf': True})
        if self.signe_de:
            self.write({
                'statut': 'signe',
                'date_double_signature': fields.Date.today(),
            })
        self.message_post(body="Signature CAF apposee sur l ordre de virement.")

    def action_signer_de(self):
        self.ensure_one()
        self.write({'signe_de': True})
        if self.signe_caf:
            self.write({
                'statut': 'signe',
                'date_double_signature': fields.Date.today(),
            })
        self.message_post(body="Signature DE apposee – double signature complete.")

    def _get_expense_account(self):
        self.ensure_one()
        account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', self.env.company.id),
        ], limit=1)
        if not account:
            raise exceptions.UserError(
                "Aucun compte de charge n'est configuré dans le Plan comptable."
            )
        return account

    def _creer_facture_consultant(self):
        """Crée et poste la facture consultant (account.move), pour le montant NET
        (après retenue à la source déjà calculée sur cette tranche)."""
        self.ensure_one()
        if self.move_id:
            return self.move_id
        if not self.marche_id.fournisseur_id:
            raise exceptions.UserError("Aucun consultant retenu sur le dossier marché.")
        partner = self.marche_id.fournisseur_id.get_or_create_partner()
        account = self._get_expense_account()
        analytic_distribution = False
        analytic_account = (
            self.marche_id.ligne_budgetaire_id.analytic_account_id
            or self.marche_id.analytic_account_id
        )
        if analytic_account:
            analytic_distribution = {str(analytic_account.id): 100.0}

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'ref': f"{self.marche_id.name} - Tranche {self.num_tranche}",
            'invoice_line_ids': [(0, 0, {
                'name': f"Honoraires {self.get_type_tranche_display() if hasattr(self, 'get_type_tranche_display') else self.type_tranche} – {self.name}",
                'quantity': 1,
                'price_unit': self.montant_net,
                'account_id': account.id,
                'analytic_distribution': analytic_distribution,
            })],
        })
        move.action_post()
        self.move_id = move.id
        return move

    def _creer_et_reconcilier_paiement(self, move):
        self.ensure_one()
        if not self.journal_id:
            raise exceptions.UserError(
                "Sélectionnez le journal bancaire/caisse utilisé pour ce paiement."
            )
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': move.partner_id.id,
            'amount': self.montant_net,
            'journal_id': self.journal_id.id,
            'memo': self.reference_virement or self.name,
            'date': fields.Date.today(),
        })
        payment.action_post()
        move_lines = move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        payment_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        (move_lines + payment_lines).reconcile()
        self.payment_id = payment.id
        return payment

    def action_executer_paiement(self):
        """
        P-PL-02 étape 6 : exécution du paiement (montant NET, retenue à la
        source déjà déduite) + génération de la facture et du paiement
        Odoo Accounting réels (remplace la simple case SAGE).
        """
        self.ensure_one()
        if not self.double_signature_ok:
            raise exceptions.UserError(
                "La double signature DE + CAF est obligatoire avant l execution "
                "du paiement – P-PL-02 B.6 etape 6."
            )
        if not self.reference_virement:
            raise exceptions.UserError("Renseignez la reference du virement / cheque.")
        move = self._creer_facture_consultant()
        self._creer_et_reconcilier_paiement(move)
        self.write({
            'statut': 'paye',
            'date_execution': fields.Date.today(),
            'comptabilise_sage': True,
        })

        # ─── Synchronisation automatique avec le Budget RESADE ─────
        # Les honoraires sont payés par tranches : chaque tranche exécutée
        # incrémente le montant réellement payé sur le dossier marché, et
        # ne solde l'engagement budgétaire qu'une seule fois (1ère tranche).
        marche = self.marche_id
        marche.montant_paye = (marche.montant_paye or 0.0) + self.montant_net
        if marche.state == 'certifie':
            marche.action_payer()
        elif marche.ligne_budgetaire_id and marche.credit_budgetaire_reserve:
            marche.ligne_budgetaire_id.constater_realisation(0.0, self.montant_net)

        self.message_post(
            body=f"💳 Paiement exécuté – Ref : {self.reference_virement} – "
                 f"Montant net : {self.montant_net:,.0f} FCFA "
                 f"(retenue source : {self.montant_retenue:,.0f}).\n"
                 f"Facture Odoo : {move.name} — Paiement : {self.payment_id.name}.\n"
                 f"Budget RESADE synchronisé automatiquement."
        )

    def action_comptabiliser_sage(self):
        """Conservé pour compatibilité : clôture le dossier (idempotent avec action_executer_paiement)."""
        self.ensure_one()
        if self.statut not in ('paye', 'comptabilise'):
            raise exceptions.UserError("Executez le paiement avant la comptabilisation.")
        if not self.move_id or not self.payment_id:
            move = self._creer_facture_consultant()
            self._creer_et_reconcilier_paiement(move)
        self.write({'statut': 'comptabilise', 'comptabilise_sage': True})
        self.message_post(
            body=f"✅ Comptabilisé — Facture {self.move_id.name}, Paiement {self.payment_id.name}."
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.honoraires')
                    or 'HON-2026-001'
                )
        return super().create(vals_list)


# ═══════════════════════════════════════════════════════
# P-PL-01 – CHECKLIST DOSSIER PAIEMENT FOURNISSEUR
# Manuel RESADE Carnet E Module 02 – B.4
# Document RESADE-F-PL-01-01
# ═══════════════════════════════════════════════════════
class ResadeMarchePaiementFournisseur(models.Model):
    _name = 'resade.marche.paiement'
    _description = 'Dossier paiement fournisseur – P-PL-01'
    _inherit = ['mail.thread']
    _order = 'marche_id, date_creation desc'

    name = fields.Char(
        string='Ref. dossier paiement', required=True,
        readonly=True, default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marche', ondelete='cascade', required=True
    )
    date_creation = fields.Date(
        string='Date constitution dossier', default=fields.Date.today
    )
    montant = fields.Monetary(
        string='Montant a payer', currency_field='currency_id', required=True
    )
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)

    # ─── Intégration Comptabilité Odoo Enterprise ──────
    journal_id = fields.Many2one(
        'account.journal', string='Journal de paiement (banque/caisse)',
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="Journal bancaire ou caisse utilisé pour exécuter le paiement."
    )
    move_id = fields.Many2one(
        'account.move', string='Facture fournisseur (Odoo)', readonly=True, copy=False
    )
    payment_id = fields.Many2one(
        'account.payment', string='Paiement (Odoo)', readonly=True, copy=False
    )

    # Checklist pieces obligatoires (RESADE-F-PL-01-01 – Manuel B.4)
    cl_feb_visee = fields.Boolean(
        string='FEB visee et autorisee (toujours)',
        help='Fiche Expression des Besoins signee demandeur + CAF + DE'
    )
    cl_bc_contrat = fields.Boolean(
        string='Bon de commande / contrat signe (toujours)'
    )
    cl_pvr = fields.Boolean(
        string='PVR conforme (fournitures et materiels)',
        help='Obligatoire pour fournitures – Facility Mgr + Demandeur + CAF'
    )
    cl_asf = fields.Boolean(
        string='ASF validee (prestations intellectuelles et services)',
        help='Obligatoire pour services – Chef dept / Pool R&D'
    )
    cl_facture_certifiee = fields.Boolean(
        string='Facture originale certifiee par le CAF (toujours)'
    )
    cl_rib = fields.Boolean(
        string='RIB fournisseur (1er paiement ou changement domiciliation)'
    )
    cl_cotations = fields.Boolean(
        string='Devis / cotations (entente directe > 200 000 FCFA)'
    )
    cl_pv_cam = fields.Boolean(
        string='PV CAM (consultation restreinte et AOO)'
    )

    dossier_complet = fields.Boolean(
        string='Dossier certifie complet par le CAF',
        compute='_compute_dossier', store=True
    )

    # Verification budgetaire SAGE
    disponibilite_sage = fields.Boolean(
        string='Disponibilite budgetaire confirmee dans SAGE – P-PL-01 B.5 etape 2'
    )
    code_analytique_sage = fields.Char(string='Code analytique SAGE')

    # Ordre de virement – double signature DE + CAF (P-PL-01 B.5 etapes 3 et 4)
    ordre_virement_prepare = fields.Boolean(
        string='Ordre de virement / cheque prepare'
    )
    signe_caf = fields.Boolean(string='Signature CAF', default=False, tracking=True)
    signe_de = fields.Boolean(string='Signature DE', default=False, tracking=True)
    double_signature_ok = fields.Boolean(
        string='Double signature DE + CAF complete',
        compute='_compute_double_sig', store=True
    )
    date_double_signature = fields.Date(string='Date double signature')

    # Execution (P-PL-01 B.5 etapes 5 a 8)
    mode_paiement = fields.Selection([
        ('virement', 'Virement bancaire'),
        ('cheque', 'Cheque'),
        ('mobile_money', 'Mobile Money'),
    ], string='Mode de paiement', default='virement')
    reference_paiement = fields.Char(string='Reference virement / N° cheque')
    date_execution = fields.Date(string='Date execution paiement')
    fournisseur_notifie = fields.Boolean(
        string='Fournisseur notifie (email / SMS)',
        help='P-PL-01 B.5 etape 7 – notification obligatoire apres execution'
    )
    comptabilise_sage = fields.Boolean(
        string='Comptabilise SAGE le jour de paiement',
        help='Regle : comptabilisation SAGE le jour meme – P-PL-01 B.5 etape 6'
    )
    dossier_archive_ged = fields.Boolean(
        string='Dossier complet archive dans GED',
        help='P-PL-01 B.5 etape 8 + P-DA-02'
    )
    ref_ged = fields.Char(string='Reference GED')

    statut = fields.Selection([
        ('constitution', 'En constitution'),
        ('complet', 'Dossier complet – en attente signature'),
        ('signe', 'Double signature obtenue'),
        ('execute', 'Paiement execute'),
        ('comptabilise', 'Comptabilise et archive'),
    ], string='Statut', default='constitution', tracking=True)

    pj_dossier = fields.Many2many(
        'ir.attachment', 'paiement_pj_rel',
        string='Pieces justificatives completes'
    )
    motif_blocage = fields.Text(string='Motif blocage / pieces manquantes')

    @api.depends('cl_feb_visee', 'cl_bc_contrat', 'cl_facture_certifiee')
    def _compute_dossier(self):
        for rec in self:
            # Pieces toujours obligatoires
            rec.dossier_complet = all([
                rec.cl_feb_visee,
                rec.cl_bc_contrat,
                rec.cl_facture_certifiee,
            ])

    @api.depends('signe_caf', 'signe_de')
    def _compute_double_sig(self):
        for rec in self:
            rec.double_signature_ok = rec.signe_caf and rec.signe_de

    def action_certifier_dossier(self):
        self.ensure_one()
        if not self.dossier_complet:
            raise exceptions.UserError(
                "Le dossier n est pas complet. Les pieces FEB + BC/contrat + "
                "facture certifiee sont toujours obligatoires – P-PL-01 B.4."
            )
        if not self.disponibilite_sage:
            raise exceptions.UserError(
                "Confirmez la disponibilite budgetaire dans SAGE – P-PL-01 B.5 etape 2."
            )
        self.write({'statut': 'complet'})
        self.message_post(body="Dossier paiement certifie complet par le CAF (RESADE-F-PL-01-01).")

    def action_signer_caf(self):
        self.ensure_one()
        self.write({'signe_caf': True})
        if self.signe_de:
            self.write({
                'statut': 'signe',
                'date_double_signature': fields.Date.today(),
            })
        self.message_post(body="Signature CAF apposee.")

    def action_signer_de(self):
        self.ensure_one()
        self.write({'signe_de': True})
        if self.signe_caf:
            self.write({
                'statut': 'signe',
                'date_double_signature': fields.Date.today(),
            })
        self.message_post(body="Signature DE apposee – double signature complete.")

    def _get_expense_account(self):
        """Compte de charge par défaut pour la facture fournisseur générée."""
        self.ensure_one()
        account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', self.env.company.id),
        ], limit=1)
        if not account:
            raise exceptions.UserError(
                "Aucun compte de charge n'est configuré dans le Plan comptable. "
                "Configurez la Comptabilité Odoo (Paramètres > Comptabilité) avant paiement."
            )
        return account

    def _creer_facture_fournisseur(self):
        """Crée et poste une facture fournisseur (account.move) Odoo pour ce dossier,
        avec distribution analytique vers le compte lié à la ligne budgétaire RESADE."""
        self.ensure_one()
        if self.move_id:
            return self.move_id
        if not self.marche_id.fournisseur_id:
            raise exceptions.UserError("Aucun fournisseur retenu sur le dossier marché.")
        partner = self.marche_id.fournisseur_id.get_or_create_partner()
        account = self._get_expense_account()
        analytic_distribution = False
        analytic_account = (
            self.marche_id.ligne_budgetaire_id.analytic_account_id
            or self.marche_id.analytic_account_id
        )
        if analytic_account:
            analytic_distribution = {str(analytic_account.id): 100.0}

        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'ref': self.marche_id.name,
            'invoice_line_ids': [(0, 0, {
                'name': f"{self.marche_id.objet} – Dossier paiement {self.name}",
                'quantity': 1,
                'price_unit': self.montant,
                'account_id': account.id,
                'analytic_distribution': analytic_distribution,
            })],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.move_id = move.id
        return move

    def _creer_et_reconcilier_paiement(self, move):
        """Crée un account.payment fournisseur, le poste, et le lettre avec la facture."""
        self.ensure_one()
        if not self.journal_id:
            raise exceptions.UserError(
                "Sélectionnez le journal bancaire/caisse utilisé pour ce paiement."
            )
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': move.partner_id.id,
            'amount': self.montant,
            'journal_id': self.journal_id.id,
            'memo': self.reference_paiement or self.name,
            'date': fields.Date.today(),
        })
        payment.action_post()
        # Lettrage automatique paiement <-> facture
        move_lines = move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        payment_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        (move_lines + payment_lines).reconcile()
        self.payment_id = payment.id
        return payment

    def action_executer(self):
        """
        P-PL-01 étape 4-6 : exécution du paiement + comptabilisation réelle.
        Génère une facture fournisseur (account.move) et un paiement
        (account.payment) dans Odoo Accounting Enterprise — remplace la
        double saisie SAGE par une écriture comptable auditable native.
        """
        self.ensure_one()
        if not self.double_signature_ok:
            raise exceptions.UserError(
                "Double signature DE + CAF obligatoire avant execution – "
                "P-PL-01 B.5 etape 4."
            )
        if not self.reference_paiement:
            raise exceptions.UserError("Renseignez la reference du virement ou du cheque.")
        move = self._creer_facture_fournisseur()
        self._creer_et_reconcilier_paiement(move)
        self.write({
            'statut': 'execute',
            'date_execution': fields.Date.today(),
            'comptabilise_sage': True,
        })

        # ─── Synchronisation automatique avec le Budget RESADE ─────
        # Sans ceci, l'exécution comptable (facture+paiement réels) et la
        # réalisation budgétaire (constater_realisation) restaient deux
        # actions manuelles séparées, avec risque de désynchronisation
        # budget ↔ comptabilité. On les lie ici en un seul clic.
        marche = self.marche_id
        marche.montant_paye = (marche.montant_paye or 0.0) + self.montant
        if marche.state == 'certifie':
            marche.action_payer()
        elif marche.ligne_budgetaire_id and marche.credit_budgetaire_reserve:
            # Dossier déjà clôturé (paiement complémentaire sur le même
            # marché) : l'engagement a déjà été soldé au premier paiement,
            # on ne fait que constater le complément réellement décaissé.
            marche.ligne_budgetaire_id.constater_realisation(0.0, self.montant)

        self.message_post(
            body=f"💳 Paiement exécuté – Ref : {self.reference_paiement} – "
                 f"Montant : {self.montant:,.0f} FCFA.\n"
                 f"Facture Odoo : {move.name} — Paiement : {self.payment_id.name}.\n"
                 f"Budget RESADE synchronisé automatiquement."
        )

    def action_comptabiliser(self):
        """
        Conservé pour compatibilité avec les vues existantes : marque le
        dossier comme comptabilisé. La comptabilisation réelle (facture +
        paiement Odoo) est désormais faite automatiquement par
        action_executer() ; cette méthode ne fait que clôturer le dossier
        si ce n'est pas déjà le cas (idempotente).
        """
        self.ensure_one()
        if self.statut not in ('execute', 'comptabilise'):
            raise exceptions.UserError("Executez le paiement avant la comptabilisation.")
        if not self.move_id or not self.payment_id:
            # Sécurité : si jamais l'écriture n'a pas été créée à l'exécution.
            move = self._creer_facture_fournisseur()
            self._creer_et_reconcilier_paiement(move)
        self.write({'statut': 'comptabilise', 'comptabilise_sage': True})
        self.message_post(
            body=f"✅ Dossier comptabilisé — Facture {self.move_id.name}, "
                 f"Paiement {self.payment_id.name}. "
                 f"Notification fournisseur : {'OK' if self.fournisseur_notifie else 'a faire'}."
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.paiement')
                    or 'PAI-2026-001'
                )
        return super().create(vals_list)


# ═══════════════════════════════════════════════════════
# P-SCM-01 – KPI TABLEAU DE BORD SUIVI MARCHES
# Manuel RESADE Carnet E Module 03
# Mise a jour mensuelle – Rapport CA trimestriel
# ═══════════════════════════════════════════════════════
class ResadeMarcheKPI(models.Model):
    _name = 'resade.marche.kpi'
    _description = 'KPI Tableau de bord suivi marches – P-SCM-01'
    _inherit = ['mail.thread']
    _order = 'periode desc'

    name = fields.Char(string='Periode', required=True, readonly=True, default='Nouveau')
    periode = fields.Date(string='Date du tableau de bord', required=True)
    genere_par = fields.Many2one('res.users', string='Genere par', readonly=True)
    date_generation = fields.Datetime(string='Date generation', readonly=True)

    # KPI Manuel P-SCM-01 B.12
    # --- Passation ---
    nb_dossiers_en_cours = fields.Integer(
        string='Nb dossiers en cours de passation', readonly=True
    )
    nb_dossiers_execution = fields.Integer(
        string='Nb dossiers en execution', readonly=True
    )
    nb_dossiers_payes = fields.Integer(
        string='Nb dossiers payes / clotures (periode)', readonly=True
    )
    nb_dossiers_annules = fields.Integer(
        string='Nb dossiers annules (periode)', readonly=True
    )

    # --- Conformite ---
    taux_pvr_conformes = fields.Float(
        string='Taux PVR conformes (%)',
        help='(Nb PVR statut conforme / Nb PVR total) x 100 – cible 100%',
        readonly=True
    )
    taux_factures_certifiees = fields.Float(
        string='Taux factures certifiees (%)',
        help='(Nb factures certifiees / Nb factures recues) x 100 – cible 100%',
        readonly=True
    )
    taux_asf_dans_delai = fields.Float(
        string='Taux ASF validees dans delai grille (%)',
        help='(Nb ASF dans delai / Nb ASF recues) x 100 – cible >=85%',
        readonly=True
    )
    taux_paiements_double_signature = fields.Float(
        string='Taux paiements avec double signature (%)',
        help='(Nb ordres double signature / Nb ordres totaux) x 100 – cible 100%',
        readonly=True
    )

    # --- Delais ---
    delai_moyen_passation = fields.Float(
        string='Delai moyen passation (jours)',
        help='Delai moyen entre requisition et attribution',
        readonly=True
    )
    delai_moyen_paiement = fields.Float(
        string='Delai moyen paiement (jours apres dossier complet)',
        help='Cible : <= 5 jours ouvrables – P-PL-01 B.12',
        readonly=True
    )

    # --- Montants ---
    montant_total_en_cours = fields.Monetary(
        string='Montant total marches en cours', currency_field='currency_id',
        readonly=True
    )
    montant_total_paye_periode = fields.Monetary(
        string='Montant total paye (periode)', currency_field='currency_id',
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )

    # Alertes
    nb_dossiers_en_retard = fields.Integer(
        string='Nb dossiers en retard sur calendrier', readonly=True
    )
    nb_factures_non_certifiees = fields.Integer(
        string='Nb factures recues non certifiees', readonly=True
    )
    nb_pvr_non_conformes = fields.Integer(
        string='Nb PVR non conformes / avec reserves', readonly=True
    )

    note_analyse = fields.Text(string='Analyse et points d attention CAF')

    def action_generer_kpi(self):
        """Calcul automatique des KPI depuis les donnees du module."""
        self.ensure_one()
        Marche = self.env['resade.marche']
        PVR = self.env['resade.marche.pvr']
        Facture = self.env['resade.marche.facture']
        ASF = self.env['resade.marche.asf']
        Paiement = self.env['resade.marche.paiement']

        # Dossiers par statut
        en_passation = Marche.search([
            ('state', 'in', [
                'valide_resp', 'valide_caf', 'ao_lance',
                'depouillement', 'analyse', 'cam_convoquee', 'notifie'
            ])
        ])
        en_execution = Marche.search([
            ('state', 'in', ['bon_commande', 'en_cours', 'reception', 'certifie'])
        ])
        payes = Marche.search([('state', '=', 'paye')])
        annules = Marche.search([('state', '=', 'annule')])

        # PVR
        pvr_tous = PVR.search([])
        pvr_conformes = pvr_tous.filtered(lambda p: p.statut == 'conforme')
        pvr_nc = pvr_tous.filtered(lambda p: p.statut in ['rejet_partiel', 'rejet_total', 'reserves'])
        taux_pvr = (len(pvr_conformes) / len(pvr_tous) * 100) if pvr_tous else 100.0

        # Factures
        fac_tous = Facture.search([])
        fac_certifiees = fac_tous.filtered(lambda f: f.statut == 'certifiee')
        fac_non_certifiees = fac_tous.filtered(lambda f: f.statut not in ['certifiee', 'rejetee'])
        taux_fac = (len(fac_certifiees) / len(fac_tous) * 100) if fac_tous else 100.0

        # ASF
        asf_tous = ASF.search([])
        asf_valides = asf_tous.filtered(lambda a: a.statut_validation == 'valide')
        taux_asf = (len(asf_valides) / len(asf_tous) * 100) if asf_tous else 100.0

        # Paiements double signature
        pai_tous = Paiement.search([('statut', 'in', ['signe', 'execute', 'comptabilise'])])
        pai_double_sig = pai_tous.filtered(lambda p: p.double_signature_ok)
        taux_sig = (len(pai_double_sig) / len(pai_tous) * 100) if pai_tous else 100.0

        # Delai moyen paiement
        delai_moy = 0.0
        pai_executes = Paiement.search([('statut', 'in', ['execute', 'comptabilise'])])
        if pai_executes:
            delais = []
            for p in pai_executes:
                if p.date_creation and p.date_execution:
                    d = (p.date_execution - p.date_creation).days
                    delais.append(d)
            delai_moy = sum(delais) / len(delais) if delais else 0.0

        # Montants
        montant_en_cours = sum(
            (m.montant_final or m.montant_estime or 0) for m in en_execution
        )
        montant_paye = sum(m.montant_paye or 0 for m in payes)

        # Dossiers en retard (date_fin_prevue < aujourd'hui et pas cloture)
        aujourd_hui = fields.Date.today()
        en_retard = en_execution.filtered(
            lambda m: m.date_fin_prevue and m.date_fin_prevue < aujourd_hui
        )

        self.write({
            'nb_dossiers_en_cours': len(en_passation),
            'nb_dossiers_execution': len(en_execution),
            'nb_dossiers_payes': len(payes),
            'nb_dossiers_annules': len(annules),
            'taux_pvr_conformes': round(taux_pvr, 1),
            'taux_factures_certifiees': round(taux_fac, 1),
            'taux_asf_dans_delai': round(taux_asf, 1),
            'taux_paiements_double_signature': round(taux_sig, 1),
            'delai_moyen_paiement': round(delai_moy, 1),
            'montant_total_en_cours': montant_en_cours,
            'montant_total_paye_periode': montant_paye,
            'nb_dossiers_en_retard': len(en_retard),
            'nb_factures_non_certifiees': len(fac_non_certifiees),
            'nb_pvr_non_conformes': len(pvr_nc),
            'genere_par': self.env.uid,
            'date_generation': fields.Datetime.now(),
        })
        self.message_post(body="KPI tableau de bord recalcules automatiquement.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                today = fields.Date.today()
                vals['name'] = f"TDB-{today.strftime('%Y-%m')}"
                if 'periode' not in vals:
                    vals['periode'] = today
        return super().create(vals_list)
