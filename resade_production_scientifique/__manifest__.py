# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Production Scientifique, Communication & Dissémination (Carnet I)',
    'version': '18.0.1.0.0',
    'summary': 'Gestion de la production scientifique, publications, communication et dissémination — RESADE',
    'description': """
Module RESADE — Carnet I
========================
Ce module couvre les 3 modules du Carnet I du Manuel de Procédures RESADE v2.0 (2026) :

Module 01 — Processus de Recherche
    • P-CI-01 : Conception et validation d'un protocole de recherche
    • P-CI-02 : Conduite des études et enquêtes terrain
    • P-CI-03 : Gestion des données de recherche

Module 02 — Publication Scientifique
    • P-CI-04 : Rédaction et revue interne des articles scientifiques
    • P-CI-05 : Soumission à des revues scientifiques indexées

Module 03 — Communication Institutionnelle
    • P-CI-06 : Communication interne (réunions, groupes de travail, rapports)
    • P-CI-07 : Participation aux événements scientifiques
    • P-CI-08 : Gestion du site web et de la bibliothèque en ligne
    • P-CI-09 : Organisation d'événements scientifiques
    • P-CI-10 : Relations presse et communication externe

Conforme aux matrices RACI & AECD du Manuel RESADE.
    """,
    'author': 'IT PROJET SARL — Projet ERP Odoo RESADE',
    'website': 'https://it-projet.com',
    'category': 'RESADE/Scientifique',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'project',
        'resade_projet_h',
        'hr',
        'calendar',
        'contacts',
    ],
    'data': [
        # Sécurité
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        # Données de référence
        'data/sequence_data.xml',
        'data/stage_data.xml',
        # Vues
        'views/domaine_recherche_views.xml', 
        'views/protocole_recherche_views.xml',
        'views/etude_enquete_views.xml',
        'views/donnees_recherche_views.xml',
        'views/article_scientifique_views.xml',
        'views/soumission_revue_views.xml',
        'views/evenement_scientifique_views.xml',
        'views/communication_interne_views.xml',
        'views/bibliotheque_views.xml',
        'views/presse_communication_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],
}
