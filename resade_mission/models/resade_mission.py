# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class ResadeMission(models.Model):
    _name = 'resade.mission'
    _description = 'Ordre de Mission RESADE – P-GMD-01/02/03'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_demande desc, name desc'

    # ─────────────────────────────────────────────
    # IDENTIFICATION  (RESADE-F-GMD-01-03)
    # ─────────────────────────────────────────────
    name = fields.Char(
        string='Numéro OM',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    type_mission = fields.Selection([
        ('ordinaire',   'Mission ordinaire (nationale / sous-régionale)'),
        ('strategique', 'Mission stratégique (internationale / bailleur / CA requis)'),
    ], string='Type de mission', required=True, default='ordinaire', tracking=True)

    # ─────────────────────────────────────────────
    # MISSIONNAIRE & PARTICIPANTS  (F-GMD-01-04 : composition du groupe)
    # ─────────────────────────────────────────────
    employee_id = fields.Many2one(
        'hr.employee', string='Missionnaire principal', required=True, tracking=True,
        domain="[('active', '=', True)]"
    )
    department_id = fields.Many2one(
        'hr.department', string='Département / Pool',
        related='employee_id.department_id', store=True
    )
    job_id = fields.Many2one(
        'hr.job', string='Poste',
        related='employee_id.job_id', store=True
    )
    chef_dept_id = fields.Many2one(
        'hr.employee', string='Chef de département / Pool',
        tracking=True,
        help='Chef hiérarchique qui co-valide les TDR (B.5 P-GMD-01)'
    )
    # AJOUT : liste des participants (composition du groupe – F-GMD-01-04)
    participant_ids = fields.Many2many(
        'hr.employee',
        'resade_mission_participant_rel',
        'mission_id', 'employee_id',
        string='Autres participants / Groupe',
        help='Composition complète du groupe missionnaire (RESADE-F-GMD-01-04)'
    )
    nb_participants = fields.Integer(
        string='Nombre de participants',
        compute='_compute_nb_participants', store=True
    )

    # ─────────────────────────────────────────────
    # PLANIFICATION  (P-GMD-01)
    # ─────────────────────────────────────────────
    date_demande = fields.Date(
        string='Date de la demande', required=True,
        default=fields.Date.today, tracking=True
    )
    date_depart = fields.Date(string='Date de départ prévue', required=True, tracking=True)
    date_retour = fields.Date(string='Date de retour prévue', required=True, tracking=True)
    # AJOUT : dates réelles d'exécution (P-GMD-02 : suivi réel vs prévu)
    date_depart_effectif = fields.Date(
        string='Date départ effectif', tracking=True,
        help='Date de départ réelle (peut différer de la date prévue)'
    )
    date_retour_effectif = fields.Date(
        string='Date retour effectif', tracking=True,
        help='Date de retour réelle – sert au calcul du délai rapport (J+5)'
    )
    duree_jours = fields.Integer(
        string='Durée prévue (jours)', compute='_compute_duree', store=True
    )
    duree_reelle_jours = fields.Integer(
        string='Durée réelle (jours)', compute='_compute_duree_reelle', store=True
    )
    destination = fields.Char(string='Destination', required=True, tracking=True)
    zone_mission = fields.Selection([
        ('ouaga',        'Ouagadougou (même jour)'),
        ('interieur_bf', 'Intérieur BF (nuitée)'),
        ('cedeao',       'Région CEDEAO / sous-saharienne'),
        ('international','International (hors CEDEAO)'),
    ], string='Zone de mission', required=True, default='interieur_bf', tracking=True)
    objet_mission = fields.Text(string='Objet de la mission', required=True, tracking=True)

    # Justification (TDR ou note – RESADE-F-GMD-01-01 / 01-02)
    type_justification = fields.Selection([
        ('tdr',  'Termes de Référence (TDR) – RESADE-F-GMD-01-01 (mission ≥ 2 jours)'),
        ('note', 'Note de justification – RESADE-F-GMD-01-02 (mission courte / routine)'),
    ], string='Type de justification', required=True, default='tdr', tracking=True)
    tdr_note = fields.Html(string='Contenu TDR / Note de justification')
    # AJOUT : pièce jointe TDR (RESADE-F-GMD-01-01)
    tdr_attachment_ids = fields.Many2many(
        'ir.attachment',
        'resade_mission_tdr_rel',
        'mission_id', 'attachment_id',
        string='TDR / Note de justification (fichiers)',
        help='Fichiers joints : RESADE-F-GMD-01-01 ou RESADE-F-GMD-01-02'
    )

    # Ligne budgétaire
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Compte analytique (Projet / Bailleur)',
        tracking=True,
    )
    # Lien réel vers le référentiel budgétaire RESADE (module resade_budget).
    # Remplace la référence en texte libre par une vérification effective
    # de disponibilité de crédit (Manuel P-GMD-01 étape 3 / P-ESB-01).
    ligne_budgetaire_id = fields.Many2one(
        'resade.budget.ligne', string='Ligne budgétaire (imputation RESADE)', tracking=True,
        help="Ligne budgétaire RESADE (POA ou projet bailleur) sur laquelle cette mission "
             "sera imputée. Le visa CAF réserve automatiquement le crédit sur cette ligne."
    )
    montant_disponible_ligne = fields.Monetary(
        related='ligne_budgetaire_id.montant_disponible', string='Disponible sur la ligne', readonly=True
    )
    credit_budgetaire_reserve = fields.Boolean(
        string='Crédit réservé sur la ligne budgétaire', default=False, readonly=True, tracking=True
    )
    # Champ historique conservé pour compatibilité ascendante (missions créées
    # avant l'intégration resade_budget, ou imputation hors ligne structurée).
    budget_line_info = fields.Char(
        string='Ligne budgétaire POA / Projet (legacy / hors ligne RESADE)', tracking=True,
        help='Référence libre, utilisée seulement si ligne_budgetaire_id est vide.'
    )

    # AJOUT : avis PCA pour missions stratégiques (B.5 P-GMD-01 : Conseil d'Administration)
    avis_pca_requis = fields.Boolean(
        string='Avis PCA requis',
        compute='_compute_avis_pca', store=True,
        help='Automatique pour les missions stratégiques (P-GMD-01 B.5)'
    )
    avis_pca_date = fields.Date(
        string='Date avis PCA', tracking=True,
        help='Date à laquelle le PCA a été consulté (missions stratégiques)'
    )
    avis_pca_note = fields.Text(
        string='Note avis PCA', tracking=True
    )

    # ─────────────────────────────────────────────
    # FRAIS ESTIMÉS  (F-GMD-01-04 / F-GMD-01-05)
    # ─────────────────────────────────────────────
    line_ids = fields.One2many(
        'resade.mission.line', 'mission_id', string='Détail des frais estimés'
    )
    montant_avance_demande = fields.Monetary(
        string='Montant avance demandée (total, toutes lignes)',
        compute='_compute_montants', store=True, currency_field='currency_id'
    )
    # Décomposition forfait (per diem) / frais annexes — voir Manuel RESADE :
    # le per diem est un forfait acquis dès décaissement, sans justificatif ;
    # les frais annexes sont avancés par le missionnaire puis remboursés sur
    # justificatif réel au retour.
    montant_perdiem_demande = fields.Monetary(
        string='Per diem demandé (forfaitaire)',
        compute='_compute_montants', store=True, currency_field='currency_id'
    )
    montant_frais_annexes_demande = fields.Monetary(
        string='Frais annexes demandés (à justifier)',
        compute='_compute_montants', store=True, currency_field='currency_id'
    )
    montant_avance_approuve = fields.Monetary(
        string='Montant avance approuvé', tracking=True,
        currency_field='currency_id',
        help="Montant total décaissé au missionnaire avant la mission "
             "(per diem forfaitaire approuvé + éventuelle avance sur frais annexes)."
    )
    montant_perdiem_approuve_de = fields.Monetary(
        string='Per diem approuvé (DE) — acquis', compute='_compute_montants', store=True,
        currency_field='currency_id',
        help="Calculé sur les nuitées effectivement approuvées par le DE (ligne(s) Per diem). "
             "Ce montant est définitivement acquis au missionnaire dès décaissement : "
             "aucun justificatif, aucun trop-perçu sur cette partie (Manuel RESADE)."
    )
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    # ─────────────────────────────────────────────
    # INTÉGRATION COMPTABILITÉ ODOO (avance + régularisation réelles)
    # ─────────────────────────────────────────────
    journal_id = fields.Many2one(
        'account.journal', string='Journal de paiement (avance mission)',
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="Journal banque/caisse utilisé pour décaisser l'avance et pour la régularisation finale."
    )
    compte_avance_id = fields.Many2one(
        'account.account', string='Compte « Avances et acomptes au personnel »',
        domain="[('account_type', '=', 'asset_current'), ('reconcile', '=', True)]",
        help="Compte de TIERS sur lequel l'avance est imputée en attendant sa justification "
             "(ex. compte OHADA/SYCEBNL 421/425 – Avances et acomptes au personnel). "
             "⚠️ Ne jamais utiliser un compte de stock/marchandises : le compte doit être "
             "coché « Autoriser le lettrage » (reconcile = True), sinon le paiement ne peut "
             "pas être créé. Si aucun compte adapté n'apparaît dans la liste, il faut d'abord "
             "le créer dans Comptabilité > Configuration > Plan comptable, avec cette case cochée."
    )
    payment_avance_id = fields.Many2one(
        'account.payment', string='Paiement de l\'avance (Odoo)', readonly=True, copy=False
    )
    move_avance_id = fields.Many2one(
        related='payment_avance_id.move_id', string='Pièce comptable avance', readonly=True
    )
    payment_regularisation_id = fields.Many2one(
        'account.payment', string='Paiement de régularisation (Odoo)', readonly=True, copy=False,
        help="Trop-perçu reversé par le missionnaire (entrant) ou complément versé par RESADE (sortant)."
    )
    move_regularisation_id = fields.Many2one(
        related='payment_regularisation_id.move_id', string='Pièce comptable régularisation', readonly=True
    )

    # ─────────────────────────────────────────────
    # SUIVI « RESTE À PAYER » (affiché sur l'Ordre de Mission)
    # ─────────────────────────────────────────────
    montant_deja_verse = fields.Monetary(
        string='Montant déjà décaissé', currency_field='currency_id',
        compute='_compute_reste_a_payer',
        help="Montant déjà effectivement décaissé au missionnaire (avance versée à ce jour)."
    )
    montant_reste_a_payer = fields.Monetary(
        string='Reste à payer', currency_field='currency_id',
        compute='_compute_reste_a_payer',
        help="Différence entre l'avance approuvée par le DE et ce qui a déjà été décaissé. "
             "À 0 lorsque l'intégralité de l'avance a été versée."
    )

    @api.depends('montant_avance_approuve', 'payment_avance_id', 'payment_avance_id.amount')
    def _compute_reste_a_payer(self):
        for rec in self:
            deja_verse = rec.payment_avance_id.amount if rec.payment_avance_id else 0.0
            rec.montant_deja_verse = deja_verse
            rec.montant_reste_a_payer = max(0.0, (rec.montant_avance_approuve or 0.0) - deja_verse)

    # ─────────────────────────────────────────────
    # EXÉCUTION  (P-GMD-02)
    # ─────────────────────────────────────────────
    rapport_mission = fields.Html(string='Rapport de mission (RESADE-F-GMD-02-01)')
    date_soumission_rapport = fields.Date(
        string='Date soumission rapport', tracking=True
    )
    delai_rapport_ok = fields.Boolean(
        string='Rapport dans les délais (≤5j ouvrables)',
        compute='_compute_delai_rapport', store=True
    )
    jours_retard_rapport = fields.Integer(
        string='Jours de retard rapport',
        compute='_compute_delai_rapport', store=True
    )
    pieces_jointes_rapport = fields.Many2many(
        'ir.attachment',
        'resade_mission_rapport_rel',
        'mission_id', 'attachment_id',
        string='Pièces jointes rapport (annexes)'
    )
    # AJOUT : fiche décompte frais réels (RESADE-F-GMD-02-02)
    fiche_decompte_ids = fields.Many2many(
        'ir.attachment',
        'resade_mission_decompte_rel',
        'mission_id', 'attachment_id',
        string='Fiche décompte frais réels (RESADE-F-GMD-02-02)',
        help='Tableau réconciliation avance vs frais réels par poste'
    )
    # AJOUT : carnet de bord véhicule (RESADE-F-GMD-02-03)
    vehicule_resade = fields.Boolean(
        string='Véhicule RESADE utilisé', tracking=True
    )
    carnet_bord_ids = fields.Many2many(
        'ir.attachment',
        'resade_mission_carnet_rel',
        'mission_id', 'attachment_id',
        string='Carnet de bord véhicule (RESADE-F-GMD-02-03)',
        help='Km départ/arrivée, pleins effectués. Obligatoire si véhicule RESADE.'
    )
    # AJOUT : checklist conformité dossier retour (RESADE-F-GMD-02-05)
    checklist_rapport_ok = fields.Boolean(
        string='Checklist conformité dossier retour ✓',
        tracking=True,
        help='RESADE-F-GMD-02-05 : contrôle CAF – rapport + décompte + justificatifs + carnet de bord + OM original'
    )
    checklist_note = fields.Text(string='Observations checklist dossier retour')

    # Validation rapport en 2 étapes (P-GMD-02 : CD valide → DE approuve)
    rapport_valide_chef = fields.Boolean(
        string='Rapport validé par Chef Dépt', readonly=True, tracking=True,
        help='Étape B.8 P-GMD-02 séq. 6 : le CD valide avant transmission au DE'
    )
    rapport_valide_chef_date = fields.Datetime(
        string='Date validation rapport (Chef Dépt)', readonly=True
    )
    rapport_valide_chef_id = fields.Many2one(
        'res.users', string='Validé rapport par', readonly=True
    )
    rapport_approuve_de = fields.Boolean(
        string='Rapport approuvé par DE', readonly=True, tracking=True,
        help='Étape B.8 P-GMD-02 séq. 7 : approbation finale DE avant diffusion'
    )
    rapport_approuve_de_date = fields.Datetime(
        string='Date approbation rapport (DE)', readonly=True
    )
    rapport_approuve_de_id = fields.Many2one(
        'res.users', string='Approuvé rapport par (DE)', readonly=True
    )

    # Capitalisation / restitution (P-GMD-02 étape 8)
    restitution_interne_faite = fields.Boolean(
        string='Restitution interne effectuée',
        help='Obligatoire pour missions stratégiques (P-GMD-02 B.7 étape 8)'
    )
    enseignements_capitalises = fields.Text(
        string='Enseignements / capitalisation',
        help='Compte rendu restitution interne et enseignements documentés'
    )

    # ─────────────────────────────────────────────
    # JUSTIFICATION / REMBOURSEMENT  (P-GMD-03)
    # ─────────────────────────────────────────────
    montant_depense_reel = fields.Monetary(
        string='Total frais annexes réels (justifiés)', compute='_compute_montants_reel',
        store=True, currency_field='currency_id',
        help="Ne comprend PAS le per diem (forfaitaire, acquis) — uniquement les frais "
             "annexes (transport, péages, etc.) présentés avec justificatif au retour."
    )
    montant_avance_frais_annexes_a_solder = fields.Monetary(
        string='Avance sur frais annexes (à solder)', compute='_compute_montants_reel',
        store=True, currency_field='currency_id',
        help="Partie de l'avance décaissée qui couvrait les frais annexes "
             "(montant_avance_approuve - per diem acquis). C'est sur cette seule "
             "partie que porte le trop-perçu / complément ci-dessous."
    )
    montant_a_rembourser = fields.Monetary(
        string='Trop-perçu à reverser à RESADE (frais annexes uniquement)',
        compute='_compute_solde', store=True, currency_field='currency_id',
        help='Avance sur frais annexes - Frais annexes réels justifiés (si positif : '
             'missionnaire reverse). Le per diem forfaitaire n\'entre jamais dans ce calcul.'
    )
    montant_complement = fields.Monetary(
        string='Complément à verser au missionnaire (frais annexes uniquement)',
        compute='_compute_solde', store=True, currency_field='currency_id',
        help='Frais annexes réels justifiés - Avance sur frais annexes (si positif : '
             'RESADE rembourse). Le per diem forfaitaire n\'entre jamais dans ce calcul.'
    )
    pieces_jointes_justif = fields.Many2many(
        'ir.attachment',
        'resade_mission_justif_rel',
        'mission_id', 'attachment_id',
        string='Pièces justificatives de dépenses (factures, reçus)',
        help='Factures hôtel, tickets carburant, billets transport, etc.'
    )
    note_justification_frais = fields.Text(string='Observations justification frais')
    date_justification = fields.Date(
        string='Date soumission justification', tracking=True
    )
    # AJOUT : validation remboursement par CAF avant clôture
    remboursement_valide_caf = fields.Boolean(
        string='Remboursement/reversement validé par CAF',
        tracking=True,
        help='P-GMD-03 : le CAF valide le solde avant clôture comptable'
    )
    date_remboursement = fields.Date(
        string='Date remboursement / reversement', tracking=True
    )
    note_remboursement = fields.Text(string='Note remboursement')

    # ─────────────────────────────────────────────
    # WORKFLOW / ÉTAT
    # ─────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon',         '📝 Brouillon'),
        ('valide_chef',       '✅ Validé Chef Dépt'),
        ('approuve_caf',      '💰 Approuvé CAF (visa budgétaire)'),
        ('autorise_de',       '📋 Autorisé DE (OM signé)'),
        ('avance_decaisse',   '💵 Avance décaissée'),
        ('en_mission',        '✈️ En mission'),
        ('rapport_soumis',    '📄 Rapport soumis'),
        ('rapport_approuve',  '✔️ Rapport approuvé DE'),   # AJOUT
        ('justif_soumise',    '🧾 Justification soumise'),
        ('remboursement_ok',  '💳 Remboursement/reversement validé'),  # AJOUT
        ('cloture',           '🏁 Clôturé'),
        ('refuse',            '❌ Refusé'),
    ], string='État', default='brouillon', tracking=True, copy=False)

    # Validateurs
    valide_par_chef_id = fields.Many2one('res.users', string='Validé par (Chef)', readonly=True)
    valide_chef_date = fields.Datetime(string='Date validation Chef', readonly=True)
    approuve_par_caf_id = fields.Many2one('res.users', string='Approuvé par (CAF)', readonly=True)
    approuve_caf_date = fields.Datetime(string='Date approbation CAF', readonly=True)
    autorise_par_de_id = fields.Many2one('res.users', string='Autorisé par (DE)', readonly=True)
    autorise_de_date = fields.Datetime(string='Date autorisation DE', readonly=True)
    refuse_par_id = fields.Many2one('res.users', string='Refusé par', readonly=True)
    motif_refus = fields.Text(string='Motif du refus', tracking=True)

    # Visa budgétaire CAF (P-GMD-01 étape 3)
    visa_budgetaire = fields.Boolean(string='Visa budgétaire accordé', tracking=True)
    note_visa = fields.Text(string='Note visa budgétaire')

    # AJOUT : délai préavis conforme (P-GMD-01 B.7 étape 1)
    delai_preavis_ok = fields.Boolean(
        string='Préavis conforme (5j / 10j)',
        compute='_compute_preavis', store=True,
        help='5 jours ouvrables min pour missions ordinaires, 10j pour stratégiques'
    )
    nb_jours_preavis = fields.Integer(
        string='Jours de préavis',
        compute='_compute_preavis', store=True
    )

    # Analytique (module budget)
    analytic_line_ids = fields.One2many(
        'account.analytic.line', 'resade_mission_id',
        string='Écritures analytiques GFIC', readonly=True
    )
    analytic_line_count = fields.Integer(
        string='Nb écritures analytiques',
        compute='_compute_analytic_line_count'
    )

    # ─────────────────────────────────────────────
    # COMPUTED
    # ─────────────────────────────────────────────
    @api.depends('participant_ids')
    def _compute_nb_participants(self):
        for rec in self:
            rec.nb_participants = len(rec.participant_ids) + (1 if rec.employee_id else 0)

    @api.depends('type_mission')
    def _compute_avis_pca(self):
        for rec in self:
            rec.avis_pca_requis = rec.type_mission == 'strategique'

    @api.depends('date_depart', 'date_retour')
    def _compute_duree(self):
        for rec in self:
            if rec.date_depart and rec.date_retour:
                rec.duree_jours = max((rec.date_retour - rec.date_depart).days + 1, 1)
            else:
                rec.duree_jours = 0

    @api.depends('date_depart_effectif', 'date_retour_effectif')
    def _compute_duree_reelle(self):
        for rec in self:
            if rec.date_depart_effectif and rec.date_retour_effectif:
                rec.duree_reelle_jours = max(
                    (rec.date_retour_effectif - rec.date_depart_effectif).days + 1, 1
                )
            else:
                rec.duree_reelle_jours = 0

    @api.depends('date_demande', 'date_depart', 'type_mission')
    def _compute_preavis(self):
        for rec in self:
            if rec.date_demande and rec.date_depart:
                jours = (rec.date_depart - rec.date_demande).days
                rec.nb_jours_preavis = jours
                min_j = 10 if rec.type_mission == 'strategique' else 5
                rec.delai_preavis_ok = jours >= min_j
            else:
                rec.nb_jours_preavis = 0
                rec.delai_preavis_ok = False

    @api.depends('line_ids.montant_estime', 'line_ids.est_forfaitaire')
    def _compute_montants(self):
        for rec in self:
            rec.montant_avance_demande = sum(l.montant_estime for l in rec.line_ids)
            rec.montant_perdiem_demande = sum(
                l.montant_estime for l in rec.line_ids if l.est_forfaitaire
            )
            rec.montant_frais_annexes_demande = sum(
                l.montant_estime for l in rec.line_ids if not l.est_forfaitaire
            )
            # Per diem réellement acquis = nuitées APPROUVÉES PAR LE DE × taux,
            # pas la demande initiale du missionnaire (Manuel P-GMD-01 étape 5).
            rec.montant_perdiem_approuve_de = sum(
                l.montant_forfaitaire_du for l in rec.line_ids if l.est_forfaitaire
            )

    @api.depends('line_ids.montant_reel', 'line_ids.est_forfaitaire',
                 'montant_avance_approuve', 'montant_perdiem_approuve_de')
    def _compute_montants_reel(self):
        for rec in self:
            # Le per diem n'est jamais "réalisé" via justificatif : il est acquis
            # dès décaissement. Seuls les frais annexes sont comparés à un réel.
            rec.montant_depense_reel = sum(
                l.montant_reel for l in rec.line_ids
                if l.montant_reel and not l.est_forfaitaire
            )
            rec.montant_avance_frais_annexes_a_solder = max(
                0.0, (rec.montant_avance_approuve or 0.0) - (rec.montant_perdiem_approuve_de or 0.0)
            )

    @api.depends('montant_avance_frais_annexes_a_solder', 'montant_depense_reel')
    def _compute_solde(self):
        for rec in self:
            # Solde calculé UNIQUEMENT sur la partie frais annexes de l'avance.
            # Le per diem forfaitaire (montant_perdiem_approuve_de) est exclu :
            # il reste acquis au missionnaire quoi qu'il arrive (Manuel RESADE).
            diff = rec.montant_avance_frais_annexes_a_solder - rec.montant_depense_reel
            rec.montant_a_rembourser = diff if diff > 0 else 0
            rec.montant_complement = abs(diff) if diff < 0 else 0

    @api.depends('date_retour_effectif', 'date_retour', 'date_soumission_rapport')
    def _compute_delai_rapport(self):
        for rec in self:
            date_ref = rec.date_retour_effectif or rec.date_retour
            if date_ref and rec.date_soumission_rapport:
                delta = (rec.date_soumission_rapport - date_ref).days
                rec.delai_rapport_ok = delta <= 5
                rec.jours_retard_rapport = max(delta - 5, 0)
            else:
                rec.delai_rapport_ok = False
                rec.jours_retard_rapport = 0

    def _compute_analytic_line_count(self):
        for rec in self:
            rec.analytic_line_count = len(rec.analytic_line_ids)

    # ─────────────────────────────────────────────
    # CONTRAINTES
    # ─────────────────────────────────────────────
    @api.constrains('date_depart', 'date_retour', 'date_demande')
    def _check_dates(self):
        for rec in self:
            if rec.date_depart and rec.date_retour:
                if rec.date_retour < rec.date_depart:
                    raise ValidationError(
                        _('La date de retour doit être postérieure à la date de départ.')
                    )
            if rec.date_demande and rec.date_depart:
                delta = (rec.date_depart - rec.date_demande).days
                min_days = 10 if rec.type_mission == 'strategique' else 5
                if delta < min_days:
                    raise ValidationError(
                        _('Préavis insuffisant : %d jour(s) au lieu de %d jours minimum '
                          'pour une mission %s (P-GMD-01 B.7).') % (delta, min_days, rec.type_mission)
                    )

    @api.constrains('vehicule_resade', 'carnet_bord_ids', 'state')
    def _check_carnet_bord(self):
        for rec in self:
            if (rec.vehicule_resade
                    and rec.state in ('rapport_soumis', 'rapport_approuve', 'justif_soumise',
                                      'remboursement_ok', 'cloture')
                    and not rec.carnet_bord_ids):
                raise ValidationError(
                    _('Le carnet de bord véhicule est obligatoire '
                      'quand un véhicule RESADE est utilisé (RESADE-F-GMD-02-03).')
                )

    # ─────────────────────────────────────────────
    # SÉQUENCE
    # ─────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resade.mission'
                ) or _('Nouveau')
        return super().create(vals_list)

    # ─────────────────────────────────────────────
    # WORKFLOW BUTTONS
    # ─────────────────────────────────────────────
    def action_valider_chef(self):
        """P-GMD-01 étape 2 – Validation Chef de département (co-signe TDR)"""
        self.ensure_one()
        if self.state != 'brouillon':
            raise UserError(_('Seul un brouillon peut être validé.'))
        if not self.chef_dept_id:
            raise UserError(_('Veuillez renseigner le Chef de département / Pool.'))
        if not self.tdr_note and not self.tdr_attachment_ids:
            raise UserError(
                _('Veuillez renseigner les TDR ou la note de justification '
                  'avant la validation (RESADE-F-GMD-01-01 ou 01-02).')
            )
        self.write({
            'state': 'valide_chef',
            'valide_par_chef_id': self.env.user.id,
            'valide_chef_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            '✅ TDR/Note co-validé(e) par le Chef de département. '
            'Mission transmise au CAF pour visa budgétaire.'
        ))

    def action_approuver_caf(self):
        """
        P-GMD-01 étape 3 – Approbation CAF avec visa budgétaire.
        Si une ligne budgétaire RESADE est liée, le crédit est réellement
        vérifié et réservé (et non plus une simple case à cocher). Sinon,
        on retombe sur l'ancien comportement déclaratif (legacy).
        """
        self.ensure_one()
        if self.state != 'valide_chef':
            raise UserError(_('La mission doit être validée par le Chef de département.'))
        if self.ligne_budgetaire_id:
            # Lève une UserError explicite si le crédit est insuffisant.
            self.ligne_budgetaire_id.reserver_credit(self.montant_avance_demande or 0.0)
            self.credit_budgetaire_reserve = True
            self.visa_budgetaire = True
        elif not self.visa_budgetaire:
            raise UserError(
                _('Veuillez sélectionner une ligne budgétaire RESADE (recommandé) ou, à défaut, '
                  'accorder le visa budgétaire manuellement avant de soumettre au DE '
                  '(P-GMD-01 étape 3 : vérification disponibilité crédits).')
            )
        self.write({
            'state': 'approuve_caf',
            'approuve_par_caf_id': self.env.user.id,
            'approuve_caf_date': fields.Datetime.now(),
        })
        self.message_post(body=_('💰 Visa budgétaire accordé par le CAF. Mission soumise au DE.'))

    def action_autoriser_de(self):
        """P-GMD-01 étape 5 – Signature Ordre de Mission par le Directeur Exécutif"""
        self.ensure_one()
        if self.state != 'approuve_caf':
            raise UserError(_('La mission doit être approuvée par le CAF.'))
        if self.avis_pca_requis and not self.avis_pca_date:
            raise UserError(
                _('Mission stratégique : la consultation du PCA est obligatoire '
                  'avant l\'autorisation du DE (P-GMD-01 B.5).\n'
                  'Renseignez la date d\'avis PCA.')
            )
        self.write({
            'state': 'autorise_de',
            'autorise_par_de_id': self.env.user.id,
            'autorise_de_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            '📋 Ordre de Mission signé par le Directeur Exécutif. '
            'Numéro : %s') % self.name
        )

    # ─────────────────────────────────────────────
    # INTÉGRATION COMPTABILITÉ ODOO
    # ─────────────────────────────────────────────
    def _get_partner_missionnaire(self):
        """Retourne le res.partner associé au missionnaire (employé), pour
        pouvoir lui adresser un paiement réel (avance) ou recevoir un
        paiement de sa part (reversement de trop-perçu)."""
        self.ensure_one()
        employee = self.employee_id
        if not employee:
            raise UserError(_("Aucun missionnaire (employé) renseigné sur cette mission."))
        partner = getattr(employee, 'work_contact_id', False) or getattr(employee, 'address_home_id', False)
        if not partner:
            raise UserError(_(
                "L'employé %s n'a pas de contact personnel (adresse privée) configuré dans sa fiche RH. "
                "Renseignez-le (fiche employé > Informations privées > Adresse personnelle) avant de "
                "pouvoir décaisser une avance."
            ) % employee.name)
        return partner

    def _creer_paiement_avance(self):
        """Crée et poste le paiement réel de l'avance de mission dans la
        comptabilité Odoo (sortie de banque/caisse vers le compte d'avances
        et acomptes au personnel, sans facture puisqu'il n'y a pas encore de
        justificatif à ce stade)."""
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_(
                "Sélectionnez le journal de paiement (banque/caisse) utilisé pour décaisser l'avance."
            ))
        if not self.compte_avance_id:
            raise UserError(_(
                "Sélectionnez le compte comptable « Avances et acomptes au personnel » à utiliser."
            ))
        if not self.compte_avance_id.reconcile:
            raise UserError(_(
                "Le compte « %s » n'est pas configuré comme lettrable (« Autoriser le lettrage »). "
                "N'utilisez jamais un compte de stock/marchandises pour une avance au personnel : "
                "choisissez ou créez un vrai compte de tiers « Avances et acomptes au personnel » "
                "(Comptabilité > Configuration > Plan comptable), avec le lettrage activé."
            ) % self.compte_avance_id.display_name)
        if not self.montant_avance_approuve or self.montant_avance_approuve <= 0:
            return False
        partner = self._get_partner_missionnaire()
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': self.montant_avance_approuve,
            'journal_id': self.journal_id.id,
            'destination_account_id': self.compte_avance_id.id,
            'memo': _("Avance de mission %s - %s") % (self.name, self.employee_id.name),
            'date': fields.Date.today(),
        })
        payment.action_post()
        self.payment_avance_id = payment.id
        self.message_post(body=_(
            "💳 Pièce comptable créée pour l'avance : paiement %s de %s %s sur le journal %s "
            "(compte %s), bénéficiaire %s."
        ) % (
            payment.name, '{:,.0f}'.format(self.montant_avance_approuve), self.currency_id.name,
            self.journal_id.name, self.compte_avance_id.display_name, partner.name
        ))
        return payment

    def _creer_paiement_regularisation(self):
        """Crée et poste le paiement de régularisation à la clôture financière
        de la mission :
        - trop-perçu (montant_a_rembourser > 0) : le missionnaire reverse la
          différence -> paiement ENTRANT, imputé sur le même compte d'avances
          (le solde du compte d'avance revient ainsi à zéro) ;
        - complément (montant_complement > 0) : RESADE verse la différence
          au missionnaire -> paiement SORTANT, même compte de contrepartie.
        Si les deux montants sont nuls (avance strictement égale aux frais
        réels), aucune écriture supplémentaire n'est nécessaire.

        Cas particulier « aucune avance versée » (P-GMD-01, modalité
        « paiement total après mission ») : le per diem acquis n'a alors
        jamais été payé au missionnaire (il n'est normalement réglé qu'au
        moment du décaissement de l'avance). On l'ajoute dans ce cas au
        complément à verser, pour que le missionnaire perçoive bien
        l'intégralité de ce qui lui est dû."""
        self.ensure_one()
        a_rembourser = self.montant_a_rembourser or 0.0
        complement = self.montant_complement or 0.0
        perdiem_restant_du = 0.0
        if not self.payment_avance_id:
            # Aucune avance n'a été effectivement décaissée : le per diem
            # acquis n'a jamais été versé, on le rajoute au complément.
            perdiem_restant_du = self.montant_perdiem_approuve_de or 0.0
        complement += perdiem_restant_du
        if not a_rembourser and not complement:
            self.message_post(body=_(
                "ℹ️ Avance exactement soldée par les frais réels justifiés : aucune régularisation "
                "comptable nécessaire."
            ))
            return False
        if not self.journal_id:
            raise UserError(_(
                "Sélectionnez le journal de paiement (banque/caisse) utilisé pour la régularisation."
            ))
        if not self.compte_avance_id:
            raise UserError(_(
                "Sélectionnez le compte comptable « Avances et acomptes au personnel » à utiliser."
            ))
        if not self.compte_avance_id.reconcile:
            raise UserError(_(
                "Le compte « %s » n'est pas configuré comme lettrable (« Autoriser le lettrage »). "
                "Choisissez un vrai compte de tiers « Avances et acomptes au personnel »."
            ) % self.compte_avance_id.display_name)
        partner = self._get_partner_missionnaire()
        if a_rembourser > 0:
            payment_type, partner_type, montant = 'inbound', 'customer', a_rembourser
            libelle = _("Reversement trop-perçu mission %s - %s") % (self.name, self.employee_id.name)
        else:
            payment_type, partner_type, montant = 'outbound', 'supplier', complement
            libelle = _("Complément à verser mission %s - %s") % (self.name, self.employee_id.name)
            if perdiem_restant_du:
                libelle += _(" (dont per diem %s %s jamais avancé)") % (
                    '{:,.0f}'.format(perdiem_restant_du), self.currency_id.name
                )
        payment = self.env['account.payment'].create({
            'payment_type': payment_type,
            'partner_type': partner_type,
            'partner_id': partner.id,
            'amount': montant,
            'journal_id': self.journal_id.id,
            'destination_account_id': self.compte_avance_id.id,
            'memo': libelle,
            'date': fields.Date.today(),
        })
        payment.action_post()
        self.payment_regularisation_id = payment.id
        self.message_post(body=_(
            "💳 Pièce comptable de régularisation créée : paiement %s (%s) sur le journal %s."
        ) % (payment.name, libelle, self.journal_id.name))
        return payment

    def action_voir_paiements(self):
        """Ouvre les paiements Odoo (avance + régularisation) liés à cette mission."""
        self.ensure_one()
        payment_ids = (self.payment_avance_id + self.payment_regularisation_id).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiements comptables – %s') % self.name,
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payment_ids)],
        }

    def action_regulariser_paiement_manquant(self):
        """
        BOUTON DE RATTRAPAGE — pour les missions décaissées AVANT la mise à
        jour du module intégrant la génération comptable réelle (le statut
        est déjà « Avance décaissée » ou au-delà, mais aucun account.payment
        n'existe encore pour l'avance).

        Permet de régulariser ces dossiers historiques sans avoir à annuler
        et refaire tout le circuit de validation. N'a aucun effet si un
        paiement existe déjà (pour éviter tout doublon).
        """
        self.ensure_one()
        if self.payment_avance_id:
            raise UserError(_(
                "Un paiement d'avance existe déjà pour cette mission (%s). Aucune régularisation "
                "nécessaire."
            ) % self.payment_avance_id.name)
        if self.state not in ('avance_decaisse', 'en_mission', 'rapport_soumis', 'rapport_approuve',
                               'justif_soumise'):
            raise UserError(_(
                "Cette régularisation ne s'applique qu'aux missions dont l'avance a déjà été "
                "marquée comme décaissée dans le workflow, mais sans pièce comptable associée."
            ))
        self._creer_paiement_avance()
        self.message_post(body=_(
            "🔧 Régularisation comptable manuelle : cette avance avait été marquée décaissée "
            "avant la mise à jour du module (sans pièce comptable générée). Le paiement a été "
            "créé rétroactivement."
        ))

    def action_decaisser_avance(self):
        """
        P-GMD-01 étape 7 – Décaissement de l'avance sur frais (par CAF).

        RESADE autorise 3 modalités de financement de la mission (décision
        du CAF/DE au cas par cas, selon la nature de la mission et la
        confiance accordée au missionnaire) :
        1) Avance totale versée avant le départ (cas le plus fréquent) ;
        2) Aucune avance : tout est payé au missionnaire après la mission,
           sur justificatifs, à l'étape de régularisation (P-GMD-03) ;
        3) Avance partielle, le solde étant réglé après la mission.
        Le montant de l'avance approuvée peut donc légitimement être à 0 —
        ce n'est pas une anomalie, seule une valeur négative est rejetée.

        Le DE a pu réduire les nuitées per diem à l'étape 5 : le montant
        réellement approuvé peut donc être inférieur à ce qui avait été
        réservé sur la ligne budgétaire à l'étape 3 (sur la base de la
        demande initiale). On ajuste ici la réservation à la baisse pour
        libérer l'écart, sans jamais la réajuster à la hausse au-delà de
        ce qui avait été initialement vérifié disponible.
        """
        self.ensure_one()
        if self.state != 'autorise_de':
            raise UserError(_("L'Ordre de Mission doit être signé par le DE."))
        if self.montant_avance_approuve < 0:
            raise UserError(_("Le montant de l'avance approuvée ne peut pas être négatif."))
        if self.credit_budgetaire_reserve and self.ligne_budgetaire_id:
            ecart = (self.montant_avance_demande or 0.0) - (self.montant_avance_approuve or 0.0)
            if ecart > 0:
                # Le DE a approuvé moins que demandé (ex : nuitées réduites,
                # avance partielle, ou aucune avance) : on libère la
                # différence, devenue inutile à ce stade — elle sera
                # réengagée sur le montant réel lors de la régularisation
                # finale (action_valider_remboursement -> constater_realisation).
                self.ligne_budgetaire_id.liberer_credit(ecart)
            elif ecart < 0:
                # Cas rare : montant approuvé supérieur à la demande initiale.
                # Vérifie et réserve le complément (peut lever une erreur si
                # le disponible ne le permet pas).
                self.ligne_budgetaire_id.reserver_credit(-ecart)
        self.write({'state': 'avance_decaisse'})
        if self.montant_avance_approuve > 0:
            self._creer_paiement_avance()
            self.message_post(
                body=_('💵 Avance de %s %s décaissée. Missionnaire a signé le reçu.') % (
                    '{:,.0f}'.format(self.montant_avance_approuve),
                    self.currency_id.name
                )
            )
        else:
            self.message_post(body=_(
                "ℹ️ Aucune avance versée pour cette mission (modalité « paiement total après "
                "mission »). Le missionnaire sera réglé intégralement à la régularisation finale, "
                "sur présentation de ses justificatifs (P-GMD-03)."
            ))


    def action_partir_mission(self):
        """P-GMD-02 étape 1 – Départ en mission"""
        self.ensure_one()
        if self.state != 'avance_decaisse':
            raise UserError(_("L'avance doit être décaissée avant le départ."))
        vals = {'state': 'en_mission'}
        if not self.date_depart_effectif:
            vals['date_depart_effectif'] = fields.Date.today()
        self.write(vals)
        self.message_post(body=_('✈️ Mission démarrée – %s en route vers %s.') % (
            self.employee_id.name, self.destination
        ))

    def action_soumettre_rapport(self):
        """P-GMD-02 étape 4 – Soumission rapport de mission par le missionnaire"""
        self.ensure_one()
        if self.state != 'en_mission':
            raise UserError(_('La mission doit être en cours.'))
        if not self.rapport_mission:
            raise UserError(
                _('Rédigez le rapport de mission avant de le soumettre '
                  '(canevas RESADE-F-GMD-02-01 obligatoire).')
            )
        if not self.fiche_decompte_ids and not self.pieces_jointes_rapport:
            raise UserError(
                _('Joignez la fiche de décompte des frais réels '
                  '(RESADE-F-GMD-02-02) et les pièces justificatives.')
            )
        if self.vehicule_resade and not self.carnet_bord_ids:
            raise UserError(
                _('Joignez le carnet de bord du véhicule RESADE '
                  '(RESADE-F-GMD-02-03).')
            )
        vals = {
            'state': 'rapport_soumis',
            'date_soumission_rapport': fields.Date.today(),
        }
        if not self.date_retour_effectif:
            vals['date_retour_effectif'] = fields.Date.today()
        self.write(vals)
        date_ref = self.date_retour_effectif or self.date_retour
        if date_ref:
            delta = (fields.Date.today() - date_ref).days
            if delta > 5:
                self.message_post(
                    body=_('⚠️ Rapport soumis avec %d jour(s) de retard '
                           '(délai max : 5 jours ouvrables – P-GMD-02 B.3).') % delta
                )
            else:
                self.message_post(body=_('📄 Rapport de mission soumis dans les délais.'))

    def action_valider_rapport_chef(self):
        """P-GMD-02 étape 6 – Validation rapport par le Chef de département"""
        self.ensure_one()
        if self.state != 'rapport_soumis':
            raise UserError(_('Le rapport doit être soumis avant validation.'))
        if not self.checklist_rapport_ok:
            raise UserError(
                _('Validez la checklist de conformité du dossier de retour '
                  '(RESADE-F-GMD-02-05) avant de valider le rapport.')
            )
        self.write({
            'rapport_valide_chef': True,
            'rapport_valide_chef_date': fields.Datetime.now(),
            'rapport_valide_chef_id': self.env.user.id,
        })
        self.message_post(body=_(
            '✅ Rapport validé par le Chef de département. '
            'Transmis au DE pour approbation finale (P-GMD-02 étape 6).'
        ))

    def action_approuver_rapport_de(self):
        """P-GMD-02 étape 7 – Approbation rapport par le Directeur Exécutif"""
        self.ensure_one()
        if self.state != 'rapport_soumis':
            raise UserError(_('Le rapport doit être soumis.'))
        if not self.rapport_valide_chef:
            raise UserError(
                _('Le Chef de département doit valider le rapport '
                  'avant l\'approbation du DE (P-GMD-02 B.8 séq. 6→7).')
            )
        self.write({
            'state': 'rapport_approuve',
            'rapport_approuve_de': True,
            'rapport_approuve_de_date': fields.Datetime.now(),
            'rapport_approuve_de_id': self.env.user.id,
        })
        self.message_post(body=_(
            '✔️ Rapport de mission approuvé par le Directeur Exécutif. '
            'Rapport diffusé aux destinataires internes. '
            'Processus P-GMD-03 (justification/remboursement) déclenché.'
        ))

    def action_soumettre_justification(self):
        """P-GMD-03 – Soumission justification frais de mission"""
        self.ensure_one()
        if self.state != 'rapport_approuve':
            raise UserError(
                _('Le rapport de mission doit être approuvé par le DE '
                  'avant la soumission de la justification (P-GMD-03).')
            )
        if not self.pieces_jointes_justif and not self.fiche_decompte_ids:
            raise UserError(
                _('Joignez les pièces justificatives de dépenses '
                  '(factures, reçus, billets) et la fiche de décompte RESADE-F-GMD-02-02.')
            )
        self.write({
            'state': 'justif_soumise',
            'date_justification': fields.Date.today(),
        })
        self.message_post(body=_(
            '🧾 Justification des frais soumise au CAF pour contrôle. '
            'Solde à régler : %s %s (trop-perçu) / %s %s (complément).') % (
            '{:,.0f}'.format(self.montant_a_rembourser), self.currency_id.name,
            '{:,.0f}'.format(self.montant_complement), self.currency_id.name,
        ))

    def action_valider_remboursement(self):
        """P-GMD-03 – Validation remboursement/reversement par le CAF"""
        self.ensure_one()
        if self.state != 'justif_soumise':
            raise UserError(_('La justification doit être soumise.'))
        if not self.remboursement_valide_caf:
            raise UserError(
                _('Cochez la validation du remboursement/reversement '
                  'par le CAF avant de clôturer (P-GMD-03).')
            )
        if self.credit_budgetaire_reserve and self.ligne_budgetaire_id:
            # Manuel P-ESB-01, étape 7 : solde l'engagement réellement réservé
            # (montant_avance_approuve, déjà ajusté au décaissement — voir
            # action_decaisser_avance) et constate la dépense définitive :
            # le per diem approuvé est acquis en entier (forfaitaire, jamais
            # justifié) + les frais annexes réellement justifiés sur reçu.
            montant_realise_definitif = (
                (self.montant_perdiem_approuve_de or 0.0) + (self.montant_depense_reel or 0.0)
            )
            self.ligne_budgetaire_id.constater_realisation(
                self.montant_avance_approuve or 0.0, montant_realise_definitif
            )
        self.write({
            'state': 'remboursement_ok',
            'date_remboursement': self.date_remboursement or fields.Date.today(),
        })
        self._creer_paiement_regularisation()
        self.message_post(body=_(
            '💳 Remboursement/reversement validé par le CAF. '
            'Trop-perçu reversé : %s %s | Complément versé : %s %s.') % (
            '{:,.0f}'.format(self.montant_a_rembourser), self.currency_id.name,
            '{:,.0f}'.format(self.montant_complement), self.currency_id.name,
        ))

    def action_cloturer(self):
        """Clôture finale – écriture analytique GFIC + archivage"""
        self.ensure_one()
        if self.state != 'remboursement_ok':
            raise UserError(
                _('Le remboursement/reversement doit être validé par le CAF '
                  'avant la clôture (P-GMD-03).')
            )
        self.write({'state': 'cloture'})
        self._generer_ecriture_analytique()
        if self.type_mission == 'strategique' and not self.restitution_interne_faite:
            self.message_post(body=_(
                '⚠️ Rappel : La restitution interne est obligatoire '
                'pour les missions stratégiques (P-GMD-02 B.7 étape 8).'
            ))
        self.message_post(body=_('🏁 Mission clôturée et dossier archivé dans la GED.'))

    def action_refuser(self):
        """Refus à toute étape"""
        self.ensure_one()
        if not self.motif_refus:
            raise UserError(
                _('Renseignez le motif du refus '
                  '(obligatoire – RESADE-F-GMD-01-06 registre OM).')
            )
        if self.credit_budgetaire_reserve and self.ligne_budgetaire_id:
            # Le montant réellement engagé sur la ligne dépend de l'étape :
            # avant le décaissement (action_decaisser_avance), c'est encore la
            # demande initiale ; après, c'est le montant approuvé (ajusté).
            montant_engage = (
                self.montant_avance_approuve
                if self.state in ('autorise_de', 'avance_decaisse', 'en_mission',
                                  'rapport_soumis', 'rapport_approuve', 'justif_soumise')
                and self.montant_avance_approuve
                else self.montant_avance_demande
            )
            self.ligne_budgetaire_id.liberer_credit(montant_engage or 0.0)
            self.credit_budgetaire_reserve = False
        self.write({
            'state': 'refuse',
            'refuse_par_id': self.env.user.id,
        })
        self.message_post(
            body=_('❌ Mission refusée par %s.\nMotif : %s\nCrédit budgétaire libéré le cas échéant.') % (
                self.env.user.name, self.motif_refus
            )
        )

    def action_remettre_brouillon(self):
        """Remettre en brouillon pour correction"""
        self.ensure_one()
        if self.state in ('avance_decaisse', 'en_mission', 'remboursement_ok', 'cloture'):
            raise UserError(_('Impossible de revenir en brouillon à ce stade.'))
        self.write({'state': 'brouillon'})
        self.message_post(body=_('🔄 Mission remise en brouillon pour correction.'))

    # ─────────────────────────────────────────────
    # ANALYTIQUE / GFIC
    # ─────────────────────────────────────────────
    def _generer_ecriture_analytique(self):
        """Crée une écriture analytique dans GFIC à la clôture de la mission"""
        self.ensure_one()
        montant = self.montant_depense_reel or self.montant_avance_approuve
        if not montant or not self.analytic_account_id:
            return
        date_ecriture = self.date_retour_effectif or self.date_retour or fields.Date.today()
        vals = {
            'name': f'Mission {self.name} – {self.destination} – {self.employee_id.name}',
            'date': date_ecriture,
            'account_id': self.analytic_account_id.id,
            'amount': -montant,
            'resade_mission_id': self.id,
            'ref': self.name,
        }
        self.env['account.analytic.line'].sudo().create(vals)
        self.message_post(
            body=_('📊 Écriture analytique créée dans GFIC : %s FCFA imputés sur %s') % (
                '{:,.0f}'.format(montant), self.analytic_account_id.name
            )
        )

    def action_voir_ecritures(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Écritures analytiques – {self.name}',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form',
            'domain': [('resade_mission_id', '=', self.id)],
        }

    # ─────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────
    def action_imprimer_om(self):
        """Imprimer l'Ordre de Mission (RESADE-F-GMD-01-03)"""
        return self.env.ref(
            'resade_mission.action_report_resade_mission'
        ).report_action(self)

    # ─────────────────────────────────────────────
    # CRON
    # ─────────────────────────────────────────────
    @api.model
    def _cron_alertes_rapports(self):
        """CRON : alerte automatique J+4 pour les rapports de mission en retard (P-GMD-02 R6)"""
        seuil_alerte = fields.Date.today() - timedelta(days=4)
        seuil_retard = fields.Date.today() - timedelta(days=5)
        # Alerte préventive J+4
        missions_alerte = self.search([
            ('state', '=', 'en_mission'),
            ('date_retour_effectif', '<=', seuil_alerte),
            ('date_retour_effectif', '>', seuil_retard),
        ])
        for m in missions_alerte:
            m.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('📋 Rapport de mission à soumettre demain (J+5 max)'),
                note=_('La mission %s – %s doit faire l\'objet d\'un rapport '
                       'au plus tard demain (délai P-GMD-02 : 5 jours ouvrables).') % (
                    m.name, m.destination),
                user_id=m.employee_id.user_id.id,
            )
        # Retard confirmé J+5 dépassé
        missions_retard = self.search([
            ('state', '=', 'en_mission'),
            ('date_retour_effectif', '<=', seuil_retard),
        ])
        for m in missions_retard:
            m.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('⚠️ RETARD : Rapport de mission en retard !'),
                note=_('La mission %s est en retard de rapport. '
                       'Suspension des nouvelles avances possible (R6 P-GMD-02).') % m.name,
                user_id=m.employee_id.user_id.id,
            )


    # ─────────────────────────────────────────────
    # REGISTRE F-GMD-02-04 (création automatique)
    # ─────────────────────────────────────────────
    registre_id = fields.Many2one(
        'resade.registre.mission',
        string='Entrée registre F-GMD-02-04',
        readonly=True,
        copy=False,
    )

    def action_partir_mission_et_registre(self):
        """Override pour créer l'entrée registre au départ en mission"""
        self.ensure_one()
        # Appel de la méthode parente
        self.action_partir_mission()
        # Création automatique dans le registre F-GMD-02-04
        if not self.registre_id:
            registre = self.env['resade.registre.mission'].create({
                'mission_id': self.id,
                'lien_ged': f'02_ADMINISTRATION/Archives_Missions/{self.name}',
            })
            self.registre_id = registre.id
            self.message_post(
                body=_(
                    '📋 Enregistrement créé dans le Registre des missions '
                    'exécutées (RESADE-F-GMD-02-04). '
                    'L\'AA devra confirmer l\'archivage GED après approbation du rapport.'
                )
            )

    def action_voir_registre(self):
        """Ouvrir l'entrée registre depuis la mission"""
        self.ensure_one()
        if self.registre_id:
            return {
                'type': 'ir.actions.act_window',
                'name': f'Registre F-GMD-02-04 – {self.name}',
                'res_model': 'resade.registre.mission',
                'res_id': self.registre_id.id,
                'view_mode': 'form',
            }
