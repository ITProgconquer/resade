from odoo import models, fields, api, exceptions


class ResadeMarcheCAM(models.Model):
    """
    Commission d'Attribution des Marchés (CAM) – Carnet D Module 01
    Processus P-CIP-01 : Composition et fonctionnement
    Convoquée pour tout marché > 2 000 000 FCFA
    Présidée par le DE, secrétariat assuré par le CAF
    Quorum : 3 membres minimum dont DE + CAF
    """
    _name = 'resade.marche.cam'
    _description = "Séance CAM – Commission d'Attribution des Marchés"
    _inherit = ['mail.thread']
    _order = 'date_prevue desc'

    name = fields.Char(
        string='Réf. PV CAM', required=True,
        readonly=True, default='Nouveau', copy=False
    )
    marche_id = fields.Many2one(
        'resade.marche', string='Dossier marché', required=True, ondelete='cascade'
    )
    objet = fields.Char(string='Objet de la séance', required=True)
    date_prevue = fields.Date(string='Date prévue', required=True)
    date_effective = fields.Date(string='Date effective')
    lieu = fields.Char(string='Lieu', default='Locaux RESADE – Ouagadougou')

    # Membres permanents (organigramme RESADE 2025)
    president_id = fields.Many2one(
        'hr.employee', string='Président CAM (Directeur Exécutif)'
    )
    secretaire_id = fields.Many2one(
        'hr.employee', string='Secrétaire CAM (CAF)'
    )
    # Membres techniques selon nature du marché
    membre_ids = fields.One2many(
        'resade.marche.cam.membre', 'cam_id', string='Membres présents'
    )

    # Quorum – règle Manuel : min 3 membres dont obligatoirement DE + CAF
    quorum_atteint = fields.Boolean(
        string='Quorum atteint (≥3 dont DE+CAF)', compute='_compute_quorum', store=True
    )
    nb_membres_presents = fields.Integer(
        string='Nb membres présents', compute='_compute_quorum', store=True
    )

    # Déclarations absence conflits d'intérêts (P-DA-01 – obligatoire avant ouverture)
    declarations_ci_signees = fields.Boolean(
        string="Déclarations CI signées par tous les membres", default=False
    )

    # Délibérations
    fournisseur_recommande_id = fields.Many2one(
        'resade.fournisseur', string='Fournisseur recommandé'
    )
    montant_recommande = fields.Monetary(
        string='Montant recommandé', currency_field='currency_id'
    )
    currency_id = fields.Many2one(related='marche_id.currency_id', store=True)
    recommandation = fields.Text(string='Recommandation motivée (obligatoire)')
    motif_attribution = fields.Text(string='Motif de l\'attribution')

    # PV
    pv_signe = fields.Boolean(string='PV signé par tous', default=False)
    date_signature_pv = fields.Date(string='Date signature PV')
    pj_pv = fields.Many2many('ir.attachment', 'cam_pj_pv_rel', string='PV signé (scan GED)')

    state = fields.Selection([
        ('brouillon', 'Convocation préparée'),
        ('tenue', 'Séance tenue'),
        ('pv_signe', 'PV signé'),
        ('cloturee', 'Clôturée'),
    ], string='État', default='brouillon', tracking=True)

    @api.depends('membre_ids', 'membre_ids.present', 'president_id', 'secretaire_id')
    def _compute_quorum(self):
        for rec in self:
            nb = len(rec.membre_ids.filtered(lambda m: m.present))
            if rec.president_id:
                nb += 1
            if rec.secretaire_id:
                nb += 1
            rec.nb_membres_presents = nb
            rec.quorum_atteint = nb >= 3 and bool(rec.president_id) and bool(rec.secretaire_id)

    def action_tenir_seance(self):
        self.ensure_one()
        if not self.quorum_atteint:
            raise exceptions.UserError(
                "Quorum non atteint. La CAM requiert au moins 3 membres "
                "dont le Président (DE) et le Secrétaire (CAF) – Manuel RESADE P-CIP-01."
            )
        if not self.declarations_ci_signees:
            raise exceptions.UserError(
                "Les déclarations d'absence de conflit d'intérêts doivent être signées "
                "par tous les membres avant l'ouverture de la séance (P-DA-01 Carnet D)."
            )
        self.write({'state': 'tenue', 'date_effective': fields.Date.today()})
        self.message_post(body="📋 Séance CAM tenue – quorum et déclarations CI validés.")

    def action_signer_pv(self):
        self.ensure_one()
        if not self.recommandation:
            raise exceptions.UserError(
                "La recommandation motivée est obligatoire avant la signature du PV CAM."
            )
        if not self.fournisseur_recommande_id:
            raise exceptions.UserError("Renseignez le fournisseur recommandé.")
        self.write({
            'state': 'pv_signe',
            'pv_signe': True,
            'date_signature_pv': fields.Date.today(),
        })
        self.message_post(body="✍️ PV CAM signé.")

    def action_cloturer(self):
        self.ensure_one()
        self.write({'state': 'cloturee'})
        self.message_post(body="🔒 Séance CAM clôturée et archivée.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.marche.cam')
                    or 'CAM-2026-001'
                )
        return super().create(vals_list)


class ResadeMarcheCamMembre(models.Model):
    """Membres présents à la séance CAM avec déclaration CI"""
    _name = 'resade.marche.cam.membre'
    _description = 'Membre présent à la séance CAM'

    cam_id = fields.Many2one('resade.marche.cam', string='Séance CAM', ondelete='cascade')
    employe_id = fields.Many2one('hr.employee', string='Membre', required=True)
    role = fields.Char(string='Rôle dans la CAM')
    present = fields.Boolean(string='Présent', default=True)
    signature_declaration = fields.Boolean(string='Déclaration CI signée', default=False)
    conflit_interet = fields.Boolean(string="Conflit d'intérêt déclaré", default=False)
    nature_conflit = fields.Text(string='Nature du conflit')
    recuse = fields.Boolean(string='Récusé', default=False)
