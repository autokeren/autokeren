"""FDDM auto-hook — automatic sniff before task, emit after task completion."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

FDDM_DEFAULT_URL = "https://autokeren-b6481c9f.pyscalp.workers.dev"


def fddm_sniff(query: str, top_k: int = 3, radius: float = 0.2) -> list[dict[str, Any]]:
    try:
        import httpx

        r = httpx.post(
            f"{FDDM_DEFAULT_URL}/api/sniff_text",
            json={"text": query, "top_k": top_k, "radius": radius},
            timeout=10.0,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.debug(f"FDDM sniff failed: {e}")
        return []


def fddm_emit(type_: str, text: str, emitter_id: str = "autokeren_auto") -> bool:
    try:
        import httpx

        r = httpx.post(
            f"{FDDM_DEFAULT_URL}/api/emit_text",
            json={"type": type_, "text": text, "emitter_id": emitter_id, "base_score": 0.6},
            timeout=10.0,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.debug(f"FDDM emit failed: {e}")
        return False


def build_sniff_context(query: str) -> str:
    """Sniff FDDM dan format hasil sebagai context message untuk agent."""
    results = fddm_sniff(query)
    if not results:
        return ""
    lines = ["🐜 FDDM AUTO-SNIFF: Memori relevan dari sesi/project sebelumnya:"]
    for i, hit in enumerate(results, 1):
        artifact = str(hit.get("artifact", ""))[:200]
        scent_type = hit.get("type", "?")
        score = hit.get("score", 0)
        lines.append(f"  {i}. [{scent_type}] (score {score:.2f}) {artifact}")
    return "\n".join(lines)


def auto_emit_completion(user_task: str, agent_response: str) -> None:
    """Auto-emit ke FDDM setelah agent selesai task. Extract insight dari response."""
    if not agent_response or len(agent_response.strip()) < 20:
        return

    summary = f"Task: {user_task[:200]}\nResult: {agent_response[:500]}"
    fddm_emit("decision", summary, emitter_id="autokeren_auto")
# ak:db3f8a21384cba79
