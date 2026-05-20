# PEA Dashboard Tracker

## Description
Une application web complète pour suivre, analyser et projeter les performances d'un Plan d'Épargne en Actions (PEA). Ce projet automatise la récupération des données à partir des relevés bancaires (avis d'opérés, relevés de compte) et croise ces informations avec les données de marché en temps réel pour offrir un tableau de bord détaillé et des projections financières.

## Fonctionnalités Principales

### Tableau de Bord (Dashboard)
- **Évolution du portefeuille :** Courbe de la valeur globale.
- **Métriques clés :** Total des versements, Capital valorisé, Valeur totale.
- **Performances :** Plus/Moins-values et performances (actuelles et annualisées), au global et filtrables par ETF.

### Projections & Simulations
- Simulateur de croissance sur 1, 5, 10, 20 et 40 ans.
- Paramètres ajustables dynamiquement (versements mensuels futurs, taux de rendement estimé, etc.).

### Moteur de Données
- **Parsing automatisé :** Extraction des opérations et virements depuis les documents PDF (relevés de comptes, avis d'opérés, relevés de titres).
- **Mise à jour incrémentale :** Ajout mensuel des nouveaux documents pour actualiser la base.
- **Données de marché :** Actualisation régulière des cours des ETF via l'API `yfinance`.

### Administration & Sécurité
- Système d'authentification robuste via API.
- Gestion multi-utilisateurs (dimensionné pour ~10 utilisateurs).
- Isolation stricte des données utilisateurs via Row-Level Security (RLS).

## Architecture & Stack Technique
- **Backend (API & Logique métier) :** FastAPI (Python)
- **Frontend (Interface & Dataviz) :** Streamlit (Python)
- **Base de données :** PostgreSQL
- **Déploiement :** Docker & Docker Compose
- **Infrastructure :** Hébergé sur VM Proxmox
- **Exposition Réseau :** Reverse Proxy (Nginx Proxy Manager / Traefik) avec certificats SSL et domaine dédié.

## Roadmap

- [ ] Initialiser l'environnement de développement et le repo Git.
- [ ] Modéliser la base de données PostgreSQL et configurer les règles RLS (Row-Level Security).
- [ ] Développer l'API FastAPI (Authentification et Endpoints de données).
- [ ] Développer le script de parsing des PDF (Avis d'opérés Fortuneo/autre).
- [ ] Intégrer `yfinance` pour la récupération quotidienne des cours.
- [ ] Coder l'interface Streamlit (connexion à l'API et création des vues du Dashboard).
- [ ] Conteneuriser les services (API, Front, DB) avec Docker Compose.
- [ ] Déployer sur Proxmox et configurer l'accès distant sécurisé (Reverse Proxy + SSL).