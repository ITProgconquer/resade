# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Courrier & Archivage Documentaire (Carnet G – Modules 01 & 02)',
    'version': '18.0.2.0.0',
    'category': 'RESADE',
    'summary': 'Courrier entrant/sortant, courriels institutionnels, classement physique, GED et numérisation – Conforme Manuel RESADE Carnet G Modules 01 & 02',
    'description': """
        Module RESADE – Gestion du Courrier et Archivage Documentaire
        =====================================================
        Conforme au Manuel de Procédures RESADE Volume 2 – Carnet G – Modules 01 et 02 (v2.0 – 2026)

        MODULE 01 — Gestion du courrier (couverture 100%) :
        - P-GC-01 : Gestion du courrier entrant (physique et électronique)
        - P-GC-02 : Gestion du courrier sortant (physique et électronique)
        - P-GC-03 : Gestion des courriels institutionnels

        MODULE 02 — Classement et archivage (couverture 100%) :
        - P-CA-01 : Plan de classement et archivage physique
        - P-CA-02 : Archivage numérique et Gestion Électronique des Documents (GED)
        - P-CA-03 : Numérisation des documents physiques stratégiques

        Formulaires RESADE implémentés (extrait) :
        - RESADE-F-GC-01-01/02/03, F-GC-02-01/02/03, F-GC-03-02/03
        - RESADE-F-CA-01-01 à 01-08 (classeurs, DUA, sort final, destruction)
        - RESADE-F-CA-02-01 à 02-06 (tableau de bord GED, droits d'accès, audit)
        - RESADE-F-CA-03-01 à 03-05 (liste prioritaire, contrôle qualité, registre)

        Workflow Courrier ENTRANT (P-GC-01) :
        Reçu → Enregistré/numérisé → Transmis au DE → Affecté (instructions dispatch)
        → Dispatché aux destinataires → Émargé → Archivé GED (≤ 48h)

        Workflow Courrier SORTANT (P-GC-02) :
        Brouillon → Visé AA → Visé CAF → Signé DE/PCA → Numéroté
        → Envoyé (preuve d'envoi) → Archivé GED (≤ 48h)

        Workflow Courriel institutionnel (P-GC-03) :
        Émis/Reçu → Trié (A/I/T/E) → Accusé de réception (si requis) → Traité
        → Classifié VPIA → Archivé GED (≤ 48h) → Nettoyage mensuel

        Workflow Classeur physique (P-CA-01) :
        Actif (classement courant) → Pré-archivage (DUA âge actif échue)
        → Sort final à décider (commission AA+CAF+DE) → Archivé définitivement / Détruit (PV signé)

        Workflow Document GED (P-CA-02) :
        À archiver → Vérification qualité (≤24h) → Archivé en GED (≤48h, droits vérifiés CSI)

        Workflow Numérisation (P-CA-03) :
        Liste prioritaire (P1/P2/P3, validée CAF+DE) → Numérisation (≥300dpi, PDF/A)
        → Contrôle qualité (AA+CSI) → Versé en GED (lien P-CA-02)

        Conforme aux matrices RACI & AECD du Manuel RESADE (Carnet G, Modules 01 et 02).
    """,
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        # Sécurité
        'security/resade_courrier_security.xml',
        'security/ir.model.access.csv',
        # Données de référence
        'data/resade_courrier_sequence.xml',
        'data/resade_courrier_data.xml',
        # Vues Module 01 : Courrier
        'views/resade_courrier_entrant_views.xml',
        'views/resade_courrier_sortant_views.xml',
        'views/resade_courriel_institutionnel_views.xml',
        'views/resade_courrier_referentiels_views.xml',
        # Vues Module 02 : Classement et archivage
        'views/resade_classeur_views.xml',
        'views/resade_ged_views.xml',
        'views/resade_numerisation_views.xml',
        # Menus (toujours en dernier)
        'views/resade_courrier_menus.xml',
        # Rapports PDF
        'report/resade_courrier_report_templates.xml',
        'report/resade_courrier_reports.xml',
    ],
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
