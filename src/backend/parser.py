import pdfplumber
import os
import re
import glob

from sqlalchemy.orm import Session
from database import engine
from models import User, Actif, Transaction
from datetime import datetime


def extraire_transactions(chemin_fichier):
    operations = []
    with pdfplumber.open(chemin_fichier) as pdf:
        texte_complet = ""
        for page in pdf.pages:
            texte_complet += page.extract_text() + "\n"
    
    # On  toujours par ETF
    blocs_etf = texte_complet.split("TRACKER :")[1:] 
    
    for bloc in blocs_etf:
        # 1. On identifie l'ETF (valable pour tout le bloc)
        actif_match = re.search(r"(.*?)\s*\(([A-Z0-9]{12})\)", bloc)
        
        # Si on ne trouve pas d'ISIN, c'est que ce n'est pas un bloc valide
        if not actif_match:
            continue
            
        nom_etf = actif_match.group(1).strip()
        isin = actif_match.group(2)

        # 2. On trouve TOUTES les opérations sous cet ETF avec findall
        dates = re.findall(r"(\d{2}-\d{2}-\d{4})\s+Référence", bloc)
        quantites_cours = re.findall(r"Quantité\s+(\d+)\s+Cours\s+([\d,]+)\s*€", bloc)
        frais = re.findall(r"Courtage et Commission\s+([\d,]+)\s*€", bloc)
        
        # 3. On boucle sur le nombre de dates trouvées pour créer les transactions
        for i in range(len(dates)):
            try:
                jour, mois, annee = dates[i].split("-")
                
                operations.append({
                    "date": f"{annee}-{mois}-{jour}",
                    "nom": nom_etf,
                    "isin": isin,
                    "quantite": int(quantites_cours[i][0]),
                    "prix_unitaire": float(quantites_cours[i][1].replace(",", ".")),
                    "frais": float(frais[i].replace(",", "."))
                })
            except IndexError:
                # Sécurité au cas où le PDF est mal formaté
                print(f"⚠️ Erreur de lecture sur une ligne de {nom_etf}")
            
    return operations
    operations = []
    with pdfplumber.open(chemin_fichier) as pdf:
        texte_complet = ""
        for page in pdf.pages:
            texte_complet += page.extract_text() + "\n"
    
    blocs_etf = texte_complet.split("TRACKER :")[1:] 
    
    for bloc in blocs_etf:
        actif_match = re.search(r"(.*?)\s*\(([A-Z0-9]{12})\)", bloc)
        date_match = re.search(r"(\d{2}-\d{2}-\d{4})\s+Référence", bloc)
        qc_match = re.search(r"Quantité\s+(\d+)\s+Cours\s+([\d,]+)\s*€", bloc)
        frais_match = re.search(r"Courtage et Commission\s+([\d,]+)\s*€", bloc)
        
        if actif_match and date_match and qc_match and frais_match:
            jour, mois, annee = date_match.group(1).split("-")
            
            operations.append({
                "date": f"{annee}-{mois}-{jour}",
                "nom": actif_match.group(1).strip(),
                "isin": actif_match.group(2),
                "quantite": int(qc_match.group(1)),
                "prix_unitaire": float(qc_match.group(2).replace(",", ".")),
                "frais": float(frais_match.group(1).replace(",", "."))
            })
            
    return operations

def sauvegarder_en_base(operations):
    with Session(engine) as session:
        utilisateur = session.query(User).filter_by(email="admin@test.com").first()
        if not utilisateur:
            utilisateur = User(email="admin@test.com", hashed_password="mdp")
            session.add(utilisateur)
            session.commit()

        print(f"Enregistrement pour l'utilisateur {utilisateur.email} (ID: {utilisateur.id})")

        for op in operations:
            actif = session.query(Actif).filter_by(isin_code=op['isin']).first()
            if not actif:
                print(f"Création de l'actif {op['nom']} (ISIN: {op['isin']})")
                actif = Actif(
                    isin_code=op['isin'],
                    nom_etf=op['nom'],
                    ticker_yfinance="A_DEFINIR"
                )
                session.add(actif)
                session.commit()
            
            date_transaction = datetime.strptime(op['date'], "%Y-%m-%d").date()
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
            session.add(nouvelle_transaction)
        session.commit()
        print("Toutes les transactions ont été enregistrées en base.")

if __name__ == "__main__":
    dossier_data = "data"
    fichiers = glob.glob(os.path.join(dossier_data, "*.pdf"))

    if not fichiers:
        print(f"Aucun fichier PDF trouvé dans le dossier '{dossier_data}'. Veuillez ajouter un fichier PDF d'avis d'opération.")
    else:
        print(f"Fichiers PDF trouvés : {fichiers}")
        operations_all = []
        for fichier in fichiers:
            
            print(f"Traitement du fichier : {fichier}")
            operations = extraire_transactions(fichier)
            operations_all.extend(operations)
            print(f"Transactions extraites : {operations}")
        print(f"Total des transactions extraites : {len(operations_all)}")
        sauvegarder_en_base(operations_all)