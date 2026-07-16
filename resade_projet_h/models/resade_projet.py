# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResadeProjet(models.Model):
    """
    P-CD-01 : Négociation et signature des conventions / contrats bailleurs
    P-CD-02 : Démarrage de projet (kick-off)
    P-CD-03 : Gestion du panier commun et clé de répartition interne
    P-EST-01 : Suivi technique de l'exécution des activités de projet
    P-EST-02 : Reporting technique aux bailleurs
    Formulaires : F-CD-01-01 à F-CD-02-07 / F-EST-01-01 à F-EST-02-05
    """
    _name = 'resade.projet'
    _description = 'Projet RESADE – Carnet H (P-CD / P-EST)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc, name'

    # ── Identification ──
    name = fields.Char(string='Intitulé du projet', required=True, tracking=True)
    ref = fields.Char(
        string='Code projet', default=lambda self: _('Nouveau'),
        copy=False, readonly=True
    )
    proposition_id = fields.Many2one(
        'resade.proposition', string='Proposition source (P-MRV-02)',
        ondelete='restrict'
    )
    bailleur = fields.Char(string='Bailleur / PTF', required=True, tracking=True)
    type_accord = fields.Selection([
        ('convention',       'Convention de financement'),
        ('contrat',          'Contrat de prestation'),
        ('mou',              'Memorandum of Understanding (MoU)'),
        ('subvention',       'Subvention directe'),
        ('consortium',       'Accord de consortium / Subaward'),
        ('accord_cadre',     'Accord-cadre pluriannuel'),
    ], string='Type d\'accord', required=True, default='convention')

    # ── Équipe ──
    pi_id = fields.Many2one('hr.employee', string='Principal Investigator (PI)', tracking=True)
    cdp_id = fields.Many2one('hr.employee', string='Chef Département Partenariat (CDP)')
    cdo_id = fields.Many2one('hr.employee', string='Chef Département Opérations (CDO)')
    rp_id = fields.Many2one(
        'hr.employee', string='Responsable de Projet (RP)',
        help='Chargé CMPPE – pilote opérationnel nommé en P-CD-02'
    )
    caf_id = fields.Many2one('hr.employee', string='CAF (Admin & Finances)')
    sea_id = fields.Many2one('hr.employee', string='Chargé SEA (Suivi-Évaluation)')

    # ── MODULE 02 : P-CD-01 — Négociation & Signature ──
    date_reception_draft = fields.Date(
        string='Date réception draft convention', tracking=True
    )
    memo_negociation = fields.Html(
        string='Mémo de négociation (F-CD-01-01)',
        help='Consolidation des amendements techniques, financiers et juridiques '
             'à discuter avec le bailleur. Produit par le Chargé DPMR (J+5 après réception).'
    )
    checklist_conformite_juridique = fields.Boolean(
        string='Checklist conformité juridique & financière (F-CD-01-04) validée',
        tracking=True,
        help='Vérification des clauses PI, délais de reporting, modalités d\'audit, '
             'standard GFGP. Obligatoire avant toute signature.'
    )
    pv_validation_de_ca = fields.Html(
        string='PV de validation institutionnelle (F-CD-01-02)',
        help='Décision DE (et CA si montant significatif) autorisant la signature. '
             'Référence : Axe 2 OS 2.1 PS RESADE 2026-2030.'
    )
    convention_signee_ids = fields.Many2many(
        'ir.attachment',
        'resade_projet_conv_rel', 'proj_id', 'att_id',
        string='Convention / Contrat signé (original numérisé)'
    )
    date_signature = fields.Date(
        string='Date de signature', tracking=True
    )
    archivage_ged_confirme = fields.Boolean(
        string='Archivage GED SharePoint confirmé (F-CD-01-05)',
        tracking=True,
        help='AA confirme l\'archivage dans 02_PARTENARIATS/Conventions/ sous 48h'
    )
    bordereau_notification_ids = fields.Many2many(
        'ir.attachment',
        'resade_projet_bord_rel', 'proj_id', 'att_id',
        string='Bordereau de notification démarrage (F-CD-01-03)'
    )

    # ── MODULE 02 : P-CD-02 — Démarrage (Kick-off) ──
    date_debut = fields.Date(
        string='Date de début', tracking=True
    )
    date_fin = fields.Date(
        string='Date de fin prévue', tracking=True
    )
    duree_mois = fields.Integer(string='Durée (mois)', tracking=True)
    code_analytique_sage = fields.Char(
        string='Code analytique SAGE',
        tracking=True,
        help='Ouvert par le CAF dans SAGE dès J+5 après signature (P-CD-02 séq. 3). '
             'Permet le suivi budgétaire et les imputations comptables.'
    )
    note_nomination_equipe = fields.Html(
        string='Note de nomination de l\'équipe (F-CD-02-02)',
        help='Note de service CDO + DE désignant le RP et les experts. J+3 après signature.'
    )
    poa_detaille = fields.Html(
        string='Plan Opérationnel Annuel – POA (F-CD-02-03)',
        help='Planification fine : activités, chronogramme, responsables, jalons, '
             'indicateurs MELA. Élaboré par le RP (J+10 après signature).'
    )
    budget_operationnel = fields.Html(
        string='Budget opérationnel (F-CD-02-04)',
        help='Budget détaillé calé sur le POA et l\'ouverture du code SAGE. J+12.'
    )
    pv_kickoff_ids = fields.Many2many(
        'ir.attachment',
        'resade_projet_kickoff_rel', 'proj_id', 'att_id',
        string='PV de réunion de démarrage – Kick-off (F-CD-02-05)',
        help='PV signé bailleur + RESADE + partenaires. Valide l\'alignement technique.'
    )
    date_kickoff = fields.Date(
        string='Date du kick-off', tracking=True
    )
    delai_demarrage_jours = fields.Integer(
        string='Délai démarrage (jours)',
        compute='_compute_delai_demarrage', store=True,
        help='Délai entre signature et kick-off. Cible : ≤ 15 jours calendaires (KPI P-CD-02).'
    )
    checklist_demarrage_ok = fields.Boolean(
        string='Checklist démarrage GFGP validée (F-CD-02-07)',
        tracking=True,
        help='Tous les prérequis RH, logistique, SAGE, SharePoint sont prêts avant kick-off.'
    )

    # ── MODULE 02 : P-CD-03 — Panier commun & Clé de répartition ──
    panier_commun_id = fields.Many2one(
        'resade.panier.commun',
        string='Panier commun de rattachement (P-CD-03)'
    )
    taux_overhead_convention = fields.Float(
        string='Taux coûts indirects / Overhead (%)',
        help='Taux négocié avec le bailleur (GFGP Module 3). '
             'Alimenté automatiquement dans le panier commun à chaque paiement.'
    )
    montant_overhead_prevu = fields.Monetary(
        string='Overhead prévu (FCFA)',
        compute='_compute_overhead', store=True,
        currency_field='currency_id'
    )

    # ── Financier ──
    montant_convention = fields.Monetary(
        string='Montant total de la convention',
        currency_field='currency_id', tracking=True
    )
    montant_recu = fields.Monetary(
        string='Montant reçu à ce jour',
        currency_field='currency_id', tracking=True
    )
    montant_depense = fields.Monetary(
        string='Montant dépensé à ce jour',
        currency_field='currency_id', tracking=True
    )
    taux_execution_financier = fields.Float(
        string='Taux d\'exécution financier (%)',
        compute='_compute_taux_execution', store=True
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )

    # ── MODULE 03 : P-EST-01 — Suivi technique ──
    activite_ids = fields.One2many(
        'resade.activite.projet', 'projet_id',
        string='Activités du projet (POA)'
    )
    indicateur_ids = fields.One2many(
        'resade.indicateur.projet', 'projet_id',
        string='Indicateurs MELA / Cadre logique'
    )
    risque_ids = fields.One2many(
        'resade.risque.projet', 'projet_id',
        string='Registre des risques projet'
    )
    rapport_avancement_ids = fields.One2many(
        'resade.rapport.projet', 'projet_id',
        string='Rapports d\'avancement'
    )
    nb_activites = fields.Integer(
        string='Nb activités', compute='_compute_stats_activites'
    )
    nb_activites_realisees = fields.Integer(
        string='Nb réalisées', compute='_compute_stats_activites'
    )
    taux_execution_technique = fields.Float(
        string='Taux d\'exécution technique (%)',
        compute='_compute_stats_activites', store=True
    )

    # ── MODULE 03 : P-EST-02 — Reporting bailleurs ──
    prochain_rapport_bailleur = fields.Date(
        string='Prochaine échéance rapport bailleur',
        tracking=True
    )
    frequence_rapport_bailleur = fields.Selection([
        ('mensuel',      'Mensuel'),
        ('trimestriel',  'Trimestriel'),
        ('semestriel',   'Semestriel'),
        ('annuel',       'Annuel'),
        ('fin_projet',   'Rapport final uniquement'),
    ], string='Fréquence rapports bailleur', default='trimestriel'
    )

    # ── Partenaires & Sous-traitants ──
    partenaire_ids = fields.One2many(
        'resade.partenaire.projet', 'projet_id',
        string='Partenaires et Sous-traitants (P-EST-03)'
    )

    # ── Clôture ──
    cloture_id = fields.Many2one(
        'resade.cloture.projet', string='Dossier de clôture (P-CC-01)',
        readonly=True
    )

    # ── GED / SharePoint ──
    lien_sharepoint = fields.Char(
        string='Lien SharePoint projet',
        help='Espace projet SharePoint : 03_PROJETS/[Code projet]/'
    )
    document_ids = fields.Many2many(
        'ir.attachment',
        'resade_projet_doc_rel', 'proj_id', 'att_id',
        string='Documents projets (conventions, POA, rapports...)'
    )

    # ── État ──
    state = fields.Selection([
        ('negociation',   '📋 Négociation convention (P-CD-01)'),
        ('demarrage',     '🚀 Démarrage (P-CD-02)'),
        ('execution',     '⚙️ En exécution (P-EST-01)'),
        ('cloture',       '🏁 En clôture (P-CC-01)'),
        ('cloture_ok',    '✅ Clôturé'),
        ('suspendu',      '⏸️ Suspendu'),
        ('abandonne',     '❌ Abandonné'),
    ], string='Phase', default='negociation', tracking=True, copy=False)

    # ────────────────────────────────────────
    # COMPUTED
    # ────────────────────────────────────────
    @api.depends('date_signature', 'date_kickoff')
    def _compute_delai_demarrage(self):
        for rec in self:
            if rec.date_signature and rec.date_kickoff:
                rec.delai_demarrage_jours = (rec.date_kickoff - rec.date_signature).days
            else:
                rec.delai_demarrage_jours = 0

    @api.depends('montant_convention', 'taux_overhead_convention')
    def _compute_overhead(self):
        for rec in self:
            rec.montant_overhead_prevu = (
                rec.montant_convention * rec.taux_overhead_convention / 100
            )

    @api.depends('montant_convention', 'montant_depense')
    def _compute_taux_execution(self):
        for rec in self:
            rec.taux_execution_financier = (
                rec.montant_depense / rec.montant_convention * 100
                if rec.montant_convention else 0.0
            )

    @api.depends('activite_ids', 'activite_ids.state')
    def _compute_stats_activites(self):
        for rec in self:
            total = len(rec.activite_ids)
            realisees = len(rec.activite_ids.filtered(
                lambda a: a.state == 'realisee'
            ))
            rec.nb_activites = total
            rec.nb_activites_realisees = realisees
            rec.taux_execution_technique = (
                realisees / total * 100 if total else 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', _('Nouveau')) == _('Nouveau'):
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'resade.projet'
                ) or _('Nouveau')
        return super().create(vals_list)

    # ────────────────────────────────────────
    # WORKFLOW P-CD-01
    # ────────────────────────────────────────
    def action_convention_signee(self):
        """P-CD-01 séq. 7 – Convention signée, notification démarrage"""
        self.ensure_one()
        if not self.checklist_conformite_juridique:
            raise UserError(
                _('Validez la checklist de conformité juridique et financière '
                  '(F-CD-01-04 / Standard GFGP) avant de confirmer la signature.')
            )
        if not self.convention_signee_ids:
            raise UserError(
                _('Joignez la convention signée numérisée '
                  'avant de confirmer (archivage GED obligatoire sous 48h – F-CD-01-05).')
            )
        if not self.date_signature:
            raise UserError(_('Renseignez la date de signature.'))
        self.write({'state': 'demarrage'})
        self.message_post(
            body=_('📋 Convention signée le %s. '
                   'Bordereau de notification émis → démarrage P-CD-02. '
                   'Archivage GED SharePoint à confirmer sous 48h.') % self.date_signature
        )

    # ────────────────────────────────────────
    # WORKFLOW P-CD-02
    # ────────────────────────────────────────
    def action_kickoff_tenu(self):
        """P-CD-02 séq. 6 – Kick-off tenu, projet en exécution"""
        self.ensure_one()
        if self.state != 'demarrage':
            raise UserError(_('Le projet doit être en phase de démarrage.'))
        if not self.code_analytique_sage:
            raise UserError(
                _('Renseignez le code analytique SAGE ouvert par le CAF '
                  '(P-CD-02 séq. 3 – obligatoire avant tout décaissement).')
            )
        if not self.pv_kickoff_ids:
            raise UserError(
                _('Joignez le PV de la réunion de démarrage (F-CD-02-05) '
                  'signé par le bailleur et RESADE.')
            )
        if not self.rp_id:
            raise UserError(
                _('Désignez le Responsable de Projet (RP / CMPPE) '
                  '(F-CD-02-02 – Note de nomination).')
            )
        if self.delai_demarrage_jours > 15:
            self.message_post(
                body=_('⚠️ Délai de démarrage : %d jours (KPI cible ≤ 15j – P-CD-02).') % (
                    self.delai_demarrage_jours
                )
            )
        self.write({
            'state': 'execution',
            'date_debut': self.date_kickoff or fields.Date.today(),
        })
        self.message_post(
            body=_('🚀 Kick-off tenu le %s. Projet en exécution (P-EST-01). '
                   'Code SAGE : %s') % (self.date_kickoff, self.code_analytique_sage)
        )

    # ────────────────────────────────────────
    # WORKFLOW P-CC-01
    # ────────────────────────────────────────
    def action_lancer_cloture(self):
        """Déclenche le processus de clôture P-CC-01"""
        self.ensure_one()
        if self.state != 'execution':
            raise UserError(_('Le projet doit être en exécution pour lancer la clôture.'))
        if self.cloture_id:
            raise UserError(_('Un dossier de clôture existe déjà pour ce projet.'))
        cloture = self.env['resade.cloture.projet'].create({
            'projet_id': self.id,
            'name': f'Clôture – {self.name}',
        })
        self.write({
            'state': 'cloture',
            'cloture_id': cloture.id,
        })
        self.message_post(
            body=_('🏁 Processus de clôture P-CC-01 déclenché. '
                   'Dossier de clôture créé. '
                   'Calendrier des livrables finaux à établir (J+15 après fin terrain).')
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dossier de Clôture',
            'res_model': 'resade.cloture.projet',
            'res_id': cloture.id,
            'view_mode': 'form',
        }


class ResadeActiviteProjet(models.Model):
    """P-EST-01 : Activités du POA – suivi d'exécution"""
    _name = 'resade.activite.projet'
    _description = 'Activité de Projet – POA (P-EST-01)'
    _order = 'sequence, date_debut_prevue'

    sequence = fields.Integer(default=10)
    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True, ondelete='cascade'
    )
    name = fields.Char(string='Intitulé de l\'activité', required=True)
    code_activite = fields.Char(string='Code activité (POA)')
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    date_debut_prevue = fields.Date(string='Début prévu')
    date_fin_prevue = fields.Date(string='Fin prévue')
    date_realisation = fields.Date(string='Date de réalisation effective')
    budget_prevu = fields.Monetary(
        string='Budget prévu', currency_field='currency_id'
    )
    depense_reelle = fields.Monetary(
        string='Dépense réelle', currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='projet_id.currency_id', store=True
    )
    state = fields.Selection([
        ('planifiee',   '📅 Planifiée'),
        ('en_cours',    '⚙️ En cours'),
        ('realisee',    '✅ Réalisée'),
        ('reportee',    '⏳ Reportée'),
        ('annulee',     '❌ Annulée'),
    ], string='Statut', default='planifiee', tracking=True)
    taux_realisation = fields.Integer(
        string='Taux de réalisation (%)', default=0
    )
    livrables = fields.Text(string='Livrables produits')
    observations = fields.Text(string='Observations / Écarts vs POA')
    document_ids = fields.Many2many(
        'ir.attachment', string='Documents livrables'
    )


class ResadeIndicateurProjet(models.Model):
    """P-EST-01 / MELA : Indicateurs du cadre logique"""
    _name = 'resade.indicateur.projet'
    _description = 'Indicateur MELA – Cadre logique projet'
    _order = 'niveau, sequence'

    sequence = fields.Integer(default=10)
    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True, ondelete='cascade'
    )
    niveau = fields.Selection([
        ('impact',    'Impact'),
        ('effet',     'Effet / Outcome'),
        ('produit',   'Produit / Output'),
        ('activite',  'Activité'),
    ], string='Niveau logframe', required=True, default='produit')
    name = fields.Char(string='Intitulé de l\'indicateur', required=True)
    formule = fields.Char(string='Formule de calcul')
    unite = fields.Char(string='Unité de mesure')
    valeur_baseline = fields.Float(string='Valeur de référence (Baseline)')
    cible_finale = fields.Float(string='Cible finale')
    valeur_actuelle = fields.Float(string='Valeur actuelle')
    taux_atteinte = fields.Float(
        string='Taux d\'atteinte (%)',
        compute='_compute_taux_atteinte', store=True
    )
    source_verification = fields.Char(string='Source de vérification')
    frequence_collecte = fields.Selection([
        ('mensuelle',    'Mensuelle'),
        ('trimestrielle','Trimestrielle'),
        ('semestrielle', 'Semestrielle'),
        ('annuelle',     'Annuelle'),
        ('fin_projet',   'Fin de projet'),
    ], string='Fréquence de collecte', default='trimestrielle')
    observations = fields.Text(string='Observations')

    @api.depends('cible_finale', 'valeur_baseline', 'valeur_actuelle')
    def _compute_taux_atteinte(self):
        for rec in self:
            cible_nette = rec.cible_finale - rec.valeur_baseline
            if cible_nette:
                rec.taux_atteinte = min(
                    (rec.valeur_actuelle - rec.valeur_baseline) / cible_nette * 100,
                    100.0
                )
            else:
                rec.taux_atteinte = 0.0


class ResadeRisqueProjet(models.Model):
    """Registre des risques projet – P-EST-01"""
    _name = 'resade.risque.projet'
    _description = 'Risque Projet – Registre (P-EST-01)'
    _order = 'score_risque desc'

    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True, ondelete='cascade'
    )
    name = fields.Char(string='Description du risque', required=True)
    categorie = fields.Selection([
        ('technique',    'Technique / Scientifique'),
        ('financier',    'Financier'),
        ('partenarial',  'Partenarial'),
        ('securite',     'Sécurité terrain'),
        ('ethique',      'Éthique'),
        ('operationnel', 'Opérationnel'),
    ], string='Catégorie')
    probabilite = fields.Selection([
        ('1', '1 – Faible'),
        ('2', '2 – Modérée'),
        ('3', '3 – Élevée'),
    ], string='Probabilité', default='2')
    impact = fields.Selection([
        ('1', '1 – Mineur'),
        ('2', '2 – Modéré'),
        ('3', '3 – Majeur'),
    ], string='Impact', default='2')
    score_risque = fields.Integer(
        string='Score', compute='_compute_score', store=True
    )
    niveau_risque = fields.Selection([
        ('faible',   '🟢 Faible'),
        ('moyen',    '🟡 Moyen'),
        ('eleve',    '🔴 Élevé'),
    ], string='Niveau', compute='_compute_score', store=True)
    mesure_mitigation = fields.Text(string='Mesure de mitigation')
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    statut = fields.Selection([
        ('actif',     'Actif'),
        ('surveille', 'Surveillé'),
        ('resolu',    'Résolu'),
    ], string='Statut', default='actif')

    @api.depends('probabilite', 'impact')
    def _compute_score(self):
        for rec in self:
            if rec.probabilite and rec.impact:
                score = int(rec.probabilite) * int(rec.impact)
                rec.score_risque = score
                if score <= 2:
                    rec.niveau_risque = 'faible'
                elif score <= 4:
                    rec.niveau_risque = 'moyen'
                else:
                    rec.niveau_risque = 'eleve'
            else:
                rec.score_risque = 0
                rec.niveau_risque = 'faible'


class ResadeRapportProjet(models.Model):
    """P-EST-02 : Rapports d'avancement et rapports bailleurs"""
    _name = 'resade.rapport.projet'
    _description = 'Rapport d\'avancement Projet – P-EST-02 (F-EST-02-01 à 05)'
    _inherit = ['mail.thread']
    _order = 'date_rapport desc'

    name = fields.Char(string='Intitulé du rapport', required=True)
    projet_id = fields.Many2one(
        'resade.projet', string='Projet', required=True, ondelete='cascade'
    )
    type_rapport = fields.Selection([
        ('mensuel',          '📅 Rapport mensuel interne'),
        ('trimestriel',      '📊 Rapport trimestriel bailleur'),
        ('semestriel',       '📈 Rapport semestriel bailleur'),
        ('annuel',           '📋 Rapport annuel bailleur'),
        ('final',            '🏁 Rapport final de projet'),
        ('incident',         '⚠️ Rapport d\'incident'),
    ], string='Type de rapport', required=True, default='trimestriel')
    periode_debut = fields.Date(string='Période du rapport : début')
    periode_fin = fields.Date(string='Période du rapport : fin')
    date_rapport = fields.Date(
        string='Date de production', default=fields.Date.today
    )
    date_soumission_bailleur = fields.Date(
        string='Date de soumission au bailleur'
    )
    contenu_narratif = fields.Html(
        string='Rapport narratif (F-EST-02-01 à F-EST-02-05)',
        help='Sections : Avancement activités – Indicateurs MELA – '
             'Difficultés – Actions correctives – Perspectives'
    )
    taux_execution_technique_rapport = fields.Float(
        string='Taux d\'exécution technique (%)'
    )
    taux_execution_financier_rapport = fields.Float(
        string='Taux d\'exécution financier (%)'
    )
    valide_par_rp = fields.Boolean(string='Validé par RP', tracking=True)
    valide_par_cdp = fields.Boolean(string='Validé par CDP', tracking=True)
    approuve_par_de = fields.Boolean(
        string='Approuvé par DE (si rapport bailleur)', tracking=True
    )
    soumis_au_bailleur = fields.Boolean(
        string='Soumis au bailleur', tracking=True
    )
    accuse_reception_bailleur = fields.Char(
        string='Accusé de réception bailleur'
    )
    document_ids = fields.Many2many(
        'ir.attachment', string='Rapport joint (PDF, tableaux Excel...)'
    )


class ResadePanierCommun(models.Model):
    """P-CD-03 : Panier commun et clé de répartition interne"""
    _name = 'resade.panier.commun'
    _description = 'Panier Commun RESADE – P-CD-03'
    _inherit = ['mail.thread']
    _order = 'exercice desc'

    name = fields.Char(
        string='Libellé', compute='_compute_name', store=True
    )
    exercice = fields.Integer(
        string='Exercice budgétaire',
        default=lambda self: fields.Date.today().year,
        required=True
    )
    cle_repartition = fields.Html(
        string='Clé de répartition interne',
        help='Formule validée annuellement par le CA sur proposition DE/CAF. '
             'Définit le % de prélèvement par projet selon type bailleur, durée, overhead.'
    )
    taux_prelevement_defaut = fields.Float(
        string='Taux de prélèvement par défaut (%)',
        help='% d\'overhead standard prélevé sur chaque projet non exception'
    )
    solde_panier = fields.Monetary(
        string='Solde panier commun (FCFA)',
        currency_field='currency_id', tracking=True
    )
    montant_alloue_support = fields.Monetary(
        string='Allocations fonctions support', currency_field='currency_id'
    )
    montant_alloue_institutionnel = fields.Monetary(
        string='Charges institutionnelles', currency_field='currency_id'
    )
    montant_reserve_audit = fields.Monetary(
        string='Provision audit externe', currency_field='currency_id'
    )
    valide_par_ca = fields.Boolean(
        string='Clé de répartition validée par CA', tracking=True
    )
    date_validation_ca = fields.Date(string='Date de validation CA')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    projet_ids = fields.One2many(
        'resade.projet', 'panier_commun_id', string='Projets contribuants'
    )
    document_ids = fields.Many2many(
        'ir.attachment', string='PV CA, politique overhead, arrêté comptable...'
    )

    @api.depends('exercice')
    def _compute_name(self):
        for rec in self:
            rec.name = f'Panier Commun {rec.exercice}'
