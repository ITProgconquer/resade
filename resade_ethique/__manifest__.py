# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Éthique, Déontologie et Gestion des Risques (Carnet J)',
    'version': '18.0.1.0.0',
    'category': 'RESADE',
    'summary': 'Éthique de la recherche, déontologie/conformité et gestion des risques institutionnels – Conforme Manuel RESADE Carnet J',
    'description': """
        Module RESADE – Carnet J : Éthique, Déontologie et Gestion des Risques
        =====================================================================
        Conforme au Manuel de Procédures RESADE Volume 3 – Carnet J (v2.0 – 2026)

        MODULE 01 – Éthique de la recherche :
        - P-ER-01 : Soumission au Comité pour la recherche en santé (CERS)
        - P-ER-02 : Soumission au visa statistique (INSD)
        - P-ER-03 : Soumission aux autorités sanitaires (ANRP, ministère)
        - P-ER-04 : Soumission au comité d'éthique institutionnel
        - P-ER-05 : Consentement éclairé des participants

        MODULE 02 – Déontologie et conformité :
        - P-DC-01 : Code de conduite et déontologie (signalements et manquements)
        - P-DC-02 : Gestion des conflits d'intérêts (recherche et marchés)
        - P-DC-03 : Protection des données personnelles (registre des traitements)

        MODULE 03 – Gestion des risques institutionnels :
        - P-GRI-01 : Identification et évaluation des risques (registre des risques)
        - P-GRI-02 : Plans de mitigation et de continuité des activités

        Groupes sécurité :
          Déclarant -> Chargé Éthique/Conformité (CRSP) -> Directeur Exécutif (DE) -> Conseil d'Administration (CA/Admin)

        Remarque : cette première version couvre les modèles, workflows, sécurité et
        vues de gestion des 10 processus du Carnet J. Les modèles d'impression PDF
        (rapports) ne sont pas inclus dans cette v1 et pourront être ajoutés dans une
        itération suivante si nécessaire.
    """,
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        # Sécurité
        'security/resade_ethique_security.xml',
        'security/ir.model.access.csv',
        # Données de référence
        'data/resade_ethique_sequence.xml',
        # Vues – Module 01 : Éthique de la recherche
        'views/resade_ethique_soumission_views.xml',
        'views/resade_ethique_consentement_views.xml',
        # Vues – Module 02 : Déontologie et conformité
        'views/resade_ethique_conflit_views.xml',
        'views/resade_ethique_signalement_views.xml',
        'views/resade_ethique_traitement_views.xml',
        # Vues – Module 03 : Gestion des risques institutionnels
        'views/resade_ethique_risque_views.xml',
        'views/resade_ethique_plan_continuite_views.xml',
        # Menus (toujours en dernier)
        'views/resade_ethique_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
