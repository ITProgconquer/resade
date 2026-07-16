# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Carnet H : Cycle des Projets et Partenariats',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Gestion du cycle des projets et partenariats – Carnet H / P-MRV / P-CD / P-EST / P-CC',
    'description': """
        Module RESADE – Carnet H : Gestion du Cycle des Projets et des Partenariats
        ===========================================================================
        Conforme au Manuel de Procédures RESADE Volume 3 – Carnet H (v2.0 – 2026)
        Plan Stratégique RESADE 2026-2030 – Axes 1 et 2

        MODULE 01 : MOBILISATION DES RESSOURCES ET VEILLE (MRV)
        - P-MRV-01 : Veille sur les appels à projets et opportunités de financement
        - P-MRV-02 : Rédaction et soumission des propositions techniques et financières

        MODULE 02 : CONTRACTUALISATION ET DÉMARRAGE (CD)
        - P-CD-01 : Négociation et signature des conventions / contrats bailleurs
        - P-CD-02 : Démarrage de projet (kick-off)
        - P-CD-03 : Gestion du panier commun et clé de répartition interne

        MODULE 03 : EXÉCUTION ET SUIVI TECHNIQUE (EST)
        - P-EST-01 : Suivi technique de l'exécution des activités de projet
        - P-EST-02 : Reporting technique aux bailleurs
        - P-EST-03 : Gestion des partenaires et sous-traitants

        MODULE 04 : CLÔTURE ET CAPITALISATION (CC)
        - P-CC-01 : Clôture technique et financière du projet
        - P-CC-02 : Revue de fin de projet et rapport de leçons apprises

        Formulaires couverts :
        F-MRV-01-01 à 07, F-MRV-02-01 à 08,
        F-CD-01-01 à 05, F-CD-02-01 à 07,
        F-EST-01-01 à 06, F-EST-02-01 à 05, F-EST-03-01 à 08,
        F-CC-01-01 à 04, F-CC-02-01 à 02
    """,
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': [
        'base', 'hr', 'account', 'mail', 'project',
    ],
    'data': [
        'security/resade_projet_security.xml',
        'security/ir.model.access.csv',
        'data/resade_projet_sequence.xml',
        'views/resade_opportunite_views.xml',
        'views/resade_proposition_views.xml',
        'views/resade_projet_views.xml',
        'views/resade_partenaire_views.xml',
        'views/resade_cloture_views.xml',
        'views/resade_projet_menus.xml',
        'report/resade_projet_reports.xml',
        'report/resade_projet_report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
