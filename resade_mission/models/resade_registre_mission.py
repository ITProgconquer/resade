# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeRegistreMission(models.Model):
    """
    RESADE-F-GMD-02-04 : Registre des missions exécutées
    Journal chronologique de toutes les missions exécutées :
    numéro, missionnaire, destination, dates, objet,
    date de remise du rapport, statut, lien GED.
    Mis à jour automatiquement depuis resade.mission.
    """
    _name = 'resade.registre.mission'
    _description = 'Registre des Missions Exécutées – RESADE-F-GMD-02-04'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_retour_effectif desc, name desc'
    _rec_name = 'mission_id'

    # Lien vers l'OM source
    mission_id = fields.Many2one(
        'resade.mission',
        string='Ordre de Mission',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ─── Colonnes du registre (F-GMD-02-04) ───
    name = fields.Char(
        string='N° OM',
        related='mission_id.name',
        store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Missionnaire',
        related='mission_id.employee_id',
        store=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Département / Pool',
        related='mission_id.department_id',
        store=True,
    )
    destination = fields.Char(
        string='Destination',
        related='mission_id.destination',
        store=True,
    )
    zone_mission = fields.Selection(
        related='mission_id.zone_mission',
        store=True,
        string='Zone',
    )
    objet_mission = fields.Text(
        string='Objet de la mission',
        related='mission_id.objet_mission',
        store=True,
    )
    date_depart = fields.Date(
        string='Date départ prévue',
        related='mission_id.date_depart',
        store=True,
    )
    date_retour = fields.Date(
        string='Date retour prévue',
        related='mission_id.date_retour',
        store=True,
    )
    date_depart_effectif = fields.Date(
        string='Date départ effectif',
        related='mission_id.date_depart_effectif',
        store=True,
    )
    date_retour_effectif = fields.Date(
        string='Date retour effectif',
        related='mission_id.date_retour_effectif',
        store=True,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Projet / Bailleur',
        related='mission_id.analytic_account_id',
        store=True,
    )
    montant_avance_approuve = fields.Monetary(
        string='Avance approuvée',
        related='mission_id.montant_avance_approuve',
        store=True,
        currency_field='currency_id',
    )
    montant_depense_reel = fields.Monetary(
        string='Frais réels',
        related='mission_id.montant_depense_reel',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='mission_id.currency_id',
        store=True,
    )

    # ─── Colonnes spécifiques au registre ───
    date_soumission_rapport = fields.Date(
        string='Date remise rapport',
        related='mission_id.date_soumission_rapport',
        store=True,
    )
    delai_rapport_ok = fields.Boolean(
        string='Rapport dans les délais',
        related='mission_id.delai_rapport_ok',
        store=True,
    )

    # Statut registre : reflète l'état de la mission
    statut_registre = fields.Selection([
        ('en_cours',          '✈️ En cours'),
        ('rapport_attente',   '⏳ Rapport en attente'),
        ('rapport_soumis',    '📄 Rapport soumis'),
        ('rapport_valide',    '✅ Rapport validé'),
        ('rapport_approuve',  '✔️ Rapport approuvé DE'),
        ('justif_en_cours',   '🧾 Justification en cours'),
        ('remboursement_ok',  '💳 Remboursement validé'),
        ('archive',           '📁 Archivé / Clôturé'),
    ], string='Statut registre', compute='_compute_statut_registre',
        store=True, tracking=True)

    # Lien GED / SharePoint
    lien_ged = fields.Char(
        string='Lien GED SharePoint',
        help='Chemin SharePoint : 02_ADMINISTRATION/Archives_Missions/[N°OM]'
    )
    archivage_confirme = fields.Boolean(
        string='Archivage GED confirmé',
        tracking=True,
        help='L\'AA confirme l\'archivage du dossier complet dans la GED '
             'avant déclenchement de P-GMD-03 (P-GMD-02 B.7 étape 7)'
    )
    date_archivage = fields.Date(
        string='Date archivage GED',
        tracking=True,
    )
    archivage_par_id = fields.Many2one(
        'res.users',
        string='Archivé par (AA)',
        readonly=True,
    )
    note_registre = fields.Text(
        string='Observations / Écarts TDR',
        help='Modifications substantielles par rapport aux TDR, '
             'incidents, enseignements documentés'
    )

    @api.depends('mission_id.state', 'mission_id.rapport_valide_chef',
                 'mission_id.rapport_approuve_de')
    def _compute_statut_registre(self):
        mapping = {
            'en_mission':       'en_cours',
            'rapport_soumis':   'rapport_soumis',
            'rapport_approuve': 'rapport_approuve',
            'justif_soumise':   'justif_en_cours',
            'remboursement_ok': 'remboursement_ok',
            'cloture':          'archive',
        }
        for rec in self:
            state = rec.mission_id.state
            if state == 'rapport_soumis' and rec.mission_id.rapport_valide_chef:
                rec.statut_registre = 'rapport_valide'
            elif state in ('brouillon', 'valide_chef', 'approuve_caf',
                           'autorise_de', 'avance_decaisse'):
                rec.statut_registre = 'rapport_attente'
            else:
                rec.statut_registre = mapping.get(state, 'rapport_attente')

    def action_confirmer_archivage(self):
        """L'AA confirme l'archivage dans la GED et déclenche P-GMD-03"""
        self.ensure_one()
        self.write({
            'archivage_confirme': True,
            'date_archivage': fields.Date.today(),
            'archivage_par_id': self.env.user.id,
        })
        self.mission_id.message_post(
            body=_(
                '📁 Dossier de mission archivé dans la GED SharePoint '
                '(02_ADMINISTRATION/Archives_Missions) par %s. '
                'Registre F-GMD-02-04 mis à jour. '
                'Processus P-GMD-03 (justification/remboursement) déclenché.'
            ) % self.env.user.name
        )

    def action_ouvrir_mission(self):
        """Ouvrir la fiche mission depuis le registre"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordre de Mission',
            'res_model': 'resade.mission',
            'res_id': self.mission_id.id,
            'view_mode': 'form',
        }
