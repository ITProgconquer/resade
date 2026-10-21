# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ArticleScientifique(models.Model):
    """
    Processus P-CI-04 : Rédaction et revue interne des articles scientifiques
    Carnet I — Module 02 : Publication Scientifique — RESADE
    Conforme aux standards ICMJE (auteurship) et COPE (éthique éditoriale)
    """
    _name = 'resade.article.scientifique'
    _description = 'Article Scientifique (P-CI-04)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc'
    _rec_name = 'reference'

    # ─── Identification ───────────────────────────────────────────────────────
    reference = fields.Char(
        string='Code Article',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    titre = fields.Char(string="Titre de l'article", required=True, tracking=True)
    titre_court = fields.Char(string='Titre court (running head)')
    mots_cles = fields.Char(string='Mots-clés (séparés par des virgules)')
    resume = fields.Text(string='Résumé (Abstract)')

    # ─── Source / Origine ────────────────────────────────────────────────────
    protocole_id = fields.Many2one(
        'resade.protocole.recherche',
        string='Protocole source',
    )
    etude_id = fields.Many2one(
        'resade.etude.enquete',
        string='Étude source',
    )
    projet_id = fields.Many2one('resade.projet', string='Projet rattaché')

    # ─── Auteurs (conformité ICMJE) ───────────────────────────────────────────
    auteur_correspondant_id = fields.Many2one(
        'hr.employee',
        string='Auteur correspondant (CRSP / PI)',
        required=True,
        tracking=True,
    )
    auteurs_ids = fields.Many2many(
        'hr.employee',
        'article_auteur_rel',
        'article_id', 'employee_id',
        string='Co-auteurs',
    )
    auteurs_externes = fields.Text(
        string='Auteurs externes (nom, institution)',
    )

    # ─── Type & Format ────────────────────────────────────────────────────────
    type_article = fields.Selection([
        ('original', 'Article original (recherche primaire)'),
        ('revue', 'Revue systématique / Méta-analyse'),
        ('bref', 'Communication brève / Short communication'),
        ('commentaire', 'Commentaire / Éditorial'),
        ('note_politique', 'Note de politique (Policy Brief)'),
        ('rapport_technique', 'Rapport technique'),
        ('autre', 'Autre'),
    ], string="Type d'article", required=True)

    sutr=fields.Char(string='Préciser le type d\'article si autre', help='Indiquez le type d\'article si différent des options ci-dessus')

    langue = fields.Selection([
        ('fr', 'Français'),
        ('en', 'Anglais'),
        ('fr_en', 'Français & Anglais'),
    ], string='Langue', default='fr', required=True)
    nb_mots = fields.Integer(string='Nombre de mots (version actuelle)')

    # ─── Dates ────────────────────────────────────────────────────────────────
    date_creation = fields.Date(
        string='Date de création',
        default=fields.Date.today,
        required=True,
    )
    date_revue_interne = fields.Date(string='Date envoi revue interne')
    date_retour_revue = fields.Date(string='Date retour commentaires')
    date_finalisation = fields.Date(string='Date finalisation / Approbation DE')

    # ─── Statut workflow ──────────────────────────────────────────────────────
    state = fields.Selection([
        ('brouillon', 'Brouillon (rédaction)'),
        ('revue_interne', 'Revue interne en cours'),
        ('revision', 'En révision (suite à revue)'),
        ('valide_interne', 'Validé en interne'),
        ('soumis', 'Soumis à une revue'),
        ('revision_externe', 'Révision externe demandée'),
        ('accepte', 'Accepté'),
        ('publie', 'Publié'),
        ('rejete', 'Rejeté'),
        ('retire', 'Retiré'),
    ], string='Statut', default='brouillon', tracking=True, required=True)

    # ─── Revue interne ────────────────────────────────────────────────────────
    reviewers_internes_ids = fields.Many2many(
        'hr.employee',
        'article_reviewer_rel',
        'article_id', 'employee_id',
        string='Relecteurs internes',
    )
    commentaires_revue_interne = fields.Html(string='Commentaires de la revue interne', help='Commentaires et recommandations des relecteurs internes')
    grille_revue = fields.Binary(string='Grille de revue interne complétée')
    grille_revue_filename = fields.Char()

    # ─── Conflit d'intérêts & Financement ────────────────────────────────────
    declaration_coi = fields.Boolean(
        string="Déclaration de conflit d'intérêts ?",
        default=False,
        tracking=True,
    )
    source_financement = fields.Text(
        string='Source(s) de financement à déclarer',
    )

    # ─── Documents ───────────────────────────────────────────────────────────
    manuscrit = fields.Binary(string='Manuscrit (version actuelle)')
    manuscrit_filename = fields.Char()
    # ─── Soumissions liées ────────────────────────────────────────────────────
    soumission_count = fields.Integer(
        string='Soumissions',
        compute='_compute_soumission_count',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'resade.article.scientifique') or _('Nouveau')
        return super().create(vals_list)

    def _compute_soumission_count(self):
        for rec in self:
            rec.soumission_count = self.env['resade.soumission.revue'].search_count(
                [('article_id', '=', rec.id)])

    # ─── Workflow ────────────────────────────────────────────────────────────
    def action_envoyer_revue_interne(self):
        self.ensure_one()
        if not self.auteur_correspondant_id:
            raise UserError(_("Veuillez désigner un auteur correspondant."))
        self.write({'state': 'revue_interne', 'date_revue_interne': fields.Date.today()})

    def action_valider_interne(self):
        self.ensure_one()
        if not self.declaration_coi:
            raise UserError(_("La déclaration de conflit d'intérêts est obligatoire (COPE/ICMJE)."))
        self.write({'state': 'valide_interne', 'date_finalisation': fields.Date.today()})

    def action_marquer_soumis(self):
        self.state = 'soumis'

    def action_marquer_accepte(self):
        self.state = 'accepte'

    def action_marquer_publie(self):
        self.state = 'publie'

    def action_voir_soumissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Soumissions — %s') % self.titre[:40],
            'res_model': 'resade.soumission.revue',
            'view_mode': 'list,form',
            'domain': [('article_id', '=', self.id)],
            'context': {'default_article_id': self.id},
        }
