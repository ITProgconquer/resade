# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeCourrierSortant(models.Model):
    """
    Processus P-GC-02 : Gestion du courrier sortant (physique et électronique)
    Manuel RESADE - Carnet G - Module 01

    Circuit (Manuel B.7 / B.8) :
    1. Rédaction du projet (Initiateur)             -> brouillon
    2. Visa AA                                       -> vise_aa
    3. Visa CAF (cohérence administrative/financière)-> vise_caf
    4. Signature DE (ou PCA)                         -> signe
    5. Numérotation institutionnelle (AA)            -> numerote
       [N°ordre]-[AAAA]/[Code projet]/[Initiateur]/[Signataire]
    6. Envoi / expédition + preuve d'envoi           -> envoye
    7. Classement + archivage GED (<= 48h)           -> archive
    """
    _name = 'resade.courrier.sortant'
    _description = 'Courrier Sortant RESADE (P-GC-02)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'numero'
    _order = 'create_date desc'

    # ─────────────────────────────────────────────
    # IDENTIFICATION
    # ─────────────────────────────────────────────
    numero = fields.Char(
        string='N° du courrier', readonly=True, copy=False, tracking=True,
        help="Convention : [N°ordre]-[AAAA]/[Code projet ou RESADE]/[Initiateur]/[Signataire]"
    )
    objet_id = fields.Many2one('resade.courrier.objet', string='Objet / Catégorie')
    objet_libre = fields.Char(string='Objet du courrier', required=True, tracking=True)
    confidentiel = fields.Boolean(string='Confidentiel', default=False)

    code_projet = fields.Char(string='Code projet (ou « RESADE »)', default='RESADE')

    # Initiateur
    initiateur_id = fields.Many2one(
        'hr.employee', string='Initiateur', required=True, tracking=True,
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
    )
    service_initiateur_id = fields.Many2one('resade.courrier.service', string='Service initiateur')

    # Destinataire externe
    tiers_destinataire_id = fields.Many2one('resade.courrier.tiers', string='Structure destinataire')
    contact_destinataire_id = fields.Many2one('resade.courrier.contact', string='Contact destinataire')
    nom_destinataire_libre = fields.Char(string="Destinataire (si non répertorié)")

    type_envoi = fields.Selection([
        ('remise_physique', 'Remise physique (agent de liaison)'),
        ('postal', 'Envoi postal'),
        ('electronique', 'Envoi électronique (@resade)'),
    ], string="Mode d'envoi prévu", default='electronique')

    # ─────────────────────────────────────────────
    # PROJET DE COURRIER
    # ─────────────────────────────────────────────
    document_projet = fields.Many2many(
        'ir.attachment', 'courrier_sortant_pj_projet_rel', string='Projet de lettre + pièces jointes'
    )
    document_signe = fields.Many2many(
        'ir.attachment', 'courrier_sortant_pj_signe_rel', string='Courrier signé (scan)'
    )

    # ─────────────────────────────────────────────
    # VISAS / CIRCUIT DE VALIDATION (B.8 du Manuel)
    # ─────────────────────────────────────────────
    vise_aa_par = fields.Many2one('res.users', string='Visé AA par', readonly=True)
    date_visa_aa = fields.Datetime(string='Date visa AA', readonly=True)

    vise_caf_par = fields.Many2one('res.users', string='Visé CAF par', readonly=True)
    date_visa_caf = fields.Datetime(string='Date visa CAF', readonly=True)
    commentaire_caf = fields.Text(string='Commentaire CAF (en cas d\'anomalie)')

    signataire_id = fields.Many2one(
        'hr.employee', string='Signataire',
        help="Directeur Exécutif (par défaut). Président du CA pour les courriers du DE lui-même."
    )
    type_signataire = fields.Selection([
        ('de', 'Directeur Exécutif'),
        ('pca', "Président du Conseil d'Administration"),
        ('sg', 'Secrétaire Général (courriers du PCA)'),
    ], string='Qualité du signataire', default='de')
    date_signature = fields.Datetime(string='Date de signature', readonly=True)
    annotation_retour = fields.Text(string='Annotations (si retourné pour correction)')

    # ─────────────────────────────────────────────
    # ENVOI / PREUVE D'ENVOI
    # ─────────────────────────────────────────────
    date_envoi = fields.Datetime(string="Date d'envoi")
    preuve_envoi = fields.Many2many(
        'ir.attachment', 'courrier_sortant_pj_preuve_rel',
        string="Preuve d'envoi (décharge, AR, bordereau, n° de suivi)"
    )
    reference_suivi_postal = fields.Char(string='N° de suivi postal (si envoi postal)')
    copie_initiateur_remise = fields.Boolean(string='Copie remise à l\'initiateur', default=False)

    # ─────────────────────────────────────────────
    # ARCHIVAGE (<= 48h après envoi)
    # ─────────────────────────────────────────────
    archive_chrono_physique = fields.Boolean(string='Classé au Chrono Courrier Départ', default=False)
    archive_ged = fields.Boolean(string='Archivé en GED', default=False, tracking=True)
    date_archivage_ged = fields.Datetime(string='Date archivage GED')
    reference_ged = fields.Char(string='Référence / lien GED')

    # ─────────────────────────────────────────────
    # ÉTAT
    # ─────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', '📝 Brouillon'),
        ('vise_aa', '✅ Visé AA'),
        ('vise_caf', '💰 Visé CAF'),
        ('signe', '✍️ Signé DE/PCA'),
        ('numerote', '🔢 Numéroté'),
        ('envoye', '📤 Envoyé'),
        ('archive', '🗄️ Archivé (clôturé)'),
        ('refuse', '❌ Retourné pour correction'),
    ], string='État', default='brouillon', tracking=True, copy=False)

    delai_validation_h = fields.Float(
        string='Délai initiation → signature (h)', compute='_compute_delais', store=True
    )
    depassement_validation = fields.Boolean(
        string='Délai validation dépassé (> 24h std / > 4h urgent)',
        compute='_compute_delais', store=True
    )
    urgent = fields.Boolean(string='Urgent (délai cible 4h)', default=False)

    note_interne = fields.Text(string='Note interne')

    @api.depends('create_date', 'date_signature')
    def _compute_delais(self):
        for rec in self:
            rec.delai_validation_h = 0.0
            rec.depassement_validation = False
            if rec.create_date and rec.date_signature:
                delta = rec.date_signature - rec.create_date
                heures = delta.total_seconds() / 3600.0
                rec.delai_validation_h = heures
                seuil = 4.0 if rec.urgent else 24.0
                rec.depassement_validation = heures > seuil

    # ─────────────────────────────────────────────
    # ACTIONS DU WORKFLOW
    # ─────────────────────────────────────────────
    def action_viser_aa(self):
        """Étape 2a : visa de conformité formelle par l'AA."""
        for rec in self:
            if not rec.document_projet:
                raise UserError(_(
                    "Veuillez joindre le projet de lettre avant de le viser (Manuel P-GC-02, étape 1)."
                ))
            rec.write({
                'state': 'vise_aa',
                'vise_aa_par': self.env.user.id,
                'date_visa_aa': fields.Datetime.now(),
            })

    def action_viser_caf(self):
        """Étape 2b : visa de cohérence administrative/financière par le CAF."""
        for rec in self:
            rec.write({
                'state': 'vise_caf',
                'vise_caf_par': self.env.user.id,
                'date_visa_caf': fields.Datetime.now(),
            })

    def action_retourner_initiateur(self):
        """Le CAF ou le DE retourne le projet à l'initiateur avec commentaire."""
        for rec in self:
            if not rec.commentaire_caf and not rec.annotation_retour:
                raise UserError(_("Merci d'indiquer le motif du retour à l'initiateur."))
            rec.write({'state': 'refuse'})

    def action_signer(self):
        """Étape 2c : signature DE (ou PCA pour les courriers du DE)."""
        for rec in self:
            if not rec.signataire_id:
                raise UserError(_("Veuillez désigner le signataire avant la signature."))
            rec.write({
                'state': 'signe',
                'date_signature': fields.Datetime.now(),
            })

    def action_numeroter(self):
        """Étape 3 : attribution du numéro séquentiel institutionnel."""
        for rec in self:
            if rec.numero:
                continue
            initiateur_code = (rec.initiateur_id.name or 'NA')[:3].upper()
            signataire_code = dict(rec._fields['type_signataire'].selection).get(
                rec.type_signataire, 'DE'
            )[:3].upper()
            seq = self.env['ir.sequence'].next_by_code('resade.courrier.sortant') or '000'
            annee = fields.Date.context_today(self).year
            rec.numero = f"{seq}-{annee}/{rec.code_projet or 'RESADE'}/{initiateur_code}/{signataire_code}"
            rec.state = 'numerote'

    def action_envoyer(self):
        """Étape 5 : envoi effectif + preuve d'envoi."""
        for rec in self:
            if not rec.numero:
                raise UserError(_("Le courrier doit être numéroté avant l'envoi (Manuel P-GC-02, étape 3)."))
            if not rec.preuve_envoi:
                raise UserError(_(
                    "Une preuve d'envoi (décharge, accusé de réception, n° de suivi) est requise "
                    "avant de confirmer l'envoi (Manuel P-GC-02, étape 5)."
                ))
            rec.write({
                'state': 'envoye',
                'date_envoi': fields.Datetime.now(),
            })

    def action_archiver(self):
        """Étape 7 : classement + archivage GED (<= 48h après envoi)."""
        for rec in self:
            if not rec.archive_ged:
                raise UserError(_("Veuillez confirmer l'archivage GED avant de clôturer ce courrier."))
            rec.write({
                'state': 'archive',
                'date_archivage_ged': rec.date_archivage_ged or fields.Datetime.now(),
            })
