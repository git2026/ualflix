# Imagem do Python
FROM python:3.10-slim

# Diretório da App
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação (Python, templates, estáticos)
COPY app.py ./
COPY templates/ ./templates/
COPY static/    ./static/

# Expõe a porta do serviço
EXPOSE 8000

# Comando de arranque do container
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]