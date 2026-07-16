from odoo import models, fields, api


class ResadeFournisseur(models.Model):
    _name = 'resade.fournisseur'
    _description = 'Fournisseur / Prestataire RESADE'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Raison sociale', required=True, tracking=True)
    sigle = fields.Char(string='Sigle / Abréviation')
    type_fournisseur = fields.Selection([
        ('entreprise', 'Entreprise'),
        ('consultant', 'Consultant individuel'),
        ('ong', 'ONG / Association'),
        ('institution', 'Institution publique'),
        ('autre', 'Autre'),
    ], string='Type', default='entreprise', required=True)

    # ─── Coordonnées ───────────────────────────────────
    adresse = fields.Char(string='Adresse')
    ville = fields.Char(string='Ville', default='Ouagadougou')
    pays_id = fields.Many2one(
        'res.country', string='Pays',
        default=lambda self: self.env.ref('base.bf', raise_if_not_found=False)
    )
    telephone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    site_web = fields.Char(string='Site web')

    # ─── Intégration Comptabilité Odoo (Enterprise) ────
    partner_id = fields.Many2one(
        'res.partner', string='Contact comptable (Odoo)',
        help="Contact Odoo Accounting utilisé pour les factures et paiements de ce "
             "fournisseur. Généré automatiquement si vide lors du premier paiement."
    )

    def get_or_create_partner(self):
        """Retourne le res.partner comptable lié, en le créant si nécessaire."""
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        partner = self.env['res.partner'].search(
            [('name', '=', self.name), ('supplier_rank', '>', 0)], limit=1
        )
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.name,
                'is_company': self.type_fournisseur != 'consultant',
                'supplier_rank': 1,
                'street': self.adresse,
                'city': self.ville,
                'country_id': self.pays_id.id if self.pays_id else False,
                'phone': self.telephone,
                'email': self.email,
                'website': self.site_web,
            })
        self.partner_id = partner.id
        return partner

    # ─── Documents légaux ──────────────────────────────
    ifu = fields.Char(string='IFU / NIF')
    rccm = fields.Char(string='RCCM')
    date_expiration_agrement = fields.Date(string='Expiration agrément')

    # ─── Domaines de compétence ────────────────────────
    domaines = fields.Many2many('resade.domaine.marche', string='Domaines de compétence')
    note = fields.Text(string='Observations')

    # ─── Statistiques ──────────────────────────────────
    marche_ids = fields.One2many('resade.marche', 'fournisseur_id', string='Marchés attribués')
    nb_marches = fields.Integer(
        string='Nb marchés', compute='_compute_nb_marches', store=True
    )
    montant_total_marches = fields.Monetary(
        string='Montant total marchés', compute='_compute_nb_marches',
        store=True, currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )

    active = fields.Boolean(default=True)
    blackliste = fields.Boolean(string='Blacklisté', default=False, tracking=True)
    motif_blacklist = fields.Text(string='Motif blacklistage')

    @api.depends('marche_ids', 'marche_ids.montant_final', 'marche_ids.state')
    def _compute_nb_marches(self):
        for rec in self:
            marches = rec.marche_ids.filtered(lambda m: m.state not in ['annule'])
            rec.nb_marches = len(marches)
            rec.montant_total_marches = sum(marches.mapped('montant_final'))


class ResadeDomaineMarch(models.Model):
    _name = 'resade.domaine.marche'
    _description = 'Domaine de marché'
    _order = 'name'

    name = fields.Char(string='Domaine', required=True)
    code = fields.Char(string='Code')
