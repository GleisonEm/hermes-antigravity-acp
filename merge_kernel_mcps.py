"""Merge dos MCPs stdio-enabled do Hermes no mcp_config.json do kernel Antigravity.

Lê `mcp_servers` do config.yaml do profile (fonte única — sem hard-codar
credenciais, o redactor do Hermes mascara segredos em outputs mas o valor
real viaja dentro do processo), filtra:
  - enabled: true
  - tem `command` (stdio local) — NUNCA url/oauth remoto (mercadopago)
  - command resolve no PATH (shutil.which) ou é caminho absoluto existente

E adiciona/atualiza em ~/.gemini/config/mcp_config.json preservando os
servidores existentes do kernel (postgres/chrome-devtools-mcp/xcodebuild/
ios-simulator). Backup antes de escrever. Idempotente.
"""
import json
import shutil
import sys
from pathlib import Path

import yaml

HOME = Path.home()
KERNEL_CFG = HOME / ".gemini" / "config" / "mcp_config.json"
PROFILE_CFG = HOME / ".hermes" / "profiles" / "simpay" / "config.yaml"
KERNEL_RESERVED = {"postgres", "chrome-devtools-mcp", "xcodebuild", "ios-simulator"}


def resolve_ok(command: str) -> bool:
    if command.startswith("/"):
        return Path(command).exists()
    return shutil.which(command) is not None


def main() -> int:
    if not PROFILE_CFG.is_file():
        print(f"ERRO: {PROFILE_CFG} não existe")
        return 1
    if not KERNEL_CFG.is_file():
        print(f"ERRO: {KERNEL_CFG} não existe")
        return 1

    cfg_yaml = yaml.safe_load(PROFILE_CFG.read_text(encoding="utf-8")) or {}
    hermes_mcps = cfg_yaml.get("mcp_servers", {}) or {}

    try:
        kernel = json.loads(KERNEL_CFG.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERRO: lendo {KERNEL_CFG}: {e}")
        return 1

    servers = kernel.setdefault("mcpServers", {})
    backup = Path(str(KERNEL_CFG) + ".hermes-merge.bak")
    backup.write_text(json.dumps(kernel, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"backup: {backup}")

    added, skipped = [], []
    for name, spec in hermes_mcps.items():
        if not isinstance(spec, dict):
            continue
        if spec.get("enabled", True) is False:
            skipped.append(f"{name} (disabled)")
            continue
        if "url" in spec:
            skipped.append(f"{name} (url/oauth — kernel só carrega stdio)")
            continue
        command = spec.get("command", "")
        if not command or not resolve_ok(command):
            skipped.append(f"{name} (command não resolve: {command})")
            continue
        if name in servers or name in KERNEL_RESERVED:
            skipped.append(f"{name} (já existe no kernel)")
            continue
        entry = {"command": command, "args": list(spec.get("args", []))}
        if spec.get("env"):
            entry["env"] = dict(spec["env"])
        servers[name] = entry
        added.append(name)

    tmp = Path(str(KERNEL_CFG) + ".tmp")
    tmp.write_text(json.dumps(kernel, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(KERNEL_CFG)

    print(f"adicionados ({len(added)}): {', '.join(added) or '-'}")
    print(f"pulados ({len(skipped)}): {', '.join(skipped) or '-'}")
    print(f"total mcpServers no kernel: {len(servers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())