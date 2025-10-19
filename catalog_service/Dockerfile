# Imagem do Python
FROM python:3.10-slim

# Diretório da App
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copia o código da aplicação
COPY . .

# Expõe a porta do serviço
EXPOSE 5000

# Comando de arranque do container
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]