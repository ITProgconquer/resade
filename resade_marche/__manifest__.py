{
    'name': 'RESADE - Passation et Gestion des Marches',
    'version': '18.0.6.2.0',
    'summary': 'Passation et Gestion des Marches RESADE – v5 (P-PTM-02/03/04/05 complétés)',
    'description': """
Module COMPLET de gestion de la passation et execution des marches RESADE.
Conforme au Manuel de Procedures RESADE Volume 2 (Carnets D et E) Version 2.0 2026.

CARNET D - PASSATION DES MARCHES :
  MODULE 01 - Cadre et instances
    P-CIP-01 : Commission Attribution des Marches CAM - Composition et fonctionnement
    P-CIP-02 : Mise a jour des seuils de passation
    P-ESB-01 : Fiche Expression des Besoins FEB - Piece justificative N1

  MODULE 02 - Procedures par type
    P-PTM-01 : Entente directe Gre a gre <=2 000 000 FCFA - 3 cotations obligatoires
    P-PTM-02 : Consultation restreinte 2M-10M FCFA
    P-PTM-03 : Appel offres ouvert 10M-50M FCFA + ANO bailleur si >50M
    P-PTM-04 : Recrutement consultant individuel
    P-PTM-05 : Services specialises recherche enquetes

  MODULE 03 - Deontologie et archivage
    P-DA-01 : Gestion conflits interets - declaration et recusation
    P-DA-02 : Archivage GED des dossiers de passation

CARNET E - EXECUTION DES MARCHES :
  MODULE 01 - Reception et certification
    P-RC-01 : Reception fournitures - PVR quantitatif + qualitatif + test
    P-RC-02 : Certification factures - registre + checklist 8 mentions legales
    P-RC-03 : Reception prestations intellectuelles - ASF + grille valideurs + cycles revision

  MODULE 02 - Paiement et liquidation
    P-PL-01 : Paiement fournisseurs - dossier complet + double signature DE+CAF + comptabilisation SAGE
    P-PL-02 : Paiement honoraires consultants - tranches + verification fiscale + retenue source

  MODULE 03 - Suivi et cloture
    P-SCM-01 : Tableau de bord KPI - calcul automatique 12 indicateurs
    P-SCM-02 : Cloture et archivage du dossier marche

Groupes securite (organigramme RESADE 2025):
  Demandeur -> Chef departement -> Membre CAM -> CAF -> Directeur Executif -> Admin
    """,
    'category': 'RESADE',
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'account', 'analytic', 'mail', 'resade_budget','website'],
    'data': [
        # Securite
        'security/resade_marche_security.xml',
        'security/ir.model.access.csv',
        # Donnees reference
        'data/resade_marche_sequence.xml',
        'data/resade_marche_data.xml',
        # Vues de base (lignes et offres)
        'views/resade_marche_line_views.xml',
        # Vue principale marche (formulaire + onglets complets)
        'views/resade_marche_views.xml',
        # Vues CAM P-CIP-01
        'views/resade_marche_cam_views.xml',
        # Vues Carnet E : PVR P-RC-01 + ASF P-RC-03 + Factures P-RC-02 + TDB P-SCM-01
        'views/resade_marche_execution_views.xml',
        # Vues Paiement : FEB P-ESB-01 + P-PL-01 + P-PL-02 + KPI P-SCM-01
        'views/resade_marche_paiement_views.xml',
        # Vues fournisseurs
        'views/resade_fournisseur_views.xml',
        # Wizards
        'wizard/wizard_cloture_marche_views.xml',
        # Menus (toujours en dernier)
        'views/resade_marche_menus.xml',
        # Rapports PDF
        'report/resade_marche_report.xml',
        'report/resade_marche_report_template.xml',
        # Emails
        'data/mail_template_invitation.xml',
        'views/templates_portal.xml',
    ],

    'controllers': ['controllers/portal.py'],

    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
