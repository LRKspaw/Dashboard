import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from src.backend.models import Transaction, Actif, HistoriquePrix

def calculer_historique_portefeuille_df(db: Session, user_id: int) -> pd.DataFrame:
    """
    Calcule l'histroique quotidien du Capital Inversi et de la Valorisation Réeelle.
    Retourne un DataFrmame Pandas pret pour Ploty.
    """
    # Récupération de toutes les transactions d'achat de l'utilisateur
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date).all()

    if not transactions:
        return pd.DataFrame(columns=["Date", "Capital Investi", "Valorisation"])
    
    start_date = transactions[0].date
    end_date = datetime.now()

    date_range = pd.date_range(start=start_date, end=end_date, freq='D').date

    prix_history = db.query(HistoriquePrix).order_by(HistoriquePrix.date).all()

    prices_map = {(p.actif_id, p.date): p.prix_cloture for p in prix_history}

    records = []

    for current_date in date_range:
        capital_cumule = 0.0
        valorisation_totale = 0.0

        tx_au_jour_j = [t for t in transactions if t.date <= current_date]

        assets_quantites = {}

        for tx in tx_au_jour_j:
            cout_transaction = float(tx.quantity) * float(tx.unit_price) + float(tx.fees)
            if tx.operation_type == "Achat":
                capital_cumule += cout_transaction
                assets_quantites[tx.actif_id] = assets_quantites.get(tx.actif_id, 0) + float(tx.quantity)
            elif tx.operation_type == "Vente":
                pass

        for actif_id, quantite in assets_quantites.items():
            prix = prices_map.get((actif_id, current_date))

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
