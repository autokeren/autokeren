"""FDDM auto-hook — automatic sniff before task, emit after task completion."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fddm_sniff(url: str, query: str, top_k: int = 3, radius: float = 0.2, api_key: str = "") -> list[dict[str, Any]]:
    try:
        import httpx

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        r = httpx.post(
            f"{url.rstrip('/')}/api/sniff_text",
            json={"text": query, "top_k": top_k, "radius": radius},
            headers=headers,
            timeout=10.0,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.debug(f"FDDM sniff failed: {e}")
        return []


def fddm_emit(url: str, type_: str, text: str, emitter_id: str = "autokeren_auto", api_key: str = "") -> bool:
    try:
        import httpx

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        r = httpx.post(
            f"{url.rstrip('/')}/api/emit_text",
            json={"type": type_, "text": text, "emitter_id": emitter_id, "base_score": 0.6},
            headers=headers,
            timeout=10.0,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.debug(f"FDDM emit failed: {e}")
        return False


def build_sniff_context(fddm_url: str, query: str, api_key: str = "") -> str:
    """Sniff FDDM dan format hasil sebagai context message untuk agent."""
    if not fddm_url:
        return ""
    results = fddm_sniff(fddm_url, query, api_key=api_key)
    if not results:
        return ""
    lines = ["🐜 FDDM AUTO-SNIFF: Memori relevan dari sesi/project sebelumnya:"]
    for i, hit in enumerate(results, 1):
        artifact = str(hit.get("artifact", ""))[:200]
        scent_type = hit.get("type", "?")
        score = hit.get("score", 0)
        lines.append(f"  {i}. [{scent_type}] (score {score:.2f}) {artifact}")
    return "\n".join(lines)


def auto_emit_completion(fddm_url: str, user_task: str, agent_response: str, api_key: str = "") -> None:
    """Auto-emit ke FDDM setelah agent selesai task."""
    if not fddm_url or not agent_response or len(agent_response.strip()) < 20:
        return
    summary = f"Task: {user_task[:200]}\nResult: {agent_response[:500]}"
    fddm_emit(fddm_url, "decision", summary, emitter_id="autokeren_auto", api_key=api_key)
# ak:96ca274ded73d234
