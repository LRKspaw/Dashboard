import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
from src.backend.database import SessionLocal
from src.backend.auth import (
    verify_user, register_user, obtenir_uri_mfa, verifier_code_mfa, valider_password, valider_synthaxe_email
)
from src.backend.models import User

def afficher_formulaire_authentification():
    """Affiche l'interface de connexion/inscription avec gestion du MFA."""
    st.title("Authentification Sécurisée PEA")
    
    if "mfa_step" not in st.session_state:
        st.session_state.mfa_step = False
        st.session_state.pending_user_id = None
        st.session_state.pending_user_email = None

    db = SessionLocal()

    try:
        if st.session_state.mfa_step:
            st.subheader("Double Authentification (MFA)")
            st.info("Ouvrez votre application d'authentification (Google Authenticator, Bitwarden...) pour récupérer votre code de sécurité.")
            
            with st.form("form_mfa"):
                code_mfa = st.text_input("Code de sécurité (6 chiffres)", max_chars=6, help="Exemple: 123456")
                submit_mfa = st.form_submit_button("Vérifier et Se connecter", use_container_width=True)

                if submit_mfa:
                    user = db.query(User).filter_by(id=st.session_state.pending_user_id).first()
                    
                    if user and verifier_code_mfa(user.mfa_secret, code_mfa):
                        st.session_state.authenticated = True
                        st.session_state.user_id = user.id
                        st.session_state.user_email = user.email
                        
                        if not user.mfa_enabled:
                            user.mfa_enabled = True
                            db.commit()
                            
                        st.success("Connexion validée cryptographiquement !")
                        
                        del st.session_state.mfa_step
                        del st.session_state.pending_user_id
                        del st.session_state.pending_user_email
                        st.rerun()
                    else:
                        st.error("Code de sécurité invalide ou expiré. Veuillez réessayer.")
            
            if st.button("⬅ Retour à l'écran de connexion"):
                st.session_state.mfa_step = False
                st.rerun()
            return

        tab_login, tab_register = st.tabs(["Connexion", "Créer un compte"])

        with tab_login:
            with st.form("form_login"):
                email = st.text_input("Adresse Email")
                password = st.text_input("Mot de passe", type="password")
                submit_login = st.form_submit_button("Étape suivante ", use_container_width=True)

                if submit_login:
                    user = verify_user(db, email, password)
                    if user:
                        st.session_state.mfa_step = True
                        st.session_state.pending_user_id = user.id
                        st.session_state.pending_user_email = user.email
                        st.rerun()
                    else:
                        st.error("Email ou mot de passe incorrect.")
        
        with tab_register:
            with st.form("form_register"):
                st.subheader("Minimum 12 caractères, 1 majuscule, 1 minuscule, 1 chiffre, 1 caractère spécial")
                new_email = st.text_input("Adresse Email", key="register_email")
                new_password = st.text_input("Mot de passe", type="password", key="register_password")
                confirm_password = st.text_input("Confirmer le mot de passe", type="password", key="register_confirm_password")
                submit_register = st.form_submit_button("Créer mon compte & Générer mon MFA", use_container_width=True)

                if submit_register:
                    if new_password != confirm_password:
                        st.error("Les mots de passe ne correspondent pas.")
                    else:
                        success, message, secret_mfa = register_user(db, new_email, new_password)
                        if success and secret_mfa:
                            st.success(message)
                            
                            uri = obtenir_uri_mfa(new_email.strip().lower(), secret_mfa)
                            qr = qrcode.QRCode(version=1, box_size=10, border=4)
                            qr.add_data(uri)
                            qr.make(fit=True)
                            
                            img_qr = qr.make_image(fill_color="black", back_color="white")
                            
                            buf = BytesIO()
                            img_qr.save(buf, format="PNG")
                            byte_im = buf.getvalue()
                            
                            st.markdown("### Scannez ce QR Code")
                            st.image(byte_im, caption="Scannez ce code avec Google Authenticator ou Bitwarden pour lier votre compte.", width=300)
                            st.code(f"Clé secrète de secours (si scan impossible) : {secret_mfa}")
                            st.warning("Notez bien cette clé. Vous passerez par l'onglet Connexion au prochain rafraîchissement.")
                        else:
                            st.error(message)
    finally:
        db.close()