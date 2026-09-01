#!/bin/bash
# Re-apply the antigravity-acp Hermes provider patches after a `hermes update`
# / git pull rewrote the Hermes repo. Run from anywhere.
#
# Configuravel por env (PORTABILIDADE — para passar a um amigo):
#   REPO          caminho do repo hermes git (default: ~/.hermes/hermes-agent)
#   HERMES_HOME   home do hermes (default: ~/.hermes)
#   PROFILE       profile destino do plugin (default: vazio = HERMES_HOME direto)
#   AGY_ACP_PAR   caminho do kernel agy_acp_server.par (default: auto-detectar)
set -euo pipefail

REPO="${REPO:-$HOME/.hermes/hermes-agent}"
BASE_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PATCH="$HERE/hermes-antigravity-acp.patch"
PLUGIN_SRC="$HERE/model-providers-antigravity-acp"

if [ -n "${PROFILE:-}" ]; then
  PLUGIN_TARGET="$BASE_HOME/profiles/$PROFILE/plugins/model-providers/antigravity-acp"
else
  PLUGIN_TARGET="$BASE_HOME/plugins/model-providers/antigravity-acp"
fi

echo "==> repo: $REPO"
echo "==> plugin alvo: $PLUGIN_TARGET"

if [ ! -d "$REPO/.git" ]; then
  echo "ERROR: $REPO nao e um checkout git — nao da pra aplicar o patch. Restaure manualmente."
  exit 1
fi

if git -C "$REPO" apply --check "$PATCH" 2>/dev/null; then
  git -C "$REPO" apply "$PATCH"
  echo "patched: $REPO ($(grep -c '^diff --git' "$PATCH") arquivos)"
elif grep -q "antigravity-acp" "$REPO/hermes_cli/models.py" 2>/dev/null; then
  echo "patches ja aplicados (models.py ja menciona antigravity-acp) — pulando"
else
  echo "WARNING: patch nao aplica limpo e o repo nao esta patchado."
  echo "Possiveis causas: versao do hermes diferente (patch gerado contra v0.20.0/2026.8.3,"
  echo "commit 3e09adb109). Tente: cd $REPO && git apply --3way $PATCH"
  echo "Se conflitar, aplique manualmente seguindo o README.md (pitfall 7)."
  exit 1
fi

mkdir -p "$(dirname "$PLUGIN_TARGET")"
cp -R "$PLUGIN_SRC" "$PLUGIN_TARGET"
echo "plugin instalado: $PLUGIN_TARGET"

# Symlink estavel (conveniencia; o resolver prefere o path real do registry).
# No macOS via Zed: auto-detecta. Em qualquer OS: sete AGY_ACP_PAR.
if [ -n "${AGY_ACP_PAR:-}" ]; then
  ln -sfn "$AGY_ACP_PAR" "$HOME/.local/bin/agy_acp_server.par"
  echo "symlink: ~/.local/bin/agy_acp_server.par -> $AGY_ACP_PAR"
elif [ "$(uname)" = "Darwin" ]; then
  ZED_PAR=$(ls -d "$HOME/Library/Application Support/Zed/external_agents/registry/antigravity-acp/"*/agy_acp_server.par 2>/dev/null | head -1 || true)
  if [ -n "$ZED_PAR" ]; then
    ln -sfn "$ZED_PAR" "$HOME/.local/bin/agy_acp_server.par"
    echo "symlink: ~/.local/bin/agy_acp_server.par -> $ZED_PAR"
  else
    echo "AVISO: agy_acp_server.par nao encontrado no registry do Zed."
    echo "  Instale com o Zed (extensao Antigravity) ou set AGY_ACP_PAR=/caminho/agy_acp_server.par"
  fi
else
  echo "AVISO: plataforma nao-Darwin — o kernel .par e especifico da plataforma."
  echo "  Obtenha o agy_acp_server.par da sua plataforma e sete AGY_ACP_PAR=$(pwd)  ou use HERMES_ANTIGRAVITY_ACP_COMMAND."
fi

echo
echo "OK — valide com:"
echo "  hermes chat -q 'oi' --provider antigravity-acp -m antigravity-acp"
echo "  (se o kernel nao for auto-detectado: export HERMES_ANTIGRAVITY_ACP_COMMAND=/caminho/agy_acp_server.par)"
echo
echo "Lembrete: o login do Antigravity e por conta (oauth-personal) — o amigo precisa"
echo "da propria sessao (~/.gemini/antigravity-acp/ via Zed, ou 'agy' logado)."