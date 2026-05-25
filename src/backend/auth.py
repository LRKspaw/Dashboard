import os
import hashlib
from sqlalchemy.orm import Session
from src.backend.models import User
import re
import pyotp

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{12,}$'

def valider_synthaxe_email(email: str) -> bool:
     return bool(re.match(EMAIL_REGEX, email))

def valider_password(password: str) -> bool:
     return bool(re.match(PASSWORD_REGEX, password))

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
        """
        Hache un mot de passse en utilisant PBKDF2-HMAC-SHA256 avec un salt.
        Si aucun salt n'est fourni, un nouveau salt aléatoire est généré.
        Retourne (password_hash, salt_hex)
        """
        if salt is None:
            salt = os.urandom(32)
        
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100_000
        )
        return pwd_hash.hex(), salt.hex()
    
def verify_user(db: Session, email: str, password: str) -> User | None:
      """Vérifie les informations d'identification de l'utilisateur.
        Args:
            db (Session): Session de base de données SQLAlchemy.
            email (str): Adresse e-mail de l'utilisateur.
            password (str): Mot de passe en clair à vérifier.
        Returns:
            User | None: L'utilisateur correspondant si les informations sont valides, sinon None.
        """
      user = db.query(User).filter_by(email=email).first()

      if not user:
          return None
      
      salt_bytes = bytes.fromhex(user.salt) if hasattr(user, 'salt') else None

      if salt_bytes is None:
          return user if user.hashed_password == password else None
      
      calculed_hash, _ = hash_password(password, salt_bytes)
      if calculed_hash == user.hashed_password:
          return user
      return None

def register_user(db: Session, email: str, password: str) -> tuple[bool, str]:
    """Enregistre un nouvel utilisateur avec un mot de passe haché.
    Args:
        db (Session): Session de base de données SQLAlchemy.
        email (str): Adresse e-mail de l'utilisateur à enregistrer.
        password (str): Mot de passe en clair à hacher et stocker.
    Returns:
        tuple[bool, str]: (succès, message) où succès indique si l'enregistrement a réussi, et message fournit des détails.
    """
    email_clean=email.strip().lower()
    if not valider_synthaxe_email(email_clean):
         return False, "L'adresse email saisie possède un format invalide.", None
    if not valider_password(password):
         return False, "Le mot de passe est trop faible.", None 
    
    existing_user = db.query(User).filter_by(email=email).first()
    if existing_user:
        return False, "Un utilisateur avec cet e-mail existe déjà.", None
    
    hashed_password, salt_hex = hash_password(password)
    mfa_secret = generer_secret_mfa()

    new_user = User(
        email=email,
        hashed_password=hashed_password,
        salt=salt_hex,
        mfa_secret=mfa_secret,
        mfa_enabled =False
    )
    db.add(new_user)
    db.commit()
    return True, "Utilisateur enregistré avec succès. Veuillez configurer votre 2FA.", mfa_secret


def generer_secret_mfa() -> str:
    """Génère un secret aléatoire au format Base32 pour le TOTP."""
    return pyotp.random_base32()

def obtenir_uri_mfa(email: str, secret: str) -> str:
    """Génère l'URI standardisé pour créer le QR Code (reconnu par Google Authenticator, etc.)."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="PEA Dashboard")

def verifier_code_mfa(secret: str, code: str) -> bool:
    """
    Vérifie si le code à 6 chiffres fourni par l'utilisateur est valide
    par rapport au secret et au timestamp actuel.
    """
    totp = pyotp.TOTP(secret)
    # verify() gère automatiquement une petite tolérance de temps (fenêtre de 30s)
    return totp.verify(code)