import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from google.cloud.sql.connector import Connector, IPTypes
except Exception:
    Connector = None
    IPTypes = None

def _is_true(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_cloud_sql_engine():
    if Connector is None:
        raise RuntimeError(
            "cloud-sql-python-connector no esta instalado. "
            "Agrega la dependencia para usar Cloud SQL Connector."
        )

    instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME", "").strip()
    db_user = os.getenv("DB_USER", "").strip()
    db_pass = os.getenv("DB_PASS", "")
    db_name = os.getenv("DB_NAME", "").strip()

    missing = [
        name
        for name, value in [
            ("INSTANCE_CONNECTION_NAME", instance_connection_name),
            ("DB_USER", db_user),
            ("DB_PASS", db_pass),
            ("DB_NAME", db_name),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Faltan variables para Cloud SQL Connector: " + ", ".join(missing)
        )

    ip_type_raw = os.getenv("DB_IP_TYPE", "PUBLIC").strip().upper()
    ip_type = IPTypes.PRIVATE if ip_type_raw == "PRIVATE" else IPTypes.PUBLIC

    connector = Connector()

    def getconn():
        return connector.connect(
            instance_connection_name,
            "psycopg2",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type=ip_type,
        )

    return create_engine(
        "postgresql+psycopg2://",
        creator=getconn,
        pool_pre_ping=True,
    )


instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
use_cloud_sql_connector_env = os.getenv("USE_CLOUD_SQL_CONNECTOR")

if use_cloud_sql_connector_env is None:
    use_cloud_sql_connector = bool(instance_connection_name)
else:
    use_cloud_sql_connector = _is_true(use_cloud_sql_connector_env)

if use_cloud_sql_connector:
    engine = _build_cloud_sql_engine()
else:
    # URL de la base de datos. Docker Compose pasa esto como variable de entorno.
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://admin:secreto@localhost:5432/faq_db"
    )
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
