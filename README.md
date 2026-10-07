# Quem Sou Eu? 👾

Mini game web, multiplayer e em tempo real, temático de **Dia das Crianças**.
Um grupo de amigos se cadastra, cada um envia uma foto de quando era criança, e
uma API gera a versão "atual" da pessoa. O dono da sala conduz rodadas em que
todos votam **quem é** a pessoa mostrada (foto de criança e/ou gerada); ao final
revelam-se identidades, votos e o placar. Visual **fliperama 8-bit / pixel art**.

## Stack

- **Backend:** Python + FastAPI + WebSocket (estado em memória com snapshots em
  disco; sem banco externo).
- **Frontend:** Vite + Preact + TypeScript (SPA servida pelo backend em produção).
- **Geração de imagem:** interface plugável (`ImageGenerator`); adapters `fake`
  (dev/testes, sem custo) e `gemini`.

## Pré-requisitos

- Python 3.11+ (testado em 3.13)
- Node.js 20+ (testado em 25)

## Setup e execução (desenvolvimento)

```bash
# 1) Backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate   |  Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # ajuste IMAGE_PROVIDER / IMAGE_API_KEY se usar gemini

# 2) Frontend
cd frontend
npm install
npm run build               # gera app/static (servido pelo backend)
cd ..

# 3) Sobe o servidor (serve API + WS + SPA)
uvicorn app.main:app --host 127.0.0.1 --port 8000
# abra http://127.0.0.1:8000
```

### Dev com hot-reload do frontend

```bash
# terminal 1
uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend && npm run dev     # http://localhost:5173 (proxy p/ :8000)
```

## Configuração (`.env`)

| Variável | Default | Descrição |
|---|---|---|
| `IMAGE_PROVIDER` | `fake` | `fake` (sem custo) ou `gemini` |
| `IMAGE_API_KEY` | — | chave do provedor (obrigatória p/ `gemini`) |
| `GEMINI_IMAGE_MODEL` | `gemini-2.0-flash-exp` | modelo de imagem |
| `ROOM_TTL_HOURS` | `24` | tempo de inatividade até a sala/imagens serem apagadas |
| `MAX_UPLOAD_MB` | `10` | tamanho máximo de upload |
| `DATA_DIR` | `./data` | pasta de imagens + snapshots |
| `CORS_ORIGINS` | `http://localhost:5173` | origens de dev (vazio em prod) |

## Testes

```bash
pytest           # regras do jogo (puras) + integração REST/WS (gerador fake)
```

## Fontes bitmap (tema 8-bit)

Para o visual pixel-art completo, baixe e coloque os `.woff2` em
`frontend/public/fonts/` e descomente os `@font-face` em
`frontend/src/theme.css` (ex.: *Press Start 2P* e *VT323*). Sem elas, a UI usa
um fallback monospace — tudo funciona, só muda a fonte. As fontes são
self-hosted (sem CDN de terceiros).

## Privacidade

As fotos (de crianças) nunca são expostas publicamente: o servidor só serve uma
imagem a quem pertence à sala **e** quando o estado do jogo libera aquela imagem
(`projection.py` + autorização em `GET /api/rooms/{code}/images/{id}`). EXIF é
removido no upload. Tudo é apagado quando a sala expira (`ROOM_TTL_HOURS`) ou o
host encerra. Páginas marcadas `noindex`.

## Docker (opcional, single-image)

```bash
docker build -t quem-sou-eu .
docker run --rm -p 8000:8000 --env-file .env quem-sou-eu
# http://127.0.0.1:8000
```

## Estrutura

```
app/                 backend FastAPI
  domain/            modelos + regras puras (engine)
  services/          room_manager, images, generation, persistence, cleanup, ratelimit
  realtime/          hub de WS + projeção por destinatário
  routes/            REST + WebSocket
  static/            SPA buildada (gerada pelo frontend)
frontend/            Vite + Preact + TS
tests/               pytest (domínio puro + integração)
```
