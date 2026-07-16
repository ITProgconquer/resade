# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Gestion des Missions et Déplacements',
    'version': '18.0.3.0.0',
    'category': 'Human Resources',
    'summary': 'Gestion des missions et déplacements – Carnet G / P-GMD-01/02/03 – Couverture 100%',
    'description': """
        Module RESADE – Gestion des Missions et Déplacements
        =====================================================
        Conforme au Manuel de Procédures RESADE Volume 2 – Carnet G – Module 03 (v2.0 – 2026)
        Couverture 100% du Carnet G (v3.0 – ajout F-GMD-02-04)

        Processus couverts :
        - P-GMD-01 : Planification et autorisation d'une mission
        - P-GMD-02 : Exécution et rapport de mission
        - P-GMD-03 : Justification et remboursement des frais de mission

        Formulaires RESADE implémentés (100%) :
        - RESADE-F-GMD-01-01 : TDR de mission
        - RESADE-F-GMD-01-02 : Note de justification de mission
        - RESADE-F-GMD-01-03 : Ordre de mission (imprimable PDF)
        - RESADE-F-GMD-01-04 : Demande d'avance sur frais (détail groupe)
        - RESADE-F-GMD-01-05 : Grille des taux per diem et indemnités
        - RESADE-F-GMD-01-06 : Registre des ordres de mission (liste Odoo)
        - RESADE-F-GMD-02-01 : Canevas rapport de mission
        - RESADE-F-GMD-02-02 : Fiche décompte frais réels
        - RESADE-F-GMD-02-03 : Carnet de bord véhicule (pièce jointe)
        - RESADE-F-GMD-02-04 : Registre des missions exécutées ← NOUVEAU v3
        - RESADE-F-GMD-02-05 : Checklist conformité dossier retour

        Workflow complet :
        Brouillon → Validé Chef Dépt → Approuvé CAF (visa budgétaire)
        → Autorisé DE (OM signé, avis PCA si stratégique) → Avance décaissée
        → En mission [Registre F-GMD-02-04 créé automatiquement]
        → Rapport soumis → Rapport approuvé DE [Archivage GED confirmé AA]
        → Justification soumise → Remboursement/reversement validé CAF → Clôturé

        Nouveautés v3 :
        - Modèle resade.registre.mission (F-GMD-02-04)
        - Création automatique dans le registre au départ en mission
        - Confirmation archivage GED par l'AA (déclencheur P-GMD-03)
        - Vue liste exportable (registre chronologique)
        - Menu dédié AA pour archivages GED à confirmer
    """,
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'account',
        'mail',
        'hr_expense',
        'resade_budget',
    ],
    'data': [
        'security/resade_mission_security.xml',
        'security/ir.model.access.csv',
        'data/resade_mission_sequence.xml',
        'data/resade_mission_data.xml',
        'views/resade_mission_views.xml',
        'views/resade_taux_perdiem_views.xml',
        'views/resade_mission_budget_views.xml',
        'views/resade_registre_mission_views.xml',
        'views/resade_mission_menus.xml',
        'report/resade_mission_report.xml',
        'report/resade_mission_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
