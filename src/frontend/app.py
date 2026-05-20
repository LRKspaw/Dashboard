import streamlit as st
import pandas as pd
import sys
import os
import plotly.express as px

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import engine
from sqlalchemy.orm import Session
from models import Actif, Transaction, HistoriquePrix

st.set_page_config(page_title="Dashboard PEA", page_icon="📈", layout="wide")
st.title("📈 Dashboard de suivi de portefeuille PEA")

@st.cache_data(ttl=3600)
def charger_donnees():
    donnees = []

    with Session(engine) as session:
        actifs = session.query(Actif).all()
        for actif in actifs:
            achats = session.query(Transaction).filter_by(actif_id=actif.id, operation_type="Achat").all()

            if not achats:
                continue

            quantites = float(sum(t.quantity for t in achats))
            cout_total = sum(float(t.quantity) * float(t.unit_price) + float(t.fees) for t in achats)

            dernier_prix = session.query(HistoriquePrix).filter_by(actif_id=actif.id).order_by(HistoriquePrix.date.desc()).first()
            prix_actuel = float(dernier_prix.prix) if dernier_prix else 0.0

            valeur_actuelle = quantites * prix_actuel

            donnees.append({
                "ETF": actif.nom_etf,
                "ISIN": actif.isin_code,
                "Ticker": actif.ticker_yfinance,
                "Quantité": quantites,
                "PRU (€)": round(cout_total / quantites, 2) if quantites > 0 else 0.0,
                "Prix Actuel (€)": round(prix_actuel, 2),
                "Investissement Total (€)": round(cout_total, 2),
                "Valeur Actuelle (€)": round(valeur_actuelle, 2),
                "Plus-Value (€)": round(valeur_actuelle - cout_total, 2)
            })
    return donnees

@st.cache_data(ttl=3600)
def charger_evolution():
    with Session(engine) as session:
        achats = session.query(Transaction).filter_by(operation_type="Achat").order_by(Transaction.date).all()

        if not achats:
            return pd.DataFrame()
        date_premier_achat = achats[0].date
        premier_jour_mois = date_premier_achat.replace(day=1)

        donnees_evolution = [{
            "Date": pd.to_datetime(premier_jour_mois),
            "Montant": 0.0
        }]

        for t in achats:
            montant_investi = float(t.quantity) * float(t.unit_price) + float(t.fees)
            donnees_evolution.append({
                "Date": pd.to_datetime(t.date),
                "Montant": montant_investi
            })
        
        df_achats = pd.DataFrame(donnees_evolution)
        df_group = df_achats.groupby("Date")["Montant"].sum().reset_index()
        df_group["Investissement Cumulé (€)"] = df_group["Montant"].cumsum()

        return df_group

st.subheader("Vue d'ensemble du portefeuille")
donnees_portefeuille = charger_donnees()

if donnees_portefeuille:
    df_repatrition = pd.DataFrame(donnees_portefeuille)
    st.dataframe(df_repatrition, use_container_width=True, hide_index=True)
else:
    st.info("Aucun actif trouvé dans le portefeuille. Veuillez importer vos transactions pour voir les données ici.")


# --- GRAPHIQUES ---
st.subheader("Analyse Visuelle")

col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    fig_repartition = px.pie(
        df_repatrition, 
        values="Valeur Actuelle (€)", 
        names="ETF", 
        hole=0.4,
        title="Répartition par ETF"
    )
    st.plotly_chart(fig_repartition, use_container_width=True)
    
with col_graph2:
    df_evolution = charger_evolution()
    
    if not df_evolution.empty:
        fig_evolution = px.line(
            df_evolution, 
            x="Date", 
            y="Investissement Cumulé (€)", 
            markers=True,
            title="Évolution des apports en capital"
        )
        fig_evolution.update_traces(fill='tozeroy', line_color='#2E86C1')
        st.plotly_chart(fig_evolution, use_container_width=True)
        
st.divider()