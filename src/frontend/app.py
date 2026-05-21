import streamlit as st
import io
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import sessionmaker, Session
from src.backend.database import engine
from src.backend.parser import sauvegarder_en_base
from src.backend.models import Actif, Transaction, HistoriquePrix, User, FichierImporte
from src.backend.sync_yfincance import synchroniser_un_actif
import plotly.graph_objects as go
from src.frontend.auth_ui import afficher_formulaire_authentification
from src.backend.calculs import calculer_historique_portefeuille_df, calculer_portefeuille
import hashlib

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
        st.session_state.fichiers_traites = set()
        st.cache_data.clear()
        st.rerun()

if "fichiers_traites" not in st.session_state:
    st.session_state.fichiers_traites = set()

@st.cache_data(ttl=3600)
def charger_donnees(_db: Session, user_id: int):
    res = calculer_portefeuille(_db, user_id)
    return res

@st.cache_data(ttl=3600)
def charger_evolution(_db: Session, user_id: int):
    return calculer_historique_portefeuille_df(_db, user_id)

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
                    
                    uploaded_file.seek(0)

                    file_bytes = uploaded_file.getvalue()
                    file_hash = hashlib.md5(file_bytes).hexdigest()

                    deja_importe = db.query(FichierImporte).filter_by(
                        user_id=CURRENT_USER_ID,
                        hash_md5=file_hash
                    ).first()

                    if deja_importe:
                        st.sidebar.warning(f"Le fichier {uploaded_file.name} a déjà été importé avant (ignoré)")
                        st.session_state.fichiers_traites.add(uploaded_file.name)
                        continue

                    pdf_buffer = io.BytesIO(uploaded_file.read())

                    with st.spinner(f"Traitement de {uploaded_file.name}..."):
                        try:
                            res = sauvegarder_en_base(pdf_buffer, db, CURRENT_USER_ID)
                            if res:
                                isins_du_fichier = set(op['isin'] for op in res)
                                for isin in isins_du_fichier:
                                    synchroniser_un_actif(isin, db)
                                nouvel_import = FichierImporte(
                                    user_id=CURRENT_USER_ID,
                                    nom_fichier=uploaded_file.name,
                                    hash_md5=file_hash
                                )
                                db.add(nouvel_import)
                                db.commit()

                                st.session_state.fichiers_traites.add(uploaded_file.name)
                                fichiers_traite_count += 1
                        
                        except Exception as e:
                            db.rollback()
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
    # 1. On récupère TOUT l'objet calculé par le backend
    res_portefeuille = charger_donnees(db_view, CURRENT_USER_ID)

    if res_portefeuille and res_portefeuille.get("details"):
        # On sépare les deux branches du dictionnaire
        inf_global = res_portefeuille["global"]
        details_actifs = res_portefeuille["details"]

        # 2. Construction du DataFrame pour le tableau et le camembert
        df_repatrition = pd.DataFrame(details_actifs)
        
        # On renomme simplement les colonnes brutes du back pour faire un joli tableau affiché
        mapping_table = {
            "Nom": "ETF",
            "PRU": "PRU (€)",
            "Prix Actuel": "Prix Actuel (€)",
            "Valeur Actuelle": "Valeur Actuelle (€)",
            "Plus-Value (€)": "Plus-Value (€)",
            "Plus-Value (%)": "Plus-Value (%)"
        }
        df_table_affichee = df_repatrition.rename(columns=mapping_table)

        # 3. Affichage des KPIs directement calculés par le backend
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Investissement Global", f"{inf_global['investissement']:,.2f} €".replace(",", " "))
        kpi2.metric("Valeur Portefeuille", f"{inf_global['valeur_actuelle']:,.2f} €".replace(",", " "))
        kpi3.metric(
            "Plus-Value Latente", 
            f"{inf_global['plus_value_euro']:,.2f} €".replace(",", " "), 
            f"{inf_global['plus_value_pct']:.2f} %"
        )
        
        st.markdown("### Récapitulatif des lignes")
        st.dataframe(df_table_affichee, use_container_width=True, hide_index=True)

        # --- GRAPHIQUES ---
        st.subheader("Analyse Visuelle")
        col_graph1, col_graph2 = st.columns(2)

        with col_graph1:
            # Le camembert utilise les clés brutes de details_actifs contenues dans df_repatrition
            fig_repartition = px.pie(
                df_repatrition, 
                values="Valeur Actuelle", 
                names="Nom", # Nom de ta clé dans calculs.py
                hole=0.4,
                title="Répartition par ETF"
            )
            fig_repartition.update_layout(margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_repartition, use_container_width=True)
            
        with col_graph2:
            df_evolution = charger_evolution(db_view, CURRENT_USER_ID)
            
            if not df_evolution.empty:
                
                # --- TON IDÉE : FORCER LE POINT D'AMORCE ---
                premiere_date = df_evolution["Date"].min()
                date_amorce = pd.to_datetime(f"{premiere_date.year}-01-01")
                
                # Si le DataFrame ne commence pas exactement au 1er janvier, on l'injecte !
                if premiere_date > date_amorce:
                    df_amorce = pd.DataFrame([{
                        "Date": date_amorce,
                        "Capital Investi": 0.0,
                        "Valorisation Réelle": 0.0,
                        "Plus-Value": 0.0
                    }])
                    # On fusionne ce point zéro avec le reste de l'historique
                    df_evolution = pd.concat([df_amorce, df_evolution], ignore_index=True)
                # -------------------------------------------

                df_evolution = df_evolution.rename(columns={
                    "Capital Investi": "Capital Investi (€)",
                    "Valorisation Réelle": "Valorisation Réelle (€)"
                })

                fig_evolution = go.Figure()

                # Courbe 1 : Capital Investi
                fig_evolution.add_trace(go.Scatter(
                    x=df_evolution["Date"],
                    y=df_evolution["Capital Investi (€)"],
                    mode='lines',
                    name='Capital Investi',
                    line=dict(color='#A0A0A0', width=2, shape='hv'),
                    fill='tozeroy',
                    fillcolor='rgba(200, 200, 200, 0.05)'
                ))

                # Courbe 2 : Valorisation Réelle
                fig_evolution.add_trace(go.Scatter(
                    x=df_evolution["Date"],
                    y=df_evolution["Valorisation Réelle (€)"],
                    mode='lines',
                    name='Valorisation Réelle',
                    line=dict(color='#2E86C1', width=3)
                ))

                fig_evolution.update_layout(
                    title="Évolution du Portefeuille vs. Capital Investi",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=10, r=10, t=50, b=10),
                    xaxis=dict(showgrid=True, gridcolor='rgba(128, 128, 128, 0.1)'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(128, 128, 128, 0.1)'),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )

                st.plotly_chart(fig_evolution, use_container_width=True)
    else:
        st.info("Aucun actif trouvé dans le portefeuille. Veuillez glisser un PDF dans la barre latérale pour lancer le pipeline initial.")

finally:
    db_view.close()