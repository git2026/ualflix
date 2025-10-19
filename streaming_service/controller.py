# Imports Gerais
import os
from typing import Iterator

# Imports Extra
import httpx
from fastapi import HTTPException

# Imports dos Ficheiros
from model import VideoMeta

# Configuração do URL
CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog_service:5000")

# Fecth dos metadados de um vídeo a partir do serviço de catálogo
async def fetch_meta(video_id: int) -> VideoMeta:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CATALOG_URL}/videos/{video_id}")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Metadados não encontrados")
        return VideoMeta(**resp.json())