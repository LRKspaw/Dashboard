import requests
import yfinance as yf
from datetime import date, datetime

from sqlalchemy.orm import Session
from database import engine
from models import Actif, HistoriquePrix

def synchroniser_prix_yfinance():
    with Session(engine) as session:
        actifs = session.query(Actif).all()

        for actif in actifs:
            if actif.ticker_yfinance == "A_DEFINIR":
                nouveau_ticker = trouver_ticker_par_isin(actif.isin_code)
                actif.ticker_yfinance = nouveau_ticker
                session.commit()
                
            if actif.ticker_yfinance != "A_DEFINIR" :
                print(f"Synchronisation du prix pour {actif.nom_etf} (ISIN: {actif.isin_code})")
                ticker = yf.Ticker(actif.ticker_yfinance)
                historique = ticker.history(period="1d")

                if not historique.empty:
                    dernier_prix = float(historique['Close'].iloc[-1])
                    print(f"   Dernier prix trouvé : {dernier_prix}€")

                    nouveau_prix = HistoriquePrix(
                        actif_id=actif.id,
                        date=date.today(),
                        prix=dernier_prix
                    )
                    session.add(nouveau_prix)
        session.commit()
        print("Synchronisation terminée.")

def trouver_ticker_par_isin(isin):
    print(f"Recherche du Ticker pour l'ISIN {isin}...")
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": isin, "quotesCount": 5, "newsCount": 0}
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        reponse = requests.get(url, params=params, headers=headers)
        data = reponse.json()

        if "quotes" in data and len(data["quotes"]) > 0:
            for quote in data["quotes"]:
                symbol = quote.get("symbol", "")
                if symbol.endswith(".PA"):
                    return symbol
            
            return data["quotes"][0]["symbol"]
            
    except Exception as e:
        print(f"Erreur lors de la recherche web : {e}")

    return "A_DEFINIR"

if __name__ == "__main__":
    synchroniser_prix_yfinance()