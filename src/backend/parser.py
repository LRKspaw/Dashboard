import pdfplumber
import os
import re

PDF_PATH = "data/Avis_Operation_Mai_2026.pdf"

def extraire_transactions(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"    
    regex_actif = r"TRACKER\s*:\s*(.*?)\s*\(([A-Z0-9]{12})\)"
    regex_date = r"(\d{2}-\d{2}-\d{4})\s+Référence"
    regex_quantite_cours = r"Quantité\s+(\d+)\s+Cours\s+([\d,]+)\s*€"
    regex_frais = r"Courtage et Commission\s+([\d,]+)\s*€"

    actifs = re.findall(regex_actif, text)
    dates = re.findall(regex_date, text)
    quantite_cours = re.findall(regex_quantite_cours, text)
    frais = re.findall(regex_frais, text)

    operations = []

    for i in range(len(actifs)):
        nom_etf = actifs[i][0].strip()
        isin_code = actifs[i][1]

        jour, mois, annee = dates[i].split("-")
        date = f"{annee}-{mois}-{jour}"
        quantite = int(quantite_cours[i][0])
        cours = float(quantite_cours[i][1].replace(",", "."))
        frais_montant = float(frais[i].replace(",", "."))

        transaction = {
            "date": date,
            "nom": nom_etf,
            "isin": isin_code,
            "quantite": quantite,
            "prix_unitaire": cours,
            "frais": frais_montant
        }
        operations.append(transaction)
    return operations

if __name__ == "__main__":
    if os.path.exists(PDF_PATH):
        resultats = extraire_transactions(PDF_PATH)
        print(f"J'ai trouvé {len(resultats)} opérations :\n")
        
        for op in resultats:
            print(f"Le {op['date']} : Achat de {op['quantite']} x {op['nom']} ({op['isin']})")
            print(f"   Prix : {op['prix_unitaire']}€/unité | Frais : {op['frais']}€\n")
    else:
        print(f"Erreur : fichier introuvable.")