# Tasks — "Quem Sou Eu?" (Jogo do Dia das Crianças)

Lista ordenada e executável. Cada tarefa é incremental, verificável e referencia
os requisitos (RF/RNF) que atende. Marque `[x]` ao concluir. A ordem é
sequencial salvo onde indicado "pode ser paralela". Backend em Python
(FastAPI); frontend em Preact/TS (Vite); tema 8-bit pixel art.

Legenda: cada tarefa lista **Entrega** (o que fica pronto), **Verificação**
(como provar que funciona) e **Reqs** (rastreabilidade).

---

## Fase A — Fundações do projeto

- [x] **A1. Esqueleto do backend**
  - Entrega: projeto Python (`pyproject.toml`), FastAPI + Uvicorn, estrutura
    `app/` (`main.py`, `routes/`, `domain/`, `services/`, `realtime/`),
    `.env.example` (`IMAGE_PROVIDER`, `IMAGE_API_KEY`, `ROOM_TTL_HOURS=24`,
    `MAX_UPLOAD_MB=10`, `DATA_DIR=./data`), config via Pydantic Settings.
  - Verificação: `uvicorn app.main:app` sobe; `GET /api/health` responde 200.
  - Reqs: RNF-6.

- [x] **A2. Esqueleto do frontend**
  - Entrega: app Vite + Preact + TS, roteador leve (Home/Lobby/Round/Reveal/
    Scoreboard como rotas vazias), build estático servido pelo FastAPI em prod
    (StaticFiles + fallback para index). Gera/lê `identityToken` (uuid4) em
    `localStorage` num hook `useIdentity`.
  - Verificação: `npm run dev` abre a Home; build integra ao backend e carrega
    em `/`.
  - Reqs: RF-1.4, RNF-5, RNF-7, RNF-8. (Pode ser paralela a A1.)

- [x] **A3. Tema 8-bit (theme.css + componentes base)**
  - Entrega: `theme.css` com os tokens da §10b (paleta, bordas/sombras de pixel,
    overlay de scanlines, `prefers-reduced-motion`); fontes bitmap self-hosted
    (Press Start 2P + VT323/Silkscreen); componentes `PixelPanel`,
    `ArcadeButton`, `PixelFrame`, `Hud`, `Scoreboard` (shells estilizados, sem
    lógica); `image-rendering: pixelated` global para sprites.
  - Verificação: página de "style guide" interna renderiza cada componente;
    contraste AA verificado; `prefers-reduced-motion` desliga scanlines/piscar.
  - Reqs: §10b, RNF-5.

## Fase B — Domínio e regras (lógica pura, testável)

- [x] **B1. Modelo de domínio**
  - Entrega: dataclasses/Pydantic de `Room`, `RoomConfig`, `Player`, `PhotoRef`,
    `Round` e enums (`Phase`, `DisplayMode`, `RevealMode`, `GenStatus`,
    `RoundStatus`) conforme §4. Geração de código de sala (alfabeto sem
    ambíguos, 6 chars, unicidade).
  - Verificação: testes de criação/serialização; códigos únicos e sem 0/O/1/I.
  - Reqs: RF-1.1, RF-3.

- [x] **B2. GameEngine — montagem de rodadas**
  - Entrega: função que recebe jogadores + `targets_per_round` e produz as
    `Round`s (shuffle, partição em grupos de k com resto, resolução do
    `display_mode` por alvo incluindo RANDOM) — §6.
  - Verificação: testes: 7 jogadores k=3 → [3,3,1]; k=1 → 7 rodadas; RANDOM
    sorteia só entre CHILD/GENERATED/BOTH; ordem imprevisível (não ordenada por
    entrada).
  - Reqs: RF-6.2, RF-6.3, RF-3.1, RF-3.3.

- [x] **B3. GameEngine — votação e encerramento**
  - Entrega: registrar/alterar voto por alvo; impedir voto do alvo sobre si
    mesmo; cálculo de `vote_progress`; encerramento automático quando todos os
    votantes elegíveis completaram todos os alvos; `force_close_round` (host).
  - Verificação: testes cobrindo rodada agrupada (2–3 alvos), troca de voto,
    bloqueio do auto-voto, progresso correto, fechamento automático vs forçado.
  - Reqs: RF-7.3, RF-7.4, RF-7.5, RF-7.6, RF-7.8, decisão "encerramento automático".

- [x] **B4. GameEngine — pontuação e placar**
  - Entrega: +1 por acerto por alvo; placar ordenado desc; empates compartilham
    posição; identificação de vencedor(es).
  - Verificação: testes: acerto único, múltiplos acertos em rodada agrupada,
    empate triplo, zero acertos.
  - Reqs: RF-8.2, RF-8.3, decisão "1 ponto por acerto".

- [x] **B5. Máquina de estados da sala**
  - Entrega: transições `LOBBY→GENERATING/PLAYING→REVEAL→(PLAYING|FINISHED)`
    com validação de pré-condições e permissão de host; derivação de REVEAL por
    `reveal_mode` (PER_ROUND vs END_OF_GAME) — §5.
  - Verificação: testes: início bloqueado sem fotos/geração; PER_ROUND alterna
    reveal↔playing; END_OF_GAME joga tudo e revela ao fim.
  - Reqs: RF-6.1, RF-8.1, RF-8.4, RF-3.6.

## Fase C — Armazenamento, imagens e geração

- [x] **C1. ImageStore + upload/validação**
  - Entrega: `POST /api/rooms/{code}/photo` (multipart): valida MIME
    (JPEG/PNG/WebP) e tamanho (`MAX_UPLOAD_MB`), normaliza com Pillow (reorienta
    EXIF, reencoda removendo metadados, limita dimensão), salva em
    `data/images/<room>/`, associa ao jogador, marca "foto enviada".
  - Verificação: upload válido salva e associa; arquivo grande/inválido é
    rejeitado; EXIF removido no arquivo final; preview possível no cliente.
  - Reqs: RF-4.1, RF-4.2, RF-4.3, RNF-1.

- [x] **C2. Interface ImageGenerator + GeminiAdapter**
  - Entrega: `Protocol ImageGenerator.generate_adult(bytes, mime)`; `GeminiAdapter`
    via `httpx` com prompt centralizado (versão adulta realista, preserva
    traços), timeout (~60s) e `ImageGenError`; seleção por `IMAGE_PROVIDER`.
  - Verificação: teste com adapter fake (sucesso/erro/timeout); chamada real
    atrás de flag/manual (não em CI). Sem chave → erro claro na inicialização.
  - Reqs: RF-5.1, RF-5.6, RNF-3, decisão "provedor plugável".

- [x] **C3. Geração assíncrona + status + retry**
  - Entrega: background task dispara geração quando foto confirmada E modo exige
    gerada; atualiza `gen_status` (PENDING→GENERATING→READY|FAILED) e
    `generated_photo`; `POST .../photo/regen` para retry; não dispara se o modo
    não exige.
  - Verificação: status transita e emite evento; falha → FAILED + retry
    funciona; trocar para modo sem geração não dispara novas.
  - Reqs: RF-5.2, RF-5.3, RF-5.4, RNF-4.

- [x] **C4. Serviço de imagens com autorização e privacidade**
  - Entrega: `GET /api/rooms/{code}/images/{imageId}` serve só a membros da sala
    e só quando o estado de jogo libera aquela imagem; `Cache-Control: private`,
    `X-Robots-Tag: noindex`.
  - Verificação: não-membro recebe 403; imagem de alvo não liberada recebe 403;
    liberada na revelação é servida; headers presentes.
  - Reqs: RNF-1, RF-4.5, RF-7.7, RF-8.1.

## Fase D — API REST e ciclo de vida

- [x] **D1. RoomManager + rotas de sala**
  - Entrega: `RoomManager` (criar/obter/encerrar, registro em memória);
    `POST /api/rooms` (cria + host + identityToken), `POST .../join` (erros
    404/409/423/403, limite 3–12, só em LOBBY), `PATCH .../config` (host, só
    LOBBY), `POST .../start` (pré-condições), `POST .../close`.
  - Verificação: testes de API para cada rota e cada erro; join após start é
    bloqueado; config travada fora do lobby; start exige fotos/geração.
  - Reqs: RF-1, RF-2, RF-3, RF-6.1.

- [x] **D2. Persistência (snapshot + reload)**
  - Entrega: snapshot JSON debounced por mutação em `data/rooms/<code>.json`;
    reload de salas não expiradas no start do processo (imagens referenciadas
    por `PhotoRef`).
  - Verificação: reiniciar o processo preserva sala/jogadores/fotos; sala
    expirada não é recarregada.
  - Reqs: RF-9.2 (parcial), RF-10.

- [x] **D3. Limpeza por TTL**
  - Entrega: background task periódica remove salas inativas > `ROOM_TTL_HOURS`
    (snapshot + diretório de imagens); `close` faz imediato; acesso a sala
    expirada retorna estado "encerrada".
  - Verificação: sala envelhecida é apagada (arquivos somem); link de sala
    encerrada mostra a tela correta.
  - Reqs: RF-10.1, RF-10.2, RF-10.3, RNF-1.

## Fase E — Tempo real (WebSocket)

- [x] **E1. WS hub + conexão por sala**
  - Entrega: `GET /ws/rooms/{code}?token=...`; registra conexão por jogador;
    envia `room_state` projetado ao conectar; `ping`/keepalive; broadcast por
    sala.
  - Verificação: dois clientes na mesma sala; conectar entrega estado atual;
    desconectar/reconectar reentrega estado (volta ao ponto).
  - Reqs: RF-9.1, RF-9.2, RF-9.3.

- [x] **E2. Projeção por destinatário**
  - Entrega: montagem do `room_state`/eventos por destinatário conforme §8:
    lobby sem fotos de terceiros; durante VOTING só imagens do alvo no estágio
    permitido; votos individuais ocultos; identidades/votos só em REVEAL.
  - Verificação: testes de projeção: cliente nunca recebe dado não autorizado em
    cada fase; `vote_progress` agregado sem revelar quem votou em quem.
  - Reqs: RF-4.5, RF-7.7, RF-8.1, RNF-1.

- [x] **E3. Eventos de jogo via WS**
  - Entrega: handlers `vote`, `advance_image` (modos SEQ_*), `force_close_round`,
    `next` (avança rodada/revelação/finaliza) — todos validando host/fase;
    emissão de `player_joined/left/updated`, `config_updated`, `round_started`,
    `vote_progress`, `image_advanced`, `round_revealed`, `game_revealed`,
    `error`.
  - Verificação: fluxo completo de uma rodada via WS em teste de integração;
    permissões de host respeitadas; eventos chegam a todos.
  - Reqs: RF-7, RF-8, RF-9.1.

## Fase F — Frontend (telas, tema 8-bit)

- [x] **F1. Home (criar/entrar)**
  - Entrega: criar sala (apelido) → recebe código + link compartilhável; entrar
    por código (link preenche o código); tratamento de erros de join; estilo
    arcade (tela de "INSERT COIN").
  - Verificação: criar e entrar funcionam ponta a ponta; link abre com código
    preenchido; erros exibidos.
  - Reqs: RF-1.1–1.3, RF-2.1–2.3.

- [x] **F2. Lobby**
  - Entrega: lista de participantes com status (foto enviada / gen PENDING/
    GENERATING/READY/FAILED), upload com preview (câmera/galeria no mobile),
    painel de config do host (6 modos de exibição, reveal mode, targets/round)
    com resumo das regras em tempo real, botão "START" habilitado só nas
    pré-condições; retry de geração.
  - Verificação: config propaga em tempo real; "START" só habilita com 3–12
    jogadores, todas as fotos e (se exige) geradas prontas; não revela fotos no
    lobby.
  - Reqs: RF-3, RF-4, RF-5.2, RF-6.1.

- [x] **F3. Tela de Rodada/Votação**
  - Entrega: `PixelFrame`(s) do(s) alvo(s) conforme modo (foto nítida dentro da
    moldura pixel; scanlines opcionais); grade de nomes para votar (um voto por
    alvo; próprio nome bloqueado quando você é o alvo); HUD "VOTES X/N";
    controles do host (avançar imagem nos modos SEQ_*, forçar encerramento,
    próxima); troca de voto até fechar.
  - Verificação: todos veem o alvo simultaneamente; voto registra/altera;
    auto-voto bloqueado; rodada agrupada pede um voto por alvo; progresso
    correto.
  - Reqs: RF-7.1–7.8.

- [x] **F4. Revelação + Placar**
  - Entrega: revelação com efeito "power-up" (identidade, foto criança + gerada,
    mapa de quem votou em quem); placar parcial (PER_ROUND) ou sequência de
    revelações (END_OF_GAME); tela final "HIGH SCORE" com medalhas e empate;
    botão "jogar de novo" (nova sala reusando participantes/fotos, com opção de
    regerar).
  - Verificação: revelação mostra tudo corretamente; placar reflete pontuação;
    empate compartilha posição; "jogar de novo" cria sala reaproveitando dados.
  - Reqs: RF-8.1–8.5.

- [x] **F5. Reconexão e estados de borda no cliente**
  - Entrega: reconexão automática do WS com reidratação do estado; telas de
    "sala encerrada", "jogo já começou", perda de host (jogo não trava), erros
    de rede amigáveis.
  - Verificação: derrubar/reconectar o socket volta ao ponto; host reconecta e
    retoma controle; sala expirada mostra tela correta.
  - Reqs: RF-9.2, RF-9.3, RF-10.2.

## Fase G — Qualidade, segurança e entrega

- [x] **G1. Rate limiting e hardening**
  - Entrega: rate limit simples por IP/token em `POST /api/rooms` e upload;
    limites de tamanho/dimensão reforçados; validação de todos os inputs.
  - Verificação: exceder limite retorna 429; uploads abusivos barrados.
  - Reqs: RNF-1, §12.

- [x] **G2. Testes de integração ponta a ponta**
  - Entrega: cenário completo automatizado (criar → 4 jogadores entram → fotos
    (geração fake) → start → rodadas (incl. agrupada) → votos → revelação →
    placar) para os modos END_OF_GAME e PER_ROUND, k=1 e k=3.
  - Verificação: suíte verde cobrindo os caminhos principais e os erros chave.
  - Reqs: RF-6..RF-9.

- [x] **G3. Acessibilidade e mobile**
  - Entrega: auditoria do tema (contraste AA, foco visível, área de toque
    ≥44px, `prefers-reduced-motion`), layout testado em viewport de celular.
  - Verificação: checklist de a11y passa; fluxo jogável só com o polegar no
    celular.
  - Reqs: §10b (acessibilidade), RNF-5.

- [x] **G4. Empacotamento e execução local**
  - Entrega: `README` com setup (venv, `.env`, `npm build`, `uvicorn`),
    `Dockerfile` opcional single-image (build do front + serve pelo back),
    instruções de self-host; sem serviços pagos além da API de imagem.
  - Verificação: do zero, seguindo o README, a app sobe e um jogo completo roda
    localmente; container (se usado) serve front+back.
  - Reqs: RNF-6, §15.

---

### Ordem de execução recomendada
A → B (lógica pura cedo, com testes) → C → D → E → F → G. B pode andar em
paralelo a A2/A3. As tarefas de frontend (F) dependem de D/E prontos para
integração real, mas F1–F2 podem começar contra mocks assim que A3 existir.
