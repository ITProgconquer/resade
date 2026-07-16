# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeEthiqueTraitement(models.Model):
    """
    Processus P-DC-03 : Protection des données personnelles
    Manuel RESADE - Carnet J - Module 02 : Déontologie et conformité

    Registre des traitements de données à caractère personnel, conforme à la loi
    n°010-2004/AN relative à la protection des données au Burkina Faso. Couvre
    tous les fichiers de RESADE (recherche, RH, comptabilité, bénéficiaires).

    Complète P-PR-03 (gestion des données de recherche, module production
    scientifique) et P-ER-05 (consentement éclairé) sur le volet spécifiquement
    légal de la protection des données.
    """
    _name = 'resade.ethique.traitement'
    _description = "Registre des traitements de données personnelles (P-DC-03)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Réf. traitement', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    intitule_traitement = fields.Char(string='Intitulé du traitement', required=True, tracking=True)
    finalite = fields.Text(string='Finalité du traitement', required=True)
    base_legale = fields.Char(string='Base légale (consentement, obligation légale, intérêt légitime...)')

    categorie_donnees = fields.Selection([
        ('rh', 'Données RH'),
        ('recherche', 'Données de recherche'),
        ('comptabilite', 'Données comptables/financières'),
        ('beneficiaires', 'Données des bénéficiaires'),
        ('autre', 'Autre'),
    ], string='Catégorie de données', required=True, tracking=True)

    donnees_sensibles = fields.Boolean(string='Inclut des données sensibles (santé, biométrie...)')

    responsable_traitement_id = fields.Many2one('hr.employee', string='Responsable du traitement')
    correspondant_donnees_id = fields.Many2one('hr.employee', string='Correspondant à la protection des données')

    duree_conservation = fields.Char(string='Durée de conservation')
    mesures_securite = fields.Text(string='Mesures de sécurité mises en œuvre')

    declare_cil = fields.Boolean(string='Déclaré à la CIL Burkina Faso')
    date_declaration_cil = fields.Date(string='Date de déclaration CIL')

    date_derniere_revue = fields.Date(string='Date de dernière revue')
    date_prochaine_revue = fields.Date(string='Date de prochaine revue')

    incident_ids_count = fields.Integer(string='Nombre de violations de données signalées', default=0)

    state = fields.Selection([
        ('actif', 'Actif'),
        ('en_revue', 'En revue'),
        ('archive', 'Archivé'),
    ], string='Statut', default='actif', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.traitement') or _('Nouveau')
        return super().create(vals_list)

    def action_mettre_en_revue(self):
        self.write({'state': 'en_revue', 'date_derniere_revue': fields.Date.context_today(self)})

    def action_reactiver(self):
        self.write({'state': 'actif'})

    def action_archiver(self):
        self.write({'state': 'archive'})
