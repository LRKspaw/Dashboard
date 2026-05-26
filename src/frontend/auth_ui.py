import streamlit as st
import qrcode
from io import BytesIO
from src.backend.database import SessionLocal
from src.backend.auth import (
    verify_user, register_user, obtenir_uri_mfa, verifier_code_mfa, 
    initier_mfa_email, verifier_code_otp_email
)
from src.backend.models import User

def afficher_formulaire_authentification():
    """Affiche l'interface de connexion/inscription avec routage dynamique du MFA."""
    st.title("Authentification Sécurisée PEA")
    
    if "mfa_step" not in st.session_state:
        st.session_state.mfa_step = False
        st.session_state.pending_user_id = None
        st.session_state.pending_user_email = None
        st.session_state.mfa_type_required = None
        st.session_state.email_otp_sent = False

    db = SessionLocal()

    try:
        # ÉTAPE 2 : DOUBLE AUTHENTIFICATION (MFA)
        if st.session_state.mfa_step:
            user = db.query(User).filter_by(id=st.session_state.pending_user_id).first()
            
            if not user:
                st.error("Erreur de session utilisateur.")
                st.session_state.mfa_step = False
                st.rerun()

            st.subheader("Double Authentification (2FA)")

            # --- CAS 1 : L'UTILISATEUR SÉCURISE PAR APP TOTP ---
            if st.session_state.mfa_type_required == "TOTP":
                st.info("Ouvrez votre application (Google Authenticator, Bitwarden...) pour copier votre code.")
                with st.form("form_mfa_totp"):
                    code_mfa = st.text_input("Code de sécurité (6 chiffres)", max_chars=6)
                    submit_mfa = st.form_submit_button("Vérifier et Se connecter", use_container_width=True)

                    if submit_mfa:
                        if verifier_code_mfa(user.mfa_secret, code_mfa):
                            st.session_state.authenticated = True
                            st.session_state.user_id = user.id
                            st.session_state.user_email = user.email
                            if not user.mfa_enabled:
                                user.mfa_enabled = True
                            db.commit()
                            st.success("Connexion validée !")
                            st.rerun()
                        else:
                            st.error("Code invalide ou expiré.")

            # --- CAS 2 : L'UTILISATEUR SÉCURISE PAR EMAIL ---
            elif st.session_state.mfa_type_required == "EMAIL":
                # On déclenche l'envoi de l'e-mail une seule fois au chargement de l'étape
                if not st.session_state.email_otp_sent:
                    with st.spinner("Envoi du code de sécurité par e-mail..."):
                        initier_mfa_email(db, user)
                        st.session_state.email_otp_sent = True
                    st.toast("Un code de sécurité vient de vous être envoyé par e-mail !")

                st.info(f"Un code de sécurité temporaire a été envoyé à l'adresse **{user.email}**.")
                st.caption("(Consultez vos e-mails ou les logs de votre console de développement pour voir le code simulé)")
                
                with st.form("form_mfa_email"):
                    code_email = st.text_input("Entrez le code reçu par e-mail (6 chiffres)", max_chars=6)
                    submit_email = st.form_submit_button("Valider le code & Se connecter", use_container_width=True)

                    if submit_email:
                        if verifier_code_otp_email(db, user, code_email):
                            st.session_state.authenticated = True
                            st.session_state.user_id = user.id
                            st.session_state.user_email = user.email
                            st.success("Connexion validée !")
                            st.rerun()
                        else:
                            st.error("Code e-mail incorrect ou expiré. Veuillez réessayer.")
                            
                if st.button("Renvoyer un nouveau code e-mail", use_container_width=True):
                    st.session_state.email_otp_sent = False
                    st.rerun()

            if st.button("⬅ Retour à l'écran de connexion"):
                st.session_state.mfa_step = False
                st.session_state.email_otp_sent = False
                st.rerun()
            return

        # ÉTAPE 1 : CONNEXION OU CRÉATION DE COMPTE
        tab_login, tab_register = st.tabs(["Connexion", "Créer un compte"])

        with tab_login:
            with st.form("form_login"):
                email = st.text_input("Adresse Email")
                password = st.text_input("Mot de passe", type="password")
                submit_login = st.form_submit_button("Étape suivante", use_container_width=True)

                if submit_login:
                    user = verify_user(db, email, password)
                    if user:
                        st.session_state.mfa_step = True
                        st.session_state.pending_user_id = user.id
                        st.session_state.pending_user_email = user.email
                        # Récupération du choix configuré par l'utilisateur
                        st.session_state.mfa_type_required = user.mfa_type if user.mfa_type != "NONE" else "TOTP"
                        st.rerun()
                    else:
                        st.error("Email ou mot de passe incorrect.")
        
        with tab_register:
            with st.form("form_register"):
                st.subheader("Informations d'inscription")
                new_email = st.text_input("Adresse Email")
                new_password = st.text_input("Mot de passe", type="password")
                confirm_password = st.text_input("Confirmer le mot de passe", type="password")
                
                st.markdown("---")
                st.subheader("🔒 Choisissez votre méthode 2FA")
                mfa_choix = st.radio(
                    "Cette méthode vous sera demandée à chaque connexion :",
                    options=["TOTP", "EMAIL"],
                    format_func=lambda x: "📱 Application d'authentification (TOTP)" if x == "TOTP" else "📩 Code temporaire par E-mail (OTP)"
                )
                
                submit_register = st.form_submit_button("Créer mon compte", use_container_width=True)

                if submit_register:
                    if new_password != confirm_password:
                        st.error("Les mots de passe ne correspondent pas.")
                    else:
                        success, message, secret_mfa = register_user(db, new_email, new_password, mfa_choix)
                        if success:
                            st.success(message)
                            
                            # Si choix TOTP, on génère le QR code immédiatement pour configuration
                            if mfa_choix == "TOTP" and secret_mfa:
                                uri = obtenir_uri_mfa(new_email.strip().lower(), secret_mfa)
                                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                                qr.add_data(uri)
                                qr.make(fit=True)
                                img_qr = qr.make_image(fill_color="black", back_color="white")
                                
                                buf = BytesIO()
                                img_qr.save(buf, format="PNG")
                                byte_im = buf.getvalue()
                                
                                st.markdown("### 🛠️ Scannez ce QR Code pour finaliser")
                                st.image(byte_im, caption="Scannez ce code avec Google Authenticator ou Bitwarden.", width=250)
                                st.code(f"Clé secrète de secours : {secret_mfa}")
                            
                            st.info("Configuration enregistrée. Rendez-vous sur l'onglet 'Connexion' pour vous connecter.")
                        else:
                            st.error(message)
    finally:
        db.close()