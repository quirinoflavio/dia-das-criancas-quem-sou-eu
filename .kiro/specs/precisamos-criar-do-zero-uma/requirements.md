# Requirements — "Quem Sou Eu?" (Jogo do Dia das Crianças)

## 1. Visão geral

Aplicação web multiplayer, em tempo real, para um grupo de amigos jogar um
mini-game temático de Dia das Crianças. Cada participante envia uma foto de
quando era criança; uma API de geração de imagens produz uma versão
"atual/envelhecida" dessa pessoa. O dono da sala conduz rodadas em que o grupo
vota quem é a pessoa mostrada na foto (criança e/ou gerada), e ao final
revelam-se identidades e votos.

O jogo é efêmero: uma sala existe para uma sessão de jogo entre amigos
reunidos (presencial ou por chamada). Não há contas permanentes nem perfis
persistentes de longo prazo.

## 2. Papéis (atores)

- **Host (dono da sala):** cria a sala, define as configurações, controla o
  fluxo (iniciar jogo, avançar rodada, revelar). Também é um jogador.
- **Jogador (participante):** entra na sala com um código, envia a foto de
  criança, vota nas rodadas, vê revelações.
- **Sistema:** gera a foto "atual" via API externa, sorteia a ordem das
  rodadas, apura votos.

## 3. Glossário

- **Sala (room):** instância de jogo identificada por um código curto.
- **Foto de criança:** imagem original enviada pelo participante.
- **Foto gerada:** imagem produzida pela API a partir da foto de criança,
  representando a pessoa "hoje".
- **Rodada (round):** uma unidade de votação sobre uma pessoa-alvo.
- **Alvo (target):** a pessoa cuja identidade está sendo adivinhada na rodada.
- **Voto:** o palpite de um jogador sobre quem é o alvo da rodada.

## 4. Requisitos funcionais

### RF-1 — Criar sala
**História:** Como host, quero criar uma sala e receber um código de convite,
para que meus amigos entrem.

Critérios de aceite:
1. QUANDO o host acessa a home e escolhe "Criar sala" ENTÃO o sistema cria uma
   sala com um código único de 6 caracteres (A–Z, 0–9, sem caracteres ambíguos
   como 0/O e 1/I) e marca esse usuário como host.
2. QUANDO a sala é criada ENTÃO o host informa um apelido (nickname) de 1–20
   caracteres e entra automaticamente como jogador.
3. QUANDO a sala é criada ENTÃO o sistema exibe o código e um link
   compartilhável que leva direto à tela de entrada já com o código preenchido.
4. SE o host fecha a aba e reabre o link dentro da validade da sala ENTÃO ele
   recupera seu papel de host e seu lugar na sala (via identidade persistida no
   navegador).

### RF-2 — Entrar na sala
**História:** Como jogador, quero entrar na sala pelo código, para participar.

Critérios de aceite:
1. QUANDO um jogador informa um código válido e um apelido ENTÃO ele entra na
   sala e aparece na lista de participantes para todos em tempo real.
2. SE o código não existe ou a sala já encerrou ENTÃO o sistema exibe mensagem
   de erro clara e não permite a entrada.
3. SE o apelido já está em uso na sala ENTÃO o sistema rejeita e pede outro.
4. QUANDO o jogo já começou (fase de rodadas) ENTÃO novos jogadores NÃO podem
   entrar; a sala só aceita entradas na fase de lobby/preparação.
5. O sistema impõe um limite de 3 a 12 jogadores por sala.

### RF-3 — Configurar a sala (feito pelo host, antes de iniciar)
**História:** Como host, quero configurar como as fotos aparecem e como a
votação acontece, para adaptar o jogo ao grupo.

Critérios de aceite:
1. QUANDO o host está no lobby ENTÃO pode escolher o **modo de exibição da
   foto** por rodada, dentre:
   - a) apenas foto de criança;
   - b) apenas foto gerada (hoje);
   - c) ambas ao mesmo tempo;
   - d) uma por vez, começando pela de criança (gerada revelada depois, no mesmo alvo);
   - e) uma por vez, começando pela gerada;
   - f) aleatório por rodada (sistema sorteia uma das opções a–c para cada alvo).
2. QUANDO o host configura ENTÃO pode escolher o **momento da revelação**:
   - a) revelar somente ao final de todas as rodadas; ou
   - b) revelar ao final de cada rodada.
3. QUANDO o host configura ENTÃO pode definir o **agrupamento de alvos por
   rodada**: 1 alvo por rodada (padrão), ou 2–3 alvos votados juntos na mesma
   rodada. O número de rodadas resultante é derivado automaticamente do total
   de jogadores e do agrupamento.
4. SE o modo de exibição exige foto gerada (b, c, d, e, e possivelmente f) ENTÃO
   o sistema só permite iniciar o jogo após todas as fotos geradas estarem
   prontas (ver RF-5).
5. QUANDO o host altera uma configuração ENTÃO a mudança é visível para todos
   os jogadores no lobby em tempo real (resumo das regras).
6. As configurações só podem ser alteradas na fase de lobby; após iniciar o
   jogo ficam travadas.

### RF-4 — Enviar a foto de criança
**História:** Como jogador, quero enviar minha foto de criança, para o jogo
usá-la.

Critérios de aceite:
1. QUANDO um jogador está no lobby ENTÃO pode enviar uma imagem (JPEG, PNG ou
   WebP) de no máximo 10 MB.
2. QUANDO a imagem é enviada ENTÃO o sistema valida formato e tamanho e exibe
   uma pré-visualização; o jogador pode substituir antes de confirmar.
3. QUANDO o jogador confirma ENTÃO a foto fica associada a ele e a lista do
   lobby indica "foto enviada" (sem revelar a imagem aos demais).
4. SE o jogador não enviou foto ENTÃO ele aparece como "pendente" e o host não
   consegue iniciar o jogo enquanto houver pendentes.
5. A foto de criança de um jogador NUNCA é mostrada a outros jogadores antes de
   começarem as rodadas (nada no lobby revela quem é quem).

### RF-5 — Gerar a foto "atual" via API
**História:** Como sistema, quero gerar a versão atual de cada pessoa a partir
da foto de criança, para usá-la nas rodadas conforme a configuração.

Critérios de aceite:
1. QUANDO uma foto de criança é confirmada E o modo configurado requer foto
   gerada ENTÃO o sistema envia a imagem a uma API de geração de imagem com um
   prompt que pede uma versão realista da mesma pessoa em idade adulta/atual.
2. QUANDO a geração está em andamento ENTÃO o lobby mostra o status por jogador
   (pendente / gerando / pronto / falhou).
3. SE a geração falha ENTÃO o sistema permite nova tentativa (pelo jogador ou
   pelo host) e registra o erro de forma legível.
4. SE o modo configurado NÃO usa foto gerada ENTÃO a geração não é disparada e
   não bloqueia o início do jogo.
5. A foto gerada é tratada como derivada da foto de criança e segue as mesmas
   regras de privacidade (não revelada antes das rodadas).
6. O sistema trata a chamada à API como custosa e potencialmente lenta:
   execução assíncrona, com timeout e sem travar a interface.

### RF-6 — Iniciar o jogo
**História:** Como host, quero iniciar o jogo quando tudo estiver pronto, para
começar as rodadas.

Critérios de aceite:
1. O botão "Iniciar jogo" só fica habilitado QUANDO: há de 3 a 12 jogadores,
   todos enviaram foto, e (se o modo exige) todas as fotos geradas estão
   prontas.
2. QUANDO o host inicia ENTÃO o sistema sorteia a ordem dos alvos, monta as
   rodadas conforme o agrupamento configurado, trava as configurações e move a
   sala para a fase de rodadas para todos simultaneamente.
3. QUANDO o jogo inicia ENTÃO a ordem dos alvos é sorteada de forma que a
   sequência não seja previsível pelos jogadores.

### RF-7 — Conduzir uma rodada e votar
**História:** Como jogador, quero ver a(s) foto(s) do alvo e votar em quem eu
acho que é, para competir.

Critérios de aceite:
1. QUANDO uma rodada começa ENTÃO todos os jogadores veem simultaneamente a(s)
   foto(s) do(s) alvo(s) conforme o modo de exibição configurado.
2. QUANDO o modo é "uma por vez" ENTÃO o host (ou um temporizador configurado)
   avança da primeira imagem para a segunda imagem do mesmo alvo antes de
   encerrar a votação.
3. QUANDO há 2–3 alvos agrupados na rodada ENTÃO cada jogador registra um voto
   para CADA alvo da rodada (um palpite por alvo).
4. QUANDO um jogador vota ENTÃO escolhe o palpite a partir da lista de
   participantes da sala; um jogador NÃO pode votar em si mesmo como alvo (seu
   próprio nome fica indisponível apenas para o alvo que é ele; ele ainda pode
   votar em outros alvos).
5. QUANDO um jogador já votou em um alvo ENTÃO pode alterar o voto até o
   encerramento da votação daquele alvo/rodada.
6. QUANDO todos votaram OU o host encerra a votação ENTÃO a rodada é fechada
   para novos votos.
7. DURANTE a votação, o progresso ("X de N votaram") é visível para todos, mas
   os votos individuais permanecem ocultos até a revelação.
8. O próprio alvo (a pessoa cuja foto está em jogo) NÃO vota sobre si mesmo
   naquela rodada; se agrupado com outros alvos, vota normalmente nos demais.

### RF-8 — Revelação e pontuação
**História:** Como jogador, quero ver quem era a pessoa e os votos de todos, e
acompanhar o placar.

Critérios de aceite:
1. QUANDO uma revelação ocorre (ao final de cada rodada OU ao final de todas,
   conforme configurado) ENTÃO o sistema mostra, para cada alvo revelado: a
   identidade real (apelido), a foto de criança e a foto gerada (se existir), e
   a lista de quem votou em quem.
2. QUANDO a revelação ocorre ENTÃO cada jogador que acertou o alvo ganha 1
   ponto por acerto.
3. QUANDO a revelação de todas as rodadas termina ENTÃO o sistema exibe um
   placar final ordenado por pontos, com destaque para o(s) vencedor(es) e
   tratamento de empate (posições compartilhadas).
4. SE a revelação é por rodada ENTÃO o placar parcial é mostrado após cada
   revelação.
5. QUANDO o jogo termina ENTÃO o host pode "jogar de novo" criando uma nova
   sala reaproveitando os mesmos participantes e fotos já enviadas (sem
   reenviar), opcionalmente regerando as fotos.

### RF-9 — Sincronização em tempo real
**História:** Como jogador, quero que a tela de todos acompanhe o estado do
jogo, para jogarmos juntos sem recarregar.

Critérios de aceite:
1. Entradas/saídas de jogadores, status de fotos, início de rodada, progresso
   de votos, revelações e placar propagam para todos os clientes conectados em
   tempo real (sem recarregar a página).
2. SE um jogador perde a conexão e reconecta ENTÃO ele recebe o estado atual da
   sala e volta exatamente ao ponto do jogo.
3. SE o host se desconecta durante o jogo ENTÃO o jogo não trava: a sala
   mantém o estado e o host retoma o controle ao reconectar.

### RF-10 — Ciclo de vida e limpeza
**História:** Como operador, quero que salas e imagens não acumulem para
sempre, para controlar custo e privacidade.

Critérios de aceite:
1. QUANDO uma sala fica inativa por um período configurável (padrão 24 h) OU o
   host a encerra ENTÃO a sala e suas imagens (fotos de criança e geradas) são
   removidas do armazenamento.
2. QUANDO uma sala é encerrada/expira ENTÃO acessar seu link mostra "sala
   encerrada".
3. O sistema NÃO retém as fotos além do ciclo de vida da sala.

## 5. Requisitos não-funcionais

- **RNF-1 Privacidade:** fotos são dados sensíveis (crianças). Acesso a uma
  imagem exige pertencer à sala; nada de listagem pública. Imagens são apagadas
  no fim da vida da sala (RF-10). Nenhuma indexação por buscadores.
- **RNF-2 Tempo real:** latência de propagação de eventos de jogo percebida
  como "instantânea" (< ~500 ms em rede boa). Reconexão automática.
- **RNF-3 Resiliência da API de geração:** a indisponibilidade/erro da API de
  imagem nunca derruba a sala; o jogo degrada para modos que não exigem foto
  gerada ou permite retry.
- **RNF-4 Custo:** a geração de imagem é a operação cara; o sistema evita
  gerar imagens desnecessárias (só gera quando o modo exige) e não regera sem
  pedido explícito.
- **RNF-5 Dispositivos:** uso majoritariamente em celular; a interface é
  responsiva e funciona bem em telas pequenas (envio de foto pela câmera/galeria).
- **RNF-6 Simplicidade operacional (dev solo):** stack enxuta, poucas peças,
  self-hostável; sem dependência de serviços pagos além da API de imagem.
- **RNF-7 Idioma:** interface em Português (pt-BR).
- **RNF-8 Sem contas:** identidade do jogador é por sala, baseada em token no
  navegador; sem cadastro/login tradicional.

## 6. Fora de escopo (desta versão)

- Contas de usuário permanentes, histórico entre sessões e perfis.
- Chat de texto/voz dentro do jogo (presume-se que o grupo já conversa).
- Moderação automática de conteúdo das fotos.
- Internacionalização além de pt-BR.
- Aplicativos nativos (é web).

## 7. Decisões em aberto (ver chat)

Pontos marcados para confirmação do usuário antes do Design — ver a pergunta no
chat.
