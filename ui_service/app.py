# Imports Gerais
import os
from datetime import datetime

# Imports Extra
import aiofiles
import httpx
from fastapi import (FastAPI, Request, UploadFile, File, Form, Header, Response, HTTPException)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

# Imports dos Ficheiros
BASE_DIR = os.path.dirname(__file__)
CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog_service:5000")
STREAMING_URL = os.getenv("STREAMING_URL", "http://streaming_service:5001")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "static", "uploads"))

class CachingStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

app = FastAPI(title="UI Service")
app.mount("/static", CachingStaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Endpoint para verificação de saúde do serviço do UI
@app.get("/healthz", status_code=200)
async def health_check():
    return {"status": "ok"}

# Mostra a página principal com o catálogo de vídeos
@app.get("/")
async def index(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CATALOG_URL}/videos/")
        response.raise_for_status()
        videos = response.json()
    
    # Adiciona um parâmetro para evitar cache do browser no streaming
    for video in videos:
        updated_ts = int(datetime.fromisoformat(video["updated_time"]).timestamp())
        video["stream_url"] = f"/stream/{video['id']}?v={updated_ts}"
    return templates.TemplateResponse(request, "index.html", {
        "videos": videos
    })

# Mostra a página de upload de vídeos
@app.get("/upload")
async def upload_form(request: Request):
    return templates.TemplateResponse(request, "upload.html")

# Faz proxy do upload do ficheiro para o catalog_service
@app.post("/upload")
async def upload(request: Request):
    async with httpx.AsyncClient() as client:
        # Faz stream do corpo do pedido diretamente para o catalog_service
        resp = await client.post(
            f"{CATALOG_URL}/videos/",
            headers={k: v for k, v in request.headers.items() if k.lower() not in ('host', 'transfer-encoding')},
            content=request.stream(),
            timeout=None
        )
    # Retorna a resposta exata do catalog_service para o browser
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# Mostra a página para ver o video
@app.get("/watch/{video_id}")
async def watch(request: Request, video_id: int):
    async with httpx.AsyncClient() as client:
        # Fetch do video que é para ser visualizado
        video_resp = await client.get(f"{CATALOG_URL}/videos/{video_id}")
        if video_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Vídeo não encontrado")
        video = video_resp.json()

        # Fetch de todos os videos para a sidebar
        videos_resp = await client.get(f"{CATALOG_URL}/videos/")
        videos_resp.raise_for_status()
        all_videos = videos_resp.json()

    # Adicionar um URL de Stream para todos os videos
    for v in all_videos:
        updated_ts = int(datetime.fromisoformat(v["updated_time"]).timestamp())
        v["stream_url"] = f"/stream/{v['id']}?v={updated_ts}"
        
    # Cria um URL de Stream para o video atual
    updated_ts = int(datetime.fromisoformat(video["updated_time"]).timestamp())
    stream_url = f"/stream/{video_id}?v={updated_ts}"

    return templates.TemplateResponse(request, "watch.html", {
        "video": video,
        "stream_url": stream_url,
        "videos": [v for v in all_videos if v['id'] != video_id]
    })

# Mostra o painel de administração com a lista de vídeos
@app.get("/admin")
async def admin_panel(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CATALOG_URL}/videos/")
        response.raise_for_status()
        videos = response.json()
    return templates.TemplateResponse(request, "admin.html", {
        "videos": videos
    })

# Mostra a pagina do formulário para editar um vídeo
@app.get("/admin/edit/{video_id}")
async def edit_form(request: Request, video_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CATALOG_URL}/videos/{video_id}")
        response.raise_for_status()
        video = response.json()
    return templates.TemplateResponse(request, "edit.html", {
        "video": video
    })

# Processa a edição de um vídeo, enviando os dados para o catalog_service
@app.post("/admin/edit/{video_id}")
async def do_edit(
    video_id: int,
    title: str = Form(...),
    description: str = Form(None),
    duration: int = Form(...),
    file: UploadFile = File(None)):
    data = {"title": title, "description": description, "duration": duration}
    async with httpx.AsyncClient() as client:
        if file and file.filename:
            temp_path = os.path.join(UPLOAD_DIR, file.filename)
            try:
                async with aiofiles.open(temp_path, "wb") as out_f:
                    content = await file.read()
                    await out_f.write(content)
                
                with open(temp_path, "rb") as f:
                    files = {"file": (file.filename, f, file.content_type)}
                    resp = await client.put(f"{CATALOG_URL}/videos/{video_id}", data=data, files=files, timeout=None)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            resp = await client.put(f"{CATALOG_URL}/videos/{video_id}", data=data, timeout=None)

    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# Faz proxy do pedido de apagar para o catalog_service
@app.delete("/api/videos/{video_id}")
async def delete_proxy(video_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{CATALOG_URL}/videos/{video_id}")
    return {"ok": resp.status_code == 200}

# Faz proxy da verificação de estado da tarefa para o catalog_service
@app.get("/api/videos/task/{task_id}")
async def task_status_proxy(task_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CATALOG_URL}/videos/task/{task_id}")
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# Faz proxy do stream de vídeo, preservando cabeçalhos Range
@app.get("/stream/{video_id}")
async def proxy_stream(video_id: int, range: str = Header(None)):
    headers = {"Range": range} if range else {}
    async with httpx.AsyncClient() as client:
        upstream = await client.get(
            f"{STREAMING_URL}/stream/{video_id}",
            headers=headers,
            timeout=None
        )
    # Reencaminha apenas os cabeçalhos necessários para o streaming
    resp_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() in ("content-length", "content-range", "accept-ranges", "content-type")
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=resp_headers
    )