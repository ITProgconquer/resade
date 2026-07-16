# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResadeClotureProjet(models.Model):
    """
    P-CC-01 : Clôture technique et financière du projet
    P-CC-02 : Revue de fin de projet et rapport de leçons apprises
    Formulaires : F-CC-01-01 à F-CC-02-02
    """
    _name = 'resade.cloture.projet'
    _description = 'Dossier de Clôture Projet – P-CC-01 / P-CC-02'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_fin_activites desc'

    name = fields.Char(string='Intitulé', required=True)
    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True,
        ondelete='restrict', tracking=True
    )

    # ── P-CC-01 : Clôture technique & financière ──
    date_fin_activites = fields.Date(
        string='Date fin activités terrain (J0)',
        tracking=True,
        help='Déclenche le calendrier : rapport technique J+15, comptes J+20...'
    )

    # Étape 1 : Calendrier de clôture (J+0)
    calendrier_cloture = fields.Html(
        string='Calendrier de clôture validé',
        help='Dates limites pour chaque livrable : rapport technique (J+15), '
             'rapport financier (J+20), inventaire (J+25), '
             'dossier complet (J+30), quitus (J+35), archivage (J+48h).'
    )

    # Étape 2 : Rapport technique final (J+15)
    rapport_technique_final = fields.Html(
        string='Rapport technique final (F-EST-02-02 / J+15)',
        help='Synthèse exhaustive : exécution activités, atteinte indicateurs cadre logique, '
             'difficultés, écarts vs prévisions. '
             'Produit par CMPPE, supervisé CDO, contrôle CSEA (MELA).'
    )
    date_rapport_technique = fields.Date(
        string='Date production rapport technique'
    )
    rapport_technique_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_rtech_rel', 'clo_id', 'att_id',
        string='Rapport technique final (fichier)'
    )
    valide_rapport_technique = fields.Boolean(
        string='Rapport technique validé CDO', tracking=True
    )

    # Étape 3 : Arrêté des comptes (J+20)
    rapport_financier_cloture = fields.Html(
        string='Rapport financier de clôture (F-CC-01-02 / J+20)',
        help='Arrêté des comptes SAGE, liquidation avances, apurement codes analytiques, '
             'réconciliation budget vs dépenses réelles. '
             'Produit CAF, contrôle Chargé Grants (GFGP Standard).'
    )
    date_rapport_financier = fields.Date(
        string='Date rapport financier (J+20)'
    )
    rapport_financier_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_rfin_rel', 'clo_id', 'att_id',
        string='Rapport financier (fichier + états SAGE)'
    )
    valide_rapport_financier = fields.Boolean(
        string='Rapport financier validé CDO + CAF', tracking=True
    )

    # Étape 4 : Audit de clôture (si contractuel)
    audit_contractuel = fields.Boolean(
        string='Audit de clôture contractuellement requis'
    )
    audit_realise = fields.Boolean(
        string='Audit externe de clôture réalisé', tracking=True
    )
    rapport_audit_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_audit_rel', 'clo_id', 'att_id',
        string='Rapport d\'audit externe (sans réserve majeure)'
    )
    reserves_audit = fields.Text(
        string='Réserves / Points d\'audit',
        help='Résumé des éventuelles réserves et plan de correction'
    )

    # Étape 5 : Inventaire & transfert actifs (J+25)
    inventaire_actifs = fields.Html(
        string='Inventaire final du matériel (F-CC-01-03 / J+25)',
        help='Liste paraphée des équipements acquis, valeur résiduelle, '
             'destination post-projet (restitution bailleur / transfert / conservation).'
    )
    inventaire_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_inv_rel', 'clo_id', 'att_id',
        string='Bordereau d\'inventaire et transfert d\'actifs (F-CC-01-03)'
    )

    # Étape 6 : Dossier complet → DE (J+30)
    checklist_cloture_ok = fields.Boolean(
        string='Checklist de clôture complète (F-CC-01-01 / J+30)',
        tracking=True,
        help='Vérification exhaustive : rapport technique + rapport financier + '
             'audit (si requis) + inventaire + toutes pièces justificatives. '
             'Seul habilité à cocher : Chargé des Grants.'
    )
    checklist_cloture_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_check_rel', 'clo_id', 'att_id',
        string='Checklist de clôture signée (F-CC-01-01)'
    )

    # Étape 7 : Notification bailleur & quitus (J+35)
    dossier_soumis_bailleur = fields.Boolean(
        string='Dossier de clôture soumis au bailleur', tracking=True
    )
    date_soumission_bailleur = fields.Date(
        string='Date de soumission au bailleur (J+35)'
    )
    quitus_recu = fields.Boolean(
        string='Quitus final reçu du bailleur', tracking=True
    )
    date_quitus = fields.Date(string='Date du quitus')
    quitus_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_quitus_rel', 'clo_id', 'att_id',
        string='Courrier de quitus du bailleur'
    )

    # Étape 8 : Archivage GED (J+48h après quitus)
    archivage_ged_confirme = fields.Boolean(
        string='Archivage GED SharePoint confirmé (F-CC-01-04 / J+48h)',
        tracking=True,
        help='AA confirme l\'archivage de 100% des pièces dans SharePoint '
             '03_PROJETS/[Code]/CLOTURE/ sous 48h après quitus.'
    )
    lien_ged_cloture = fields.Char(
        string='Lien SharePoint dossier de clôture',
        help='Ex: 03_PROJETS/[CODE]/CLOTURE/'
    )

    # ── P-CC-02 : Revue de fin de projet & Leçons apprises ──
    # Étape 1 : TDR de l'atelier bilan
    tdr_atelier_bilan = fields.Html(
        string='TDR de l\'atelier bilan (méthode After Action Review)',
        help='Termes de référence de l\'atelier SEPO. '
             'À organiser au moins 10 jours avant la fin contractuelle des experts.'
    )
    date_atelier_bilan = fields.Date(string='Date de l\'atelier SEPO / AAR')
    participants_atelier = fields.Text(
        string='Participants à l\'atelier bilan'
    )

    # Étape 2-3 : Matrice SEPO (F-CC-02-02)
    matrice_sepo = fields.Html(
        string='Matrice SEPO (F-CC-02-02)',
        help='Succès – Échecs – Potentialités – Obstacles identifiés '
             'lors de l\'atelier After Action Review.'
    )
    cr_atelier_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_cr_rel', 'clo_id', 'att_id',
        string='Compte-rendu de l\'atelier bilan (F-CC-02-02)'
    )

    # Étape 4 : Rapport de leçons apprises (F-CC-02-01)
    rapport_lecons_apprises = fields.Html(
        string='Rapport de leçons apprises (F-CC-02-01)',
        help='Canevas institutionnel : succès marquants, échecs documentés, '
             'innovations reproductibles, recommandations organisationnelles. '
             'Produit CCGC, J+10 après atelier.'
    )
    rapport_lecons_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_lecon_rel', 'clo_id', 'att_id',
        string='Rapport de leçons apprises (fichier)'
    )

    # Étape 5 : Restitution plénière + capitalisation
    restitution_faite = fields.Boolean(
        string='Restitution interne réalisée (café-débat / réunion)',
        tracking=True
    )
    date_restitution = fields.Date(string='Date de restitution interne')
    note_politique_ids = fields.Many2many(
        'ir.attachment',
        'resade_clo_np_rel', 'clo_id', 'att_id',
        string='Notes de politique / Policy Briefs produits (F-CGC-01)'
    )

    # Étape 6 : Intégration MELA
    plan_amelioration_mela = fields.Html(
        string='Plan d\'amélioration MELA',
        help='Recommandations réintégrées dans le dispositif MELA '
             'pour les futurs cycles de projets (P-CC-02 séq. 6).'
    )
    integre_mela = fields.Boolean(
        string='Recommandations intégrées dans le dispositif MELA',
        tracking=True
    )
    diffuse_bibliotheque = fields.Boolean(
        string='Rapport diffusé dans la bibliothèque numérique RESADE',
        tracking=True
    )

    # ── État global ──
    state = fields.Selection([
        ('planification',    '📅 Planification de la clôture (J0)'),
        ('rapports_tech_fin','📊 Rapports technique & financier (J+15/J+20)'),
        ('audit',            '🔍 Audit externe (si requis)'),
        ('dossier_complet',  '📁 Dossier complet → DE (J+30)'),
        ('soumis_bailleur',  '📤 Soumis au bailleur (J+35)'),
        ('quitus_recu',      '✅ Quitus reçu'),
        ('archive',          '📦 Archivé (J+48h)'),
        ('capitalise',       '🧠 Capitalisé (P-CC-02)'),
    ], string='Étape de clôture', default='planification', tracking=True)

    # ────────────────────────────────────────
    # WORKFLOW P-CC-01
    # ────────────────────────────────────────
    def action_lancer_rapports(self):
        self.ensure_one()
        if not self.date_fin_activites:
            raise UserError(
                _('Renseignez la date de fin des activités terrain (J0) '
                  'pour déclencher le calendrier de clôture.')
            )
        self.write({'state': 'rapports_tech_fin'})
        self.message_post(
            body=_(
                '📊 Clôture démarrée (J0 = %s). Calendrier :\n'
                '• J+15 : Rapport technique final (CMPPE)\n'
                '• J+20 : Rapport financier de clôture (CAF)\n'
                '• J+25 : Inventaire des actifs (AAL)\n'
                '• J+30 : Dossier complet → DE\n'
                '• J+35 : Notification bailleur et demande quitus\n'
                '• J+48h après quitus : Archivage GED SharePoint'
            ) % self.date_fin_activites
        )

    def action_passer_audit(self):
        self.ensure_one()
        if not self.valide_rapport_technique or not self.valide_rapport_financier:
            raise UserError(
                _('Les rapports technique et financier doivent être validés '
                  'avant de lancer l\'audit (P-CC-01 séq. 4).')
            )
        self.write({'state': 'audit'})
        self.message_post(
            body=_('🔍 Phase d\'audit externe démarrée (si contractuellement requis).')
        )

    def action_constituer_dossier(self):
        self.ensure_one()
        if not self.valide_rapport_technique:
            raise UserError(
                _('Rapport technique non validé (F-EST-02-02).')
            )
        if not self.valide_rapport_financier:
            raise UserError(
                _('Rapport financier non validé (F-CC-01-02).')
            )
        if self.audit_contractuel and not self.audit_realise:
            raise UserError(
                _('L\'audit contractuel n\'a pas encore été réalisé.')
            )
        if not self.checklist_cloture_ok:
            raise UserError(
                _('Validez la checklist de clôture (F-CC-01-01) '
                  'avant de soumettre au DE (séq. 6 J+30).')
            )
        self.write({'state': 'dossier_complet'})
        self.message_post(
            body=_('📁 Dossier de clôture complet constitué (J+30). '
                   'Soumis au DE pour validation institutionnelle et signature.')
        )

    def action_soumettre_bailleur(self):
        self.ensure_one()
        if self.state not in ('dossier_complet', 'audit'):
            raise UserError(_('Le dossier doit être complet avant soumission au bailleur.'))
        self.write({
            'state': 'soumis_bailleur',
            'date_soumission_bailleur': self.date_soumission_bailleur or fields.Date.today(),
            'dossier_soumis_bailleur': True,
        })
        self.message_post(
            body=_('📤 Dossier de clôture soumis au bailleur le %s. '
                   'Demande de quitus en attente (J+35).') % self.date_soumission_bailleur
        )

    def action_quitus_recu(self):
        self.ensure_one()
        if not self.quitus_ids:
            raise UserError(
                _('Joignez le courrier de quitus du bailleur '
                  'avant de confirmer la réception.')
            )
        self.write({
            'state': 'quitus_recu',
            'quitus_recu': True,
            'date_quitus': self.date_quitus or fields.Date.today(),
        })
        self.projet_id.write({'state': 'cloture_ok'})
        self.message_post(
            body=_(
                '✅ Quitus reçu du bailleur le %s. '
                'Archivage GED SharePoint à réaliser sous 48h '
                '(F-CC-01-04 – AAL). '
                'Lancer la revue de leçons apprises (P-CC-02).'
            ) % self.date_quitus
        )

    def action_confirmer_archivage(self):
        self.ensure_one()
        if not self.archivage_ged_confirme:
            raise UserError(
                _('Confirmez l\'archivage GED SharePoint '
                  '(cocher la case + renseigner le lien SharePoint).')
            )
        self.write({'state': 'archive'})
        self.message_post(
            body=_('📦 Dossier archivé dans GED : %s. '
                   'Clôture P-CC-01 terminée. '
                   'Lancer la revue P-CC-02 (leçons apprises).') % self.lien_ged_cloture
        )

    # ────────────────────────────────────────
    # WORKFLOW P-CC-02
    # ────────────────────────────────────────
    def action_lancer_lecons_apprises(self):
        """P-CC-02 : Organiser l'atelier SEPO / After Action Review"""
        self.ensure_one()
        if self.state not in ('archive', 'quitus_recu'):
            raise UserError(
                _('Attendez la réception du quitus et l\'archivage '
                  'avant de lancer les leçons apprises (P-CC-02).')
            )
        if not self.tdr_atelier_bilan:
            raise UserError(
                _('Rédigez les TDR de l\'atelier bilan '
                  '(méthode After Action Review / SEPO) avant de lancer.')
            )
        self.message_post(
            body=_('🧠 Atelier bilan planifié le %s. '
                   'Méthode : After Action Review + SEPO. '
                   'Facilitateur : CCGC.') % (self.date_atelier_bilan or '—')
        )

    def action_valider_lecons_apprises(self):
        """Rapport de leçons apprises validé → intégration MELA + bibliothèque"""
        self.ensure_one()
        if not self.rapport_lecons_apprises:
            raise UserError(
                _('Rédigez le rapport de leçons apprises (F-CC-02-01) '
                  'avant de valider.')
            )
        if not self.restitution_faite:
            raise UserError(
                _('La restitution interne (café-débat ou réunion) '
                  'doit être réalisée avant clôture (P-CC-02 séq. 5).')
            )
        self.write({
            'state': 'capitalise',
            'integre_mela': True,
            'diffuse_bibliotheque': True,
        })
        self.message_post(
            body=_(
                '🧠 Leçons apprises capitalisées et intégrées dans le dispositif MELA. '
                'Rapport diffusé dans la bibliothèque numérique RESADE. '
                'Cycle projet P-CC-02 terminé. '
                'Identifier au moins 1 thématique d\'article publiable (Carnet I / P-PS-01).'
            )
        )
