from sqlalchemy.orm import Session
from database import engine
from models import Actif, Transaction, HistoriquePrix

def calculer_portefeuille():
    with Session(engine) as session:
        actifs = session.query(Actif).all()

        investissement_total_global = 0.0
        valeur_actuelle_global = 0.0

        print("Calcul du portefeuille :\n")

        for actif in actifs:
            achats = session.query(Transaction).filter_by(
                actif_id=actif.id,
                operation_type="Achat"
            ).all()

            if not achats:
                continue

            quantite_totale = sum(float(t.quantity) for t in achats)
            cout_total = sum(float(t.quantity) * float(t.unit_price) + float(t.fees) for t in achats)
            pru = cout_total / quantite_totale if quantite_totale > 0 else 0.0

            dernier_prix_record = session.query(HistoriquePrix).filter_by(actif_id=actif.id).order_by(HistoriquePrix.date.desc()).first()

            if dernier_prix_record:
                prix_actuel = float(dernier_prix_record.prix)
                valeur_actuelle = quantite_totale * prix_actuel

                plus_value_euro = valeur_actuelle - cout_total
                plus_value_pct = (plus_value_euro / cout_total * 100) if cout_total > 0 else 0.0

                investissement_total_global += cout_total
                valeur_actuelle_global += valeur_actuelle

                signe = "+" if plus_value_euro >= 0 else "-"

                print(f"{actif.nom_etf} (ISIN: {actif.isin_code}) - Ticker: {actif.ticker_yfinance}")
                print(f"  Quantité totale : {quantite_totale}")
                print(f"  Coût total : {cout_total:.2f} €")
                print(f"  Prix actuel : {prix_actuel:.2f} €")
                print(f"  Valeur actuelle : {valeur_actuelle:.2f} €")
                print(f"  Plus-value : {signe}{abs(plus_value_euro):.2f} € ({signe}{abs(plus_value_pct):.2f} %)")
                
        if investissement_total_global > 0:
            plus_value_global_euro = valeur_actuelle_global - investissement_total_global
            plus_value_global_pct = (plus_value_global_euro / investissement_total_global * 100) if investissement_total_global > 0 else 0.0
            signe_global = "+" if plus_value_global_euro >= 0 else "-"
            
            print("\nRésumé global :")
            print(f"  Investissement total : {investissement_total_global:.2f} €")
            print(f"  Valeur actuelle totale : {valeur_actuelle_global:.2f} €")
            print(f"  Plus-value globale : {signe_global}{abs(plus_value_global_euro):.2f} € ({signe_global}{abs(plus_value_global_pct):.2f} %)")
        else:
            print("Aucun investissement trouvé dans le portefeuille.")
        
if __name__ == "__main__":
    calculer_portefeuille()