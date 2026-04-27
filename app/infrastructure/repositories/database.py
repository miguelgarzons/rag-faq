import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# URL de la base de datos. Docker Compose pasa esto como variable de entorno.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secreto@localhost:5432/faq_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()