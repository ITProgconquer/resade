# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import datetime


class ResadeTresorerieRapprochement(models.Model):
    """
    Rapprochement bancaire mensuel — P-TB-02 B.4 étape 5 / formulaire
    RESADE-F-TB-02-01.

    Ce modèle NE remplace PAS le rapprochement bancaire technique natif
    d'Odoo Accounting (relevés, lettrage ligne à ligne) : il TRACE la
    validation institutionnelle mensuelle, conformément à la RACI réelle du
    manuel :
      - AC prépare (Responsible) ;
      - CAF valide (Accountable) — SEUL décideur, pas de blocage DE ;
      - DE est simplement INFORMÉ (I) — une notification lui est envoyée,
        sans qu'il ait à valider quoi que ce soit pour clôturer le
        rapprochement.
    Délai réglementaire : le rapprochement doit être produit au plus tard
    à J+7 après la fin du mois concerné (KPI : ≥ 95% dans les délais).
    """
    _name = 'resade.tresorerie.rapprochement'
    _description = 'Rapprochement bancaire mensuel – RESADE-F-TB-02-01'
    _inherit = ['mail.thread']
    _order = 'periode desc, journal_id'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau', copy=False)
    code_document = fields.Char(
        string='Code document', default='RESADE-F-TB-02-01', readonly=True,
        help="Référence officielle du formulaire selon le Carnet F."
    )
    journal_id = fields.Many2one(
        'account.journal', string='Compte bancaire / caisse', required=True,
        domain=[('type', 'in', ['bank', 'cash'])]
    )
    periode = fields.Date(string='Mois concerné', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.XOF', raise_if_not_found=False)
        or self.env.company.currency_id
    )

    date_limite = fields.Date(
        string='Date limite réglementaire (J+7)', compute='_compute_date_limite', store=True,
        help="Fin du mois concerné + 7 jours — délai maximal fixé par le Carnet F (P-TB-02)."
    )
    en_retard = fields.Boolean(
        string='⏱️ Hors délai', compute='_compute_en_retard', store=True,
        help="Vrai si le visa CAF n'a pas été obtenu au plus tard à la date limite."
    )

    solde_theorique_odoo = fields.Monetary(
        string='Solde théorique (comptabilité Odoo)', currency_field='currency_id',
        compute='_compute_solde_theorique', store=True,
        help="Recalculé automatiquement depuis les écritures Odoo arrêtées à la fin de période."
    )
    solde_releve_bancaire = fields.Monetary(
        string='Solde du relevé bancaire (banque)', currency_field='currency_id',
        help="Saisi depuis le relevé bancaire papier/PDF ou repris de la "
             "synchronisation bancaire Odoo Enterprise."
    )
    ecart = fields.Monetary(
        string='Écart constaté', compute='_compute_ecart', store=True,
        currency_field='currency_id'
    )
    ecart_justifie = fields.Boolean(string='Écart justifié / expliqué', default=False)
    explication_ecart = fields.Text(string="Explication de l'écart (chèques non débités, frais bancaires...)")

    releve_bancaire = fields.Many2many(
        'ir.attachment', 'resade_treso_rapprochement_pj_rel', string='Relevé bancaire (scan/PDF)'
    )

    statut = fields.Selection([
        ('brouillon', 'En préparation (AC)'),
        ('valide_caf', 'Validé CAF (clôturé)'),
    ], string='Statut', default='brouillon', tracking=True)

    ac_preparateur_id = fields.Many2one('hr.employee', string='Préparé par (AC)')
    caf_valideur_id = fields.Many2one('hr.employee', string='Validé par (CAF)')
    date_visa_caf = fields.Date(string='Date de validation CAF')
    de_notifie = fields.Boolean(
        string='DE informé', default=False, readonly=True,
        help="Le Directeur Exécutif est informé du résultat (rôle 'I' de la RACI), "
             "sans validation bloquante de sa part."
    )

    @api.depends('periode')
    def _compute_date_limite(self):
        for rec in self:
            if rec.periode:
                fin_mois = (rec.periode.replace(day=1) + relativedelta(months=1)) - datetime.timedelta(days=1)
                rec.date_limite = fin_mois + datetime.timedelta(days=7)
            else:
                rec.date_limite = False

    @api.depends('date_limite', 'statut', 'date_visa_caf')
    def _compute_en_retard(self):
        for rec in self:
            if rec.statut == 'valide_caf':
                rec.en_retard = bool(rec.date_limite and rec.date_visa_caf and rec.date_visa_caf > rec.date_limite)
            else:
                rec.en_retard = bool(rec.date_limite and fields.Date.today() > rec.date_limite)

    @api.depends('journal_id', 'periode')
    def _compute_solde_theorique(self):
        for rec in self:
            solde = 0.0
            if rec.journal_id and rec.journal_id.default_account_id and rec.periode:
                fin_periode = (rec.periode.replace(day=1) + relativedelta(months=1)) - datetime.timedelta(days=1)
                lines = self.env['account.move.line'].search([
                    ('account_id', '=', rec.journal_id.default_account_id.id),
                    ('parent_state', '=', 'posted'),
                    ('date', '<=', fin_periode),
                ])
                solde = sum(lines.mapped('balance'))
            rec.solde_theorique_odoo = solde

    @api.depends('solde_theorique_odoo', 'solde_releve_bancaire')
    def _compute_ecart(self):
        for rec in self:
            rec.ecart = (rec.solde_releve_bancaire or 0.0) - (rec.solde_theorique_odoo or 0.0)

    def action_valider_caf(self):
        """
        Validation CAF — décision finale (Accountable) qui clôture le
        rapprochement. Le DE est notifié en parallèle (rôle Informé), sans
        que sa validation soit requise (conforme RACI P-TB-02 B.8).
        """
        self.ensure_one()
        if abs(self.ecart) > 0.01 and not self.ecart_justifie:
            raise UserError(_(
                "Un écart de %s %s existe entre le solde comptable Odoo et le "
                "relevé bancaire. Justifiez l'écart avant validation CAF "
                "(Carnet F – P-TB-02)."
            ) % ('{:,.0f}'.format(self.ecart), self.currency_id.name or 'FCFA'))
        self.write({
            'statut': 'valide_caf',
            'date_visa_caf': fields.Date.today(),
            'caf_valideur_id': self.env.user.employee_id.id,
        })
        self._notifier_de()
        self.message_post(body=_("Rapprochement bancaire validé par le CAF (clôturé)."))

    def _notifier_de(self):
        """Notification du DE (rôle Informé de la RACI) — pas de blocage."""
        self.ensure_one()
        de_group = self.env.ref('resade_tresorerie.group_resade_tresorerie_de', raise_if_not_found=False)
        if de_group:
            self.message_subscribe(partner_ids=de_group.users.mapped('partner_id').ids)
        self.message_post(body=_(
            "Information Directeur Exécutif : rapprochement bancaire de %s (période %s) "
            "clôturé par le CAF. Écart : %s."
        ) % (self.journal_id.name, self.periode, '{:,.0f}'.format(self.ecart)))
        self.de_notifie = True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('resade.tresorerie.rapprochement')
                    or 'RAPP-2026-001'
                )
                vals.setdefault('ac_preparateur_id', self.env.user.employee_id.id)
        return super().create(vals_list)
