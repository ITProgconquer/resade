# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeCourrierEntrant(models.Model):
    """
    Processus P-GC-01 : Gestion du courrier entrant (physique et électronique)
    Manuel RESADE - Carnet G - Module 01

    Circuit (Manuel B.7 / B.8) :
    1. Réception (AA)                         -> recu
    2. Enregistrement + cachet (AA)            -> enregistre
    3. Numérisation / archivage GED (AA, <=2h)
    4. Transmission au DE avec Fiche d'Affectation (AA)  -> transmis_de
    5. Annotation et instructions de dispatch (DE)        -> affecte
    6. Dispatch + émargement destinataires (AA)           -> dispatche
    7. Classement + archivage GED (<=48h) (AA)            -> archive
    """
    _name = 'resade.courrier.entrant'
    _description = 'Courrier Entrant RESADE (P-GC-01)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'numero'
    _order = 'date_reception desc, numero desc'

    # ─────────────────────────────────────────────
    # IDENTIFICATION (RESADE-F-GC-01-01 / 01-01-NUM)
    # ─────────────────────────────────────────────
    numero = fields.Char(
        string="N° d'arrivée", required=True, readonly=True,
        copy=False, default=lambda self: _('Nouveau'), tracking=True
    )
    type_courrier = fields.Selection([
        ('physique', 'Physique'),
        ('electronique', 'Électronique (courriel)'),
    ], string='Type', required=True, default='physique', tracking=True)

    objet_id = fields.Many2one('resade.courrier.objet', string='Objet / Catégorie')
    objet_libre = fields.Char(string='Objet du courrier', required=True, tracking=True)
    confidentiel = fields.Boolean(string='Confidentiel', default=False, tracking=True)

    # Émetteur (tiers externe)
    tiers_emetteur_id = fields.Many2one('resade.courrier.tiers', string='Structure émettrice')
    contact_emetteur_id = fields.Many2one('resade.courrier.contact', string='Contact émetteur')
    nom_emetteur_libre = fields.Char(string="Expéditeur (si non répertorié)")

    date_emission = fields.Date(string="Date d'émission (courrier)")
    date_reception = fields.Date(
        string='Date de réception', required=True, default=fields.Date.context_today, tracking=True
    )

    # ─────────────────────────────────────────────
    # ÉTAPES 1-2 : RÉCEPTION ET ENREGISTREMENT (AA)
    # ─────────────────────────────────────────────
    receptionne_par_id = fields.Many2one(
        'res.users', string='Réceptionné par (AA)', readonly=True,
        default=lambda self: self.env.user
    )
    porteur_decharge = fields.Boolean(string='Porteur déchargé / AR envoyé', default=False)
    cachet_appose = fields.Boolean(string="Cachet « COURRIER ARRIVÉE » apposé", default=False)

    # ─────────────────────────────────────────────
    # ÉTAPE 3 : NUMÉRISATION / GED (<= 2h)
    # ─────────────────────────────────────────────
    document_numerise = fields.Many2many(
        'ir.attachment', 'courrier_entrant_pj_rel', string='Document numérisé (PDF / pièce jointe)'
    )
    date_numerisation = fields.Datetime(string='Date de numérisation')

    # ─────────────────────────────────────────────
    # ÉTAPE 4 : FICHE D'AFFECTATION -> TRANSMISSION AU DE (RESADE-F-GC-01-02)
    # ─────────────────────────────────────────────
    date_transmission_de = fields.Datetime(string='Date transmission au DE')
    urgent = fields.Boolean(string='Urgent (à lire en priorité)', default=False)

    # ─────────────────────────────────────────────
    # ÉTAPE 5 : ANNOTATION / INSTRUCTIONS DE DISPATCH (DE)
    # ─────────────────────────────────────────────
    de_id = fields.Many2one('hr.employee', string='Directeur Exécutif')
    annotation_de = fields.Text(string='Annotation / Instructions du DE')
    date_instruction_de = fields.Datetime(string='Date instruction DE', readonly=True)
    instruction_de_par = fields.Many2one('res.users', string='Instruction donnée par', readonly=True)

    # Destinataire(s) désignés par le DE
    service_destinataire_id = fields.Many2one('resade.courrier.service', string='Service destinataire')
    destinataire_ids = fields.Many2many(
        'hr.employee', 'courrier_entrant_destinataire_rel', string='Destinataire(s) désigné(s)'
    )
    delai_traitement = fields.Date(string='Délai de traitement souhaité')

    # ─────────────────────────────────────────────
    # ÉTAPE 6 : DISPATCH ET ÉMARGEMENT (RESADE-F-GC-01-03)
    # ─────────────────────────────────────────────
    emargement_ids = fields.One2many(
        'resade.courrier.emargement', 'courrier_entrant_id', string='Émargements (Cahier de transmission)'
    )
    transmission_financiere_caf = fields.Boolean(
        string='Transmis en priorité au CAF (courrier à incidence financière)', default=False
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 7 : CLASSEMENT ET ARCHIVAGE (<= 48h) (RESADE-F-GC-01-01-NUM)
    # ─────────────────────────────────────────────
    archive_chrono_physique = fields.Boolean(string='Classé au Chrono physique', default=False)
    archive_ged = fields.Boolean(string='Archivé en GED (SharePoint/Drive)', default=False, tracking=True)
    date_archivage_ged = fields.Datetime(string='Date archivage GED')
    reference_ged = fields.Char(string='Référence / lien GED')

    # ─────────────────────────────────────────────
    # ÉTAT DU PROCESSUS
    # ─────────────────────────────────────────────
    state = fields.Selection([
        ('recu', '📥 Reçu'),
        ('enregistre', '🔢 Enregistré / numérisé'),
        ('transmis_de', '📋 Transmis au DE'),
        ('affecte', '✅ Affecté (instructions DE)'),
        ('dispatche', '📤 Dispatché aux destinataires'),
        ('archive', '🗄️ Archivé (clôturé)'),
    ], string='État', default='recu', tracking=True, copy=False)

    # ─────────────────────────────────────────────
    # KPI / DÉLAIS CALCULÉS (B.12 du Manuel)
    # ─────────────────────────────────────────────
    delai_transmission_de_h = fields.Float(
        string='Délai transmission DE (h)', compute='_compute_delais', store=True
    )
    delai_archivage_ged_h = fields.Float(
        string='Délai archivage GED (h)', compute='_compute_delais', store=True
    )
    depassement_archivage = fields.Boolean(
        string='Archivage > 48h (alerte)', compute='_compute_delais', store=True
    )

    note_interne = fields.Text(string='Note interne')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('numero', _('Nouveau')) == _('Nouveau'):
                vals['numero'] = self.env['ir.sequence'].next_by_code(
                    'resade.courrier.entrant'
                ) or _('Nouveau')
        return super().create(vals_list)

    @api.depends('date_reception', 'date_transmission_de', 'date_archivage_ged')
    def _compute_delais(self):
        for rec in self:
            rec.delai_transmission_de_h = 0.0
            rec.delai_archivage_ged_h = 0.0
            rec.depassement_archivage = False
            if rec.date_reception and rec.date_transmission_de:
                delta = rec.date_transmission_de - fields.Datetime.from_string(
                    str(rec.date_reception) + ' 00:00:00'
                )
                rec.delai_transmission_de_h = delta.total_seconds() / 3600.0
            if rec.date_reception and rec.date_archivage_ged:
                delta2 = rec.date_archivage_ged - fields.Datetime.from_string(
                    str(rec.date_reception) + ' 00:00:00'
                )
                heures = delta2.total_seconds() / 3600.0
                rec.delai_archivage_ged_h = heures
                rec.depassement_archivage = heures > 48.0

    # ─────────────────────────────────────────────
    # ACTIONS DU WORKFLOW (étapes B.7 / B.8 du Manuel)
    # ─────────────────────────────────────────────
    def action_enregistrer(self):
        """Étape 2-3 : enregistrement + numérisation (<= 2h)."""
        for rec in self:
            if not rec.cachet_appose and rec.type_courrier == 'physique':
                raise UserError(_(
                    "Veuillez confirmer l'apposition du cachet « COURRIER ARRIVÉE » "
                    "avant d'enregistrer ce courrier (Manuel P-GC-01, étape 2)."
                ))
            rec.write({
                'state': 'enregistre',
                'date_numerisation': fields.Datetime.now(),
            })

    def action_transmettre_de(self):
        """Étape 4 : transmission au DE avec Fiche d'Affectation (J0 / J+1 matin)."""
        for rec in self:
            if not rec.document_numerise and rec.type_courrier == 'physique':
                raise UserError(_(
                    "Le document numérisé doit être joint avant transmission au DE "
                    "(Manuel P-GC-01, étape 3)."
                ))
            rec.write({
                'state': 'transmis_de',
                'date_transmission_de': fields.Datetime.now(),
            })

    def action_affecter(self):
        """Étape 5 : DE annote et instruit le dispatch (sous 24h)."""
        for rec in self:
            if not rec.service_destinataire_id and not rec.destinataire_ids:
                raise UserError(_(
                    "Veuillez désigner au moins un service ou destinataire avant l'affectation "
                    "(Manuel P-GC-01, étape 5)."
                ))
            rec.write({
                'state': 'affecte',
                'date_instruction_de': fields.Datetime.now(),
                'instruction_de_par': self.env.user.id,
            })

    def action_dispatcher(self):
        """Étape 6 : dispatch aux destinataires + ouverture de l'émargement."""
        for rec in self:
            rec.write({'state': 'dispatche'})

    def action_archiver(self):
        """Étape 7 : classement physique + archivage GED (<= 48h après réception)."""
        for rec in self:
            if not rec.archive_ged:
                raise UserError(_(
                    "Veuillez confirmer l'archivage GED avant de clôturer ce courrier "
                    "(Manuel P-GC-01, étape 7)."
                ))
            rec.write({
                'state': 'archive',
                'date_archivage_ged': rec.date_archivage_ged or fields.Datetime.now(),
            })


class ResadeCourrierEmargement(models.Model):
    """Cahier de transmission interne – RESADE-F-GC-01-03."""
    _name = 'resade.courrier.emargement'
    _description = 'Émargement – Cahier de transmission interne'

    courrier_entrant_id = fields.Many2one(
        'resade.courrier.entrant', string='Courrier entrant', ondelete='cascade'
    )
    destinataire_id = fields.Many2one('hr.employee', string='Destinataire', required=True)
    date_remise = fields.Datetime(string='Date de remise', default=fields.Datetime.now)
    emarge = fields.Boolean(string='Émargé', default=False)
    date_emargement = fields.Datetime(string="Date d'émargement")
