from database import engine, Base
import models

print("Connexion à la base de données...")
Base.metadata.create_all(bind=engine)
print("Les tables ont été créées avec succès !")