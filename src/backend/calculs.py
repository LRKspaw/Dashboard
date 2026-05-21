from sqlalchemy.orm import Session
from database import engine
from models import Actif, Transaction, HistoriquePrix

def calculer_portefeuille(db: Session, user_id: int):
    """Calcul et retourne les métrique du portefeuille de l'utilisateur"""

    actifs = db.query(Actif).all()

    investissement_total_global = 0.0
    valeur_actuelle_global = 0.0
    liste_actifs_calcules = []

    for actif in actifs:
        achats = db.query(Transaction).filter_by(
            actif_id=actif.id,
            operation_type="Achat"
        ).all()

        if not achats:
            continue

        quantite_totale = sum(float(t.quantity) for t in achats)
        cout_total = sum(float(t.quantity) * float(t.unit_price) + float(t.fees) for t in achats)
        pru = cout_total / quantite_totale if quantite_totale > 0 else 0.0

        dernier_prix_record = db.query(HistoriquePrix).filter_by(actif_id=actif.id).order_by(HistoriquePrix.date.desc()).first()


        prix_actuel = float(dernier_prix_record.prix)
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