import requests
import yfinance as yf
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session
from src.backend.database import engine
from src.backend.models import Actif, HistoriquePrix
from sqlalchemy import func
from src.backend.models import Actif, HistoriquePrix, Transaction


def synchroniser_un_actif(actif_isin: str, db: Session):
    """Mise a jour ciblée d'un seul actif immédiatiement après son parsing"""
    actif = db.query(Actif).filter_by(isin_code=actif_isin).first()

    if not actif:
        return
    
    if actif.ticker_yfinance == "A_DEFINIR":
        nouveau_ticker = trouver_ticker_par_isin(actif.isin_code)
        actif.ticker_yfinance = nouveau_ticker
        db.flush()
    
    if actif.ticker_yfinance != "A_DEFINIR" :

        premier_achat = db.query(func.min(Transaction.date)).filter(Transaction.actif_id==actif.id).scalar()

        if premier_achat: 
            start_date_yf = premier_achat.strftime('%Y-%m-%d')
        else:
            start_date_yf = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        ticker = yf.Ticker(actif.ticker_yfinance)
        historique = ticker.history(start=start_date_yf)

        if not historique.empty:

            dates_existantes = db.query(HistoriquePrix.date).filter(HistoriquePrix.actif_id==actif.id).all()
            dates_existantes_set = {d[0] for d in dates_existantes}

            nouveau_prix = []

            for index, row in historique.iterrows():
                date_prix = index.date()
                prix_cloture = float(row['Close'])

                if date_prix not in dates_existantes_set:
                    nouveau_prix.append(
                        HistoriquePrix(
                            actif_id=actif.id,
                            date=date_prix,
                            prix=prix_cloture
                        )
                    )
                    dates_existantes_set.add(date_prix)

            if nouveau_prix:
                db.add_all(nouveau_prix)
                db.flush()
            
            dernier_prix = float(historique['Close'].iloc[-1])

            nouveau_prix = HistoriquePrix(
                actif_id=actif.id,
                date=date.today(),
                prix=dernier_prix
            )
            db.add(nouveau_prix)
            db.flush()

def trouver_ticker_par_isin(isin):
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


def synchroniser_prix_yfinance():
   with Session(engine) as db:
        actifs = db.query(Actif).all()

        for actif in actifs:
            if actif.isin_code :
                synchroniser_un_actif(actif.isin_code, db)
        db.commit()
    
if __name__ == "__main__":
    synchroniser_prix_yfinance()