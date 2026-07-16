# -*- coding: utf-8 -*-
{
    'name': 'RESADE – Budget (Carnet C)',
    'version': '18.0.1.0.0',
    'category': 'RESADE',
    'summary': 'Élaboration, adoption, exécution et suivi du budget – Conforme Manuel RESADE Carnet C',
    'description': """
        Module RESADE – Budget
        =====================================================
        Conforme au Manuel de Procédures RESADE Volume 2 – Carnet C (v2.0 – 2026)

        Processus couverts (couverture 100%) :
        MODULE 01 – Élaboration et adoption du budget
        - P-EAB-01 : Élaboration du budget annuel (POA)
        - P-EAB-02 : Élaboration des budgets de projets bailleurs

        MODULE 02 – Exécution et suivi budgétaire
        - P-ESB-01 : Engagement des dépenses et niveaux d'autorisation (FEB)
        - P-ESB-02 : Suivi budgétaire mensuel et reporting interne
        - P-ESB-03 : Révision et réajustement budgétaire

        Formulaires RESADE implémentés :
        - RESADE-F-EAB-01-01 : Note de cadrage budgétaire annuel
        - RESADE-F-EAB-01-02 : Canevas de budget départemental
        - RESADE-F-EAB-01-03 : Budget annuel consolidé (POA) – SYCEBNL
        - RESADE-F-EAB-02-01 : Canevas de budget projet bailleur
        - RESADE-F-EAB-02-02 : Fiche d'ouverture de code analytique
        - RESADE-F-ESB-01-01 : Fiche d'Expression des Besoins (FEB) — pivot institutionnel
        - RESADE-F-ESB-01-02 : Registre des FEB et engagements budgétaires
        - RESADE-F-ESB-02-01 : Tableau de bord budgétaire mensuel consolidé
        - RESADE-F-ESB-02-02 : Rapport de performance budgétaire trimestriel (CA)
        - RESADE-F-ESB-03-01 : Tableau de modification budgétaire
        - RESADE-F-ESB-03-02 : Décision d'approbation de la modification budgétaire

        ─────────────────────────────────────────────────────
        INTÉGRATION AVEC LES AUTRES MODULES RESADE (Marché / Mission)
        ─────────────────────────────────────────────────────
        Ce module est le RÉFÉRENTIEL BUDGÉTAIRE CENTRAL de RESADE. Il remplace la
        case "visa budgétaire" purement déclarative des modules resade_marche et
        resade_mission par une VÉRIFICATION RÉELLE de disponibilité de crédit :

        - Le modèle resade.budget.feb (P-ESB-01) est LE pivot institutionnel
          d'engagement de dépense. resade_marche (FEB par dossier marché) et
          resade_mission (visa budgétaire OM) peuvent créer/lier une FEB RESADE
          via la méthode resade.budget.ligne.reserver_credit(montant) qui :
            1) vérifie le disponible (Budget approuvé - Engagé - Réalisé)
            2) lève une erreur explicite si crédit insuffisant
            3) incrémente le montant "Engagé" de la ligne en cas de succès
        - Le champ resade.budget.ligne (ligne budgétaire officielle, code
          SYCEBNL + code analytique) est conçu pour être référencé par
          Many2one depuis resade.marche.feb.ligne_budgetaire et
          resade.mission.budget_line_info dans une prochaine itération
          d'intégration (non modifiée ici pour ne pas casser les modules
          existants déjà installés).
        - Compatible avec le module budget (HSN) déjà présent : ce module
          NE remplace PAS budget.budget / budget.ligne (suivi mensuel détaillé
          par compte analytique), il ajoute la couche RESADE manquante
          (élaboration annuelle, FEB, révision) qui pilote ces données.
    """,
    'author': 'IT PROJET SARL',
    'website': 'https://www.it-projet.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'account', 'analytic'],
    'data': [
        # Sécurité
        'security/resade_budget_security.xml',
        'security/ir.model.access.csv',
        # Données de référence
        'data/resade_budget_sequence.xml',
        'data/resade_budget_data.xml',
        # Vues
        'views/resade_budget_ligne_views.xml',
        'views/resade_budget_annuel_views.xml',
        'views/resade_budget_projet_bailleur_views.xml',
        'views/resade_budget_feb_views.xml',
        'views/resade_budget_tdb_views.xml',
        'views/resade_budget_revision_views.xml',
        'views/resade_budget_menus.xml',
        # Rapports PDF
        'report/resade_budget_report_templates.xml',
        'report/resade_budget_reports.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
