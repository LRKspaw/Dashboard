from sqlalchemy.orm import Session
from src.backend.models import Actif, Transaction, HistoriquePrix
import pandas as pd
from datetime import datetime, date

def calculer_portefeuille(db: Session, user_id: int):
    """Calcul et retourne les métrique du portefeuille de l'utilisateur"""

    # Récupérer les transactions d'achat de l'utilisateur
    transactions_user = db.query(Transaction).filter_by(
        user_id=user_id,
        operation_type="Achat"
    ).all()

    # Récupérer les actifs uniques de cet utilisateur
    actif_ids = set(t.actif_id for t in transactions_user if t.actif_id)
    actifs = db.query(Actif).filter(Actif.id.in_(actif_ids)).all()

    investissement_total_global = 0.0
    valeur_actuelle_global = 0.0
    liste_actifs_calcules = []

    for actif in actifs:
        achats = [t for t in transactions_user if t.actif_id == actif.id]

        if not achats:
            continue

        quantite_totale = sum(float(t.quantity) for t in achats)
        cout_total = sum(float(t.quantity) * float(t.unit_price) + float(t.fees) for t in achats)
        pru = cout_total / quantite_totale if quantite_totale > 0 else 0.0

        dernier_prix_record = db.query(HistoriquePrix).filter_by(actif_id=actif.id).order_by(HistoriquePrix.date.desc()).first()

        prix_actuel = float(dernier_prix_record.prix) if dernier_prix_record is not None else 0.0
        valeur_actuelle = quantite_totale * prix_actuel

        plus_value_euro = valeur_actuelle - cout_total
        plus_value_pct = (plus_value_euro / cout_total * 100) if cout_total > 0 else 0.0

        investissement_total_global += cout_total
        valeur_actuelle_global += valeur_actuelle

        liste_actifs_calcules.append({
            "Nom": actif.nom_etf,
            "ISIN": actif.isin_code,
            "Quantité": quantite_totale,
            "PRU": pru,
            "Prix Actuel": prix_actuel,
            "Valeur Actuelle": valeur_actuelle,
            "Plus-Value (€)": plus_value_euro,
            "Plus-Value (%)": plus_value_pct
        })

    plus_value_global_euro = valeur_actuelle_global - investissement_total_global
    plus_value_global_pct = (plus_value_global_euro / investissement_total_global * 100) if investissement_total_global > 0 else 0.0

    return {
        "global": {
            "investissement": investissement_total_global,
            "valeur_actuelle": valeur_actuelle_global,
            "plus_value_euro": plus_value_global_euro,
            "plus_value_pct": plus_value_global_pct
        },
        "details": liste_actifs_calcules
    }


def calculer_historique_portefeuille_df(db: Session, user_id: int) -> pd.DataFrame:
    """
    Calcule l'historique quotidien du Capital Investi et de la Valorisation Réelle.
    Ancre la chronologie au 1er janvier de l'année du premier achat à 0 €.
    Retourne un DataFrame Pandas prêt pour Plotly.
    """
    # 1. Récupération de toutes les transactions de l'utilisateur ordonnées par date
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date).all()

    if not transactions:
        return pd.DataFrame(columns=["Date", "Capital Investi", "Valorisation Réelle", "Plus-Value"])
    
    # 2. CALCUL DE L'ANCRAGE CHRONOLOGIQUE
    # On récupère la date de la toute première transaction
    date_premier_achat = transactions[0].date
    # On force le départ au 1er jour (1er) du 1er mois (Janvier) de cette même année
    start_date = date(date_premier_achat.year, date_premier_achat.month, 1)
    
    # Si tu préférais le 1er jour du MOIS de l'achat plutôt que de l'année, il suffirait de mettre :
    # start_date = date(date_premier_achat.year, date_premier_achat.month, 1)

    end_date = datetime.now().date()

    # 3. Génération de la plage de dates complètes
    date_range = pd.date_range(start=start_date, end=end_date, freq='D').date

    # 4. Chargement de toute la carte des prix en mémoire pour éviter les requêtes N+1 dans la boucle
    prix_history = db.query(HistoriquePrix).order_by(HistoriquePrix.date).all()
    prices_map = {(p.actif_id, p.date): float(p.prix) for p in prix_history}

    records = []

    # 5. Évaluation quotidienne du portefeuille
    for current_date in date_range:
        capital_cumule = 0.0
        valorisation_totale = 0.0

        # Filtrage des transactions passées ou égales au jour courant
        tx_au_jour_j = [t for t in transactions if t.date <= current_date]

        assets_quantites = {}

        for tx in tx_au_jour_j:
            cout_transaction = float(tx.quantity) * float(tx.unit_price) + float(tx.fees)
            if tx.operation_type == "Achat":
                capital_cumule += cout_transaction
                assets_quantites[tx.actif_id] = assets_quantites.get(tx.actif_id, 0) + float(tx.quantity)
            elif tx.operation_type == "Vente":
                # À implémenter plus tard au jalon des ventes
                pass

        # Calcul de la valorisation des lignes possédées à cette date précise
        for actif_id, quantite in assets_quantites.items():
            prix = prices_map.get((actif_id, current_date))

            # Si pas de prix pour ce jour précis (ex: week-end), on prend le dernier disponible dans le passé
            if prix is None:
                historique_actif = [p for (a_id, d), p in prices_map.items() if a_id == actif_id and d <= current_date]
                prix = historique_actif[-1] if historique_actif else 0.0
            
            valorisation_totale += quantite * prix
        
        records.append({
            "Date": pd.to_datetime(current_date),
            "Capital Investi": capital_cumule,
            "Valorisation Réelle": valorisation_totale,
            "Plus-Value": valorisation_totale - capital_cumule
        })
    
    return pd.DataFrame(records)

def calculer_evolution_par_etf_df(db: Session, user_id: int) -> pd.DataFrame:
    """
    Calcule l'historique quotidien de la valorisation individualisée de chaque ETF.
    Retourne un DataFrame au format long idéal pour Plotly Express (Date, ETF, Valorisation).
    """
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date).all()

    if not transactions:
        return pd.DataFrame(columns=["Date", "ETF", "Valorisation (€)"])

    actifs = db.query(Actif).all()
    actifs_map = {a.id: a.nom_etf for a in actifs}

    date_premier_achat = transactions[0].date
    start_date = date(date_premier_achat.year, date_premier_achat.month, 1)
    end_date = datetime.now().date()
    date_range = pd.date_range(start=start_date, end=end_date, freq='D').date

    # 3. Chargement de l'historique des prix en mémoire
    prix_history = db.query(HistoriquePrix).order_by(HistoriquePrix.date).all()
    prices_map = {(p.actif_id, p.date): float(p.prix) for p in prix_history}

    records = []

    # 4. Identification des actifs uniques pour forcer le point d'amorce à 0€ au 1er Janvier
    actifs_uniques = set(t.actif_id for t in transactions if t.actif_id)
    for actif_id in actifs_uniques:
        records.append({
            "Date": pd.to_datetime(start_date),
            "ETF": actifs_map.get(actif_id, f"Actif {actif_id}"),
            "Valorisation (€)": 0.0
        })

    # 5. Évolution quotidienne par actif
    for current_date in date_range:
        if current_date == start_date:
            continue # Déjà couvert par le point d'amorce

        tx_au_jour_j = [t for t in transactions if t.date <= current_date]
        assets_quantites = {}

        # Calcul des quantités cumulées pour ce jour précis
        for tx in tx_au_jour_j:
            if tx.operation_type == "Achat":
                assets_quantites[tx.actif_id] = assets_quantites.get(tx.actif_id, 0) + float(tx.quantity)

        # Calcul de la valorisation de chaque ligne active
        for actif_id, quantite in assets_quantites.items():
            if quantite > 0:
                prix = prices_map.get((actif_id, current_date))

                # Gestion des jours sans cotation (week-end/jours fériés)
                if prix is None:
                    historique_actif = [p for (a_id, d), p in prices_map.items() if a_id == actif_id and d <= current_date]
                    prix = historique_actif[-1] if historique_actif else 0.0

                records.append({
                    "Date": pd.to_datetime(current_date),
                    "ETF": actifs_map.get(actif_id, f"Actif {actif_id}"),
                    "Valorisation (€)": quantite * prix
                })

    return pd.DataFrame(records)