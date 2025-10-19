# Imports Gerais
import os
import json

# Imports Extra
import redis
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Imports dos Ficheiros
from model import Video, SessionLocal

# Gere uma sessão de base de dados para cada pedido
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Adiciona um novo vídeo à base de dados e limpa a cache da lista
def create_video(db: Session, title: str, description: str, duration: int, file_path: str, redis_client: redis.Redis):
    video = Video(
        title=title, description=description, duration=duration, 
        file_path=file_path
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    redis_client.delete("videos_list")
    return video

# Procura um vídeo, primeiro no cache e depois na base de dados
def get_video(db: Session, video_id: int, redis_client: redis.Redis):
    cached_video = redis_client.get(f"video:{video_id}")
    if cached_video:
        return json.loads(cached_video)

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    video_data = {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "duration": video.duration,
        "file_path": video.file_path,
        "upload_time": video.upload_time.isoformat(),
        "updated_time": video.updated_time.isoformat(),
    }
    redis_client.set(f"video:{video_id}", json.dumps(video_data), ex=3600)
    return video_data

# Procura a lista de vídeos, primeiro na cache e depois na base de dados
def list_videos(db: Session, redis_client: redis.Redis, skip: int = 0, limit: int = 100):
    cached_videos = redis_client.get("videos_list")
    if cached_videos:
        return json.loads(cached_videos)

    videos = db.query(Video).offset(skip).limit(limit).all()
    videos_data = [
        {
            "id": v.id,
            "title": v.title,
            "description": v.description,
            "duration": v.duration,
            "file_path": v.file_path,
            "upload_time": v.upload_time.isoformat(),
            "updated_time": v.updated_time.isoformat(),
        } for v in videos
    ]
    redis_client.set("videos_list", json.dumps(videos_data), ex=3600)
    return videos_data

# Atualiza os dados de um vídeo existente e limpa os caches
def update_video(
    db: Session,
    video_id: int,
    title: str,
    description: str,
    duration: int,
    redis_client: redis.Redis,
    new_file_path: str = None
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    video.title = title
    video.description = description
    video.duration = duration

    if new_file_path:
        video.file_path = new_file_path
    
    try:
        db.commit()
        redis_client.delete(f"video:{video_id}")
        redis_client.delete("videos_list")
    except Exception as e:
        db.rollback()
        raise

    db.refresh(video)
    return video

# Apaga um vídeo da base de dados e do sistema de ficheiros
def delete_video(db: Session, video_id: int, redis_client: redis.Redis):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    redis_client.delete(f"video:{video_id}")
    redis_client.delete("videos_list")

    if video.file_path and os.path.exists(video.file_path):
        try:
            os.remove(video.file_path)
        except OSError as e:
            print(f"Erro ao apagar ficheiro de vídeo {video.file_path}: {e}")

    db.delete(video)
    db.commit()
    return {"detail": "Vídeo Apagado"}
