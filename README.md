# UALFlix: Mini Sistema de Streaming

1.Estrutura de Pastas

ualflix/
├── README.md
├── docker-compose.yml
├── catalog_service/
│   ├── app.py
│   ├── controller.py
│   ├── model.py
│   ├── tasks.py
│   ├── requirements.txt
│   └── Dockerfile
├── streaming_service/
│   ├── app.py
│   ├── controller.py
│   ├── model.py
│   ├── requirements.txt
│   └── Dockerfile
├── ui_service/
│   ├── app.py
│   ├── templates/
│   │   ├── admin.html
│   │   ├── base.html
│   │   ├── edit.html
│   │   ├── index.html
│   │   ├── upload.html
│   │   └── watch.html
│   ├── static/
│   │   ├── css/style.css
│   │   ├── js/admin.js
│   │   ├── js/theme.js
│   │   └── favicon.ico
│   ├── requirements.txt
│   └── Dockerfile
├── videos/video1.mp4
├── kubernetes/
    ├── catalog-deployment.yaml
    ├── ingress.yaml
    ├── postgres-deployment.yaml
    ├── postgres-init-configmap.yaml
    ├── postgres-replica-statefulset.yaml
    ├── redis-deployment.yaml
    ├── streaming-deployment.yaml
    ├── ui-deployment.yaml
    └── videos-pvc.yaml
