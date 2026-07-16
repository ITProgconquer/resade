# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeEthiqueConsentement(models.Model):
    """
    Processus P-ER-05 : Consentement éclairé des participants
    Manuel RESADE - Carnet J - Module 01 : Éthique de la recherche

    Suit, pour chaque étude, la conception des formulaires de consentement,
    leur validation par le CERS (dans le cadre de P-ER-01), leur usage sur le
    terrain et l'archivage sécurisé des consentements signés.

    Circuit :
    1. Conception du formulaire                    -> brouillon
    2. Validation par le CERS (via P-ER-01)         -> valide_cers
    3. Utilisation sur le terrain                   -> en_utilisation
    4. Fin de collecte / archivage définitif        -> cloture
    """
    _name = 'resade.ethique.consentement'
    _description = "Formulaire de consentement éclairé (P-ER-05)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Réf. formulaire', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    soumission_id = fields.Many2one('resade.ethique.soumission', string='Dossier CERS lié (P-ER-01)',
                                     domain="[('type_soumission', '=', 'cers')]")
    titre_etude = fields.Char(string="Titre de l'étude", required=True)

    type_participant = fields.Selection([
        ('adulte', 'Adulte'),
        ('mineur', "Mineur (autorisation parentale)"),
        ('vulnerable', 'Population vulnérable'),
    ], string='Type de participant', required=True)

    langue_formulaire = fields.Char(string='Langue(s) du formulaire')
    version_formulaire = fields.Char(string='Version du formulaire')
    date_validation_cers = fields.Date(string='Date de validation CERS')

    responsable_recueil_id = fields.Many2one('hr.employee', string='Responsable du recueil (enquêteur référent)')
    nb_consentements_signes = fields.Integer(string='Nombre de consentements signés')
    nb_retraits = fields.Integer(string='Nombre de retraits de consentement')
    lieu_archivage = fields.Char(string='Lieu / support d\'archivage sécurisé')

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide_cers', 'Validé CERS'),
        ('en_utilisation', 'En utilisation'),
        ('cloture', 'Clôturé'),
    ], string='Statut', default='brouillon', tracking=True)

    @api.onchange('soumission_id')
    def _onchange_soumission_id(self):
        if self.soumission_id and not self.titre_etude:
            self.titre_etude = self.soumission_id.titre_etude

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.consentement') or _('Nouveau')
            # Filet de sécurité : si la fiche est créée liée à une soumission mais sans
            # titre d'étude renseigné (ex. ajout rapide en ligne éditable), on reprend
            # automatiquement le titre de la soumission liée pour éviter un blocage
            # de validation sur ce champ obligatoire.
            if not vals.get('titre_etude') and vals.get('soumission_id'):
                soumission = self.env['resade.ethique.soumission'].browse(vals['soumission_id'])
                vals['titre_etude'] = soumission.titre_etude
        return super().create(vals_list)

    def action_valider_cers(self):
        self.write({'state': 'valide_cers', 'date_validation_cers': fields.Date.context_today(self)})

    def action_mettre_en_utilisation(self):
        self.write({'state': 'en_utilisation'})

    def action_cloturer(self):
        self.write({'state': 'cloture'})
