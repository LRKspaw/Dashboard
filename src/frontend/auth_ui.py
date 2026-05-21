import streamlit as st
from src.backend.database import SessionLocal
from src.backend.auth import verify_user, register_user

def afficher_formulaire_authentification():
    """Affiche le formulaire d'authentification et gère la logique de connexion."""
    st.title("Authentification")
    tab_login, tab_register = st.tabs(["Connexion", "Créer un compte"])

    db = SessionLocal()

    try:
        with tab_login:
            with st.form("form_login"):
                email = st.text_input("Adresse Email")
                password = st.text_input("Mot de passe", type="password")
                submit_login = st.form_submit_button("Se connecter")

                if submit_login:
                    user = verify_user(db, email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user.id
                        st.session_state.user_email = user.email
                        st.success("Connexion réussie !")
                        st.rerun()
                    else:
                        st.error("Email ou mot de passe incorrect.")
                else:
                    st.warning("Veuiller remplir tous les champs pour se connecter.")
        
        with tab_register:
            with st.form("form_register"):
                new_email = st.text_input("Adresse Email", key="register_email")
                new_password = st.text_input("Mot de passe", type="password", key="register_password")
                confirm_password = st.text_input("Confirmer le mot de passe", type="password", key="register_confirm_password")
                submit_register = st.form_submit_button("Créer un compte")

                if submit_register:
                    if new_password != confirm_password:
                        st.error("Les mots de passe ne correspondent pas.")
                    elif len(new_password) < 8:
                        st.error("Le mot de passe doit contenir au moins 8 caractères.")
                    elif new_email and new_password:
                        success, message = register_user(db, new_email, new_password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.warning("Veuiller remplir tous les champs pour créer un compte.")
    finally:
        db.close()