from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResadeEthiqueSignalement(models.Model):

    """
    Processus P-DC-01 : Code de conduite et déontologie des membres et collaborateurs
    Manuel RESADE - Carnet J - Module 02 : Déontologie et conformité

    Gère le dispositif de signalement (whistleblowing) des manquements au code
    de conduite institutionnel (harcèlement, fraude, plagiat, discrimination,
    abus de pouvoir...) et le suivi des procédures disciplinaires associées.

    Le signalement peut être anonyme (signalant_id laissé vide, canal dédié).

    Circuit :
    1. Réception du signalement                      -> recu
    2. Instruction par le référent déontologie        -> en_instruction
    3. Décision (classement, sanction...)             -> decision_rendue
    4. Clôture                                        -> cloture
    """
    _name = 'resade.ethique.signalement'
    _description = "Signalement code de conduite / déontologie (P-DC-01)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_signalement desc'

    name = fields.Char(string='Réf. signalement', required=True, readonly=True, copy=False,
                        default=lambda self: _('Nouveau'))

    date_signalement = fields.Date(string='Date de signalement', default=fields.Date.context_today, required=True)

    canal = fields.Selection([
        ('hierarchie', 'Voie hiérarchique'),
        ('email_dedie', 'Adresse email dédiée'),
        ('boite_anonyme', 'Boîte de signalement anonyme'),
        ('autre', 'Autre canal'),
    ], string='Canal de signalement', required=True)

    anonyme = fields.Boolean(
        string='Signalement anonyme',
        default=False,
        readonly=True,  # Empêche de le modifier après création
        help="Une fois le signalement soumis, l'anonymat ne peut plus être modifié."
    )
    
    signalant_id = fields.Many2one(
        'hr.employee',
        string='Signalant',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        help="Masqué si anonyme."
    )

    categorie = fields.Selection([
        ('harcelement', 'Harcèlement'),
        ('fraude', 'Fraude'),
        ('plagiat', 'Plagiat'),
        ('discrimination', 'Discrimination'),
        ('abus_pouvoir', 'Abus de pouvoir'),
        ('autre', 'Autre manquement'),
    ], string='Catégorie du manquement', required=True, tracking=True)

    description = fields.Text(string='Description des faits', required=True)

    gravite = fields.Selection([
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('elevee', 'Élevée'),
        ('critique', 'Critique'),
    ], string='Gravité estimée', tracking=True)

    instructeur_id = fields.Many2one('hr.employee', string='Instruit par (référent déontologie)')
    date_debut_instruction = fields.Date(string="Date de début d'instruction")

    decision = fields.Selection([
        ('classe_sans_suite', 'Classé sans suite'),
        ('sanction_mineure', 'Sanction mineure'),
        ('sanction_majeure', 'Sanction majeure'),
        ('transmission_justice', 'Transmission aux autorités judiciaires'),
    ], string='Décision', tracking=True)
    motivation_decision = fields.Text(string='Motivation de la décision')
    date_cloture = fields.Date(string='Date de clôture')

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('recu', 'Reçu'),
        ('en_instruction', 'En instruction'),
        ('decision_rendue', 'Décision rendue'),
        ('cloture', 'Clôturé'),
    ], string='Statut', default='brouillon', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('resade.ethique.signalement') or _('Nouveau')

        # On vérifie si au moins un des signalements est anonyme
        is_anonyme = any(vals.get('anonyme') for vals in vals_list)
        
        if is_anonyme:
            # On force la création avec l'utilisateur administrateur (ID 2) et sudo
            # Cela écrase l'utilisateur réel dans le champ create_uid
            admin_user = self.env.ref('base.user_admin')
            records = super(ResadeEthiqueSignalement, self.with_user(admin_user).sudo()).create(vals_list)
            
            # On nettoie les messages de suivi pour enlever toute trace
            for rec in records:
                if rec.anonyme:
                    rec.message_ids.unlink() # Supprime les messages "created" et "Brouillon - Reçu"
            return records
        
        return super().create(vals_list)

    # ✅ ANONYMAT : Empecher les messages du chatter de révéler le créateur
    def message_post(self, **kwargs):
        if self.anonyme:
            return super(ResadeEthiqueSignalement, self.sudo()).message_post(**kwargs)
        return super().message_post(**kwargs)

    def action_soumettre(self):
        """Soumet le signalement (transition Brouillon → Reçu)"""
        for rec in self:
            if rec.anonyme:
                rec.signalant_id = False
                
                # On change l'état en tant qu'admin ET on désactive le tracking (mail_thread) temporairement
                admin = self.env.ref('base.user_admin')
                
                # On utilise with_context(tracking_disable=True) pour empêcher Odoo de créer le message
                rec.with_user(admin).sudo().with_context(tracking_disable=True).write({'state': 'recu'})
                
                # Ceinture et bretelles : on supprime les messages restants
                rec.sudo().message_ids.unlink()
            else:
                rec.write({'state': 'recu'})
        return True

    def action_mettre_en_instruction(self):
        self._check_crsp_or_above()
        self.write({'state': 'en_instruction', 'date_debut_instruction': fields.Date.context_today(self)})

    def action_enregistrer_decision(self):
        if not self.env.user.has_group('resade_ethique.group_resade_ethique_de'):
            raise UserError(_(
                "Seul le Directeur Exécutif (ou l'Administrateur) peut enregistrer la décision "
                "d'un signalement (sanction, classement sans suite, transmission judiciaire)."
            ))
        for rec in self:
            if not rec.decision:
                raise UserError(_(
                    "Sélectionnez une décision avant de l'enregistrer."
                ))
        self.write({'state': 'decision_rendue'})

    def action_cloturer(self):
        self._check_crsp_or_above()
        self.write({'state': 'cloture', 'date_cloture': fields.Date.context_today(self)})

    def _check_crsp_or_above(self):
        if not self.env.user.has_group('resade_ethique.group_resade_ethique_crsp'):
            raise UserError(_(
                "Seul le Chargé Éthique & Conformité (référent déontologie), le Directeur Exécutif "
                "ou l'Administrateur peuvent instruire ou clôturer un signalement."
            ))