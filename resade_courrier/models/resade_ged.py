# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeGedDocument(models.Model):
    """
    Processus P-CA-02 : Archivage numérique et Gestion Électronique des
    Documents (GED) - SharePoint / Google Drive
    Manuel RESADE - Carnet G - Module 02

    Workflow (Manuel B.7 / B.8) :
    1. Déclenchement de l'archivage (responsable du document)   -> a_archiver
    2. Préparation et nommage du fichier (AA, <=24h)             -> a_archiver
    3. Classement dans la GED (AA, <=48h)                        -> archive
    4. Vérification des droits d'accès (CSI)                    -> archive
    5. Enregistrement dans le tableau de bord GED (AA)           -> archive
    """
    _name = 'resade.ged.document'
    _description = 'Document GED - Tableau de bord de suivi (P-CA-02)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_declenchement desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Référence GED', required=True, copy=False, readonly=True,
        default=lambda self: _('Nouveau'), tracking=True,
    )
    intitule_document = fields.Char(string='Intitulé du document', required=True, tracking=True)

    # ─────────────────────────────────────────────
    # CLASSIFICATION (architecture de dossiers, Encadré B.10)
    # ─────────────────────────────────────────────
    entite = fields.Selection([
        ('01_gouvernance', '01_GOUVERNANCE'),
        ('02_administration', '02_ADMINISTRATION'),
        ('03_rh', '03_RH (restreint)'),
        ('04_finances', '04_FINANCES'),
        ('05_projets', '05_PROJETS (par projet)'),
        ('06_partenariats', '06_PARTENARIATS'),
        ('07_production_scient', '07_PRODUCTION_SCIENT.'),
    ], string='Entité / Dossier cible', required=True, tracking=True)
    code_projet = fields.Char(string='Projet / Activité (si dossier par projet)')
    nature_document = fields.Char(string='Nature du document')

    responsable_document_id = fields.Many2one(
        'hr.employee', string='Responsable du document (déclencheur)', required=True
    )

    # ─────────────────────────────────────────────
    # NOMENCLATURE DE NOMMAGE (RESADE-F-CA-02-03)
    # Convention : [CODE-ENTITÉ]-[NATURE]-[PROJET/ACTIVITÉ]-[AAAA-MM-JJ]-[VERSION]
    # ─────────────────────────────────────────────
    nom_fichier = fields.Char(
        string='Nom du fichier (convention de nommage)',
        help="Convention obligatoire : [CODE-ENTITÉ]-[NATURE]-[PROJET]-[AAAA-MM-JJ]-[VERSION]"
    )
    version = fields.Char(string='Version', default='V1')
    fichier = fields.Binary(string='Fichier (PDF/A ou Office)')
    fichier_filename = fields.Char()
    format_conforme = fields.Boolean(string='Format conforme (PDF/A ou Office)', default=True)

    # ─────────────────────────────────────────────
    # DÉLAIS (Manuel B.7 : déclenchement -> archivage <= 48h)
    # ─────────────────────────────────────────────
    date_validation_document = fields.Datetime(
        string='Date de validation/signature du document',
        help='Le délai de 48h court à partir de cette date.'
    )
    date_declenchement = fields.Datetime(
        string="Date de déclenchement de l'archivage", default=fields.Datetime.now
    )
    date_archivage_ged = fields.Datetime(string='Date de classement effectif dans la GED')
    delai_archivage_h = fields.Float(
        string="Délai d'archivage (h)", compute='_compute_delai', store=True
    )
    depassement_48h = fields.Boolean(
        string='Archivage > 48h (non conforme)', compute='_compute_delai', store=True
    )

    chemin_sharepoint = fields.Char(string='Chemin SharePoint / lien Drive')

    # ─────────────────────────────────────────────
    # DROITS D'ACCÈS (Matrice RESADE-F-CA-02-02 — vérifiée par le CSI)
    # ─────────────────────────────────────────────
    droits_verifies_csi = fields.Boolean(string='Droits d\'accès vérifiés (CSI)', default=False)
    csi_id = fields.Many2one('hr.employee', string='Vérifié par (CSI)')
    niveau_acces_de = fields.Selection([
        ('lecture', 'Lecture'), ('contribution', 'Contribution'),
        ('controle', 'Contrôle'), ('administration', 'Administration'), ('aucun', 'Sans accès'),
    ], string='Accès DE', default='administration')
    niveau_acces_caf = fields.Selection([
        ('lecture', 'Lecture'), ('contribution', 'Contribution'),
        ('controle', 'Contrôle'), ('administration', 'Administration'), ('aucun', 'Sans accès'),
    ], string='Accès CAF')
    niveau_acces_agents = fields.Selection([
        ('lecture', 'Lecture'), ('contribution', 'Contribution'),
        ('controle', 'Contrôle'), ('administration', 'Administration'), ('aucun', 'Sans accès'),
    ], string='Accès agents')

    confidentiel = fields.Boolean(string='Document confidentiel', default=False)

    # ─────────────────────────────────────────────
    # SAUVEGARDE (lien vers le processus, suivi global - pas par document)
    # ─────────────────────────────────────────────
    versionnage_active = fields.Boolean(string='Versionnage activé', default=True)

    state = fields.Selection([
        ('a_archiver', '📥 À archiver'),
        ('verification_qualite', '🔍 Vérification qualité fichier'),
        ('archive', '🗄️ Archivé en GED'),
        ('retourne', '↩️ Retourné (non conforme)'),
    ], string='État', default='a_archiver', tracking=True, copy=False)

    motif_retour = fields.Text(string='Motif de retour (si non conforme)')
    notes = fields.Text(string='Notes')

    @api.depends('date_validation_document', 'date_archivage_ged')
    def _compute_delai(self):
        for rec in self:
            rec.delai_archivage_h = 0.0
            rec.depassement_48h = False
            if rec.date_validation_document and rec.date_archivage_ged:
                delta = rec.date_archivage_ged - rec.date_validation_document
                heures = delta.total_seconds() / 3600.0
                rec.delai_archivage_h = heures
                rec.depassement_48h = heures > 48.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.ged.document') or _('Nouveau')
        return super().create(vals_list)

    def action_verifier_qualite(self):
        """Étape 2 : AA vérifie lisibilité, format, complétude (<=24h)."""
        for rec in self:
            if not rec.fichier:
                raise UserError(_("Veuillez joindre le fichier avant de procéder à la vérification qualité."))
            rec.state = 'verification_qualite'

    def action_retourner(self):
        for rec in self:
            if not rec.motif_retour:
                raise UserError(_("Merci d'indiquer le motif du retour au rédacteur."))
            rec.state = 'retourne'

    def action_archiver(self):
        """Étapes 3-4-5 : classement GED + vérification droits + enregistrement (<=48h)."""
        for rec in self:
            if not rec.nom_fichier:
                raise UserError(_(
                    "Le nom du fichier doit respecter la convention de nommage institutionnelle "
                    "avant archivage (Manuel P-CA-02, étape 3 — RESADE-F-CA-02-03)."
                ))
            if not rec.droits_verifies_csi:
                raise UserError(_(
                    "Les droits d'accès du dossier cible doivent être vérifiés par le CSI "
                    "avant la clôture de l'archivage (Manuel P-CA-02, étape 4)."
                ))
            rec.write({
                'state': 'archive',
                'date_archivage_ged': rec.date_archivage_ged or fields.Datetime.now(),
            })
            if rec.depassement_48h:
                rec.message_post(
                    body=_("⚠️ Archivage réalisé au-delà du délai cible de 48h (Manuel P-CA-02, KPI).")
                )


class ResadeGedAuditMensuel(models.Model):
    """Rapport mensuel d'audit GED — RESADE-F-CA-02-04."""
    _name = 'resade.ged.audit.mensuel'
    _description = 'Rapport mensuel d\'audit GED (P-CA-02)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'mois desc'

    mois = fields.Date(string='Mois concerné', required=True, default=fields.Date.context_today)
    realise_par_id = fields.Many2one('hr.employee', string='Réalisé par (CSI + CAF)')

    nb_documents_a_archiver = fields.Integer(string='Nb documents à archiver sur le mois')
    nb_documents_archives_48h = fields.Integer(string='Nb documents archivés dans les 48h')
    taux_conformite_delai = fields.Float(
        string='Taux de conformité au délai 48h (%)', compute='_compute_taux', store=True
    )

    nb_anomalies_classement = fields.Integer(string='Nb anomalies de classement détectées')
    nb_doublons = fields.Integer(string='Nb doublons détectés')
    sauvegarde_quotidienne_ok = fields.Boolean(string='Sauvegarde quotidienne conforme', default=True)
    test_restauration_effectue = fields.Boolean(string='Test de restauration mensuel effectué', default=False)

    observations = fields.Text(string='Observations / Actions correctives')

    @api.depends('nb_documents_a_archiver', 'nb_documents_archives_48h')
    def _compute_taux(self):
        for rec in self:
            if rec.nb_documents_a_archiver:
                rec.taux_conformite_delai = (
                    rec.nb_documents_archives_48h / rec.nb_documents_a_archiver * 100.0
                )
            else:
                rec.taux_conformite_delai = 0.0
