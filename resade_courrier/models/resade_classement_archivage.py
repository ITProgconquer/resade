# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeClasseur(models.Model):
    """
    Processus P-CA-01 : Plan de classement et archivage physique
    Manuel RESADE - Carnet G - Module 02

    Cycle de vie du classeur (Manuel B.7) :
    1. Création / identification (nomenclature 3 niveaux)        -> actif
    2. Classement courant (âge actif)                            -> actif
    3. Vérification trimestrielle (RESADE-F-CA-01-05)
    4. Transfert en pré-archivage (DUA âge actif échue)          -> pre_archivage
    5. Décision de sort final (commission AA + CAF + DE)         -> sort_final_a_decider
    6a. Archivage définitif (conservation)                       -> archive_definitif
    6b. Destruction documentée (PV signé DE + CAF)                -> detruit
    """
    _name = 'resade.classeur'
    _description = 'Classeur physique - Tableau de bord (P-CA-01)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code_classeur'
    _rec_name = 'code_classeur'

    # ─────────────────────────────────────────────
    # NOMENCLATURE 3 NIVEAUX (Manuel B.6 / Annexe B.6.a)
    # ─────────────────────────────────────────────
    code_classeur = fields.Char(
        string='Code complet du classeur', required=True, copy=False, tracking=True,
        help="Format : [Code couleur/nature]-[Intitulé]-[Projet ou RESADE]-[Année]. "
             "Ex. G-COUR-ARR-2026"
    )
    nature = fields.Selection([
        ('courrier', 'Courrier'),
        ('finances', 'Finances'),
        ('rh', 'Ressources Humaines'),
        ('projets', 'Projets / R&D'),
        ('partenariats', 'Partenariats'),
        ('gouvernance', 'Gouvernance'),
    ], string='Niveau 1 : Nature', required=True, tracking=True)

    code_couleur = fields.Selection([
        ('vert', 'VERT — Courrier'),
        ('bleu', 'BLEU — Finances'),
        ('rouge', 'ROUGE — Contrats / Conventions'),
        ('orange', 'ORANGE — Projets / R&D'),
        ('gris', 'GRIS — RH'),
        ('violet', 'VIOLET — Gouvernance'),
    ], string='Code couleur', compute='_compute_code_couleur', store=True)

    intitule = fields.Char(string='Niveau 2 : Intitulé du classeur', required=True)
    code_projet = fields.Char(string='Projet / Programme (ou « RESADE »)', default='RESADE')
    annee = fields.Char(string='Niveau 3 : Année', default=lambda self: str(fields.Date.context_today(self).year))

    responsable_id = fields.Many2one(
        'hr.employee', string='Responsable classement', required=True, tracking=True
    )
    suppleant_id = fields.Many2one('hr.employee', string='Suppléant classement')
    emplacement = fields.Char(string='Armoire / Emplacement')
    confidentiel = fields.Boolean(string='Documents confidentiels (accès restreint)', default=False)

    # ─────────────────────────────────────────────
    # DURÉE D'UTILITÉ ADMINISTRATIVE (DUA) — Tableau RESADE-F-CA-01-02
    # ─────────────────────────────────────────────
    dua_age_actif_mois = fields.Integer(
        string='DUA âge actif (mois)',
        help='Durée de conservation en classement courant avant transfert en pré-archivage.'
    )
    dua_totale_annees = fields.Integer(
        string='DUA totale (années)',
        help="Durée légale/contractuelle totale (OHADA/SYCEBNL, Code du travail, exigences bailleurs)."
    )
    sort_final_prevu = fields.Selection([
        ('conservation', 'Conservation permanente'),
        ('destruction', 'Destruction après échéance DUA'),
    ], string='Sort final prévu')
    reference_reglementaire = fields.Char(string='Référence réglementaire applicable')

    # ─────────────────────────────────────────────
    # CYCLE DE VIE
    # ─────────────────────────────────────────────
    state = fields.Selection([
        ('actif', '🗂️ Classement courant (âge actif)'),
        ('pre_archivage', '📦 Pré-archivage (âge intermédiaire)'),
        ('sort_final_a_decider', '⚖️ Sort final à décider'),
        ('archive_definitif', '🏛️ Archivé définitivement'),
        ('detruit', '🗑️ Détruit (PV signé)'),
    ], string='État', default='actif', tracking=True, copy=False)

    sature = fields.Boolean(string='Classeur saturé (à diviser)', default=False, tracking=True)

    # ─────────────────────────────────────────────
    # TRANSFERT EN PRÉ-ARCHIVAGE (RESADE-F-CA-01-06)
    # ─────────────────────────────────────────────
    date_transfert_pre_archivage = fields.Date(string='Date de transfert en pré-archivage')
    date_fin_dua_totale = fields.Date(string='Date de fin DUA totale (échéance)')
    boite_archive_ref = fields.Char(string="Référence boîte d'archives")
    local_pre_archivage = fields.Char(string='Emplacement local de pré-archivage')

    # ─────────────────────────────────────────────
    # SORT FINAL (commission AA + CAF + DE) — RESADE-F-CA-01-04 / -07
    # ─────────────────────────────────────────────
    decision_sort_final = fields.Selection([
        ('conservation', 'Conservation permanente'),
        ('destruction', 'Destruction'),
    ], string='Décision de sort final')
    date_decision_sort_final = fields.Date(string='Date de la décision')
    decide_par_ids = fields.Many2many(
        'hr.employee', 'classeur_decision_sort_final_rel',
        string='Décidé par (commission AA+CAF+DE)'
    )

    # Conservation
    inventaire_archives_ref = fields.Char(string='Référence inventaire archives définitives')
    date_archivage_definitif = fields.Date(string='Date archivage définitif')

    # Destruction
    pv_destruction = fields.Binary(string='PV de destruction (signé DE + CAF)')
    pv_destruction_filename = fields.Char()
    date_destruction = fields.Date(string='Date de destruction effective')
    motif_destruction = fields.Text(string='Motif de la destruction')

    # ─────────────────────────────────────────────
    # VÉRIFICATION TRIMESTRIELLE (RESADE-F-CA-01-05)
    # ─────────────────────────────────────────────
    date_derniere_verification = fields.Date(string='Date de dernière vérification trimestrielle')
    conforme = fields.Boolean(string='Conforme à la nomenclature', default=True)
    anomalie_constatee = fields.Text(string='Anomalie constatée (si non conforme)')

    note_interne = fields.Text(string='Note interne')

    @api.depends('nature')
    def _compute_code_couleur(self):
        mapping = {
            'courrier': 'vert', 'finances': 'bleu', 'rh': 'gris',
            'projets': 'orange', 'partenariats': 'orange', 'gouvernance': 'violet',
        }
        for rec in self:
            rec.code_couleur = mapping.get(rec.nature, False)

    def action_transferer_pre_archivage(self):
        """Étape 5 : transfert en âge intermédiaire (Manuel B.7, étape 5)."""
        for rec in self:
            if not rec.boite_archive_ref:
                raise UserError(_(
                    "Veuillez indiquer la référence de la boîte d'archives avant le transfert "
                    "(Manuel P-CA-01, étape 5)."
                ))
            rec.write({
                'state': 'pre_archivage',
                'date_transfert_pre_archivage': fields.Date.today(),
            })

    def action_proposer_sort_final(self):
        """Étape 6 : ouverture de la décision collégiale de sort final."""
        for rec in self:
            rec.state = 'sort_final_a_decider'

    def action_decider_conservation(self):
        """Étape 7a : décision de conservation définitive (DE accountable)."""
        for rec in self:
            rec.write({
                'decision_sort_final': 'conservation',
                'date_decision_sort_final': fields.Date.today(),
                'state': 'archive_definitif',
                'date_archivage_definitif': fields.Date.today(),
            })
            rec.message_post(body=_("🏛️ Classeur archivé définitivement (conservation permanente)."))

    def action_decider_destruction(self):
        """Étape 7b : décision de destruction - nécessite PV signé DE + CAF."""
        for rec in self:
            if not rec.pv_destruction:
                raise UserError(_(
                    "Aucune destruction n'est possible sans PV de destruction signé "
                    "par le DE et le CAF (Manuel P-CA-01, étape 7b)."
                ))
            rec.write({
                'decision_sort_final': 'destruction',
                'date_decision_sort_final': fields.Date.today(),
                'state': 'detruit',
                'date_destruction': fields.Date.today(),
            })
            rec.message_post(body=_("🗑️ Classeur détruit conformément au PV de destruction signé."))


class ResadeNumerisation(models.Model):
    """
    Processus P-CA-03 : Numérisation des documents physiques stratégiques
    Manuel RESADE - Carnet G - Module 02

    Workflow (Manuel B.7) :
    1. Inscription sur liste prioritaire (P1/P2/P3)      -> a_numeriser
    2. Numérisation (scan >= 300dpi, PDF/A)               -> en_cours
    3. Contrôle qualité (fiche RESADE-F-CA-03-02)         -> controle
    4. Versement dans la GED (selon P-CA-02)              -> numerise
    """
    _name = 'resade.numerisation'
    _description = 'Numérisation document physique stratégique (P-CA-03)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_inscription desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Référence registre', required=True, copy=False, readonly=True,
        default=lambda self: _('Nouveau'), tracking=True,
    )
    intitule_document = fields.Char(string='Intitulé du document', required=True, tracking=True)
    classeur_id = fields.Many2one('resade.classeur', string='Classeur physique d\'origine')

    # ─────────────────────────────────────────────
    # LISTE PRIORITAIRE (RESADE-F-CA-03-01) — Grille de critères
    # ─────────────────────────────────────────────
    priorite = fields.Selection([
        ('p1', 'P1 — Urgente (valeur juridique/financière critique, risque de perte élevé)'),
        ('p2', 'P2 — Importante'),
        ('p3', 'P3 — Standard'),
    ], string='Niveau de priorité', required=True, default='p2', tracking=True)
    valeur_juridique = fields.Boolean(string='Valeur juridique')
    valeur_financiere = fields.Boolean(string='Valeur financière')
    risque_perte = fields.Boolean(string='Risque de perte élevé')
    irremplacable = fields.Boolean(string='Document irremplaçable')

    chef_dept_demandeur_id = fields.Many2one(
        'hr.employee', string='Chef de département demandeur'
    )
    valide_par_caf = fields.Boolean(string='Liste validée par le CAF', default=False)
    approuve_par_de = fields.Boolean(string='Liste approuvée par le DE', default=False)

    date_inscription = fields.Date(string="Date d'inscription sur la liste", default=fields.Date.context_today)

    # ─────────────────────────────────────────────
    # EXÉCUTION DE LA NUMÉRISATION
    # ─────────────────────────────────────────────
    date_debut_numerisation = fields.Date(string='Date de début de numérisation')
    date_fin_numerisation = fields.Date(string='Date de fin de numérisation')
    resolution_dpi = fields.Integer(string='Résolution (dpi)', default=300)
    format_fichier = fields.Selection([
        ('pdfa', 'PDF/A (archivage pérenne)'),
        ('pdf', 'PDF standard (non conforme archivage long terme)'),
    ], string='Format du fichier', default='pdfa')
    fichier_numerise = fields.Binary(string='Fichier numérisé')
    fichier_numerise_filename = fields.Char()

    # ─────────────────────────────────────────────
    # CONTRÔLE QUALITÉ (Fiche RESADE-F-CA-03-02)
    # ─────────────────────────────────────────────
    controle_lisibilite_ok = fields.Boolean(string='Lisibilité vérifiée')
    controle_integrite_ok = fields.Boolean(string='Intégrité / complétude vérifiée')
    controle_nommage_ok = fields.Boolean(string='Nommage conforme à la convention RESADE-F-CA-02-03')
    controle_par_id = fields.Many2one('hr.employee', string='Contrôlé par (AA + CSI)')
    date_controle = fields.Date(string='Date du contrôle qualité')
    motif_rejet = fields.Text(string='Motif de rejet (si non conforme)')

    # ─────────────────────────────────────────────
    # VERSEMENT DANS LA GED (lien vers P-CA-02)
    # ─────────────────────────────────────────────
    ged_document_id = fields.Many2one(
        'resade.ged.document', string='Document GED associé (P-CA-02)'
    )
    original_conserve = fields.Boolean(
        string='Original physique conservé', default=True,
        help="Règle : tout original est conservé après numérisation sauf décision explicite du DE "
             "(Manuel P-CA-03, risque R11)."
    )
    etiquette_apposee = fields.Boolean(string="Étiquette « NUMÉRISÉ — Original à conserver » apposée")

    state = fields.Selection([
        ('a_numeriser', '📋 À numériser (liste prioritaire)'),
        ('en_cours', '🖨️ Numérisation en cours'),
        ('controle', '🔍 Contrôle qualité'),
        ('rejete', '❌ Rejeté (à refaire)'),
        ('numerise', '✅ Numérisé et versé en GED'),
    ], string='État', default='a_numeriser', tracking=True, copy=False)

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.numerisation') or _('Nouveau')
        return super().create(vals_list)

    def action_demarrer_numerisation(self):
        for rec in self:
            if not (rec.valide_par_caf and rec.approuve_par_de):
                raise UserError(_(
                    "La liste prioritaire doit être validée par le CAF et approuvée par le DE "
                    "avant de démarrer la numérisation (Manuel P-CA-03, B.5)."
                ))
            rec.write({'state': 'en_cours', 'date_debut_numerisation': fields.Date.today()})

    def action_soumettre_controle(self):
        for rec in self:
            if not rec.fichier_numerise:
                raise UserError(_("Veuillez joindre le fichier numérisé avant de le soumettre au contrôle qualité."))
            rec.write({'state': 'controle', 'date_fin_numerisation': fields.Date.today()})

    def action_valider_controle(self):
        """Double validation AA + CSI obligatoire avant tout versement GED (risque R6)."""
        for rec in self:
            if not (rec.controle_lisibilite_ok and rec.controle_integrite_ok and rec.controle_nommage_ok):
                raise UserError(_(
                    "Le versement dans la GED est refusé : la fiche de contrôle qualité "
                    "(lisibilité, intégrité, nommage) doit être entièrement validée "
                    "(Manuel P-CA-03, risque R6)."
                ))
            if rec.format_fichier != 'pdfa':
                raise UserError(_(
                    "Le format PDF/A est obligatoire pour tout document à vocation d'archivage "
                    "(Manuel P-CA-03, risque R8)."
                ))
            rec.write({
                'state': 'numerise',
                'date_controle': fields.Date.today(),
                'etiquette_apposee': True,
            })
            rec.message_post(body=_("✅ Document numérisé, contrôlé et versé en GED (P-CA-03 → P-CA-02)."))

    def action_rejeter(self):
        for rec in self:
            if not rec.motif_rejet:
                raise UserError(_("Merci d'indiquer le motif du rejet."))
            rec.write({'state': 'rejete'})
