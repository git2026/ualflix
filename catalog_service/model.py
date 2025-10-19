# Imports Gerais
import os
from datetime import datetime

# Imports Extras
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Configuração da Base de Dados
Base = declarative_base()
DB_USER = os.getenv("DB_USER", "ualflix")
DB_PASSWORD = os.getenv("DB_PASSWORD", "senha123")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "catalogdb")

# Configuração do Engine do SQLAlchemy com um pool de conexões robusto:
# - pool_pre_ping: Verifica se a conexão está ativa antes de cada uso
# - pool_recycle: Recicla ligações a cada 30 minutos para evitar timeouts
# - connect_args: Argumentos de keepalive TCP para manter as conexões estáveis
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

# Definição  do modelo da tabela 'videos' para o SQLAlchemy
class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    updated_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Inicialização das Tabelas na BD nos modelos definidos
def init_db():
    Base.metadata.create_all(bind=engine)