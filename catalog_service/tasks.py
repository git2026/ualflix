# Imports Gerais
import os
import shutil
import uuid
import warnings
import subprocess

# Imports Extra
import redis
from celery import Celery
from sqlalchemy.orm import Session

# Imports dos Ficheiros
from controller import create_video as create_video_in_db
from model import SessionLocal

# Remove avisos do worker Celery sobre os privilégios de superuser
try:
    from celery.platforms import SecurityWarning as CeleryPlatformsSecurityWarning
    warnings.filterwarnings(
        "ignore",
        category=CeleryPlatformsSecurityWarning,
        message="You're running the worker with superuser privileges"
    )
except ImportError:
    warnings.filterwarnings(
        "ignore",
        message="You're running the worker with superuser privileges"
    )

# Configuração do Celery
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND_URL", BROKER_URL)

# Instância da Aplicação Celery
app_celery = Celery(
    "catalog_tasks",
    broker=BROKER_URL,
    result_backend=RESULT_BACKEND_URL)

# Diretórios de Upload
BASE_UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/videos")
TEMP_UPLOAD_DIR = os.path.join(BASE_UPLOAD_DIR, "temp")
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# Tarefa em background que move o vídeo para a localizção final e o regista na base de dados
@app_celery.task
def process_video_upload(title: str, description: str, duration: int, temp_file_path: str, original_filename: str):
    db: Session = SessionLocal()
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
    video_id = str(uuid.uuid4())
    _, ext = os.path.splitext(original_filename)
    unique_filename = f"{video_id}{ext}"
    final_file_path = os.path.join(BASE_UPLOAD_DIR, unique_filename)
    
    try:
        shutil.move(temp_file_path, final_file_path)

        video = create_video_in_db(
            db, title=title, description=description, duration=duration, 
            file_path=final_file_path,
            redis_client=redis_client
        )
        video_data = {
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "duration": video.duration,
            "file_path": video.file_path,
            "upload_time": video.upload_time.isoformat(),
            "updated_time": video.updated_time.isoformat()
        }
        return video_data
    except Exception as e:
        print(f"Erro ao processar o vídeo {original_filename}: {e}")
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e_remove:
                print(f"Erro ao remover ficheiro temporário {temp_file_path} após falha: {e_remove}")
        raise
    finally:
        db.close()
        if redis_client:
            redis_client.close()

# Configuração das Rotas de Tarefas Celery
app_celery.conf.update(
    task_routes={
        'tasks.process_video_upload': {'queue': 'catalog_queue'}},
    worker_prefetch_multiplier=1,
    task_acks_late=True,)