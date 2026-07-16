# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeEthiqueSoumission(models.Model):
    """
    Processus P-ER-01, P-ER-02, P-ER-03, P-ER-04 : Soumissions éthiques et réglementaires
    Manuel RESADE - Carnet J - Module 01 : Éthique de la recherche

    Modèle unifié couvrant les 4 types de soumission externe/interne requis avant
    et pendant la conduite d'une étude impliquant des participants humains ou une
    collecte de données :
      - CERS (P-ER-01) : Comité pour la recherche en santé
      - INSD (P-ER-02) : Visa statistique
      - Autorités sanitaires (P-ER-03) : ANRP / ministère de la Santé
      - Comité d'éthique institutionnel (P-ER-04)

    Circuit :
    1. Préparation du dossier (Chercheur responsable)      -> brouillon
    2. Soumission à l'organisme compétent                  -> soumis
    3. Instruction / échanges / amendements demandés       -> en_instruction
    4. Décision rendue par l'organisme                     -> decision_rendue
    5. Clôture (fin d'étude ou rapport annuel transmis)     -> clos
    """
    _name = 'resade.ethique.soumission'
    _description = "Soumission éthique/réglementaire (P-ER-01/02/03/04)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_soumission desc'

    name = fields.Char(string='Réf. dossier', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    type_soumission = fields.Selection([
        ('cers', "P-ER-01 : Comité pour la recherche en santé (CERS)"),
        ('insd', "P-ER-02 : Visa statistique (INSD)"),
        ('sanitaire', "P-ER-03 : Autorités sanitaires (ANRP / Ministère)"),
        ('interne', "P-ER-04 : Comité d'éthique institutionnel"),
    ], string='Type de soumission', required=True, tracking=True)

    titre_etude = fields.Char(string="Titre de l'étude / du protocole", required=True, tracking=True)
    chercheur_responsable_id = fields.Many2one(
        'hr.employee', string='Chercheur responsable', required=True, tracking=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        help="Dans RESADE, le déclarant qui prépare le dossier EST le chercheur responsable "
             "(rôle unique) — c'est pourquoi ce champ se pré-remplit avec l'employé lié à "
             "l'utilisateur connecté. La règle d'accès du groupe Déclarant n'autorise à voir/créer "
             "que les soumissions dont il est lui-même le chercheur responsable."
    )
    organisme = fields.Char(string='Organisme destinataire', help="Ex. CERS, INSD, ANRP, Comité interne RESADE")
    numero_reference_externe = fields.Char(string='Référence dossier chez l\'organisme')

    date_soumission = fields.Date(string='Date de soumission', tracking=True)
    date_decision = fields.Date(string='Date de décision', tracking=True)
    date_expiration = fields.Date(string="Date d'expiration / renouvellement requis")

    decision = fields.Selection([
        ('en_attente', 'En attente'),
        ('approuve', 'Approuvé'),
        ('approuve_conditions', 'Approuvé sous conditions'),
        ('amendement_demande', 'Amendement demandé'),
        ('rejete', 'Rejeté'),
    ], string='Décision', default='en_attente', tracking=True)

    observations = fields.Text(string='Observations / conditions de l\'organisme')
    rapport_annuel_transmis = fields.Boolean(string='Rapport annuel de suivi transmis')

    consentement_ids = fields.One2many('resade.ethique.consentement', 'soumission_id', string='Consentements liés')

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('soumis', 'Soumis'),
        ('en_instruction', 'En instruction'),
        ('decision_rendue', 'Décision rendue'),
        ('clos', 'Clos'),
    ], string='Statut', default='brouillon', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.soumission') or _('Nouveau')
        return super().create(vals_list)

    def action_soumettre(self):
        for rec in self:
            rec.write({'state': 'soumis', 'date_soumission': rec.date_soumission or fields.Date.context_today(rec)})

    def action_mettre_en_instruction(self):
        self._check_crsp_or_above()
        self.write({'state': 'en_instruction'})

    def action_enregistrer_decision(self):
        self._check_crsp_or_above()
        for rec in self:
            if not rec.decision or rec.decision == 'en_attente':
                raise UserError(_(
                    "Impossible d'enregistrer la décision : le champ « Décision » doit indiquer "
                    "le résultat réel communiqué par l'organisme (%s) — « En attente » ne suffit pas."
                ) % (rec.organisme or 'CERS/INSD/ANRP/Comité interne'))
            rec.write({
                'state': 'decision_rendue',
                'date_decision': rec.date_decision or fields.Date.context_today(rec),
            })

    def action_cloturer(self):
        self._check_crsp_or_above()
        self.write({'state': 'clos'})

    def action_reouvrir(self):
        self._check_crsp_or_above()
        self.write({'state': 'brouillon'})

    def _check_crsp_or_above(self):
        if not self.env.user.has_group('resade_ethique.group_resade_ethique_crsp'):
            raise UserError(_(
                "Seul le Chargé Éthique & Conformité (CRSP), le Directeur Exécutif ou l'Administrateur "
                "peuvent faire avancer une soumission au-delà de sa transmission initiale. Le chercheur "
                "responsable ne peut que préparer et soumettre son dossier (bouton « Soumettre »)."
            ))
