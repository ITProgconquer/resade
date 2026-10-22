# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProtocoleRecherche(models.Model):
    """
    Processus P-CI-01 : Conception et validation d'un protocole de recherche
    Carnet I — Module 01 : Processus de Recherche — RESADE
    """
    _name = 'resade.protocole.recherche'
    _description = 'Protocole de Recherche (P-CI-01)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc'
    _rec_name = 'reference'

    # ─── Identification ───────────────────────────────────────────────────────
    reference = fields.Char(
        string='Code Protocole',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    titre = fields.Char(
        string='Titre du protocole',
        required=True,
        tracking=True,
    )
    acronyme = fields.Char(string='Acronyme / Code court')
    projet_id = fields.Many2one(
        'resade.projet',
        string='Projet rattaché',
        tracking=True,
    )

    # ─── Responsables (RACI) ─────────────────────────────────────────────────
    investigateur_principal_id = fields.Many2one(
        'hr.employee',
        string='Investigateur Principal (PI)',
        required=True,
        tracking=True,
    )
    equipe_ids = fields.Many2many(
        'hr.employee',
        'protocole_equipe_rel',
        'protocole_id', 'employee_id',
        string='Équipe de recherche',
    )
    responsable_validation_id = fields.Many2one(
        'hr.employee',
        string='Responsable validation (DE)',
        tracking=True,
    )

    # ─── Contexte scientifique ────────────────────────────────────────────────
    domaine_recherche_ids = fields.Many2many(
        'resade.domaine.recherche',
        'protocole_domaine_rel', 'protocole_id', 'domaine_id',
        string='Domaines de recherche',
        required=True
    )
    
    objectif_general = fields.Html(string='Objectif', help='Objectif du protocole de recherche', required=True)
    hypotheses = fields.Html(string='Hypothèses de recherche')
    # methodologie = fields.Html(string='Méthodologie')
    type_etude = fields.Html(string='Type d\'étude')
    cadre_etude = fields.Html(string='Cadre de l\'étude & période')
    echantillonnage = fields.Html(string='Échantillonnage')
    population_cible = fields.Html(string="Population cible")
    duree_mois = fields.Integer(string='Durée prévisionnelle (mois)')
    zone_etude = fields.Html(string='Zone d’étude')
    outils_collecte = fields.Html(string='Outils de collecte de données')
    analyse_donnees = fields.Html(string='Analyse des données')

    # ─── Dates ────────────────────────────────────────────────────────────────
    date_creation = fields.Date(
        string='Date de création',
        default=fields.Date.today,
        required=True,
    )
    date_soumission_ethique = fields.Date(string='Date soumission CERS')
    date_avis_ethique = fields.Date(string='Date avis CERS reçu')
    date_visa_statistique = fields.Date(string='Date visa statistique (INSD)')
    date_validation_interne = fields.Date(string='Date validation interne (DE)')
    date_demarrage_prevu = fields.Date(string='Date de démarrage prévue')

    date_soumission_visa_statistique = fields.Date(string='Date soumission visa statistique')
    date_avis_visa_statistique = fields.Date(string='Date avis visa statistique reçu')
    commentaire_visa_statistique = fields.Html(string='Commentaire visa statistique', help='Commentaires ou réserves du visa statistique INSD')

    date_soumission_ministere = fields.Date(string='Date soumission Ministère')
    date_avis_ministere = fields.Date(string='Date avis Ministère reçu')
    commentaire_ministere = fields.Html(string='Commentaire Ministère', help='Commentaires ou réserves du Ministère de la Santé')

    # ─── Statut / Workflow ───────────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('revue_interne', 'En revue interne'),
        ('soumission_ethique', 'Soumis au CERS'),
        ('avis_ethique_recu', 'Avis CERS reçu'),
        ('visa_statistique', 'Visa statistique en cours'),
        ('soumission_visa', 'Soumis au Visa Statistique'),
        ('visa_statistique_recu', 'Visa Statistique reçu'),
        ('soumission_ministere', 'Soumis au Ministère'),
        ('autorisation_ministere_recue', 'Autorisation Ministère reçue'),
        ('valide', 'Validé — Approuvé'),
        ('rejete', 'Rejeté'),
        ('archive', 'Archivé'),
    ], string='Statut', default='brouillon', tracking=True, required=True)

    # ─── Éthique & Conformité ────────────────────────────────────────────────
    necessite_ethique = fields.Boolean(
        string='Nécessite avis CERS ?',
        default=True,
    )
    necessite_visa_stat = fields.Boolean(
        string='Nécessite visa statistique INSD ?',
        default=True,
    )
    necessite_autorisation_msante = fields.Boolean(
        string='Nécessite autorisation Ministère de la Santé ?',
        default=False,
    )
    avis_ethique = fields.Selection([
        ('en_attente', 'En attente'),
        ('favorable', 'Avis favorable'),
        ('favorable_reserve', 'Favorable avec réserves'),
        ('defavorable', 'Défavorable'),
    ], string='Avis CERS', default='en_attente')
    numero_autorisation_cers = fields.Char(string='N° autorisation CERS')
    commentaires_ethique = fields.Text(string='Commentaires / Réserves CERS')

    # ─── Formulaires RESADE (AECD) ────────────────────────────────────────────
    formulaire_protocole = fields.Many2many(
        'ir.attachment',
        'protocole_formulaire_rel',  # Nom de la table de liaison
        'protocole_id',              # Colonne pour le protocole
        'attachment_id',             # Colonne pour l'attachment
        string='Protocole (PDF/Word)'
    )
    formulaire_consentement = fields.Many2many(
        'ir.attachment',
        'protocole_consentement_rel',  # Nom de la table de liaison
        'protocole_id',                # Colonne pour le protocole
        'attachment_id',               # Colonne pour l'attachment
        string='Formulaire de consentement éclairé'
    )
    # ─── Notes ────────────────────────────────────────────────────────────────
    notes_internes = fields.Text(string='Notes internes')

    # ─── Compteurs ────────────────────────────────────────────────────────────
    etude_count = fields.Integer(
        string='Études liées',
        compute='_compute_etude_count',
    )

    # ─── Séquence automatique ────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.protocole.recherche') or _('Nouveau')
        return super().create(vals_list)

    def _compute_etude_count(self):
        for rec in self:
            rec.etude_count = self.env['resade.etude.enquete'].search_count(
                [('protocole_id', '=', rec.id)])

    # ─── Boutons de workflow ──────────────────────────────────────────────────
    def action_soumettre_revue(self):
        self.ensure_one()
        if not self.objectif_general:
            raise UserError(_("Veuillez renseigner l'objectif général avant la soumission."))
        self.state = 'revue_interne'

    def action_soumettre_ethique(self):
        self.ensure_one()
        self.write({'state': 'soumission_ethique', 'date_soumission_ethique': fields.Date.today()})

    def action_avis_favorable(self):
        self.ensure_one()
        self.write({'state': 'avis_ethique_recu', 'avis_ethique': 'favorable',
                    'date_avis_ethique': fields.Date.today()})


    def action_visa_statistique(self):
        for rec in self:
            rec.write({'state': 'visa_statistique'})

    def action_soumettre_visa(self):
        self.write({'state': 'soumission_visa', 'date_soumission_visa_statistique': fields.Date.today()})

    def action_avis_visa_recu(self):
        self.write({'state': 'visa_statistique_recu', 'date_avis_visa_statistique': fields.Date.today()})

    def action_soumettre_ministere(self):
        self.write({'state': 'soumission_ministere', 'date_soumission_ministere': fields.Date.today()})

    def action_avis_ministere_recu(self):
        self.write({'state': 'autorisation_ministere_recue', 'date_avis_ministere': fields.Date.today()})



    def action_valider(self):
        self.ensure_one()
        
        # 1. Vérification CERS
        if self.necessite_ethique and not self.date_avis_ethique:
            raise UserError(_("Ce protocole nécessite un avis CERS. "
                        "Impossible de valider tant que l'avis du Comité d'Éthique "
                        "pour la Recherche en Santé n'a pas été enregistré (Carnet I, P-CI-01)."))
            
        # 2. Vérification INSD
        if self.necessite_visa_stat and not self.date_avis_visa_statistique:
            raise UserError(_("Ce protocole nécessite un visa statistique INSD."))

        # 3. Vérification Ministère
        if self.necessite_autorisation_msante and not self.date_avis_ministere:
            raise UserError(_("Ce protocole nécessite une autorisation du Ministère."))

        self.write({
            'state': 'valide',
            'date_validation_interne': fields.Date.today()
    })

    def action_rejeter(self):
        self.ensure_one()
        self.state = 'rejete'

    def action_archiver(self):
        self.ensure_one()
        self.state = 'archive'

    def action_voir_etudes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Études — %s') % self.titre,
            'res_model': 'resade.etude.enquete',
            'view_mode': 'list,form',
            'domain': [('protocole_id', '=', self.id)],
            'context': {'default_protocole_id': self.id},
        }
