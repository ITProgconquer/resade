from odoo import models, fields, api, exceptions


class ResadeMarcheCotation(models.Model):
    """
    Fiche de comparaison des cotations – P-PTM-01 (Entente directe)
    Manuel RESADE Carnet D Module 02 – B.5 étape 2 & 3
    Règle : minimum 3 cotations écrites pour tout achat > 200 000 FCFA
    Exception : 1 cotation si fournisseur unique / urgence DE / montant ≤ 200 000
    Document référence : RESADE-F-PTM-01-01
    """
    _name = 'resade.marche.cotation'
    _description = 'Cotation fournisseur (P-PTM-01 – Entente directe)'
    _order = 'marche_id, rang'

    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', ondelete='cascade', required=True
    )
    rang = fields.Integer(string='N°', default=1)
    fournisseur_nom = fields.Char(string='Fournisseur consulté', required=True)
    fournisseur_id = fields.Many2one(
        'resade.fournisseur', string='Fournisseur (fichier)',
        help='Lier au fichier fournisseur si existant'
    )
    date_cotation = fields.Date(string='Date cotation', default=fields.Date.today)
    montant_cotation = fields.Monetary(string='Montant coté', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)
    forme = fields.Selection([
        ('ecrite', 'Écrite (document scanné)'),
        ('verbale', 'Verbale (documentée)'),
        ('email', 'Email'),
        ('proforma', 'Facture pro forma'),
    ], string='Forme de la cotation', default='ecrite')
    pj_cotation = fields.Many2many(
        'ir.attachment', 'cotation_pj_rel', string='Pièce jointe cotation'
    )
    retenue = fields.Boolean(string='Cotation retenue', default=False)
    justification_choix = fields.Text(
        string='Justification du choix',
        help='Obligatoire si cette cotation est retenue (P-PTM-01 B.5 étape 3)'
    )
    note = fields.Text(string='Observations')

    @api.constrains('retenue', 'justification_choix')
    def _check_justification(self):
        for rec in self:
            if rec.retenue and not rec.justification_choix:
                raise exceptions.ValidationError(
                    "La justification du choix est obligatoire pour la cotation retenue (P-PTM-01)."
                )


class ResadeMarcheASF(models.Model):
    """
    Attestation de Service Fait (ASF) – P-RC-03
    Manuel RESADE Carnet E Module 01 – Réception prestations intellectuelles
    Utilisée pour : consultants individuels, firmes, services spécialisés
    Document référence : RESADE-F-RC-02-03
    Le valideur compétent dépend du type de livrable (grille B.4 du Manuel)
    """
    _name = 'resade.marche.asf'
    _description = 'Attestation de Service Fait (ASF) – P-RC-03'
    _inherit = ['mail.thread']
    _order = 'marche_id, date_remise desc'

    name = fields.Char(
        string='N° ASF', required=True, readonly=True,
        default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', ondelete='cascade', required=True
    )

    # Nature du livrable (grille B.4 Manuel Carnet E)
    type_livrable = fields.Selection([
        ('rapport_etude', "Rapport d'étude / recherche (≤15j Pool R&D)"),
        ('base_donnees', 'Base de données / fichier collecte (≤10j Pool R&D)'),
        ('rapport_formation', 'Rapport de formation dispensée (≤5j Chef dept)'),
        ('logiciel', 'Logiciel / application collecte (≤15j Pool R&D + CSI)'),
        ('rapport_consultance', 'Rapport de consultance gestion (≤10j CAF + DE)'),
        ('article_scientifique', 'Article / publication scientifique (≤20j Pool R&D + DE)'),
        ('autre', 'Autre livrable'),
    ], string='Type de livrable', required=True)

    intitule_livrable = fields.Char(string='Intitulé du livrable', required=True)
    date_remise = fields.Date(string='Date remise livrable', required=True)
    date_limite_validation = fields.Date(
        string='Date limite validation',
        help='Calculée selon grille B.4 du Manuel Carnet E'
    )

    # Valideur compétent (selon grille type livrable)
    valideur_id = fields.Many2one(
        'hr.employee', string='Valideur compétent',
        help='Pool R&D pour livrables de recherche, Chef dept pour formation, CAF pour consultance'
    )
    departement_valideur = fields.Char(string='Département / pool valideur')

    # Résultat de l'évaluation
    statut_validation = fields.Selection([
        ('en_cours', 'Évaluation en cours'),
        ('corrections', 'Corrections demandées'),
        ('valide', 'Validé – ASF émise'),
        ('rejete', 'Rejet définitif'),
    ], string='Statut validation', default='en_cours', tracking=True)

    rapport_evaluation = fields.Text(
        string='Rapport d\'évaluation interne',
        help='RESADE-F-RC-03-01 – Observations du valideur (P-RC-03 B.8 étape 3)'
    )
    corrections_demandees = fields.Text(
        string='Corrections demandées au prestataire'
    )
    nb_cycles_revision = fields.Integer(string='Nb cycles de révision', default=0)

    # ASF émise
    date_validation_finale = fields.Date(string='Date validation finale')
    asf_numero = fields.Char(string='N° ASF officiel')
    pj_livrable = fields.Many2many(
        'ir.attachment', 'asf_pj_livrable_rel', string='Livrable soumis'
    )
    pj_asf = fields.Many2many(
        'ir.attachment', 'asf_pj_asf_rel', string='ASF signée (scan)'
    )

    def action_valider(self):
        self.ensure_one()
        if not self.rapport_evaluation:
            raise exceptions.UserError(
                "Le rapport d'évaluation interne est obligatoire avant d'émettre l'ASF (P-RC-03)."
            )
        self.write({
            'statut_validation': 'valide',
            'date_validation_finale': fields.Date.today(),
        })
        self.message_post(body="✅ Livrable validé – ASF émise.")

    def action_demander_corrections(self):
        self.ensure_one()
        if not self.corrections_demandees:
            raise exceptions.UserError("Listez les corrections demandées au prestataire.")
        self.write({
            'statut_validation': 'corrections',
            'nb_cycles_revision': self.nb_cycles_revision + 1,
        })
        self.message_post(body=f"🔄 Corrections demandées (cycle {self.nb_cycles_revision}).")

    def action_rejeter(self):
        self.ensure_one()
        self.write({'statut_validation': 'rejete'})
        self.message_post(body="❌ Livrable rejeté définitivement.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.asf')
                    or 'ASF-2026-001'
                )
        return super().create(vals_list)


class ResadeMarcheFacture(models.Model):
    """
    Registre de certification des factures – P-RC-02
    Manuel RESADE Carnet E Module 01 – B.5 étapes 1 à 8
    Document : RESADE-F-RC-02-01 (registre entrées) + RESADE-F-RC-02-02 (checklist)
    Règle absolue : aucun paiement sans facture certifiée par le CAF
    """
    _name = 'resade.marche.facture'
    _description = 'Certification de facture fournisseur – P-RC-02'
    _inherit = ['mail.thread']
    _order = 'date_reception desc'

    name = fields.Char(
        string='N° entrée registre', required=True,
        readonly=True, default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', required=True, ondelete='cascade'
    )

    # Identification facture
    numero_facture = fields.Char(string='N° facture fournisseur', required=True)
    date_facture = fields.Date(string='Date de la facture', required=True)
    date_reception = fields.Date(
        string='Date réception facture', default=fields.Date.today, required=True
    )
    fournisseur_id = fields.Many2one(related='marche_id.fournisseur_id', store=True, readonly=True)
    montant_ht = fields.Monetary(string='Montant HT', currency_field='currency_id')
    tva = fields.Float(string='TVA (%)', default=0.0)
    montant_ttc = fields.Monetary(string='Montant TTC', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)

    # Checklist mentions légales obligatoires (B.4 Manuel)
    cl_raison_sociale = fields.Boolean(string='Raison sociale fournisseur présente')
    cl_ifu = fields.Boolean(string='IFU / NIF présent')
    cl_numero_facture = fields.Boolean(string='N° unique et séquentiel présent')
    cl_date_emission = fields.Boolean(string='Date émission postérieure ou égale livraison')
    cl_reference_bc = fields.Boolean(string='Référence BC / contrat RESADE présente')
    cl_description = fields.Boolean(string='Description précise et quantifiée présente')
    cl_prix = fields.Boolean(string='Prix unitaire et total présents')
    cl_coordonnees_bancaires = fields.Boolean(string='Coordonnées bancaires présentes')

    mentions_legales_ok = fields.Boolean(
        string='Mentions légales complètes',
        compute='_compute_mentions', store=True
    )

    # Vérifications
    pvr_ou_asf_present = fields.Boolean(
        string='PVR ou ASF présent(e)',
        help='PVR pour fournitures, ASF pour prestations intellectuelles – obligatoire avant certification'
    )
    ref_pvr_asf = fields.Char(string='Réf. PVR ou N° ASF')
    disponibilite_sage_ok = fields.Boolean(
        string='Disponibilité budgétaire confirmée dans SAGE'
    )
    code_analytique_ok = fields.Boolean(
        string='Code analytique vérifié'
    )

    # Résultat certification
    statut = fields.Selection([
        ('recue', 'Reçue – en cours de vérification'),
        ('incomplete', 'Retournée au fournisseur (incomplète)'),
        ('certifiee', 'Certifiée par le CAF'),
        ('rejetee', 'Rejetée définitivement'),
    ], string='Statut', default='recue', tracking=True)

    date_certification = fields.Date(string='Date certification')
    certifie_par = fields.Many2one('res.users', string='Certifiée par', readonly=True)
    motif_rejet = fields.Text(string='Motif retour / rejet')
    pj_facture = fields.Many2many(
        'ir.attachment', 'facture_pj_rel', string='Facture originale'
    )

    @api.depends(
        'cl_raison_sociale', 'cl_ifu', 'cl_numero_facture', 'cl_date_emission',
        'cl_reference_bc', 'cl_description', 'cl_prix', 'cl_coordonnees_bancaires'
    )
    def _compute_mentions(self):
        for rec in self:
            rec.mentions_legales_ok = all([
                rec.cl_raison_sociale, rec.cl_ifu, rec.cl_numero_facture,
                rec.cl_date_emission, rec.cl_reference_bc, rec.cl_description,
                rec.cl_prix, rec.cl_coordonnees_bancaires
            ])

    def action_certifier(self):
        self.ensure_one()
        if not self.mentions_legales_ok:
            raise exceptions.UserError(
                "Toutes les mentions légales doivent être cochées avant la certification (P-RC-02 B.4)."
            )
        if not self.pvr_ou_asf_present:
            raise exceptions.UserError(
                "Le PVR ou l'ASF doit être présent avant toute certification de facture (règle absolue P-RC-02)."
            )
        if not self.disponibilite_sage_ok:
            raise exceptions.UserError(
                "Confirmez la disponibilité budgétaire dans SAGE avant de certifier (P-RC-02 B.5 étape 5)."
            )
        self.write({
            'statut': 'certifiee',
            'date_certification': fields.Date.today(),
            'certifie_par': self.env.uid,
        })
        self.message_post(body="✔️ Facture certifiée par le CAF (P-RC-02).")

    def action_retourner(self):
        self.ensure_one()
        if not self.motif_rejet:
            raise exceptions.UserError("Renseignez le motif de retour au fournisseur.")
        self.write({'statut': 'incomplete'})
        self.message_post(body=f"📤 Facture retournée au fournisseur : {self.motif_rejet}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.facture')
                    or 'FAC-2026-001'
                )
        return super().create(vals_list)


class ResadeMarchePVR(models.Model):
    """
    Procès-Verbal de Réception (PVR) des fournitures – P-RC-01
    Manuel RESADE Carnet E Module 01 – B.5 étapes 1 à 9
    Document : RESADE-F-RC-01-01
    Règle : PVR obligatoire avant tout paiement de fournitures
    """
    _name = 'resade.marche.pvr'
    _description = 'Procès-Verbal de Réception (PVR) – P-RC-01'
    _inherit = ['mail.thread']
    _order = 'marche_id, date_reception desc'

    name = fields.Char(
        string='N° PVR', required=True, readonly=True,
        default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', ondelete='cascade', required=True
    )
    date_reception = fields.Date(
        string='Date réception', default=fields.Date.today, required=True
    )
    receptionnaire_id = fields.Many2one(
        'hr.employee', string='Réceptionnaire (Facility Manager)',
        help='Responsable de la vérification quantitative physique'
    )
    demandeur_id = fields.Many2one(
        'hr.employee', string='Demandeur / vérificateur technique'
    )

    # Grille de vérification B.6 Manuel
    verif_quantitative = fields.Boolean(
        string='Quantités livrées conformes au BC',
        help='Nbre d\'unités livrées = BC + bordereau de livraison'
    )
    verif_qualitative = fields.Boolean(
        string='État général conforme (emballages, intégrité)',
    )
    verif_specs_techniques = fields.Boolean(
        string='Marque / modèle / références conformes aux spécifications'
    )
    verif_docs_accompagnement = fields.Boolean(
        string='Documents accompagnement présents (garanties, licences...)'
    )
    verif_test_equipement = fields.Boolean(
        string='Test fonctionnement équipements réalisé (si applicable)'
    )
    pool_rd_valide = fields.Boolean(
        string='Validation Pool R&D (équipements de recherche)',
        help='Obligatoire pour tablettes, dictaphones, GPS, matériel laboratoire'
    )

    ecarts_constates = fields.Text(string='Écarts constatés (quantitatif)')
    non_conformites = fields.Text(string='Non-conformités qualitatives / techniques')

    # Résultat
    statut = fields.Selection([
        ('conforme', 'Réception conforme – PVR signé'),
        ('reserves', 'Réception avec réserves'),
        ('rejet_partiel', 'Rejet partiel'),
        ('rejet_total', 'Rejet total'),
    ], string='Résultat réception', required=True, default='conforme', tracking=True)

    lettre_nc_envoyee = fields.Boolean(
        string='Lettre non-conformité envoyée au fournisseur',
        help='Obligatoire si rejet/réserves – délai max 5 jours ouvrables (P-RC-01 B.11 risque 3)'
    )
    date_lettre_nc = fields.Date(string='Date lettre non-conformité')
    pj_pvr = fields.Many2many(
        'ir.attachment', 'pvr_pj_rel', string='PVR signé (scan)'
    )
    pj_bordereau = fields.Many2many(
        'ir.attachment', 'pvr_bordereau_rel', string='Bordereau de livraison'
    )

    # Inventaire (B.5 étape 8)
    enregistre_inventaire = fields.Boolean(
        string='Enregistré au registre des immobilisations / stocks',
        help='Obligatoire après PVR conforme (P-RC-01 B.5 étape 8)'
    )

    def action_signer_pvr(self):
        self.ensure_one()
        if self.statut in ('rejet_partiel', 'rejet_total') and not self.lettre_nc_envoyee:
            raise exceptions.UserError(
                "La lettre de non-conformité doit être envoyée au fournisseur "
                "dans les 5 jours ouvrables (P-RC-01 B.11)."
            )
        self.message_post(body=f"📋 PVR signé – statut : {dict(self._fields['statut'].selection).get(self.statut)}.")
        # Le PVR signé ne débloque la certification de facture que s'il est
        # réellement conforme (ou avec réserves acceptées) — un rejet total
        # ou partiel non levé ne doit jamais lever le blocage.
        if self.marche_id and self.statut in ('conforme', 'reserves'):
            self.marche_id.pv_reception_signe = True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.pvr')
                    or 'PVR-2026-001'
                )
        return super().create(vals_list)
