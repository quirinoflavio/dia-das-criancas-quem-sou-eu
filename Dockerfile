# Single-image: builda o frontend e serve tudo pelo FastAPI.
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# o vite build escreve em ../app/static; aqui redirecionamos para /fe/dist
RUN npm run build -- --outDir dist --emptyOutDir

FROM python:3.12-slim AS runtime
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY app/ ./app/
# copia a SPA buildada para onde o backend serve
COPY --from=frontend /fe/dist/ ./app/static/
EXPOSE 8000
VOLUME ["/srv/data"]
ENV DATA_DIR=/srv/data CORS_ORIGINS=""
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
