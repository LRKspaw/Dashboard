from pathlib import Path

import pdfplumber
import os
import re
import glob
import io 
from typing import Union, BinaryIO

from sqlalchemy.orm import Session
from src.backend.database import engine
from src.backend.models import User, Actif, Transaction
from datetime import datetime


from pathlib import Path
import pdfplumber
import os
import re
from typing import Union, BinaryIO
from sqlalchemy.orm import Session
from src.backend.database import engine
from src.backend.models import User, Actif, Transaction
from datetime import datetime

def parse_avis_operation(file_source: Union[str, Path, BinaryIO]) -> list:
    """Fonction de parsing d'un avis d'opération PDF pour extraire les transactions (ETFs et Actions).
    
    Args:
        file_source (Union[str, Path, BinaryIO]): Chemin vers le fichier PDF ou objet binaire du PDF.
    Returns:
        list: Liste de dicationnaires contenant les transactions extraites.
    """
    operations = []
    with pdfplumber.open(file_source) as pdf:
        texte_complet = ""
        for page in pdf.pages:
            texte_complet += page.extract_text() + "\n"
    
    blocs_actifs = re.split(r'(?=(?:TRACKER|ACTION)\s*:)', texte_complet)
    blocs_actifs = [b for b in blocs_actifs if "TRACKER :" in b or "ACTION :" in b]
    
    for bloc in blocs_actifs:
        actif_match = re.search(r'(?:TRACKER|ACTION)\s*:\s*(.*?)\s*\(([A-Z0-9]{12})\)', bloc)
        
        if not actif_match:
            continue
            
        nom_actif = actif_match.group(1).strip()
        isin = actif_match.group(2)

        dates = re.findall(r"(\d{2}-\d{2}-\d{4})\s+Référence", bloc)
        quantites_cours = re.findall(r"Quantité\s+(\d+)\s+Cours\s+([\d,]+)\s*€", bloc)
        frais = re.findall(r"Courtage et Commission\s+([\d,]+)\s*€", bloc)
        
        for i in range(len(dates)):
            try:
                jour, mois, annee = dates[i].split("-")
                
                operation = {
                    "date": f"{annee}-{mois}-{jour}",
                    "nom": nom_actif,
                    "isin": isin,
                    "quantite": int(quantites_cours[i][0]),
                    "prix_unitaire": float(quantites_cours[i][1].replace(",", ".")),
                    "frais": float(frais[i].replace(",", "."))
                }
                operations.append(operation)
            except IndexError:
                print(f"Erreur de lecture sur une ligne de {nom_actif}")
                
    print(f"[PARSER] {len(operations)} transaction(s) extraite(s).")
    return operations



def sauvegarder_en_base(file_source: Union[str, Path, BinaryIO], db: Session, user_id: int):
    """
    Pipeline orchestrant le parsing et l'enregistrement en base des transactions extraites d'un avis d'opération PDF.
    Args:
        file_source (Union[str, Path, BinaryIO]): Chemin vers le fichier PDF ou objet binaire du PDF.
        db (Session): Session SQLAlchemy pour les opérations de base de données.
        user_id (int): ID de l'utilisateur auquel les transactions seront associées.
    """
    data = parse_avis_operation(file_source)
    if not data:
        raise ValueError("Aucune transaction extraite du PDF. Veuillez vérifier le format du fichier.")
    
    utilisateur = db.query(User).filter_by(id=user_id).first()

    if not utilisateur:
        raise ValueError(f"Aucun utilisateur trouvé avec l'ID {user_id}.")
    
    transactions_enregistrees = []

    try:
        for op in data:
            actif = db.query(Actif).filter_by(isin_code=op['isin']).first()
            if not actif:
                print(f"Création de l'actif {op['nom']} (ISIN: {op['isin']})")
                actif = Actif(
                    isin_code=op['isin'],
                    nom_etf=op['nom'],
                    ticker_yfinance="A_DEFINIR"
                )
                db.add(actif)
                db.flush()
            
            date_transaction = datetime.strptime(op['date'], "%Y-%m-%d").date()

            transaction_existante = db.query(Transaction).filter_by(
                user_id=utilisateur.id,
                actif_id=actif.id,
                date=date_transaction,
                operation_type="Achat",
                quantity=op['quantite'],
                unit_price=op['prix_unitaire'],
                fees=op['frais']
            ).first()

            if transaction_existante:
                print(f"Transaction déjà enregistrée pour {op['nom']} le {op['date']}. Ignorée.")
                continue

            nouvelle_transaction = Transaction(
                user_id=utilisateur.id,
                actif_id=actif.id,
                date=date_transaction,
                operation_type="Achat",
                quantity=op['quantite'],
                unit_price=op['prix_unitaire'],
                fees=op['frais']
            )
            print(f"Enregistrement de la transaction : {op['quantite']} {op['nom']} à {op['prix_unitaire']}€ le {op['date']} (Frais: {op['frais']}€)")
            db.add(nouvelle_transaction)
            transactions_enregistrees.append(op)
        db.commit()
        print("Toutes les transactions ont été enregistrées en base.")
        return transactions_enregistrees
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Erreur lors de l'enregistrement des transactions : {str(e)}")

