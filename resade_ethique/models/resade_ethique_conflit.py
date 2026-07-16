# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeEthiqueConflit(models.Model):
    """
    Processus P-DC-02 : Gestion des conflits d'intérêts
    Manuel RESADE - Carnet J - Module 02 : Déontologie et conformité

    Couvre la déclaration, l'analyse et la gestion des situations de conflit
    d'intérêts réel, potentiel ou apparent, pour toute décision institutionnelle
    sensible (marchés, recrutement, avis scientifiques, partenariats, publications).

    Ce modèle est le registre institutionnel général des conflits d'intérêts.
    Le module resade_marche conserve son propre traitement opérationnel des
    conflits liés spécifiquement à un dossier de marché (P-DA-01) ; les deux
    peuvent coexister, ce modèle-ci couvrant l'ensemble des contextes (recherche,
    RH, partenariats, publications) et pas seulement les marchés.

    Circuit :
    1. Déclaration par la personne concernée         -> declaree
    2. Analyse par le Chargé Éthique/Conformité       -> en_analyse
    3. Décision (récusation, mitigation, refus...)    -> decision_rendue
    4. Clôture / suivi des mesures                    -> cloturee
    """
    _name = 'resade.ethique.conflit'
    _description = "Déclaration de conflit d'intérêts (P-DC-02)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_declaration desc'

    name = fields.Char(string='Réf. déclaration', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    declarant_id = fields.Many2one('hr.employee', string='Déclarant', required=True, tracking=True,
                                    default=lambda self: self.env['hr.employee'].search(
                                        [('user_id', '=', self.env.uid)], limit=1))
    date_declaration = fields.Date(string='Date de déclaration', default=fields.Date.context_today, required=True)

    contexte = fields.Selection([
        ('marche', 'Sélection de prestataires / attribution de marché'),
        ('recrutement', 'Recrutement'),
        ('avis_scientifique', 'Avis scientifique / évaluation par les pairs'),
        ('partenariat', 'Partenariat'),
        ('publication', 'Publication / soumission de projet'),
        ('autre', 'Autre'),
    ], string="Contexte de la situation", required=True, tracking=True)

    type_conflit = fields.Selection([
        ('reel', 'Réel'),
        ('potentiel', 'Potentiel'),
        ('apparent', 'Apparent'),
    ], string='Type de conflit', tracking=True)

    description_situation = fields.Text(string='Description de la situation', required=True)
    reference_dossier_lie = fields.Char(string='Référence du dossier concerné (marché, recrutement, projet...)')

    analyste_id = fields.Many2one('hr.employee', string='Analysé par (Chargé Éthique/Conformité)')
    date_analyse = fields.Date(string="Date d'analyse")

    decision = fields.Selection([
        ('aucune_action', 'Aucune action requise'),
        ('recusation', 'Récusation de la personne concernée'),
        ('mesure_mitigation', 'Mesure de mitigation'),
        ('refus', 'Refus de la situation / interdiction de participer'),
    ], string='Décision', tracking=True)
    mesures_prises = fields.Text(string='Mesures prises / suivi')

    valideur_id = fields.Many2one('hr.employee', string='Validé par (DE)')
    date_decision = fields.Date(string='Date de décision')

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('declaree', 'Déclarée'),
        ('en_analyse', 'En analyse'),
        ('decision_rendue', 'Décision rendue'),
        ('cloturee', 'Clôturée'),
    ], string='Statut', default='brouillon', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.conflit') or _('Nouveau')
        return super().create(vals_list)

    def action_declarer(self):
        self.write({'state': 'declaree'})

    def action_mettre_en_analyse(self):
        if not self.env.user.has_group('resade_ethique.group_resade_ethique_crsp'):
            raise UserError(_(
                "Seul le Chargé Éthique & Conformité (CRSP) peut instruire une déclaration de "
                "conflit d'intérêts. Le déclarant ne peut pas analyser sa propre déclaration "
                "(séparation des rôles, Carnet J - P-DC-02)."
            ))
        for rec in self:
            if rec.declarant_id.user_id.id == self.env.uid and not self.env.user.has_group(
                    'resade_ethique.group_resade_ethique_admin'):
                raise UserError(_(
                    "Vous êtes le déclarant de ce dossier : vous ne pouvez pas l'analyser vous-même, "
                    "même en tant que Chargé Éthique & Conformité. Faites traiter ce dossier par un "
                    "autre membre habilité (ou par le DE)."
                ))
        self.write({'state': 'en_analyse', 'date_analyse': fields.Date.context_today(self)})
        for rec in self:
            if not rec.analyste_id:
                employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
                if employee:
                    rec.analyste_id = employee.id

    def action_enregistrer_decision(self):
        if not self.env.user.has_group('resade_ethique.group_resade_ethique_de'):
            raise UserError(_(
                "Seul le Directeur Exécutif (ou l'Administrateur) peut enregistrer la décision "
                "d'un conflit d'intérêts (Carnet J - P-DC-02, rôle « Validé par DE »)."
            ))
        for rec in self:
            if not rec.decision:
                raise UserError(_(
                    "Sélectionnez une décision (aucune action requise, récusation, mesure de "
                    "mitigation ou refus) avant de l'enregistrer."
                ))
            if rec.declarant_id.user_id.id == self.env.uid and not self.env.user.has_group(
                    'resade_ethique.group_resade_ethique_admin'):
                raise UserError(_(
                    "Vous êtes le déclarant de ce dossier : vous ne pouvez pas décider vous-même de "
                    "son issue."
                ))
        self.write({'state': 'decision_rendue', 'date_decision': fields.Date.context_today(self)})
        for rec in self:
            if not rec.valideur_id:
                employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
                if employee:
                    rec.valideur_id = employee.id

    def action_cloturer(self):
        if not self.env.user.has_group('resade_ethique.group_resade_ethique_crsp'):
            raise UserError(_(
                "Seul le Chargé Éthique & Conformité (CRSP), le Directeur Exécutif ou "
                "l'Administrateur peuvent clôturer un dossier de conflit d'intérêts."
            ))
        self.write({'state': 'cloturee'})
