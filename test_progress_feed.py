#!/usr/bin/env python3
"""E2E: progress feed ao vivo via cliente Hermes real (keep-alive, yolo).

Roda um prompt de grafo (codegraph MCP) em thread worker e amostra
get_acp_thread_progress(t.ident) a cada 3s, simulando o aviso do wait loop.
Verifica: desc de tool real, tokens > 0, registro limpo no final.
"""
import os
import sys
import threading
import time

os.environ["HERMES_ANTIGRAVITY_ACP_KEEP_ALIVE"] = "1"
os.environ["HERMES_ANTIGRAVITY_ACP_LEAN_PROMPT"] = "1"
os.environ["HERMES_ANTIGRAVITY_ACP_MODE"] = "yolo"  # sem policy gate

sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))

from hermes_cli.auth import get_external_process_provider_status  # noqa: E402
from agent.copilot_acp_client import CopilotACPClient, get_acp_thread_progress  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-flash-low"
PROMPT = (
    "Use o MCP codegraph-uniplus para mapear o fluxo principal do backend em "
    "/Users/gemanuel/dev/sub/backend/uniplus-api (2-3 buscas), e responda em "
    "3 linhas quais componentes participam. Nao edite nada."
)

status = get_external_process_provider_status("antigravity-acp")
client = CopilotACPClient(
    api_key="test",
    base_url="acp://antigravity",
    acp_command=status["command"],
    acp_args=status["args"],
    acp_cwd="/Users/gemanuel",
)

result = {}
samples = []

def worker():
    try:
        t0 = time.monotonic()
        resp = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": PROMPT}], timeout=300)
        result["ok"] = True
        result["dt"] = time.monotonic() - t0
        result["usage"] = (resp.usage.prompt_tokens, resp.usage.completion_tokens, resp.usage.total_tokens)
        result["text"] = str(resp.choices[0].message.content)[:200]
    except Exception as e:
        result["ok"] = False
        result["err"] = f"{type(e).__name__}: {e}"

t = threading.Thread(target=worker, daemon=True)
t.start()
while t.is_alive():
    holder = get_acp_thread_progress(t.ident)
    prog = (holder or {}).get("ref") if holder else None
    if prog:
        samples.append(dict(prog))
        desc = prog.get("last_desc") or ""
        last = prog.get("last_event_ts")
        now = time.monotonic()
        # simula a branch do wait loop
        if last is not None and (now - last) < 30:
            notice = f"[SIMULADO] ⏳ kernel: {desc or 'trabalhando'}…"
        else:
            silent = 0 if last is None else int(now - last)
            notice = f"[SIMULADO] ⏳ kernel sem atividade há {silent}s — última: {desc or '—'}"
        print(f"{time.monotonic():7.1f}s {notice} | tools={prog.get('tools', 0)} steps={prog.get('steps', 0)} usage={prog.get('usage')}", flush=True)
    time.sleep(3)
t.join(timeout=310)

leftover = get_acp_thread_progress(t.ident)
print("\nworker thread é viva?", t.is_alive())
print("leftover após fim:", leftover is not None)
assert t.is_alive() is False, "worker travado"
assert leftover is None, "registro de progress vazou (não foi limpo)"
assert result.get("ok"), result.get("err")

desc_tools = [s.get("last_desc") for s in samples if s.get("last_desc")]
print(f"\nRESULTADO em {result['dt']:.1f}s | usage real: in={result['usage'][0]} out={result['usage'][1]} total={result['usage'][2]}")
print("resposta:", result["text"][:150])
print(f"amostras com desc: {len(desc_tools)} | descs: {desc_tools[:6]}")
assert desc_tools, "nenhuma desc de atividade capturada"
assert result["usage"][0] > 0 or result["usage"][1] > 0, "tokens reais não chegaram ao response"
print("ALL_PASS — progress feed ativo de ponta a ponta")
client.close()