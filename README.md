# PEA Dashboard Tracker

## Description
Une application web complète pour suivre, analyser et projeter les performances de mon Plan d'Épargne en Actions (PEA). Ce projet automatise la récupération des données à partir des relevés bancaires (avis d'opérés, relevés de compte) et croise ces informations avec les données de marché en temps réel pour offrir un tableau de bord détaillé et des projections financières.

## Fonctionnalités Principales

### Tableau de Bord (Dashboard)
- **Évolution du portefeuille :** Courbe de la valeur globale.
- **Métriques clés :** Total des versements, Capital valorisé, Valeur totale.
- **Performances :** Plus/Moins-values et performances (actuelles et annualisées), au global et filtrables par ETF.

### Projections & Simulations
- Simulateur de croissance sur 1, 5, 10, 20 et 40 ans.
- Paramètres ajustables dynamiquement (versements mensuels futurs, taux de rendement estimé, etc.).

### Moteur de Données
- **Parsing automatisé :** Extraction des opérations et virements depuis les PDF (relevés de comptes, avis d'opérés, relevés de titres).
- **Mise à jour incrémentale :** Ajout mensuel des nouveaux documents pour actualiser la base.
- **Données de marché :** Actualisation régulière des cours des ETF via l'API Yahoo Finance.

### Administration
- Système de login sécurisé.
- Gestion multi-utilisateurs (dimensionné pour ~10 utilisateurs).

## Stack Technique
- **Backend & Frontend :** Python (Framework à définir : Streamlit / FastAPI)
- **Base de données :** PostgreSQL
- **Données Financières :** `yfinance`
- **Déploiement :** Docker & Docker Compose (hébergé sur VM Proxmox)

## Roadmap & Todo
- [ ] Mettre en place l'environnement de développement et le repo Git.
- [ ] Modéliser la base de données PostgreSQL.
- [ ] Développer le script de parsing des PDF (Avis d'opérés Fortuneo/autre).
- [ ] Intégrer `yfinance` pour récupérer les cours historiques et actuels.
- [ ] Créer les vues du Dashboard.
- [ ] Ajouter le système d'authentification.
- [ ] Conteneuriser l'application (Docker) et déployer sur Proxmox.