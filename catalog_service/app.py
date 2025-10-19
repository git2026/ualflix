# Imports Gerais
import os
import shutil
import time
import uuid
import json
from contextlib import asynccontextmanager

# Imports Extra
import redis
from celery.result import AsyncResult
from fastapi import (FastAPI, HTTPException, UploadFile, File, Form, Depends, Request)
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import Response

# Imports dos Ficheiros
from controller import (list_videos, get_video, update_video, delete_video, get_db)
from model import init_db
from tasks import process_video_upload, TEMP_UPLOAD_DIR, BASE_UPLOAD_DIR, app_celery

# Gere o ciclo de vida da aplicação, ininciando a BD e Redis.
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
    init_db()
    yield
    redis_client.close()

# Garante que os diretórios de upload existem ao iniciar, entre outras definições
app = FastAPI(title="Catalog Service", lifespan=lifespan)
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
redis_client = None


# Fornece a instância do cliente Redis às rotas.
def get_redis():
    return redis_client

# Verifica a ligação à base de dados.
@app.get("/healthz", status_code=200)
def health_check(db: Session = Depends(get_db)):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise HTTPException(status_code=503, detail=f"A ligação à base de dados falhou após {max_retries} tentativas: {e}")

# Devolve a lista de todos os vídeos
@app.get("/videos/")
def videos_list(response: Response, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return list_videos(db, redis_client)

# Devolve os detalhes de um vídeo específico
@app.get("/videos/{video_id}")
def video_detail(video_id: int, response: Response, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return get_video(db, video_id, redis_client)

# Devolve o ficheiro de vídeo para streaming.
@app.get("/videos/{video_id}/file")
def video_file(video_id: int, db: Session = Depends(get_db)):
    video = get_video(db, video_id)
    return FileResponse(video.file_path, media_type="video/mp4")

# Recebe um upload e cria uma tarefa em background para o processar.
@app.post("/videos/")
async def enqueue_upload_video(
    title: str = Form(...),
    description: str = Form(None),
    duration: int = Form(..., ge=0, le=9999),
    file: UploadFile = File(...),
    redis_client: redis.Redis = Depends(get_redis)):
    _, ext = os.path.splitext(file.filename)
    temp_filename = f"{uuid.uuid4()}{ext}"
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, temp_filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Falha ao guardar o ficheiro temporário: {e}")
    finally:
        await file.close()

    task = process_video_upload.apply_async(
        args=[title, description, duration, temp_file_path, file.filename],
        kwargs={},
        queue='catalog_queue')
    redis_client.delete("videos_list")
    return JSONResponse(
        status_code=202, 
        content={"message": "Upload recebido, a processar no background.", "task_id": task.id})

# Verifica o estado de uma tarefa Celery
@app.get("/videos/task/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=app_celery)
    if task_result.ready():
        if task_result.successful():
            return {"status": "SUCCESS", "result": task_result.get()}
        else:
            raise HTTPException(status_code=500, detail=str(task_result.info))
    else:
        return {"status": "PENDING"}

# Atualiza os dados de um vídeo
@app.put("/videos/{video_id}")
async def edit_video(
    video_id: int,
    title: str = Form(...),
    description: str = Form(None),
    duration: int = Form(..., ge=0, le=9999),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)):
    file_path_to_update = None
    video_data = get_video(db, video_id, redis_client)
    
    if file:
        _, ext = os.path.splitext(file.filename)
        unique_filename = f"{video_id}_{uuid.uuid4()}{ext}"
        file_path_to_update = os.path.join(BASE_UPLOAD_DIR, unique_filename)

        try:
            with open(file_path_to_update, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            if video_data and video_data.get('file_path'):
                old_path = video_data['file_path']
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"Aviso: não foi possível remover o ficheiro antigo: {old_path}, erro: {e}")
                        
        except Exception as e:
            if os.path.exists(file_path_to_update):
                os.remove(file_path_to_update)
            raise HTTPException(status_code=500, detail=f"Falha ao guardar o ficheiro: {str(e)}")
        finally:
            await file.close()
    result = update_video(db, video_id, title, description, duration, redis_client, new_file_path=file_path_to_update)
    return result

# Apaga um vídeo
@app.delete("/videos/{video_id}")
def remove_video(video_id: int, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    return delete_video(db, video_id, redis_client)