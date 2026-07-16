# -*- coding: utf-8 -*-
from odoo import models, fields


class ResadeCourrierTiers(models.Model):
    """Sociétés / structures externes : partenaires, bailleurs, administrations, prestataires."""
    _name = 'resade.courrier.tiers'
    _description = 'Société / Structure externe (partenaire, bailleur, administration, prestataire)'
    _order = 'name'

    name = fields.Char(string='Nom de la structure', required=True)
    type_tiers = fields.Selection([
        ('partenaire', 'Partenaire'),
        ('bailleur', 'Bailleur / PTF'),
        ('administration', 'Administration'),
        ('prestataire', 'Prestataire'),
        ('autre', 'Autre'),
    ], string='Type', default='autre')
    adresse = fields.Text(string='Adresse')
    email = fields.Char(string='Email')
    telephone = fields.Char(string='Téléphone')
    actif = fields.Boolean(string='Actif', default=True)


class ResadeCourrierContact(models.Model):
    """Personnes physiques externes (correspondants chez les tiers)."""
    _name = 'resade.courrier.contact'
    _description = 'Contact externe'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    fonction = fields.Char(string='Fonction')
    tiers_id = fields.Many2one('resade.courrier.tiers', string='Structure')
    email = fields.Char(string='Email')
    telephone = fields.Char(string='Téléphone')


class ResadeCourrierService(models.Model):
    """Services / départements internes RESADE pouvant être destinataires ou émetteurs."""
    _name = 'resade.courrier.service'
    _description = 'Service / Département RESADE'
    _order = 'name'

    name = fields.Char(string='Nom du service', required=True)
    responsable_id = fields.Many2one('hr.employee', string='Responsable')


class ResadeCourrierObjet(models.Model):
    """Liste contrôlée d'objets / catégories de courrier (facilite le tri et les statistiques)."""
    _name = 'resade.courrier.objet'
    _description = 'Catégorie / Objet type de courrier'
    _order = 'name'

    name = fields.Char(string='Libellé', required=True)


class ResadeCourrierTag(models.Model):
    _name = 'resade.courrier.tag'
    _description = 'Étiquette de courrier'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    color = fields.Integer(string='Couleur')
