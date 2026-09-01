#!/bin/bash
# Hermes Antigravity ACP provider — one-line installer.
#
#   curl -fsSL https://raw.githubusercontent.com/GleisonEm/hermes-antigravity-acp/main/install.sh | bash
#
# Requirements:
#   - Hermes Agent installed from git at ~/.hermes/hermes-agent (v0.20.0+)
#   - The Antigravity ACP kernel (agy_acp_server.par) — macOS: via the Zed
#     "Antigravity" extension; other platforms: set AGY_ACP_PAR below.
#   - Your own Antigravity login (oauth-personal).
set -euo pipefail

REPO_URL="https://github.com/GleisonEm/hermes-antigravity-acp"
REPO="${REPO:-$HOME/.hermes/hermes-agent}"
BASE_HOME="${HERMES_HOME:-$HOME/.hermes}"
DEST="$HOME/.hermes/scripts/antigravity-acp"

echo "==> Baixando hermes-antigravity-acp ..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "$REPO_URL/archive/refs/heads/main.tar.gz" -o "$TMP/pkg.tar.gz"
tar -xzf "$TMP/pkg.tar.gz" -C "$TMP"
PKG_DIR="$(find "$TMP" -maxdepth 1 -type d -name 'hermes-antigravity-acp-*' | head -1)"

[ -d "$REPO/.git" ] || {
  echo "ERRO: $REPO não é um checkout git do Hermes."
  echo "Instale o Hermes primeiramente: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
  exit 1
}

mkdir -p "$DEST"
cp -R "$PKG_DIR/." "$DEST/"
chmod +x "$DEST/apply.sh"
echo "==> Aplicando patch no core do Hermes ..."
"$DEST/apply.sh"

echo
echo "✅ Instalado. Próximos passos:"
echo "  1. Garanta o kernel ACP (agy_acp_server.par):"
echo "     macOS: instale a extensão Antigravity no Zed (login oauth-personal)."
echo "     Outros: export HERMES_ANTIGRAVITY_ACP_COMMAND=/caminho/agy_acp_server.par"
echo "  2. Teste: hermes chat -q 'oi' --provider antigravity-acp -m gemini-3.7-flash-medium"
echo "  3. Default (opcional): hermes config set model.provider antigravity-acp"
echo "                          hermes config set model.default gemini-3.7-flash-high"
echo "  Docs completos: $REPO_URL"