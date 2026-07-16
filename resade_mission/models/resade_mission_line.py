# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResadeMissionLine(models.Model):
    _name = 'resade.mission.line'
    _description = 'Ligne de frais – Mission RESADE (RESADE-F-GMD-01-04 / F-GMD-02-02)'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    mission_id = fields.Many2one(
        'resade.mission', string='Mission',
        required=True, ondelete='cascade'
    )
    type_frais = fields.Selection([
        ('perdiem',       'Per diem journalier'),
        ('hebergement',   'Hébergement'),
        ('transport',     'Transport / Billet'),
        ('carburant',     'Carburant (km)'),
        ('communication', 'Communication'),
        ('autre',         'Autre frais'),
    ], string='Type de frais', required=True, default='perdiem')

    # Le per diem est FORFAITAIRE (Manuel RESADE) : une fois le nombre de
    # nuitées approuvé par le DE et le montant décaissé, il est intégralement
    # acquis au missionnaire — aucun justificatif, aucun trop-perçu calculé
    # sur cette ligne. Les autres types de frais (transport, péages, etc.)
    # restent sur le circuit classique « avance de la poche du missionnaire,
    # remboursement sur justificatif réel au retour ».
    est_forfaitaire = fields.Boolean(
        string='Forfaitaire (per diem)', compute='_compute_est_forfaitaire', store=True,
        help="Vrai uniquement pour les lignes de type Per diem. Une ligne forfaitaire "
             "n'entre jamais dans le calcul du trop-perçu / complément : le montant dû "
             "est figé dès l'approbation du nombre de nuitées par le DE."
    )

    description = fields.Char(string='Description', required=True)

    # Quantité / Jours prévus (demande initiale du missionnaire)
    quantite = fields.Float(string='Quantité / Jours prévus', default=1.0)
    taux_unitaire = fields.Monetary(
        string='Taux unitaire (FCFA)',
        currency_field='currency_id'
    )
    montant_estime = fields.Monetary(
        string='Montant estimé',
        compute='_compute_montant_estime', store=True,
        currency_field='currency_id'
    )

    # ─────────────────────────────────────────────
    # PER DIEM (forfaitaire) — nuitées APPROUVÉES PAR LE DE
    # Manuel P-GMD-01 étape 5 : le DE peut réduire le nombre de nuitées
    # demandées. Le montant per diem dû suit alors ce nombre approuvé,
    # pas la demande initiale du missionnaire ni une quelconque "dépense
    # réelle" — il n'y a pas de justificatif à fournir pour le per diem.
    # ─────────────────────────────────────────────
    quantite_approuvee_de = fields.Float(
        string='Nuitées / jours approuvés (DE)', default=0.0,
        help="Pour une ligne Per diem : nombre de nuitées validées par le Directeur "
             "Exécutif à l'étape 5 (peut être inférieur à la demande initiale). "
             "Le montant forfaitaire dû = ce nombre × le taux unitaire."
    )
    montant_forfaitaire_du = fields.Monetary(
        string='Montant forfaitaire dû (DE)', compute='_compute_montant_forfaitaire_du', store=True,
        currency_field='currency_id',
        help="Montant définitivement acquis au missionnaire pour cette ligne forfaitaire, "
             "calculé sur la base des nuitées approuvées par le DE (pas sur une dépense réelle)."
    )

    # ─────────────────────────────────────────────
    # FRAIS ANNEXES (avance personnelle, remboursement sur justificatif réel)
    # ─────────────────────────────────────────────
    quantite_reelle = fields.Float(
        string='Quantité réelle (jours/km/unités effectifs)',
        default=0.0,
        help='Sert uniquement aux frais annexes non forfaitaires (transport, carburant...). '
             'Sans objet pour une ligne Per diem.'
    )
    montant_reel = fields.Monetary(
        string='Montant réel (justifié)',
        compute='_compute_montant_reel', store=True,
        currency_field='currency_id',
        help='Pour une ligne forfaitaire (per diem) : toujours égal au montant forfaitaire dû. '
             'Pour une ligne classique : calculé sur quantité réelle ou saisie manuelle, '
             'sur présentation de justificatif (péage, reçu, billet...).'
    )
    montant_reel_manuel = fields.Monetary(
        string='Montant réel (saisie manuelle)',
        currency_field='currency_id',
        help='Montant réel saisi manuellement sur justificatif (prioritaire sur le calcul automatique). '
             'Sans objet pour une ligne Per diem (forfaitaire).'
    )
    piece_justificative = fields.Char(
        string='N° pièce justificative / référence',
        help="Obligatoire pour les frais annexes (péage, reçu...). Sans objet pour le per diem, "
             "qui ne nécessite aucun justificatif."
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='mission_id.currency_id',
        store=True
    )

    # Lien avec grille per diem (RESADE-F-GMD-01-05)
    taux_perdiem_id = fields.Many2one(
        'resade.taux.perdiem',
        string='Référence grille taux (F-GMD-01-05)',
        domain="[('zone', '=', parent.zone_mission)]"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('type_frais', 'perdiem') == 'perdiem' and vals.get('mission_id'):
                mission = self.env['resade.mission'].browse(vals['mission_id'])
                duree = mission.duree_jours or 1
                # Si la quantité prévue n'a pas été explicitement renseignée
                # (valeur par défaut 1.0), on la cale sur la durée prévue de
                # la mission (Date retour - Date départ + 1).
                if not vals.get('quantite') or vals.get('quantite') == 1.0:
                    vals['quantite'] = duree
                # Idem pour les nuitées approuvées par le DE : par défaut on
                # part du principe que tout ce qui est prévu est approuvé ;
                # le DE reste libre de réduire ce nombre à l'étape 5 s'il le
                # juge nécessaire (P-GMD-01).
                if not vals.get('quantite_approuvee_de'):
                    vals['quantite_approuvee_de'] = vals['quantite']
        return super().create(vals_list)

    @api.onchange('type_frais', 'mission_id')
    def _onchange_type_frais_perdiem_defaults(self):
        """Pré-remplit automatiquement la quantité prévue et les nuitées
        approuvées (DE) sur la durée prévue de la mission dès qu'une ligne
        Per diem est ajoutée/modifiée. Le DE garde la main pour corriger
        manuellement la valeur ensuite (ex. réduction de nuitées)."""
        for line in self:
            if line.type_frais == 'perdiem' and line.mission_id:
                duree = line.mission_id.duree_jours or 1
                if not line.quantite or line.quantite == 1.0:
                    line.quantite = duree
                if not line.quantite_approuvee_de:
                    line.quantite_approuvee_de = line.quantite

    @api.depends('type_frais')
    def _compute_est_forfaitaire(self):
        for line in self:
            line.est_forfaitaire = (line.type_frais == 'perdiem')

    @api.depends('quantite', 'taux_unitaire')
    def _compute_montant_estime(self):
        for line in self:
            line.montant_estime = line.quantite * line.taux_unitaire

    @api.depends('quantite_approuvee_de', 'taux_unitaire', 'est_forfaitaire')
    def _compute_montant_forfaitaire_du(self):
        for line in self:
            if line.est_forfaitaire:
                line.montant_forfaitaire_du = line.quantite_approuvee_de * line.taux_unitaire
            else:
                line.montant_forfaitaire_du = 0.0

    @api.depends(
        'quantite_reelle', 'taux_unitaire', 'montant_reel_manuel',
        'est_forfaitaire', 'montant_forfaitaire_du'
    )
    def _compute_montant_reel(self):
        """
        Ligne forfaitaire (per diem) : le "réel" est TOUJOURS le montant
        forfaitaire dû (figé à l'approbation DE) — jamais une dépense
        constatée après coup, puisqu'aucun justificatif n'est exigé.

        Ligne classique (frais annexes) : calcul automatique si quantité
        réelle renseignée, sinon montant manuel saisi sur justificatif.
        """
        for line in self:
            if line.est_forfaitaire:
                line.montant_reel = line.montant_forfaitaire_du
            elif line.montant_reel_manuel:
                line.montant_reel = line.montant_reel_manuel
            elif line.quantite_reelle and line.taux_unitaire:
                line.montant_reel = line.quantite_reelle * line.taux_unitaire
            else:
                line.montant_reel = 0.0

    @api.onchange('taux_perdiem_id', 'type_frais')
    def _onchange_taux_perdiem(self):
        """Auto-remplissage depuis la grille des taux (RESADE-F-GMD-01-05)"""
        if self.taux_perdiem_id:
            if self.type_frais == 'perdiem':
                self.taux_unitaire = self.taux_perdiem_id.perdiem_journalier
            elif self.type_frais == 'hebergement':
                self.taux_unitaire = self.taux_perdiem_id.plafond_hebergement
            elif self.type_frais == 'carburant':
                self.taux_unitaire = self.taux_perdiem_id.taux_carburant_km
