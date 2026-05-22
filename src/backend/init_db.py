from sqlalchemy.orm import Session
from src.backend.database import engine, Base
from src.backend.models import User  

print("Connexion à la base de données...")
Base.metadata.create_all(bind=engine)
print("Les tables ont été vérifiées/créées avec succès !")

with Session(engine) as session:
    user_demo = session.query(User).filter_by(id=1).first()
    
    if not user_demo:
        print("Aucun utilisateur trouvé. Création de l'utilisateur par défaut (ID: 1)...")
        user_demo = User(
            id=1,  
            email="demo@dashboardpea.local",
            hashed_password="1"  
        )
        session.add(user_demo)
        session.commit()
        print("Utilisateur par défaut créé avec succès.")
    else:
        print("L'utilisateur par défaut existe déjà.")

print("Base de données prête pour l'ingestion !")