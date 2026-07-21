from odoo import _, models, fields, api, exceptions


class ResadeMarche(models.Model):
    _name = 'resade.marche'
    _description = 'Dossier de Passation de Marché RESADE'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_requisition desc, name'

    # ─────────────────────────────────────────────
    # IDENTIFICATION (Manuel : Convention de codification P-PTM-XX)
    # ─────────────────────────────────────────────
    name = fields.Char(
        string='Référence', required=True,
        readonly=True, default='Nouveau', copy=False, tracking=True
    )
    objet = fields.Char(string='Objet du marché', required=True, tracking=True)

    # Procédures conformes au Manuel RESADE Carnet D – Module 02
    # Seuils : ≤2M entente directe | 2M-10M consultation | >10M AOO | >50M AOO+ANO
    type_procedure = fields.Selection([
        ('entente_directe', 'Entente directe / Gré à gré (≤ 2 000 000 FCFA) – P-PTM-01'),
        ('consultation', 'Consultation restreinte (2 000 001 – 10 000 000 FCFA) – P-PTM-02'),
        ('appel_offres', 'Appel d\'offres ouvert (10 000 001 – 50 000 000 FCFA) – P-PTM-03'),
        ('appel_offres_majeur', 'Appel d\'offres majeur (> 50 000 000 FCFA) – P-PTM-03 + ANO'),
        ('consultant_individuel', 'Recrutement consultant individuel – P-PTM-04'),
        ('services_specialises', 'Services spécialisés recherche / enquêtes – P-PTM-05'),
    ], string='Type de procédure', required=True, default='entente_directe', tracking=True)

    type_marche = fields.Selection([
        ('fourniture', 'Fourniture de biens'),
        ('service', 'Prestation de services'),
        ('travaux', 'Travaux'),
        ('consultant', 'Consultance / expertise intellectuelle'),
        ('recherche', 'Services de recherche / enquêtes'),
    ], string='Type de marché', required=True, default='service', tracking=True)

    # Code processus (codification Manuel RESADE)
    code_processus = fields.Char(
        string='Code processus', compute='_compute_code_processus', store=True
    )

    # ANO Bailleur requis si > 50M FCFA
    ano_bailleur_requis = fields.Boolean(
        string='ANO bailleur requis', compute='_compute_ano_requis', store=True
    )
    ano_bailleur_recu = fields.Boolean(string='ANO bailleur reçu', default=False, tracking=True)
    pj_ano_bailleur = fields.Many2many(
        'ir.attachment', 'marche_pj_ano_rel',
        string='Avis de Non-Objection bailleur'
    )

    # ─────────────────────────────────────────────
    # ÉTATS (workflow Carnet D + E)
    # ─────────────────────────────────────────────
    state = fields.Selection([
        # Carnet D : Passation
        ('brouillon', 'Brouillon / Réquisition'),
        ('valide_resp', 'Validé chef département'),
        ('valide_caf', 'Validé CAF (disponibilité budgétaire)'),
        ('ao_lance', 'AO / Consultation lancé(e)'),
        ('depouillement', 'Dépouillement des offres'),
        ('analyse', 'Analyse comparative'),
        ('cam_convoquee', 'CAM convoquée'),
        ('approuve_de', 'Approuvé DE (Attribution)'),
        ('notifie', 'Attribution notifiée'),
        # Carnet E : Exécution
        ('bon_commande', 'Bon de commande / Contrat émis'),
        ('en_cours', 'Exécution en cours'),
        ('reception', 'Réception / Contrôle qualité'),
        ('certifie', 'Facture certifiée (ASF)'),
        ('paye', 'Payé / Clôturé'),
        ('annule', 'Annulé'),
    ], string='État', default='brouillon', readonly=True, tracking=True)

    # ─────────────────────────────────────────────
    # DATES
    # ─────────────────────────────────────────────
    date_requisition = fields.Date(
        string='Date réquisition', default=fields.Date.today, required=True
    )
    date_validation_resp = fields.Date(string='Date validation chef dept')
    date_validation_caf = fields.Date(string='Date validation CAF')
    date_publication = fields.Date(string='Date publication AO / consultation')
    date_limite_offres = fields.Date(string='Date limite dépôt offres')
    date_depouillement = fields.Date(string='Date dépouillement')
    date_cam = fields.Date(string='Date séance CAM')
    date_attribution = fields.Date(string='Date attribution')
    date_notification = fields.Date(string='Date notification attribution')
    date_debut = fields.Date(string='Date début exécution')
    date_fin_prevue = fields.Date(string='Date fin prévue')
    date_reception_effective = fields.Date(string='Date réception effective')
    date_paiement = fields.Date(string='Date paiement')
    date_cloture = fields.Date(string='Date clôture dossier')

    # ─────────────────────────────────────────────
    # ACTEURS (conformes organigramme RESADE 2025)
    # ─────────────────────────────────────────────
    demandeur_id = fields.Many2one(
        'hr.employee', string='Demandeur', required=True,
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
    )
    service_demandeur = fields.Char(string='Service / Département demandeur')
    responsable_id = fields.Many2one('hr.employee', string='Chef de département', tracking=True)
    caf_id = fields.Many2one('hr.employee', string='CAF validateur', tracking=True)
    de_id = fields.Many2one('hr.employee', string='Directeur Exécutif', tracking=True)
    fournisseur_id = fields.Many2one(
        'resade.fournisseur', string='Fournisseur / Prestataire retenu', tracking=True
    )

    # CAM liée à ce dossier
    cam_id = fields.Many2one(
        'resade.marche.cam', string='Séance CAM', readonly=True
    )
    cam_requise = fields.Boolean(
        string='CAM requise', compute='_compute_cam_requise', store=True
    )

    # ─────────────────────────────────────────────
    # MONTANTS – Seuils conformes Manuel RESADE Carnet D
    # Entente directe : ≤ 2 000 000
    # Consultation restreinte : 2 000 001 – 10 000 000
    # AOO : 10 000 001 – 50 000 000
    # AOO majeur + ANO : > 50 000 000
    # ─────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )
    montant_estime = fields.Monetary(
        string='Montant estimé', compute='_compute_montants',
        store=True, currency_field='currency_id'
    )
    montant_final = fields.Monetary(
        string='Montant final retenu', currency_field='currency_id', tracking=True
    )
    montant_paye = fields.Monetary(
        string='Montant payé', currency_field='currency_id'
    )
    retenue_garantie_pct = fields.Float(
        string='Retenue de garantie (%)', default=0.0
    )
    retenue_garantie_montant = fields.Monetary(
        string='Montant retenue de garantie',
        compute='_compute_retenue', store=True, currency_field='currency_id'
    )
    delai_garantie_jours = fields.Integer(
        string='Délai de garantie (jours)', default=0
    )
    montant_net_a_payer = fields.Monetary(
        string='Montant net à payer',
        compute='_compute_retenue', store=True, currency_field='currency_id'
    )

    # Alerte seuil procédure
    alerte_seuil = fields.Selection([
        ('ok', '✅ Procédure correcte'),
        ('attention', '⚠️ Procédure à réviser selon montant'),
        ('non_defini', 'Montant non défini'),
    ], string='Cohérence seuil/procédure', compute='_compute_alerte_seuil', store=True)

    # ─────────────────────────────────────────────
    # LIGNES / LOTS
    # ─────────────────────────────────────────────
    line_ids = fields.One2many(
        'resade.marche.line', 'marche_id', string='Lots / Lignes'
    )
    offre_ids = fields.One2many(
        'resade.marche.offre', 'marche_id', string='Offres reçues'
    )
    # Carnet D - P-PTM-01 : cotations (entente directe)
    cotation_ids = fields.One2many(
        'resade.marche.cotation', 'marche_id', string='Cotations fournisseurs'
    )
    nb_cotations = fields.Integer(
        string='Nb cotations', compute='_compute_nb_cotations', store=True
    )
    # Carnet E - P-RC-01 : PV de reception fournitures
    pvr_ids = fields.One2many(
        'resade.marche.pvr', 'marche_id', string='PV de Reception (PVR)'
    )
    # Carnet E - P-RC-03 : Attestations de Service Fait
    asf_ids = fields.One2many(
        'resade.marche.asf', 'marche_id', string='Attestations de Service Fait (ASF)'
    )
    # Carnet E - P-RC-02 : Registre factures
    facture_ids = fields.One2many(
        'resade.marche.facture', 'marche_id', string='Factures (registre P-RC-02)'
    )
    nb_factures_certifiees = fields.Integer(
        string='Factures certifiees', compute='_compute_nb_factures', store=True
    )
    # Carnet E - P-PL-01 : dossiers paiement fournisseurs
    paiement_ids = fields.One2many(
        'resade.marche.paiement', 'marche_id', string='Dossiers paiement fournisseur (P-PL-01)'
    )
    # Carnet E - P-PL-02 : paiement honoraires consultants
    honoraire_ids = fields.One2many(
        'resade.marche.honoraires', 'marche_id', string='Paiements honoraires (P-PL-02)'
    )
    # Carnet D - FEB : Fiche Expression des Besoins
    feb_ids = fields.One2many(
        'resade.marche.feb', 'marche_id', string='Fiches Expression Besoins (FEB)'
    )
    feb_autorisee = fields.Boolean(
        string='FEB autorisee DE',
        compute='_compute_feb_autorisee', store=True
    )

    # ─────────────────────────────────────────────
    # ANALYTIQUE / BUDGET
    # ─────────────────────────────────────────────
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Compte analytique (Projet / Bailleur)'
    )
    # Fiche d'Engagement Budgétaire (FEB) – référence Manuel P-ESB-01
    ref_feb = fields.Char(string='Réf. FEB (Fiche Engagement Budgétaire)')
    # Lien réel vers le référentiel budgétaire RESADE (module resade_budget).
    # Remplace la simple case de confirmation par une vérification effective
    # de disponibilité de crédit (Manuel P-ESB-01, étape 2).
    ligne_budgetaire_id = fields.Many2one(
        'resade.budget.ligne', string='Ligne budgétaire (imputation RESADE)',
        help="Ligne budgétaire RESADE sur laquelle ce dossier marché sera imputé. "
             "La validation CAF réserve automatiquement le crédit sur cette ligne."
    )
    montant_disponible_ligne = fields.Monetary(
        related='ligne_budgetaire_id.montant_disponible', string='Disponible sur la ligne',
        readonly=True, currency_field='currency_marche_id'
    )
    currency_marche_id = fields.Many2one(
        'res.currency', string='Devise (budget)', default=lambda self: self.env.company.currency_id
    )
    credit_budgetaire_reserve = fields.Boolean(
        string='Crédit réservé sur la ligne budgétaire', default=False, readonly=True, tracking=True
    )
    # Champ historique conservé pour compatibilité ascendante (anciens dossiers
    # créés avant l'intégration resade_budget, ou marchés hors ligne budgétaire
    # structurée). Si ligne_budgetaire_id est rempli, c'est lui qui fait foi.
    disponibilite_budgetaire_confirmee = fields.Boolean(
        string='Disponibilité budgétaire confirmée (legacy / hors ligne RESADE)', default=False, tracking=True
    )

    # ─────────────────────────────────────────────
    # P-PTM-02 : CONSULTATION RESTREINTE – liste courte
    # Manuel Carnet D Module 02 – étape 2 : 3 à 5 fournisseurs présélectionnés
    # ─────────────────────────────────────────────
    liste_courte_ids = fields.One2many(
        'resade.marche.liste.courte', 'marche_id',
        string='Liste courte – fournisseurs présélectionnés (P-PTM-02)'
    )
    nb_liste_courte = fields.Integer(
        string='Nb fournisseurs liste courte',
        compute='_compute_nb_liste_courte', store=True
    )

    # ─────────────────────────────────────────────
    # P-PTM-03 : AOO – délai minimum de publication
    # Manuel Carnet D Module 02 – étape 3 : délai minimum 15 jours calendaires
    # ─────────────────────────────────────────────
    date_limite_soumission = fields.Date(
        string='Date limite de soumission des offres (AOO)'
    )
    delai_publication_jours = fields.Integer(
        string='Délai de publication (jours)',
        compute='_compute_delai_publication', store=True
    )
    alerte_delai_ao = fields.Boolean(
        string='⚠️ Délai publication insuffisant (<15j)',
        compute='_compute_delai_publication', store=True
    )
    support_publication = fields.Selection([
        ('site_web', 'Site web RESADE'),
        ('presse', 'Presse nationale'),
        ('site_web_presse', 'Site web + Presse'),
        ('bailleur', 'Portail bailleur de fonds'),
        ('autre', 'Autre'),
    ], string='Support de publication (P-PTM-03)')
    reference_publication = fields.Char(
        string='Référence / lien publication AO'
    )

    # ─────────────────────────────────────────────
    # P-PTM-04 : CONSULTANT INDIVIDUEL – TOR + grille
    # Manuel Carnet D Module 02 – étape 4 : TOR obligatoires, grille scoring
    # ─────────────────────────────────────────────
    tor_reference = fields.Char(
        string='Référence TOR (Termes de Référence) – P-PTM-04'
    )
    tor_valide = fields.Boolean(
        string='TOR validés par DE', default=False, tracking=True
    )
    pj_tor = fields.Many2many(
        'ir.attachment', 'marche_pj_tor_rel',
        string='TOR / CDC consultant (P-PTM-04)'
    )
    # Grille d'évaluation des offres consultants (P-PTM-04 étape 5)
    grille_eval_ids = fields.One2many(
        'resade.marche.grille.eval', 'marche_id',
        string='Grille d\'évaluation des offres (P-PTM-04 / P-PTM-05)'
    )
    score_technique_retenu = fields.Float(
        string='Score technique offre retenue (/100)',
        digits=(5, 2)
    )
    score_financier_retenu = fields.Float(
        string='Score financier offre retenue (/100)',
        digits=(5, 2)
    )
    score_global_retenu = fields.Float(
        string='Score global offre retenue (/100)',
        compute='_compute_score_global', store=True,
        digits=(5, 2)
    )
    # Pondération technique/financier (défaut 80/20 consultants – Manuel RESADE)
    poids_technique_pct = fields.Float(
        string='Poids technique (%)', default=80.0
    )
    poids_financier_pct = fields.Float(
        string='Poids financier (%)', default=20.0
    )

    # ─────────────────────────────────────────────
    # P-PTM-05 : SERVICES SPÉCIALISÉS (RECHERCHE/ENQUÊTES)
    # Manuel Carnet D Module 02 – étape 5
    # ─────────────────────────────────────────────
    ref_protocole = fields.Char(
        string='Référence protocole de recherche (P-PTM-05)'
    )
    comite_selection_constitue = fields.Boolean(
        string='Comité de sélection constitué', default=False
    )
    pj_protocole = fields.Many2many(
        'ir.attachment', 'marche_pj_protocole_rel',
        string='Protocole / devis technique (P-PTM-05)'
    )

    # ─────────────────────────────────────────────
    # JUSTIFICATION ET DÉONTOLOGIE (Carnet D Module 03)
    # ─────────────────────────────────────────────
    justification = fields.Text(
        string='Justification / Objet détaillé', required=True
    )
    motif_entente_directe = fields.Text(
        string='Motif justifiant l\'entente directe'
    )

    # Déclaration conflit d'intérêts (P-DA-01)
    conflit_interet_declare = fields.Boolean(
        string='Conflit d\'intérêt déclaré', default=False, tracking=True
    )
    note_conflit = fields.Text(string='Nature du conflit déclaré')
    acteur_concerne_conflit = fields.Char(string='Acteur concerné par le conflit')
    recusation_effectuee = fields.Boolean(
        string='Récusation effectuée', default=False
    )

    # ─────────────────────────────────────────────
    # EXÉCUTION (Carnet E)
    # ─────────────────────────────────────────────
    # Réception et contrôle (P-E-01)
    pv_reception_signe = fields.Boolean(string='PV de réception signé', default=False)
    observations_reception = fields.Text(string='Observations lors de la réception')
    reception_conforme = fields.Boolean(string='Livraison / Prestation conforme', default=True)
    motif_non_conformite = fields.Text(string='Motif de non-conformité')

    # Certification facture (ASF) (P-E-02)
    numero_facture = fields.Char(string='N° facture fournisseur')
    date_facture = fields.Date(string='Date de la facture')
    asf_numero = fields.Char(string='N° Attestation de Service Fait (ASF)')

    # Paiement (P-E-03)
    mode_paiement = fields.Selection([
        ('virement', 'Virement bancaire'),
        ('cheque', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
        ('espece', 'Espèces (petite caisse)'),
    ], string='Mode de paiement')
    reference_paiement = fields.Char(string='Référence paiement')

    # ─────────────────────────────────────────────
    # SUIVI ET CLÔTURE (Carnet E Module 03)
    # ─────────────────────────────────────────────
    dossier_cloture = fields.Boolean(string='Dossier clôturé', default=False, tracking=True)
    ref_archivage = fields.Char(string='Référence d\'archivage GED')
    note_cloture = fields.Text(string='Note de clôture')

    # ─────────────────────────────────────────────
    # PIÈCES JOINTES (GED – Archivage P-DA-02)
    # ─────────────────────────────────────────────
    pj_dao = fields.Many2many(
        'ir.attachment', 'marche_pj_dao_rel',
        string='Dossier AO / DAO / TDR / CDC'
    )
    pj_offres = fields.Many2many(
        'ir.attachment', 'marche_pj_offres_rel',
        string='Offres reçues'
    )
    pj_rapport_analyse = fields.Many2many(
        'ir.attachment', 'marche_pj_analyse_rel',
        string='Rapport d\'analyse comparative'
    )
    pj_pv_cam = fields.Many2many(
        'ir.attachment', 'marche_pj_pvcam_rel',
        string='PV séance CAM'
    )
    pj_lettre_notification = fields.Many2many(
        'ir.attachment', 'marche_pj_notif_rel',
        string='Lettre de notification attribution'
    )
    pj_contrat = fields.Many2many(
        'ir.attachment', 'marche_pj_contrat_rel',
        string='Contrat / Bon de commande signé'
    )
    pj_reception = fields.Many2many(
        'ir.attachment', 'marche_pj_reception_rel',
        string='PV de réception'
    )
    pj_facture = fields.Many2many(
        'ir.attachment', 'marche_pj_facture_rel',
        string='Facture certifiée + ASF'
    )
    pj_preuve_paiement = fields.Many2many(
        'ir.attachment', 'marche_pj_paiement_rel',
        string='Preuve de paiement'
    )

    # ─────────────────────────────────────────────
    # TRAÇABILITÉ DES VALIDATIONS (Matrice RACI)
    # ─────────────────────────────────────────────
    valide_resp_par = fields.Many2one('res.users', string='Validé chef dept par', readonly=True)
    valide_resp_date = fields.Datetime(string='Date validation chef dept', readonly=True)
    valide_caf_par = fields.Many2one('res.users', string='Validé CAF par', readonly=True)
    valide_caf_date = fields.Datetime(string='Date validation CAF', readonly=True)
    approuve_de_par = fields.Many2one('res.users', string='Approuvé DE par', readonly=True)
    approuve_de_date = fields.Datetime(string='Date approbation DE', readonly=True)
    certifie_par = fields.Many2one('res.users', string='Facture certifiée par', readonly=True)
    certifie_date = fields.Datetime(string='Date certification', readonly=True)
    paye_par = fields.Many2one('res.users', string='Paiement enregistré par', readonly=True)
    paye_date = fields.Datetime(string='Date enregistrement paiement', readonly=True)
    cloture_par = fields.Many2one('res.users', string='Clôturé par', readonly=True)
    cloture_date = fields.Datetime(string='Date clôture', readonly=True)

    # ─────────────────────────────────────────────
    # CHAMPS CALCULÉS
    # ─────────────────────────────────────────────
    nb_offres = fields.Integer(
        string='Nb offres reçues', compute='_compute_nb_offres', store=True
    )
    delai_execution = fields.Integer(
        string='Délai exécution (jours)', compute='_compute_delai', store=True
    )
    note_interne = fields.Text(string='Note interne')

    # ─────────────────────────────────────────────
    # lien public pour consultation externe (ex: bailleur, partenaire)
    # ─────────────────────────────────────────────
    
    nom_fournisseur_tmp = fields.Char(string='Nom fournisseur (AOO)')
    email_fournisseur_tmp = fields.Char(string='Email fournisseur (AOO)')

    token_public = fields.Char(
        string='Token public AOO',
        default=lambda self: __import__('secrets').token_urlsafe(32),
        readonly=True, copy=False
    )

    lien_google_drive = fields.Char(
        string='Lien Google Drive (dépôt offres)',
        help='Lien du dossier Google Drive où les fournisseurs déposent leurs offres'
    )


    # ─────────────────────────────────────────────
    # COMPUTES
    # ─────────────────────────────────────────────
    @api.depends('liste_courte_ids')
    def _compute_nb_liste_courte(self):
        for rec in self:
            rec.nb_liste_courte = len(rec.liste_courte_ids)

    @api.depends('date_publication', 'date_limite_soumission')
    def _compute_delai_publication(self):
        for rec in self:
            if rec.date_publication and rec.date_limite_soumission:
                delta = (rec.date_limite_soumission - rec.date_publication).days
                rec.delai_publication_jours = delta
                rec.alerte_delai_ao = delta < 15
            else:
                rec.delai_publication_jours = 0
                rec.alerte_delai_ao = False

    @api.depends('score_technique_retenu', 'score_financier_retenu',
                 'poids_technique_pct', 'poids_financier_pct')
    def _compute_score_global(self):
        for rec in self:
            total_poids = (rec.poids_technique_pct or 0) + (rec.poids_financier_pct or 0)
            if total_poids > 0:
                rec.score_global_retenu = (
                    rec.score_technique_retenu * (rec.poids_technique_pct / total_poids)
                    + rec.score_financier_retenu * (rec.poids_financier_pct / total_poids)
                )
            else:
                rec.score_global_retenu = 0.0

    @api.depends('type_procedure')
    def _compute_code_processus(self):
        mapping = {
            'entente_directe': 'P-PTM-01',
            'consultation': 'P-PTM-02',
            'appel_offres': 'P-PTM-03',
            'appel_offres_majeur': 'P-PTM-03',
            'consultant_individuel': 'P-PTM-04',
            'services_specialises': 'P-PTM-05',
        }
        for rec in self:
            rec.code_processus = mapping.get(rec.type_procedure, '')

    @api.depends('montant_final', 'montant_estime', 'type_procedure')
    def _compute_ano_requis(self):
        for rec in self:
            montant = rec.montant_final or rec.montant_estime or 0
            rec.ano_bailleur_requis = (
                montant > 50_000_000
                or rec.type_procedure == 'appel_offres_majeur'
            )

    @api.depends('montant_final', 'montant_estime', 'type_procedure')
    def _compute_cam_requise(self):
        """CAM requise si montant > 2 000 000 FCFA (seuil consultation)"""
        for rec in self:
            montant = rec.montant_final or rec.montant_estime or 0
            rec.cam_requise = (
                montant > 2_000_000
                or rec.type_procedure in [
                    'consultation', 'appel_offres',
                    'appel_offres_majeur', 'consultant_individuel',
                    'services_specialises'
                ]
            )

    @api.depends('line_ids.montant_estime')
    def _compute_montants(self):
        for rec in self:
            rec.montant_estime = sum(rec.line_ids.mapped('montant_estime'))

    @api.depends('montant_final', 'retenue_garantie_pct')
    def _compute_retenue(self):
        for rec in self:
            if rec.montant_final and rec.retenue_garantie_pct:
                rec.retenue_garantie_montant = rec.montant_final * rec.retenue_garantie_pct / 100
                rec.montant_net_a_payer = rec.montant_final - rec.retenue_garantie_montant
            else:
                rec.retenue_garantie_montant = 0
                rec.montant_net_a_payer = rec.montant_final or 0

    @api.depends('offre_ids')
    def _compute_nb_offres(self):
        for rec in self:
            rec.nb_offres = len(rec.offre_ids)

    @api.depends('feb_ids', 'feb_ids.statut')
    def _compute_feb_autorisee(self):
        for rec in self:
            rec.feb_autorisee = any(
                f.statut == 'autorisee' for f in rec.feb_ids
            )

    @api.depends('cotation_ids')
    def _compute_nb_cotations(self):
        for rec in self:
            rec.nb_cotations = len(rec.cotation_ids)

    @api.depends('facture_ids', 'facture_ids.statut')
    def _compute_nb_factures(self):
        for rec in self:
            rec.nb_factures_certifiees = len(
                rec.facture_ids.filtered(lambda f: f.statut == 'certifiee')
            )

    @api.depends('date_debut', 'date_fin_prevue')
    def _compute_delai(self):
        for rec in self:
            if rec.date_debut and rec.date_fin_prevue:
                rec.delai_execution = (rec.date_fin_prevue - rec.date_debut).days
            else:
                rec.delai_execution = 0

    @api.depends('montant_final', 'montant_estime', 'type_procedure')
    def _compute_alerte_seuil(self):
        """Vérifie la cohérence entre le montant et la procédure choisie – Manuel RESADE Carnet D"""
        for rec in self:
            montant = rec.montant_final or rec.montant_estime
            if not montant:
                rec.alerte_seuil = 'non_defini'
                continue
            proc = rec.type_procedure
            if montant <= 2_000_000 and proc == 'entente_directe':
                rec.alerte_seuil = 'ok'
            elif 2_000_001 <= montant <= 10_000_000 and proc == 'consultation':
                rec.alerte_seuil = 'ok'
            elif 10_000_001 <= montant <= 50_000_000 and proc == 'appel_offres':
                rec.alerte_seuil = 'ok'
            elif montant > 50_000_000 and proc == 'appel_offres_majeur':
                rec.alerte_seuil = 'ok'
            elif proc in ('consultant_individuel', 'services_specialises'):
                rec.alerte_seuil = 'ok'
            else:
                rec.alerte_seuil = 'attention'

    # ─────────────────────────────────────────────
    # ONCHANGE
    # ─────────────────────────────────────────────
    @api.onchange('montant_estime', 'montant_final')
    def _onchange_montant_type(self):
        """Suggère le type de procédure selon les seuils RESADE (Carnet D)."""
        montant = self.montant_final or self.montant_estime
        if montant and montant > 0:
            if self.type_marche in ('consultant', 'recherche'):
                if montant > 2_000_000:
                    self.type_procedure = 'consultant_individuel'
            elif montant <= 2_000_000:
                self.type_procedure = 'entente_directe'
            elif montant <= 10_000_000:
                self.type_procedure = 'consultation'
            elif montant <= 50_000_000:
                self.type_procedure = 'appel_offres'
            else:
                self.type_procedure = 'appel_offres_majeur'

    # ─────────────────────────────────────────────
    # WORKFLOW – Carnet D : Passation
    # ─────────────────────────────────────────────
    def action_soumettre_validation(self):
        """Brouillon → Validé chef département"""
        self.ensure_one()
        if not self.line_ids:
            raise exceptions.UserError(
                "Ajoutez au moins une ligne de dépense avant de soumettre."
            )
        if not self.justification:
            raise exceptions.UserError("La justification est obligatoire.")
        if self.type_procedure == 'entente_directe' and not self.motif_entente_directe:
            raise exceptions.UserError(
                "Justifiez le recours a l entente directe (P-PTM-01 - Carnet D)."
            )
        # P-PTM-01 : minimum 3 cotations ecrites obligatoires si montant > 200 000 FCFA
        if self.type_procedure == 'entente_directe':
            montant = self.montant_final or self.montant_estime or 0
            if montant > 200_000 and len(self.cotation_ids) < 3:
                raise exceptions.UserError(
                    "P-PTM-01 : Au moins 3 cotations ecrites sont obligatoires "
                    "pour toute entente directe superieure a 200 000 FCFA.\n"
                    f"Cotations actuelles : {len(self.cotation_ids)}/3."
                )
        self.write({'state': 'valide_resp'})
        self.message_post(body="Dossier soumis a validation du chef de departement.")

    def action_valider_responsable(self):
        """Validé chef département → Validé CAF"""
        self.ensure_one()
        self.write({
            'state': 'valide_caf',
            'valide_resp_par': self.env.uid,
            'valide_resp_date': fields.Datetime.now(),
            'date_validation_resp': fields.Date.today(),
        })
        self.message_post(body="✅ Validation chef de département effectuée.")

    def action_valider_caf(self):
        """
        Validé CAF (vérification disponibilité budgétaire + FEB).
        Manuel P-ESB-01, étape 2 : si une ligne budgétaire RESADE est liée,
        le crédit est réellement vérifié et réservé (et non plus une simple
        case à cocher). Sinon, on retombe sur l'ancien comportement
        déclaratif pour les dossiers créés avant cette intégration.
        """
        self.ensure_one()
        if self.ligne_budgetaire_id:
            # Lève une UserError explicite si le crédit est insuffisant.
            self.ligne_budgetaire_id.reserver_credit(self.montant_estime or 0.0)
            self.write({
                'credit_budgetaire_reserve': True,
                'disponibilite_budgetaire_confirmee': True,
            })
        elif not self.disponibilite_budgetaire_confirmee:
            raise exceptions.UserError(
                "Veuillez sélectionner une ligne budgétaire RESADE (recommandé) ou, à défaut, "
                "confirmer manuellement la disponibilité budgétaire (FEB) avant de valider (CAF)."
            )
        self.write({
            'state': 'ao_lance',
            'valide_caf_par': self.env.uid,
            'valide_caf_date': fields.Datetime.now(),
            'date_validation_caf': fields.Date.today(),
        })
        self.message_post(body="✅ Validation CAF – disponibilité budgétaire confirmée.")

    def action_lancer_ao(self):
        """Lancer l'AO / consultation"""
        self.ensure_one()
        if not self.date_limite_offres:
            raise exceptions.UserError(
                "Définissez une date limite de dépôt des offres avant de lancer."
            )
        if self.ano_bailleur_requis and not self.ano_bailleur_recu:
            raise exceptions.UserError(
                "L'ANO bailleur est requis pour les marchés > 50 000 000 FCFA avant le lancement."
            )
        # P-PTM-02 : vérifier liste courte (3 à 5 fournisseurs obligatoires)
        if self.type_procedure == 'consultation':
            if self.nb_liste_courte < 3:
                raise exceptions.UserError(
                    "P-PTM-02 : La liste courte doit comporter au moins 3 fournisseurs "
                    "présélectionnés avant le lancement de la consultation restreinte.\n"
                    f"Fournisseurs actuels : {self.nb_liste_courte}/3 minimum."
                )
        # P-PTM-03 : vérifier délai minimum de publication AOO (15 jours calendaires)
        if self.type_procedure in ('appel_offres', 'appel_offres_majeur'):
            if not self.date_limite_soumission:
                raise exceptions.UserError(
                    "P-PTM-03 : Renseignez la date limite de soumission des offres "
                    "avant de lancer l'appel d'offres ouvert."
                )
            import datetime
            today = fields.Date.today()
            delta = (self.date_limite_soumission - today).days
            if delta < 15:
                raise exceptions.UserError(
                    f"P-PTM-03 : Le délai de publication doit être d'au moins 15 jours "
                    f"calendaires (Manuel RESADE Carnet D – étape 3).\n"
                    f"Délai actuel : {delta} jour(s). Repoussez la date limite de soumission."
                )
        # P-PTM-04 : TOR obligatoires pour consultants individuels
        if self.type_procedure == 'consultant_individuel' and not self.tor_valide:
            raise exceptions.UserError(
                "P-PTM-04 : Les Termes de Référence (TOR) doivent être validés par "
                "le DE avant le lancement du recrutement de consultant individuel."
            )
        # P-PTM-05 : protocole requis pour services spécialisés
        if self.type_procedure == 'services_specialises' and not self.ref_protocole:
            raise exceptions.UserError(
                "P-PTM-05 : Renseignez la référence du protocole de recherche / "
                "devis technique avant le lancement."
            )
        self.write({
            'state': 'depouillement',
            'date_publication': fields.Date.today(),
        })
        self.message_post(body="📢 Appel d'offres / consultation lancé(e).")

    def action_depouiller(self):
        """Dépouillement → Analyse"""
        self.ensure_one()
        if self.type_procedure == 'entente_directe':
            # En entente directe, ce sont les cotations qui font foi (déjà
            # vérifiées à la soumission : minimum 3 si montant > 200 000 FCFA),
            # pas les offres reçues (utilisées pour consultation/AOO).
            if not self.cotation_ids:
                raise exceptions.UserError(
                    "Enregistrez au moins une cotation avant le dépouillement."
                )
        else:
            if not self.offre_ids:
                raise exceptions.UserError(
                    "Enregistrez au moins une offre reçue avant le dépouillement."
                )
        self.write({
            'state': 'analyse',
            'date_depouillement': fields.Date.today(),
        })
        self.message_post(body="📋 Dépouillement effectué – passage en analyse comparative.")

    def action_convoquer_cam(self):
        """Analyse → CAM convoquée (si CAM requise)"""
        self.ensure_one()
        if not self.cam_requise:
            raise exceptions.UserError(
                "La CAM n'est pas requise pour ce dossier (montant ≤ 2 000 000 FCFA)."
            )
        # Créer automatiquement une séance CAM liée
        cam = self.env['resade.marche.cam'].create({
            'marche_id': self.id,
            'date_prevue': fields.Date.today(),
            'objet': f"Attribution – {self.objet}",
        })
        self.write({
            'state': 'cam_convoquee',
            'cam_id': cam.id,
            'date_cam': fields.Date.today(),
        })
        self.message_post(body=f"📅 Séance CAM créée : {cam.name}.")

    def action_approuver_de(self):
        """Approuver attribution (DE) → Attribution notifiée"""
        self.ensure_one()
        if not self.fournisseur_id:
            raise exceptions.UserError(
                "Sélectionnez le fournisseur / prestataire retenu avant l'approbation."
            )
        if not self.montant_final:
            raise exceptions.UserError("Le montant final est obligatoire.")
        if self.cam_requise and not self.cam_id:
            raise exceptions.UserError(
                "Une séance CAM doit être tenue avant l'approbation DE pour ce montant."
            )
        self.write({
            'state': 'notifie',
            'approuve_de_par': self.env.uid,
            'approuve_de_date': fields.Datetime.now(),
            'date_attribution': fields.Date.today(),
            'date_notification': fields.Date.today(),
        })
        self.message_post(body="🖊️ Attribution approuvée par le DE – notification envoyée.")

    # ─────────────────────────────────────────────
    # WORKFLOW – Carnet E : Exécution
    # ─────────────────────────────────────────────
    def action_emettre_bc(self):
        """Notifié → Bon de commande / contrat émis"""
        self.ensure_one()
        self.write({'state': 'bon_commande'})
        self.message_post(body="📄 Bon de commande / contrat émis.")

    def action_demarrer_execution(self):
        self.ensure_one()
        self.write({
            'state': 'en_cours',
            'date_debut': self.date_debut or fields.Date.today(),
        })
        self.message_post(body="▶️ Exécution démarrée.")

    def action_reception(self):
        """Exécution → Réception / contrôle qualité (P-E-01)"""
        self.ensure_one()
        self.write({
            'state': 'reception',
            'date_reception_effective': fields.Date.today(),
        })
        self.message_post(body="📦 Réception enregistrée – contrôle qualité en cours.")

    def action_certifier_facture(self):
        """Réception → Facture certifiée / ASF (P-E-02)

        Règle du manuel (Carnet E) : le justificatif de service fait exigé
        dépend du type de marché.
        - Fourniture / Travaux -> PV de Réception (PVR) signé, statut conforme
          ou réserves levées (P-RC-01).
        - Service / Consultance / Recherche -> Attestation de Service Fait
          (ASF) validée (P-RC-03), puisqu'il n'y a pas de réception physique
          de biens dans ces cas.
        """
        self.ensure_one()
        if self.type_marche in ('fourniture', 'travaux'):
            if not self.pv_reception_signe:
                raise exceptions.UserError(
                    "Le PV de réception (PVR) signé est obligatoire avant la certification de la "
                    "facture pour un marché de fourniture/travaux (P-RC-01). "
                    "Renseignez-le dans l'onglet « 📦 Réception (P-RC-01) » du dossier."
                )
        else:
            asf_valides = self.asf_ids.filtered(lambda a: a.statut_validation == 'valide')
            if not asf_valides:
                raise exceptions.UserError(
                    "L'Attestation de Service Fait (ASF) validée est obligatoire avant la "
                    "certification de la facture pour un marché de service/consultance/recherche "
                    "(P-RC-03). Créez-la et validez-la dans l'onglet « 📄 ASF / Livrables (P-RC-03) » "
                    "du dossier."
                )
        factures_certifiees = self.facture_ids.filtered(lambda f: f.statut == 'certifiee')
        if not factures_certifiees:
            raise exceptions.UserError(
                "Aucune facture certifiée par le CAF n'a été trouvée. Renseignez la facture "
                "fournisseur et faites-la certifier dans l'onglet « 🧾 Factures (P-RC-02) » du dossier "
                "avant de certifier le marché."
            )
        # Traçabilité : on reprend le n° de la facture certifiée la plus récente sur le dossier.
        self.numero_facture = factures_certifiees.sorted('date_reception', reverse=True)[0].numero_facture
        self.write({
            'state': 'certifie',
            'certifie_par': self.env.uid,
            'certifie_date': fields.Datetime.now(),
        })
        self.message_post(body="✔️ Facture certifiée (ASF émise).")

    def action_payer(self):
        """Certifié → Payé / Clôturé (P-E-03)"""
        self.ensure_one()
        if not self.montant_paye:
            raise exceptions.UserError("Renseignez le montant payé avant de clôturer.")
        if self.credit_budgetaire_reserve and self.ligne_budgetaire_id:
            # Manuel P-ESB-01, étape 7 : solde l'engagement et constate la
            # dépense réelle (qui peut différer légèrement du montant estimé).
            self.ligne_budgetaire_id.constater_realisation(
                self.montant_estime or 0.0, self.montant_paye
            )
        self.write({
            'state': 'paye',
            'date_paiement': fields.Date.today(),
            'paye_par': self.env.uid,
            'paye_date': fields.Datetime.now(),
        })
        self.message_post(body="💰 Paiement enregistré – dossier clôturé.")

    def action_cloturer_dossier(self):
        """Archivage du dossier (P-DA-02 Carnet D Module 03)"""
        self.ensure_one()
        if self.state not in ['paye', 'annule']:
            raise exceptions.UserError(
                "Le dossier doit être payé ou annulé avant la clôture définitive."
            )
        self.write({
            'dossier_cloture': True,
            'date_cloture': fields.Date.today(),
            'cloture_par': self.env.uid,
            'cloture_date': fields.Datetime.now(),
        })
        self.message_post(body="🗂️ Dossier clôturé et archivé (GED).")

    def action_annuler(self):
        self.ensure_one()
        if self.credit_budgetaire_reserve and self.ligne_budgetaire_id:
            self.ligne_budgetaire_id.liberer_credit(self.montant_estime or 0.0)
            self.credit_budgetaire_reserve = False
        self.write({'state': 'annule'})
        self.message_post(body="❌ Dossier annulé. Crédit budgétaire libéré le cas échéant.")

    def action_remettre_brouillon(self):
        self.ensure_one()
        self.write({'state': 'brouillon'})
        self.message_post(body="🔄 Dossier remis en brouillon.")

    # ─────────────────────────────────────────────
    # CRÉATION (séquence automatique)
    # ─────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche')
                    or 'DM-2026-001'
                )
        return super().create(vals_list)


    def action_copier_lien_aoo(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not self.token_public:
            self.token_public = __import__('secrets').token_urlsafe(32)
        url = f"{base_url}/marche/aoo/{self.token_public}"
        raise exceptions.UserError(_("Lien public de l'AOO :\n%s") % url)
    
    def action_copier_lien_drive(self):
        self.ensure_one()
        if not self.lien_google_drive:
            raise exceptions.UserError(_("Aucun lien Google Drive renseigné. Veuillez d'abord saisir le lien."))
        raise exceptions.UserError(_("Lien Google Drive du marché :\n%s") % self.lien_google_drive)