# UALFlix

Sistema de Streaming de Videos Curtos baseado em microserviços desenvolvido com Flask, PostgreSQL e Redis.

## Arquitetura

- **Catalog Service** (porta 5000): Gestão de vídeos e metadados
- **Streaming Service** (porta 5001): Servir conteúdo de vídeo
- **UI Service** (porta 8000): Interface web
- **PostgreSQL**: Base de dados principal
- **Redis**: Cache e broker para Celery
- **Celery**: Processamento assíncrono

## Execução

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f kubernetes/
```

## Acesso
- Interface: http://localhost:8000
- API Catalog: http://localhost:5000
- API Streaming: http://localhost:5001


## Licença
GNU v3.0
