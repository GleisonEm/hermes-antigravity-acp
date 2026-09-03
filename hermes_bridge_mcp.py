#!/usr/bin/env python3
"""hermes-bridge MCP server — read-only pull access to Hermes harness.

Lets the Antigravity ACP kernel (or any MCP client) pull what the Hermes
context pack can only push as text:

  - memory_search(query) → relevant lines from MEMORY.md / USER.md
  - skill_list()         → name + description + category of every skill
  - skill_view(name)     → full SKILL.md body (frontmatter stripped)

Stdlib only, no repo imports: discovers the profile's memories/skills
directories directly. Never writes anything; failures return an error
string inside the tool result (never a protocol error), so a bad query
can never break session/new.

Transport: MCP over stdio (newline-delimited JSON-RPC). Logs → stderr.
Profile resolution: --profile NAME, else $HERMES_PROFILE, else the
default ~/.hermes layout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
HERMES_BASE = HOME / ".hermes"

MEMORY_FILES = ("MEMORY.md", "USER.md")
MEMORY_CAP = 6000
SKILL_BODY_CAP = 8000
LINE_HIT_CAP = 40


def _log(msg: str) -> None:
    print(f"[hermes-bridge] {msg}", file=sys.stderr, flush=True)


def _resolve_profile(name: str) -> tuple[Path | None, list[Path]]:
    """Return (memories_dir, skill_dirs) for the profile (best effort)."""
    name = (name or "").strip()
    mem_candidates: list[Path] = []
    skill_dirs: list[Path] = []
    if name:
        mem_candidates.append(HERMES_BASE / "profiles" / name / "memories")
        skill_dirs.append(HERMES_BASE / "profiles" / name / "skills")
    home = os.getenv("HERMES_HOME", "").strip()
    if home:
        mem_candidates.append(Path(home) / "memories")
        skill_dirs.append(Path(home) / "skills")
    mem_candidates.append(HERMES_BASE / "memories")
    skill_dirs.append(HERMES_BASE / "skills")
    mem_dir = next((d for d in mem_candidates if d.is_dir()), None)
    return mem_dir, [d for d in skill_dirs if d.is_dir()]


def _read_memories(mem_dir: Path | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not mem_dir:
        return out
    for fname in MEMORY_FILES:
        p = mem_dir / fname
        try:
            if p.is_file():
                out[fname] = p.read_text(encoding="utf-8", errors="replace").strip()[:MEMORY_CAP]
        except Exception as e:
            _log(f"read {p} failed: {e}")
    return out


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (text or "").lower()))


def _tool_memory_search(mem_dir: Path | None, query: str) -> str:
    mems = _read_memories(mem_dir)
    if not mems:
        return "No Hermes memory files found for this profile."
    tokens = _tokenize(query)
    if not tokens:
        # No query → heads of both files (they are tiny by design).
        parts = [f"## {k}\n{v[:2000]}" for k, v in mems.items() if v]
        return "\n\n".join(parts) or "Memory files are empty."
    hits: list[str] = []
    for fname, text in mems.items():
        for line in text.splitlines():
            ltokens = _tokenize(line)
            if tokens & ltokens and line.strip():
                hits.append(f"[{fname}] {line.strip()}")
                if len(hits) >= LINE_HIT_CAP:
                    break
    if not hits:
        return "No memory lines matched the query. Full memory heads:\n" + "\n\n".join(
            f"## {k}\n{v[:1200]}" for k, v in mems.items() if v
        )
    return "\n".join(hits)


def _parse_frontmatter(path: Path) -> tuple[str, str, str]:
    """(name, description, category) from SKILL.md frontmatter (best effort)."""
    name = path.parent.name
    desc, cat = "", ""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            head = text[3:end] if end != -1 else text[3:800]
            m = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", head, re.M)
            if m:
                desc = m.group(1).strip()[:300]
            # category = first path segment under skills/ (convention)
        rel = path.parent.relative_to(path.parent.parent.parent)
        parts = rel.parts
        if len(parts) >= 2:
            cat = parts[0]
    except Exception as e:
        _log(f"frontmatter {path} failed: {e}")
    return name, desc, cat


def _scan_skills(skill_dirs: list[Path]) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for sdir in skill_dirs:
        try:
            for skill_md in sorted(sdir.rglob("SKILL.md")):
                name, desc, cat = _parse_frontmatter(skill_md)
                if name and name not in found:
                    found[name] = {
                        "name": name,
                        "description": desc,
                        "category": cat,
                        "path": str(skill_md.parent),
                    }
        except Exception as e:
            _log(f"scan {sdir} failed: {e}")
    return sorted(found.values(), key=lambda s: s["name"])


def _tool_skill_list(skill_dirs: list[Path]) -> str:
    skills = _scan_skills(skill_dirs)
    if not skills:
        return "No Hermes skills found."
    lines = [
        f"- {s['name']}" + (f" ({s['category']})" if s["category"] else "")
        + (f": {s['description']}" if s["description"] else "")
        for s in skills
    ]
    return f"{len(lines)} Hermes skills (use skill_view(name) for the full procedure):\n" + "\n".join(lines)


def _tool_skill_view(skill_dirs: list[Path], name: str) -> str:
    want = (name or "").strip().lower()
    if not want:
        return "Missing skill name."
    for s in _scan_skills(skill_dirs):
        if s["name"].lower() == want:
            try:
                text = Path(s["path"], "SKILL.md").read_text(encoding="utf-8-sig", errors="replace")
                if text.startswith("---"):
                    end = text.find("\n---", 3)
                    if end != -1:
                        text = text[end + 4:]
                return f"# {s['name']}\n\n" + text.strip()[:SKILL_BODY_CAP]
            except Exception as e:
                return f"Could not read skill '{s['name']}': {e}"
    return f"Skill '{name}' not found. Call skill_list() for available names."


TOOLS = [
    {
        "name": "memory_search",
        "description": "Search the Hermes persistent memory (MEMORY.md notes + USER.md profile) for lines relevant to a query. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for (keywords from the current task)."}},
            "required": ["query"],
        },
    },
    {
        "name": "skill_list",
        "description": "List all Hermes domain skills (name + description). Read-only. Use skill_view to read one in full.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "skill_view",
        "description": "Read a Hermes skill (full procedure: workflows, pitfalls, commands). Read-only. Call skill_list first if unsure of the name.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Skill name, e.g. simpay-provider-integration."}},
            "required": ["name"],
        },
    },
]


def _dispatch(name: str, args: dict, mem_dir: Path | None, skill_dirs: list[Path]) -> str:
    try:
        if name == "memory_search":
            return _tool_memory_search(mem_dir, str((args or {}).get("query", "")))
        if name == "skill_list":
            return _tool_skill_list(skill_dirs)
        if name == "skill_view":
            return _tool_skill_view(skill_dirs, str((args or {}).get("name", "")))
        return f"Unknown tool '{name}'. Available: memory_search, skill_list, skill_view."
    except Exception as e:
        _log(f"tool {name} failed: {e}")
        return f"hermes-bridge: tool '{name}' failed (non-fatal): {e}"


def _respond(rid, result=None, error=None) -> None:
    msg: dict = {"jsonrpc": "2.0", "id": rid}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result if result is not None else {}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def serve(profile: str) -> int:
    mem_dir, skill_dirs = _resolve_profile(profile or os.getenv("HERMES_PROFILE", ""))
    _log(f"profile mem_dir={mem_dir} skill_dirs={len(skill_dirs)}")
    stdin = sys.stdin
    for raw in stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        method = msg.get("method", "")
        rid = msg.get("id")
        params = msg.get("params") or {}
        try:
            if method == "initialize":
                _respond(rid, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "hermes-bridge", "version": "1.0.0"},
                })
            elif method == "tools/list":
                _respond(rid, {"tools": TOOLS})
            elif method == "tools/call":
                tname = params.get("name", "")
                targs = params.get("arguments") or {}
                text = _dispatch(tname, targs, mem_dir, skill_dirs)
                _respond(rid, {"content": [{"type": "text", "text": text}]})
            elif method == "ping":
                _respond(rid, {})
            elif method.startswith("notifications/"):
                continue  # no response for notifications
            elif rid is not None:
                _respond(rid, {})
        except Exception as e:
            _log(f"dispatch failed: {e}")
            if rid is not None:
                _respond(rid, error={"code": -32603, "message": str(e)[:300]})
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="hermes-bridge MCP server (read-only Hermes harness access)")
    ap.add_argument("--profile", default="", help="Hermes profile name (default: $HERMES_PROFILE)")
    args = ap.parse_args(argv)
    return serve(args.profile)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
