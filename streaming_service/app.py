# Imports Gerais
import os
import re

# Imports Extra
import redis
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

# Imports dos Ficheiros
from controller import fetch_meta

# Configuração da Aplicação
app = FastAPI(title="Streaming Service")

# Ligação ao Redis
try:
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0)
    redis_client.ping()
    print("Ligação ao Redis feita com Sucesso.")
except redis.exceptions.ConnectionError as e:
    print(f"Não foi possível ligar ao Redis: {e}")
    redis_client = None

# Diretório onde vão estar os videos
VIDEO_DIR = os.getenv("VIDEO_DIR", "/app/videos")

# Fornece o stream de um vídeo, suportando 'byte range requests' para streaming parcial
# Utiliza um cache em Redis para acelerar a entrega de segmentos de vídeo
@app.get("/stream/{video_id}")
async def stream_video(video_id: int, range: str = Header(None)):
    try:
        meta = await fetch_meta(video_id)
        path = meta.file_path
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Metadados do vídeo não encontrados ou serviço de catálogo indisponível: {e}")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Ficheiro de vídeo não encontrado no caminho: {path}")
    size = os.path.getsize(path)

    if range:
        m = re.match(r"bytes=(\d+)-(\d*)", range)
        if not m:
            raise HTTPException(status_code=400, detail="Cabeçalho 'Range' inválido")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        length = end - start + 1

        cache_key = f"video:{video_id}:range:{start}:{end}"
        
        # Tenta obter o segmento de vídeo do cache.
        if redis_client:
            cached_chunk = redis_client.get(cache_key)
            if cached_chunk:
                print(f"CACHE HIT para {cache_key}")
                headers = {
                    "Content-Range": f"bytes {start}-{end}/{size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(cached_chunk)),
                    "X-Cache-Status": "HIT"
                }
                return StreamingResponse(iter([cached_chunk]), status_code=206, media_type="video/mp4", headers=headers)
            print(f"CACHE MISS para {cache_key}")

        def chunker(start_pos, chunk_size):
            with open(path, "rb") as f:
                f.seek(start_pos)
                bytes_read = 0
                while bytes_read < chunk_size:
                    chunk = f.read(min(1024 * 1024, chunk_size - bytes_read))
                    if not chunk:
                        break
                    yield chunk
                    bytes_read += len(chunk)

        def cache_and_stream(start_pos, chunk_size):
            # Guarda o segmento de vídeo na cache antes de o enviar.
            with open(path, "rb") as f:
                f.seek(start_pos)
                chunk_to_cache = f.read(chunk_size)
            
            # Armazena o segmento no Redis com um tempo de expiração como 10 minutos
            if redis_client and chunk_to_cache:
                redis_client.setex(cache_key, 600, chunk_to_cache)
                print(f"CACHE GUARDADO para {cache_key}")

            # Envia o segmento de vídeo a partir da memória.
            yield chunk_to_cache
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "X-Cache-Status": "MISS"
        }
        return StreamingResponse(cache_and_stream(start, length), status_code=206, media_type="video/mp4", headers=headers)

    return FileResponse(path, media_type="video/mp4", filename=os.path.basename(path))