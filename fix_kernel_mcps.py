"""Restaura o backup e adiciona só os MCPs que funcionam no kernel.

O merge completo falhou: postgres-uniplus-local (docker) aborta session/new
(kernel não aguenta o spawn do docker no boot → timeout + 'MCP load
failed'). Estratégia: backup → adicionar apenas MCPs node/uvx puros
(codegraph x3 + code-review-graph); chrome-devtools fica de fora (o kernel
já tem chrome-devtools-mcp com o mesmo comando) e docker fica de fora.
"""
import json
import shutil
from pathlib import Path

HOME = Path.home()
KERNEL_CFG = HOME / ".gemini" / "config" / "mcp_config.json"
BACKUP = Path(str(KERNEL_CFG) + ".hermes-merge.bak")

ADD = {
    "codegraph-uniplus": {
        "command": "/Users/gemanuel/.hermes/node/bin/node",
        "args": [
            "/Users/gemanuel/.codex/plugins/cache/sisyphuslabs/omo/4.19.4/components/codegraph/dist/serve.js",
            "--env",
            "OMO_CODEGRAPH_PROJECT_CWD=/Users/gemanuel/dev/sub/backend/uniplus-api",
        ],
    },
    "codegraph-panel": {
        "command": "/Users/gemanuel/.hermes/node/bin/node",
        "args": [
            "/Users/gemanuel/.codex/plugins/cache/sisyphuslabs/omo/4.19.4/components/codegraph/dist/serve.js",
            "--env",
            "OMO_CODEGRAPH_PROJECT_CWD=/Users/gemanuel/dev/sub/frontend/uneplus-panel",
        ],
    },
    "codegraph-admin": {
        "command": "/Users/gemanuel/.hermes/node/bin/node",
        "args": [
            "/Users/gemanuel/.codex/plugins/cache/sisyphuslabs/omo/4.19.4/components/codegraph/dist/serve.js",
            "--env",
            "OMO_CODEGRAPH_PROJECT_CWD=/Users/gemanuel/dev/sub/frontend/uneplus-admin",
        ],
    },
    "code-review-graph": {
        "command": "/Users/gemanuel/.local/bin/uvx",
        "args": ["code-review-graph", "serve"],
    },
}

if BACKUP.exists():
    shutil.copy2(BACKUP, KERNEL_CFG)
    print(f"restaurado backup: {BACKUP}")
else:
    print("sem backup — usando estado atual")

cfg = json.loads(KERNEL_CFG.read_text(encoding="utf-8"))
servers = cfg.setdefault("mcpServers", {})
for name, spec in ADD.items():
    if name not in servers:
        servers[name] = spec
        print(f"+ {name}")
tmp = Path(str(KERNEL_CFG) + ".tmp")
tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
tmp.replace(KERNEL_CFG)
print(f"total: {len(servers)} mcpServers")