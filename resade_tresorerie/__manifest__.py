# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Trésorerie et Banque (Carnet F)',
    'version': '18.0.2.0.0',
    'category': 'RESADE',
    'summary': "Trésorerie, caisse, banque et rapprochement RESADE — conforme au Carnet F "
               "(Modules 03 Trésorerie et Banque), sur socle Odoo Accounting Enterprise.",
    'description': """
        Module RESADE – Trésorerie et Banque (Carnet F, Module 03)
        =====================================================
        Conforme au Manuel de Procédures RESADE Volume 2 – Carnet F : Gestion
        Comptable et Trésorerie (v2.0 – 2026), Module 03 « Trésorerie et
        Banque » :
          - P-TB-01 : Gestion de la caisse (petite caisse)
          - P-TB-02 : Gestion des comptes bancaires

        PRINCIPE D'ARCHITECTURE
        ─────────────────────────────────────────────────────
        Ce module NE réinvente PAS la mécanique comptable : écritures,
        multi-devises, rapprochement technique, clôtures et états financiers
        restent nativement gérés par Odoo Accounting Enterprise. Ce module
        ajoute UNIQUEMENT la couche de contrôle interne et de gouvernance
        propre à RESADE, absente d'Odoo en standard :
          - Plafonds réglementaires de caisse (150 000 FCFA global,
            50 000 FCFA/décaissement, seuil d'autorisation DE à 20 000 FCFA,
            seuil de reconstitution à 30 000 FCFA) et blocage si dépassement ;
          - Workflow d'autorisation de décaissement de caisse selon le
            montant (AC → CAF → DE si nécessaire), avec génération de la
            pièce comptable réelle (account.move / account.payment) ;
          - Contrôle physique hebdomadaire de caisse par le CAF
            (RESADE-F-TB-01-02) avec écart documenté ;
          - Bordereau mensuel de reconstitution de caisse
            (RESADE-F-TB-01-03), workflow AC → CAF → DE ;
          - Rapprochement bancaire mensuel (RESADE-F-TB-02-01) avec RACI
            conforme au manuel (CAF valide, DE seulement informé) et suivi
            du délai réglementaire (≤ J+7) ;
          - Gestion des comptes en devises et traçabilité des décisions de
            conversion BCEAO (CAF + DE) ;
          - Tableau de trésorerie prévisionnelle à horizons fixes 30/60/90
            jours (RESADE-F-TB-02-02), alimenté par les engagements réels
            resade_budget ;
          - KPI réglementaires : taux de contrôles hebdomadaires, taux de
            décaissements avec pièce justificative, taux de rapprochements
            produits dans les délais, écart net de rapprochement.

        NOTE DE GOUVERNANCE — SAGE → ODOO ACCOUNTING
        ─────────────────────────────────────────────────────
        Le Carnet F (texte validé) fait référence au paramétrage et à la
        comptabilisation dans SAGE. RESADE ayant fait le choix d'exploiter
        nativement Odoo Accounting Enterprise, ce module comptabilise
        directement dans Odoo (account.move / account.payment) et non plus
        dans SAGE. Une mise à jour formelle du Carnet F (remplacement des
        mentions "SAGE" par "Odoo Accounting Enterprise") est recommandée
        pour que le manuel reflète l'outil réellement utilisé.
    """,
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'account', 'analytic', 'resade_budget'],
    'data': [
        # Sécurité
        'security/resade_tresorerie_security.xml',
        'security/ir.model.access.csv',
        # Données
        'data/resade_tresorerie_sequence.xml',
        'data/resade_tresorerie_cron.xml',
        # Vues
        'views/resade_tresorerie_compte_views.xml',
        'views/resade_tresorerie_caisse_views.xml',
        'views/resade_tresorerie_controle_caisse_views.xml',
        'views/resade_tresorerie_reconstitution_views.xml',
        'views/resade_tresorerie_previsionnel_views.xml',
        'views/resade_tresorerie_rapprochement_views.xml',
        'views/resade_tresorerie_devise_views.xml',
        'views/resade_tresorerie_tdb_views.xml',
        'views/resade_tresorerie_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
