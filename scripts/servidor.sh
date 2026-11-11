#!/usr/bin/env bash
# Prepara e mantém o servidor remoto do pipeline (Dagster em Docker). Roda no Git Bash e no Linux.
# Guia: docs/02-fazer/04-operar-e-publicar.md ("Implantar num servidor"). Configuração: .env.servidor.
set -euo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' # Git Bash não pode reescrever caminhos do servidor
cd "$(dirname "$0")/.."

USO='Uso: scripts/servidor.sh <subcomando> [--dry-run]
  preparar usuario@host [porta]  chave SSH, contexto Docker, .env.servidor e verificação do servidor
  dados [--forcar]               copia landing/, arquivos/, warehouse.duckdb e estado.duckdb locais para o servidor
  implantar [--forcar]           baixa a imagem e (re)inicia webserver e daemon; --forcar ignora execução em andamento
  primeira-carga [--forcar]      lança o atualizar_tudo uma vez (só no primeiro uso; nunca é automático)
  status                         containers, últimas execuções, daemons, verificações em erro, memória e endereço
--dry-run imprime os comandos sem executar.'

ENV_FILE=${SERVIDOR_ENV_FILE:-.env.servidor}
DRY=0 FORCAR=0 ARGS=()
for a in "$@"; do
  case $a in
    --dry-run) DRY=1 ;;
    --forcar) FORCAR=1 ;;
    -h | --help) echo "$USO"; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done
CMD=${ARGS[0]:-}
exec 3>&1 # o --dry-run escreve aqui, mesmo dentro de $(...)

say() { printf '%s\n' "$*"; }
die() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }
show() { printf '+' >&3; printf ' %q' "$@" >&3; printf '\n' >&3; }
run() { if ((DRY)); then show "$@"; else "$@"; fi; }   # altera algo
rd() { if ((DRY)); then show "$@"; return 1; else "$@"; fi; } # só lê (no dry-run não executa e falha)

getv() { # arquivo chave: valor sem aspas nem CR; vazio se faltar
  { grep -m1 "^$2=" "$1" 2>/dev/null || true; } | cut -d= -f2- | tr -d '\r' | sed "s/^\"\(.*\)\"\$/\1/;s/^'\(.*\)'\$/\1/"
}
setl() { # arquivo chave linha-completa: troca a linha da chave (ou acrescenta); o valor não passa por argumento de awk
  if grep -q "^$2=" "$1"; then
    L=$3 awk -v k="$2=" 'index($0,k)==1{print ENVIRON["L"];next}{print}' "$1" >"$1.tmp" && mv "$1.tmp" "$1"
  else printf '%s\n' "$3" >>"$1"; fi
}

carregar() { # lê o .env.servidor (ou o modelo, num dry-run antes do preparar)
  local f=$ENV_FILE
  [ -f "$f" ] || { ((DRY)) && f=.env.servidor.example || die "$ENV_FILE não existe: rode 'scripts/servidor.sh preparar usuario@host [porta]'"; }
  SSH=${SSH:-$(getv "$f" SERVIDOR_SSH)} PORT=${PORT:-$(getv "$f" SERVIDOR_SSH_PORT)}
  PORT=${PORT:-22}
  DATA=$(getv "$f" DADO_PUBLICO_DATA_DIR) UIPORT=$(getv "$f" DADO_PUBLICO_PORT) BIND=$(getv "$f" DADO_PUBLICO_BIND)
  UIPORT=${UIPORT:-3000} BIND=${BIND:-127.0.0.1}
  [ -n "$SSH" ] && [ -n "$DATA" ] || die "defina SERVIDOR_SSH e DADO_PUBLICO_DATA_DIR em $ENV_FILE"
  QD=$(printf %q "$DATA")
  RSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p "$PORT" "$SSH")
  DC=(docker --context servidor compose --env-file "$ENV_FILE")
}

# Consulta o Dagster pela GraphQL do próprio webserver, de dentro do container (sem navegador nem porta aberta).
read -r -d '' PY <<'EOF' || true
import json, sys, urllib.request as u
from datetime import datetime, timezone
Q = {
    "ping": "{version}",
    "ativas": "{runsOrError(filter:{statuses:[STARTED,QUEUED,STARTING]}){... on Runs{results{runId status jobName}}}}",
    "lancada": '{runsOrError(filter:{pipelineName:"atualizar_tudo"},limit:1){... on Runs{results{runId}}}}',
    "erros": "{assetNodes{assetKey{path} assetChecksOrError{... on AssetChecks{checks{name executionForLatestMaterialization{status evaluation{severity}}}}}}}",
    "ultimas": "{runsOrError(limit:3){... on Runs{results{status jobName creationTime}}}"
    " instance{daemonHealth{allDaemonStatuses{daemonType healthy required}}}}",
}
m = sys.argv[1]
req = u.Request("http://127.0.0.1:3000/graphql", json.dumps({"query": Q[m]}).encode(), {"Content-Type": "application/json"})
d = json.load(u.urlopen(req, timeout=30))
if not d.get("data"):
    raise SystemExit(d)
d = d["data"]
r = d.get("runsOrError", {}).get("results", [])
if m == "erros":
    n = 0
    for a in d["assetNodes"]:
        for c in a["assetChecksOrError"].get("checks", []):
            e = c["executionForLatestMaterialization"]
            if e and (e["status"] == "EXECUTION_FAILED" or e["status"] == "FAILED" and e["evaluation"]["severity"] == "ERROR"):
                n += 1
                print("  %-45s %-28s %s" % ("/".join(a["assetKey"]["path"]), c["name"], e["status"]))
    print("Verificações de ativo em erro (última avaliação): %d" % n if n else "Verificações de ativo em erro: nenhuma")
elif m == "ativas":
    for x in r:
        print(x["runId"][:8], x["status"], x["jobName"])
elif m == "lancada":
    print(len(r))
elif m == "ultimas":
    print("Últimas execuções:")
    for x in r:
        print("  %-10s %s  %s" % (x["status"], x["jobName"], datetime.fromtimestamp(x["creationTime"], timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))
    print("Daemons:")
    for x in d["instance"]["daemonHealth"]["allDaemonStatuses"]:
        print("  %-14s %s" % (x["daemonType"], "ok" if x["healthy"] else "FALHA" if x["required"] else "inativo"))
else:
    print("ok")
EOF
gql() {
  if ((DRY)); then show "${DC[@]}" exec -T webserver uv run --no-sync python -c "<consulta GraphQL $1>"; return 0; fi
  "${DC[@]}" exec -T webserver uv run --no-sync python -c "$PY" "$1"
}
web_rodando() { ((!DRY)) && "${DC[@]}" ps --status running --services 2>/dev/null | grep -qx webserver; }

# ---------------------------------------------------------------------------------------------------------------- preparar
ck() { # OK|FALTA mensagem
  printf '  %-5s %s\n' "$1" "$2"; [ "$1" = OK ] || FALHAS=$((FALHAS + 1))
}

# Roda no servidor (sh): $1 pasta de dados, $2 porta da interface, $3 = 1 para tentar criar a pasta com sudo sem senha.
read -r -d '' VERIFICA <<'EOF' || true
D=$1; P=$2; FIX=$3
v=$(docker version --format '{{.Server.Version}}' 2>/dev/null) && echo "docker ok $v" || echo "docker falta"
v=$(docker compose version --short 2>/dev/null) && echo "compose ok $v" || echo "compose falta"
echo "arch $(uname -m)"
echo "mem $(awk '/MemTotal/{printf "%d",$2/1024}' /proc/meminfo) $(awk '/SwapTotal/{printf "%d",$2/1024}' /proc/meminfo)"
if [ -d "$D" ] && [ -w "$D" ]; then echo "dados ok"
elif [ "$FIX" = 1 ] && sudo -n mkdir -p "$D" 2>/dev/null && sudo -n chown "$(id -u):$(id -g)" "$D" 2>/dev/null; then echo "dados criado"
else echo "dados falta sudo mkdir -p $D && sudo chown $(id -un):$(id -gn) $D"; fi
d=$D; while [ ! -d "$d" ]; do d=$(dirname "$d"); done
echo "livre $(df -Pk "$d" | awk 'NR==2{printf "%d",$4/1048576}')"
if ! command -v ss >/dev/null 2>&1; then echo "porta desconhecida"
elif ss -ltn | awk -v p=":$P" '$4 ~ p"$"{f=1} END{exit !f}'; then
  echo "porta ocupada $(docker ps --filter "publish=$P" --format '{{.Names}}' 2>/dev/null | head -1)"
else echo "porta livre"; fi
EOF

verificar() {
  local k s rest need=0 fix=1 saida
  ((DRY)) && fix=0
  [ -d "${DADO_PUBLICO_STORAGE_ROOT:-./data_store}" ] && need=$(du -sk "${DADO_PUBLICO_STORAGE_ROOT:-./data_store}"/{landing,arquivos,warehouse.duckdb,estado.duckdb} 2>/dev/null | awk '{s+=$1}END{printf "%d",s/1048576}') || true
  say "Verificação do servidor:"
  if ((DRY)); then
    printf '+ ssh ... sh -s -- %s %s %s  # verificação (docker, compose, arch, RAM, swap, disco, pasta, porta)\n' "$QD" "$UIPORT" "$fix" >&3
    return 0
  fi
  saida=$(printf '%s\n' "$VERIFICA" | "${RSH[@]}" sh -s -- "$QD" "$UIPORT" "$fix") || die "não consegui verificar o servidor por SSH"
  FALHAS=0
  while read -r k s rest; do
    case $k in
      docker) [ "$s" = ok ] && ck OK "docker $rest (usuário acessa o daemon)" || ck FALTA "docker ausente ou sem acesso (usuário no grupo docker?)" ;;
      compose) [ "$s" = ok ] && ck OK "compose $rest" || ck FALTA "docker compose ausente" ;;
      arch) [ "$s" = x86_64 ] && ck OK "arquitetura $s" || ck FALTA "arquitetura $s (a imagem é x86_64)" ;;
      mem) [ "$rest" -ge 7500 ] && ck OK "RAM $s MB, swap $rest MB" || ck FALTA "RAM $s MB, swap $rest MB (recomendado swap de 8 GB: crie antes do rebuild)" ;;
      livre) [ "$s" -ge "$need" ] && ck OK "espaço livre $s GB (os dados locais ocupam ~$need GB)" || ck FALTA "espaço livre $s GB, os dados locais ocupam ~$need GB" ;;
      dados) case $s in
        ok) ck OK "pasta de dados gravável" ;;
        criado) ck OK "pasta de dados criada com sudo" ;;
        *) ck FALTA "pasta de dados ausente ou sem escrita; rode no servidor: $rest" ;;
        esac ;;
      porta) case $s in
        livre) ck OK "porta $UIPORT livre" ;;
        ocupada) case $rest in
          dado-publico-brasil-webserver*) ck OK "porta $UIPORT usada pelo próprio webserver" ;;
          *) ck FALTA "porta $UIPORT ocupada por ${rest:-um processo fora do Docker}: defina outra DADO_PUBLICO_PORT" ;;
          esac ;;
        *) ck OK "porta $UIPORT não verificada (ss ausente)" ;;
        esac ;;
    esac
  done <<<"$saida"
  [ "$FALHAS" -eq 0 ] && say "Servidor pronto." || { say "$FALHAS item(ns) em FALTA."; return 1; }
}

preparar() {
  [ -n "${ARGS[1]:-}" ] || die "uso: scripts/servidor.sh preparar usuario@host [porta]"
  SSH=${ARGS[1]} PORT=${ARGS[2]:-22}
  local base=$ENV_FILE ctx="ssh://$SSH" k
  [ "$PORT" = 22 ] || ctx="$ctx:$PORT"
  # 1. chave SSH
  local rsh=(ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p "$PORT" "$SSH")
  if ((DRY)) || ! "${rsh[@]}" true 2>/dev/null; then
    local key=~/.ssh/id_ed25519
    [ -f "$key" ] || run ssh-keygen -t ed25519 -N "" -f "$key"
    say "Enviando a chave pública (a senha do servidor é pedida uma vez)."
    if ((DRY)); then show tr -d '\r' "<$key.pub" "|" ssh -p "$PORT" "$SSH" "<acrescenta a chave a ~/.ssh/authorized_keys sem duplicar>"
    else
      tr -d '\r' <"$key.pub" | ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -p "$PORT" "$SSH" \
        'umask 077; mkdir -p ~/.ssh; k=$(cat); grep -qxF "$k" ~/.ssh/authorized_keys 2>/dev/null || printf "%s\n" "$k" >> ~/.ssh/authorized_keys'
      "${rsh[@]}" true || die "a chave não autenticou; confira o usuário, a porta e o sshd"
    fi
  else say "Chave SSH: já autentica sem senha."; fi
  # 2. contexto Docker (cria ou atualiza)
  if docker context inspect servidor >/dev/null 2>&1; then run docker context update servidor --docker "host=$ctx"
  else run docker context create servidor --docker "host=$ctx"; fi
  # 3. .env.servidor (só LAKE e R2 vêm do .env local; nunca o Postgres; valores não são impressos)
  if [ -f "$base" ]; then
    say "$base já existe: mantido."
    run setl "$base" SERVIDOR_SSH "SERVIDOR_SSH=$SSH"
    run setl "$base" SERVIDOR_SSH_PORT "SERVIDOR_SSH_PORT=$PORT"
  elif ((DRY)); then
    show cp .env.servidor.example "$base"; say "+ copiar de .env as variáveis DADO_PUBLICO_LAKE_URL e DADO_PUBLICO_R2_* (sem imprimir valores)" >&3
  else
    cp .env.servidor.example "$base"
    setl "$base" SERVIDOR_SSH "SERVIDOR_SSH=$SSH"
    setl "$base" SERVIDOR_SSH_PORT "SERVIDOR_SSH_PORT=$PORT"
    if [ -f .env ]; then
      while IFS= read -r l; do setl "$base" "${l%%=*}" "$l"; done < <(tr -d '\r' <.env | grep -E '^(DADO_PUBLICO_LAKE_URL|DADO_PUBLICO_R2_[A-Z_]+)=')
    fi
    say "$base criado a partir do modelo e do .env local."
  fi
  if [ -f "$base" ]; then
    for k in DADO_PUBLICO_LAKE_URL DADO_PUBLICO_R2_ACCOUNT_ID DADO_PUBLICO_R2_ACCESS_KEY_ID DADO_PUBLICO_R2_SECRET_ACCESS_KEY DADO_PUBLICO_R2_BUCKET DADO_PUBLICO_R2_BUCKET_PRIVADO; do
      [ -n "$(getv "$base" "$k")" ] || say "FALTA preencher $k em $base"
    done
  fi
  # 4. verificação
  carregar
  verificar
}

# ------------------------------------------------------------------------------------------------------------------ dados
# Roda nas duas pontas (sh): "N_ARQUIVOS BYTES" da pasta $1.
read -r -d '' STATS <<'EOF' || true
find "$1" -type f -printf '%s\n' 2>/dev/null | awk '{n++;b+=$1}END{print n+0,b+0}'
EOF

copiar_pasta() { # pasta (relativa à raiz local)
  local d=$1
  if command -v rsync >/dev/null 2>&1 && rd "${RSH[@]}" command -v rsync >/dev/null 2>&1; then
    (cd "$ROOT" && run rsync -a --partial --info=progress2 -e "ssh -o BatchMode=yes -p $PORT" "$d" "$SSH:$DATA/")
  elif ((DRY)); then
    say "+ (cd $ROOT && tar -cf - $d) | ssh ... 'tar -C $QD -xf -'   # sem rsync" >&3
  else
    (cd "$ROOT" && tar -cf - "$d") | "${RSH[@]}" "mkdir -p $QD && tar -C $QD -xf -"
  fi
}

dados() {
  local d l r w
  ROOT=${DADO_PUBLICO_STORAGE_ROOT:-./data_store}
  w=$ROOT/warehouse.duckdb
  say "Feche tudo que use o warehouse local (Dagster, CLI, DBeaver) antes de copiá-lo."
  if [ -f "$w" ]; then
    [ ! -e "$w.wal" ] || die "$w.wal existe: o warehouse local não foi fechado. Feche o que o usa e rode de novo."
    if ((!FORCAR)); then
      r=$(rd "${RSH[@]}" "stat -c %s $QD/warehouse.duckdb 2>/dev/null" || true)
      [ -z "$r" ] || die "o warehouse já existe no servidor ($r bytes). Substituí-lo apaga o histórico de lá: use --forcar se for isso mesmo."
    fi
  fi
  run "${RSH[@]}" "mkdir -p $QD"
  for d in landing arquivos; do
    [ -d "$ROOT/$d" ] || { say "$d: não existe localmente, pulado."; continue; }
    l=$(printf '%s\n' "$STATS" | sh -s -- "$ROOT/$d")
    r=$(printf '%s\n' "$STATS" | rd "${RSH[@]}" sh -s -- "$QD/$d" || true)
    if [ "$l" = "$r" ]; then say "$d: igual no servidor ($l arquivos e bytes)."; continue; fi
    say "$d: local '$l' x servidor '${r:-?}' (arquivos bytes); copiando..."
    copiar_pasta "$d"
    if ((!DRY)); then
      r=$(printf '%s\n' "$STATS" | "${RSH[@]}" sh -s -- "$QD/$d")
      [ "$l" = "$r" ] && say "$d: conferido ($l)." || die "$d: depois de copiar, local '$l' x servidor '$r'. Rode de novo."
    fi
  done
  for d in warehouse.duckdb estado.duckdb; do  # o estado (metadata e identity) mora no seu próprio arquivo
    if [ -f "$ROOT/$d" ]; then
      say "$d: copiando ($(($(wc -c <"$ROOT/$d") / 1048576)) MB)..."
      run scp -P "$PORT" -o BatchMode=yes "$ROOT/$d" "$SSH:$DATA/$d.enviando"
      run "${RSH[@]}" "mv $QD/$d.enviando $QD/$d"
    else say "$d: não existe localmente, pulado."; fi
  done
  say "Dados copiados."
}

# ----------------------------------------------------------------------------------------------------- implantar / primeira-carga
trava() { # recusa se há execução em andamento (cortá-la deixa a captura sem concluir), salvo --forcar
  local ativas
  if ((DRY)); then gql ativas
  elif ((!FORCAR)) && web_rodando; then
    ativas=$(gql ativas) || die "não consegui consultar as execuções; use --forcar para ignorar"
    [ -z "$ativas" ] || { say "$ativas"; die "há execução em andamento (cortá-la deixa a captura sem concluir). Espere ou use --forcar."; }
  fi
}

implantar() { # nunca lança o atualizar_tudo: a primeira carga é o subcomando explícito primeira-carga
  run "${DC[@]}" pull webserver daemon
  trava
  run "${DC[@]}" up -d webserver daemon
  status
}

primeira_carga() { # lança o atualizar_tudo uma vez (custo e alternativas: docs, "Implantar num servidor")
  trava
  rd "${RSH[@]}" "test -s $QD/warehouse.duckdb" || ((DRY)) || die "falta o warehouse no servidor: rode 'scripts/servidor.sh dados' (ou restaure do bucket e faça o rebuild)"
  run "${DC[@]}" up -d webserver
  if ((DRY)); then gql ping
  else
    for _ in $(seq 60); do gql ping >/dev/null 2>&1 && break; sleep 10; done
    gql ping >/dev/null 2>&1 || die "a interface não respondeu em 10 minutos: veja '${DC[*]} logs webserver'"
  fi
  if ((DRY)) || ((FORCAR)) || [ "$(gql lancada)" != 1 ]; then
    ((DRY)) && gql lancada
    # container avulso do daemon (mesmo limite de memória do daemon; o webserver tem 1 GB), sem dependências. Entra na fila (Queued).
    run "${DC[@]}" run --rm --no-deps -T daemon uv run --no-sync dagster job launch -m dado_publico_brasil.orchestration.definitions -j atualizar_tudo
  else say "atualizar_tudo já foi lançado antes: não lanço de novo (use --forcar para lançar outra vez)."; fi
  run "${DC[@]}" up -d daemon
  status
}

# ---------------------------------------------------------------------------------------------------------------- status
status() {
  local ids
  run "${DC[@]}" ps -a
  if web_rodando || ((DRY)); then gql ultimas || say "(interface ainda não responde)"; else say "Interface fora do ar (webserver parado)."; fi
  # só a GraphQL (nunca o warehouse): vale com execução ativa
  if web_rodando || ((DRY)); then gql erros || true; fi
  ids=$(rd "${DC[@]}" ps -q 2>/dev/null || true)
  # shellcheck disable=SC2086
  if ((DRY)); then show docker --context servidor stats --no-stream "<containers>"
  elif [ -n "$ids" ]; then docker --context servidor stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}' $ids; fi
  # a pergunta vai ao servidor por SSH e usa o endereço publicado (DADO_PUBLICO_BIND:PORT), o mesmo que o navegador alcança
  if ((DRY)); then show "${RSH[@]}" "curl -fsS -m 5 http://$BIND:$UIPORT/server_info"
  elif "${RSH[@]}" "curl -fsS -m 5 -o /dev/null http://$BIND:$UIPORT/server_info" 2>/dev/null; then say "Interface responde em $BIND:$UIPORT (no servidor)."
  else say "Interface NÃO responde em $BIND:$UIPORT (no servidor)."; fi
  say "Interface: http://${SSH#*@}:$UIPORT (escuta em $BIND$([ "$BIND" = 127.0.0.1 ] && echo "; de fora, túnel: ssh -L $UIPORT:127.0.0.1:$UIPORT -p $PORT $SSH"))"
}

case $CMD in
  preparar) preparar ;;
  dados) carregar; dados ;;
  implantar) carregar; implantar ;;
  primeira-carga) carregar; primeira_carga ;;
  status) carregar; status ;;
  *) echo "$USO"; [ -z "$CMD" ] || exit 1 ;;
esac
