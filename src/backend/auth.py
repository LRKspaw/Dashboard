import os
import hashlib
from sqlalchemy.orm import Session
from src.backend.models import User
import re

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'

def valider_synthaxe_email(email: str) -> bool:
     return bool(re.match(EMAIL_REGEX, email))

def valider_md(password: str) -> bool:
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
    existing_user = db.query(User).filter_by(email=email).first()
    if existing_user:
        return False, "Un utilisateur avec cet e-mail existe déjà."
    
    hashed_password, salt_hex = hash_password(password)
    new_user = User(
        email=email,
        hashed_password=hashed_password,
        salt=salt_hex
    )
    db.add(new_user)
    db.commit()
    return True, "Utilisateur enregistré avec succès."