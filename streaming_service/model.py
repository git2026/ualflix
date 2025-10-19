# Imports Gerais
from datetime import datetime
from typing import Optional

# Imports Extra
from pydantic import BaseModel

#  Define a estrutura de dados para os metadados de um vídeo que são recebidos do serviço de catálogo.
class VideoMeta(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    duration: int
    file_path: str
    upload_time: datetime
    updated_time: datetime