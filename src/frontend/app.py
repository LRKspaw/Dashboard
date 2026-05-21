import streamlit as st
import io
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import sessionmaker, Session
from src.backend.database import engine
from src.backend.parser import sauvegarder_en_base
from src.backend.models import Actif, Transaction, HistoriquePrix, User
from src.backend.sync_yfincance import synchroniser_un_actif
from src.frontend.auth_ui import afficher_formulaire_authentification


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

st.set_page_config(
    page_title="Dashboard PEA - Fortuneo",
    page_icon="",
    layout="wide", 
    initial_sidebar_state="expanded"
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_email = None

if not st.session_state.authenticated:
    afficher_formulaire_authentification()
    st.stop()

CURRENT_USER_ID = st.session_state.user_id

with st.sidebar:
    st.write(f"Connecté en tant que : {st.session_state.user_email}")

    if st.button("Se déconnecter", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.cache_data.clear()
        st.rerun()

if "fichiers_traites" not in st.session_state:
    st.session_state.fichiers_traites = set()

@st.cache_data(ttl=3600)
def charger_donnees(_db: Session, user_id: int):
    donnees = []

    actifs = _db.query(Actif).all()
    for actif in actifs:
        achats = _db.query(Transaction).filter_by(actif_id=actif.id, operation_type="Achat").all()

        if not achats:
            continue

        quantites = float(sum(t.quantity for t in achats))
        cout_total = sum(float(t.quantity) * float(t.unit_price) + float(t.fees) for t in achats)

        dernier_prix = _db.query(HistoriquePrix).filter_by(actif_id=actif.id).order_by(HistoriquePrix.date.desc()).first()
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
def charger_evolution(_db: Session, user_id: int):
    achats = _db.query(Transaction).filter_by(operation_type="Achat").order_by(Transaction.date).all()

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

st.sidebar.header("Ingestion de Données")
st.sidebar.write("Déposez vos avis d'opérés Fortuneo pour mettre à jour le dashboard.")

uploaded_files = st.sidebar.file_uploader(
    label="Glissez-déposez vos fichiers PDF",
    type=["pdf"],
    accept_multiple_files=True,
    help="Sélectionnez un ou plusieurs fichiers PDF générés par Fortuneo."
)

if uploaded_files:
    fichiers_a_traiter = [f for f in uploaded_files if f.name not in st.session_state.fichiers_traites]

    if fichiers_a_traiter:
        st.sidebar.info(f"{len(fichiers_a_traiter)} nouveau(x) fichier(s) détecté(s). Traitement en cours...")

        if st.sidebar.button("Lancer l'intégration", use_container_width=True):
            db = SessionLocal()
            fichiers_traite_count = 0
            try:
                for uploaded_file in fichiers_a_traiter:
                    pdf_buffer = io.BytesIO(uploaded_file.read())

                    with st.spinner(f"Traitement de {uploaded_file.name}..."):
                        try:
                            res = sauvegarder_en_base(pdf_buffer, db, CURRENT_USER_ID)
                            if res:
                                isins_du_fichier = set(op['isin'] for op in res)
                                for isin in isins_du_fichier:
                                    synchroniser_un_actif(isin, db)
                                
                                st.session_state.fichiers_traites.add(uploaded_file.name)
                                fichiers_traite_count += 1
                        
                        except Exception as e:
                            st.sidebar.error(f"Erreur lors du traitement de {uploaded_file.name} : {str(e)}")
                
                if fichiers_traite_count > 0:
                    st.cache_data.clear()
                    st.toast(f"{fichiers_traite_count} fichier(s) traité(s) avec succès ! Le dashboard a été mis à jour.")
                    st.rerun()
            finally:
                db.close()
    else:
        st.sidebar.info("Aucun nouveau fichier détecté. Tous les fichiers sélectionnés ont déjà été traités.")

st.title("Tableau de Bord - Suivi PEA")
st.markdown("---")


db_view = SessionLocal()
try:
    donnees_portefeuille = charger_donnees(db_view, CURRENT_USER_ID)

    if donnees_portefeuille:
        df_repatrition = pd.DataFrame(donnees_portefeuille)
        
        # Section KPIs Globaux (Calculs automatiques à la volée issus de ta logique de calculs.py)
        total_investi = df_repatrition["Investissement Total (€)"].sum()
        total_actuel = df_repatrition["Valeur Actuelle (€)"].sum()
        total_plus_value = total_actuel - total_investi
        total_plus_value_pct = (total_plus_value / total_investi * 100) if total_investi > 0 else 0.0
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Investissement Global", f"{total_investi:,.2f} €")
        kpi2.metric("Valeur Portefeuille", f"{total_actuel:,.2f} €")
        kpi3.metric("Plus-Value Latente", f"{total_plus_value:,.2f} €", f"{total_plus_value_pct:.2f} %")
        
        st.markdown("### Récapitulatif des lignes")
        st.dataframe(df_repatrition, use_container_width=True, hide_index=True)

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
            df_evolution = charger_evolution(db_view, CURRENT_USER_ID)
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
    else:
        st.info("Aucun actif trouvé dans le portefeuille. Veuillez glisser un PDF dans la barre latérale pour lancer le pipeline initial.")

finally:
    db_view.close()




