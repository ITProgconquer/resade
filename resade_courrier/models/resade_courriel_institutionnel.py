# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeCourrielInstitutionnel(models.Model):
    """
    Processus P-GC-03 : Gestion des courriels institutionnels
    Manuel RESADE - Carnet G - Module 01

    Registre de suivi (RESADE-F-GC-03-02) des courriels @resade à valeur
    institutionnelle (tri A/I/T/E, délais de réponse normalisés, classification VPIA).

    Délais normalisés (Manuel B.3 / B.7) :
      - Urgent (bailleurs / partenaires stratégiques) : réponse <= 24h
      - Standard                                       : réponse <= 48h
      - Complexe (instruction interne)                 : AR <= 24h puis réponse <= 72h
    """
    _name = 'resade.courriel.institutionnel'
    _description = 'Courriel Institutionnel RESADE (P-GC-03)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_courriel desc'

    sens = fields.Selection([
        ('emis', 'Émis'),
        ('recu', 'Reçu'),
    ], string='Sens', required=True, default='recu', tracking=True)

    agent_id = fields.Many2one(
        'hr.employee', string='Agent (titulaire boîte @resade)', required=True,
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
    )
    boite_resade = fields.Char(string='Adresse @resade concernée')

    objet = fields.Char(string='Objet du courriel', required=True, tracking=True)
    expediteur = fields.Char(string='Expéditeur')
    destinataire = fields.Char(string='Destinataire(s) (A)')
    copie = fields.Char(string='En copie (Cc)')

    tiers_id = fields.Many2one('resade.courrier.tiers', string='Structure liée (partenaire/bailleur)')
    date_courriel = fields.Datetime(
        string='Date du courriel', required=True, default=fields.Datetime.now
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 2 : TRI A / I / T / E (Manuel B.7, étape 2)
    # ─────────────────────────────────────────────
    categorie_tri = fields.Selection([
        ('a', 'A — Action requise'),
        ('i', 'I — Information / archivage'),
        ('t', 'T — Transmission à un autre service'),
        ('e', 'E — À éliminer après traitement'),
    ], string='Catégorie de tri', tracking=True)

    service_transmission_id = fields.Many2one(
        'resade.courrier.service', string='Transmis au service (si T)'
    )
    agent_transmission_id = fields.Many2one(
        'hr.employee', string='Transmis à (si T)'
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 3 : DÉLAIS / ACCUSÉ DE RÉCEPTION
    # ─────────────────────────────────────────────
    niveau_urgence = fields.Selection([
        ('urgent', 'Urgent (bailleur / partenaire stratégique) — 24h'),
        ('standard', 'Standard — 48h'),
        ('complexe', 'Complexe (instruction interne) — AR 24h puis 72h'),
    ], string="Niveau d'urgence", default='standard', tracking=True)

    accuse_reception_envoye = fields.Boolean(string='Accusé de réception envoyé', default=False)
    date_accuse_reception = fields.Datetime(string='Date AR')

    date_reponse = fields.Datetime(string='Date de réponse complète')
    delai_reponse_h = fields.Float(
        string='Délai de réponse (h)', compute='_compute_delai_reponse', store=True
    )
    delai_depasse = fields.Boolean(
        string='Délai de réponse dépassé', compute='_compute_delai_reponse', store=True
    )

    # ─────────────────────────────────────────────
    # ÉTAPE 5 : CLASSIFICATION VPIA (Manuel B.7, étape 5)
    # ─────────────────────────────────────────────
    classification_vpia = fields.Selection([
        ('probante', 'Valeur Probante (engagement, décision, accord)'),
        ('institutionnelle', 'Valeur Institutionnelle (partenariat, rapport)'),
        ('administrative', 'Valeur Administrative (RH, note interne)'),
        ('non_archivable', 'Non archivable (publicitaire, notification auto, informel)'),
    ], string='Classification VPIA', tracking=True)

    # ─────────────────────────────────────────────
    # ÉTAPE 6 : ARCHIVAGE GED (<= 48h)
    # ─────────────────────────────────────────────
    document_archive = fields.Many2many(
        'ir.attachment', 'courriel_institutionnel_pj_rel',
        string='Fichier archivé (PDF / .eml)'
    )
    archive_ged = fields.Boolean(string='Archivé en GED', default=False, tracking=True)
    date_archivage_ged = fields.Datetime(string='Date archivage GED')
    reference_ged = fields.Char(string='Référence / lien GED')

    statut_traitement = fields.Selection([
        ('en_cours', 'En cours'),
        ('traite', 'Traité'),
        ('archive', 'Archivé'),
    ], string='Statut', default='en_cours', tracking=True)

    note = fields.Text(string='Note')

    @api.depends('date_courriel', 'date_reponse', 'niveau_urgence')
    def _compute_delai_reponse(self):
        for rec in self:
            rec.delai_reponse_h = 0.0
            rec.delai_depasse = False
            if rec.date_courriel and rec.date_reponse:
                delta = rec.date_reponse - rec.date_courriel
                heures = delta.total_seconds() / 3600.0
                rec.delai_reponse_h = heures
                seuils = {'urgent': 24.0, 'standard': 48.0, 'complexe': 72.0}
                rec.delai_depasse = heures > seuils.get(rec.niveau_urgence, 48.0)

    def action_envoyer_ar(self):
        for rec in self:
            rec.write({
                'accuse_reception_envoye': True,
                'date_accuse_reception': fields.Datetime.now(),
            })

    def action_marquer_traite(self):
        for rec in self:
            rec.write({
                'statut_traitement': 'traite',
                'date_reponse': rec.date_reponse or fields.Datetime.now(),
            })

    def action_archiver(self):
        for rec in self:
            rec.write({
                'archive_ged': True,
                'statut_traitement': 'archive',
                'date_archivage_ged': rec.date_archivage_ged or fields.Datetime.now(),
            })


class ResadeRapportBoiteMail(models.Model):
    """Rapport mensuel de gestion des boîtes @resade — RESADE-F-GC-03-03."""
    _name = 'resade.rapport.boite.mail'
    _description = 'Rapport mensuel de gestion des boîtes @resade (P-GC-03)'
    _order = 'mois desc'

    mois = fields.Date(string='Mois concerné', required=True, default=fields.Date.context_today)
    agent_id = fields.Many2one('hr.employee', string='Agent / boîte @resade', required=True)
    quota_pct = fields.Float(string="Taux d'occupation de la boîte (%)")
    quota_alerte = fields.Boolean(string='Alerte > 80%', compute='_compute_alerte', store=True)
    nb_courriels_archives = fields.Integer(string='Nb courriels archivés en GED')
    nb_courriels_elimines = fields.Integer(string='Nb courriels éliminés (nettoyage)')
    conforme = fields.Boolean(string='Boîte conforme', default=True)
    observations = fields.Text(string='Observations')

    @api.depends('quota_pct')
    def _compute_alerte(self):
        for rec in self:
            rec.quota_alerte = (rec.quota_pct or 0.0) > 80.0
