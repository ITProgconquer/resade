from odoo import models, fields

class ResadeDomaineRecherche(models.Model):
    _name = 'resade.domaine.recherche'
    _description = 'Domaine de recherche (Thématique RESADE)'
    _order = 'name'

    name = fields.Char(string='Nom du domaine', required=True)
    active = fields.Boolean(string='Actif', default=True)
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Ce domaine de recherche existe déjà.')
    ]