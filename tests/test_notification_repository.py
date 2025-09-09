import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Percorso alla cartella src
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))

if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Importazioni
from clorofillo.persistence.orm_models import NotificationORM, Base
from clorofillo.persistence.notification_repository import NotificationRepository
from clorofillo.model.notification import Notification


def main():
    # Setup DB (usando database persistente)
    db_path = os.path.join(current_dir, '..', 'data', 'db.sqlite')
    engine = create_engine(f'sqlite:///{db_path}', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    repo = NotificationRepository(session)

    # Creazione oggetto dominio
    notif = Notification(
        id=None,  # Lascia che il DB assegni l'ID
        timestamp=datetime.now(),
        pot=1,
        description="Test: livello acqua basso"
    )

    # Conversione in ORM e inserimento
    notif_orm = notif.to_orm()
    repo.insert(notif_orm)
    session.commit()

    print(f"Notification salvata con id: {notif_orm.id}")

    # Recupero
    loaded_orm = repo.get_by_id(notif_orm.id)
    loaded_notif = Notification.from_orm(loaded_orm)

    print("Notifica caricata dal DB:")
    print(f"ID: {loaded_notif.id}")
    print(f"Timestamp: {loaded_notif.timestamp}")
    print(f"Pot: {loaded_notif.pot}")
    print(f"Descrizione: {loaded_notif.description}")

    # Test non trovato
    if repo.get_by_id(-1) is None:
        print("Notifica non trovata")

    session.close()

if __name__ == "__main__":
    main()
