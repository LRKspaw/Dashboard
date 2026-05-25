# Variables existantes
DC=docker compose
APP_NAME=pea-dashboard

# --- NOUVELLES VARIABLES POUR TON PROXMOX ---
LXC_SSH=root@192.168.1.XX      # Remplplace par l'IP ou le nom SSH de ton LXC
LXC_DIR=/opt/dashboard-pea     # Le dossier cible dans ton conteneur LXC

.PHONY: help build up down restart logs clean status init-db deploy

help: ## Afficher l'aide
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Builder l'image Docker sans utiliser le cache
	$(DC) build --no-cache

up: ## Lancer l'application en arrière-plan (Détaché)
	$(DC) up -d

down: ## Arrêter les conteneurs
	$(DC) down

restart: ## Redémarrer l'application
	$(DC) down && $(DC) up -d

logs: ## Afficher les logs en temps réel
	$(DC) logs -f

status: ## Afficher le statut du conteneur
	$(DC) ps

init-db: ## Initialiser la base de données à l'intérieur du conteneur
	$(DC) exec pea-dashboard python -m src.backend.init_db

clean: ## Nettoyer les images et volumes résiduels Docker
	$(DC) down --v
	docker system prune -f

# --- LA COMMANDE DE DÉPLOIEMENT DIRECT ---
deploy: ## Déployer le code sur le conteneur LXC Proxmox via SSH
	@echo "Synchronisation du code vers le LXC..."
	rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='data/' ./ $(LXC_SSH):$(LXC_DIR)/
	@echo "Relancement des conteneurs à distance..."
	ssh $(LXC_SSH) "cd $(LXC_DIR) && make build && make restart"
	@echo "Application mise à jour avec succès !"