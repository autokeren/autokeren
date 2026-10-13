from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest

from autokeren.coord.store import CoordStore
from autokeren.tools.coord import ClaimFilesTool, MergeQueueTool, ReleaseClaimTool


def make_store(tmp_path: Path) -> CoordStore:
    return CoordStore(tmp_path)


class TestClaimGrant:
    def test_grant_claim_baru(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        res = store.claim(["src/app.py"], "agent-1", ttl_seconds=60)
        assert res["status"] == "granted"
        assert res["acquired"] is True
        assert res["claim_id"] == "c-1"
        assert res["paths"] == ["src/app.py"]

    def test_claim_multi_path_atomik(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        res = store.claim(["a.py", "b.py", "c.py"], "agent-1", ttl_seconds=60)
        assert res["status"] == "granted"
        claims = {c["path"] for c in store.status()["claims"]}
        assert claims == {"a.py", "b.py", "c.py"}

    def test_claim_ulang_agent_sama_refresh_ttl(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=10)
        res = store.claim(["a.py"], "agent-1", ttl_seconds=99)
        assert res["status"] == "granted"
        assert store.status(path="a.py")["claims"][0]["remaining_seconds"] > 90

    def test_path_dinormalisasi_dan_dedup(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        res = store.claim(["./a.py", "a.py", "./a.py"], "agent-1", ttl_seconds=60)
        assert res["paths"] == ["a.py"]

    def test_path_absolut_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(ValueError):
            store.claim(["/etc/passwd"], "agent-1")

    def test_path_escape_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(ValueError):
            store.claim(["../luar.py"], "agent-1")

    def test_paths_kosong_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(ValueError):
            store.claim([], "agent-1")

    def test_ttl_invalid_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(ValueError):
            store.claim(["a.py"], "agent-1", ttl_seconds=0)


class TestClaimConflict:
    def test_konflik_path_overlap(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["src/app.py"], "agent-1", ttl_seconds=60)
        res = store.claim(["src/app.py"], "agent-2", ttl_seconds=60)
        assert res["status"] == "conflict"
        assert res["acquired"] is False
        assert res["conflicts"][0]["owner"] == "agent-1"
        assert 50 < res["conflicts"][0]["remaining_seconds"] <= 60
        assert res["options"]["retry_after_seconds"] == res["conflicts"][0]["remaining_seconds"]

    def test_konflik_multi_path_tidak_sebagian(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        res = store.claim(["a.py", "b.py"], "agent-2", ttl_seconds=60)
        assert res["status"] == "conflict"
        claims = store.status()["claims"]
        assert {c["path"] for c in claims} == {"a.py"}

    def test_wait_true_masuk_antrian(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        res = store.claim(["a.py"], "agent-2", ttl_seconds=60, wait=True)
        assert res["status"] == "queued"
        assert res["request_id"] == "w-2"
        assert res["waiters_ahead"] == 0
        assert len(store.status()["waiters"]) == 1

    def test_urutan_antrian_fifo_tercatat(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        for agent in ["agent-2", "agent-3", "agent-4"]:
            res = store.claim(["a.py"], agent, ttl_seconds=60, wait=True)
            assert res["status"] == "queued"
        assert [w["agent_id"] for w in store.status()["waiters"]] == ["agent-2", "agent-3", "agent-4"]


class TestTtlExpiry:
    def test_lease_kedaluwarsa_tak_terlihat(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=0.15)
        time.sleep(0.3)
        claims = store.status(path="a.py")["claims"]
        assert claims == []
        kinds = [e["kind"] for e in store.events()["events"]]
        assert "lease_expired" in kinds

    def test_lease_baru_bisa_claim_setelah_expiry(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=0.15)
        time.sleep(0.3)
        res = store.claim(["a.py"], "agent-2", ttl_seconds=60)
        assert res["status"] == "granted"

    def test_expiry_mempromosikan_waiter(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=0.15)
        store.claim(["a.py"], "agent-2", ttl_seconds=60, wait=True)
        time.sleep(0.3)
        claims = store.status(path="a.py")["claims"]
        assert claims and claims[0]["agent_id"] == "agent-2"
        kinds = [e["kind"] for e in store.events()["events"]]
        assert "lease_granted_from_queue" in kinds


class TestRelease:
    def test_release_eksplisit(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py", "b.py"], "agent-1", ttl_seconds=60)
        res = store.release("agent-1", paths=["a.py"])
        assert res["released"] == ["a.py"]
        remaining = {c["path"] for c in store.status()["claims"]}
        assert remaining == {"b.py"}

    def test_release_semua_milik_agent(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py", "b.py"], "agent-1", ttl_seconds=60)
        store.claim(["c.py"], "agent-2", ttl_seconds=60)
        res = store.release("agent-1")
        assert sorted(res["released"]) == ["a.py", "b.py"]
        assert {c["path"] for c in store.status()["claims"]} == {"c.py"}

    def test_release_idempotent(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        store.release("agent-1", paths=["a.py"])
        res = store.release("agent-1", paths=["a.py"])
        assert res["released"] == []

    def test_release_mempromosikan_waiter(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        store.claim(["a.py"], "agent-2", ttl_seconds=60, wait=True)
        store.claim(["a.py"], "agent-3", ttl_seconds=60, wait=True)
        res = store.release("agent-1")
        assert res["promoted"][0]["agent_id"] == "agent-2"
        assert [w["agent_id"] for w in store.status()["waiters"]] == ["agent-3"]

    def test_promosi_fifo_tidak_mendahului(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        store.claim(["b.py"], "agent-4", ttl_seconds=60)
        store.claim(["a.py", "b.py"], "agent-2", ttl_seconds=60, wait=True)
        store.claim(["b.py"], "agent-3", ttl_seconds=60, wait=True)
        res = store.release("agent-4", paths=["b.py"])
        assert res["promoted"] == []
        store.release("agent-1", paths=["a.py"])
        owners = {c["path"]: c["agent_id"] for c in store.status()["claims"]}
        assert owners == {"a.py": "agent-2", "b.py": "agent-2"}
        assert [w["agent_id"] for w in store.status()["waiters"]] == ["agent-3"]

    def test_waiter_multi_path_butuh_semua_path_bebas(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        store.claim(["b.py"], "agent-2", ttl_seconds=60)
        store.claim(["a.py", "b.py"], "agent-3", ttl_seconds=60, wait=True)
        store.release("agent-1", paths=["a.py"])
        claims = store.status()["claims"]
        assert [(c["path"], c["agent_id"]) for c in claims] == [("b.py", "agent-2")]
        store.release("agent-2", paths=["b.py"])
        owners = {c["path"]: c["agent_id"] for c in store.status()["claims"]}
        assert owners == {"a.py": "agent-3", "b.py": "agent-3"}

    def test_cancel_waiter_via_request_id(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        res = store.claim(["a.py"], "agent-2", ttl_seconds=60, wait=True)
        cancelled = store.release("agent-2", request_id=res["request_id"])
        assert cancelled["cancelled"] == [res["request_id"]]
        assert store.status()["waiters"] == []

    def test_release_semua_membatalkan_waiter_agent(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        store.claim(["a.py"], "agent-2", ttl_seconds=60, wait=True)
        res = store.release("agent-2")
        assert res["cancelled"] == ["w-2"]


class TestPersistensi:
    def test_instance_baru_melihat_state_lama(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        other = CoordStore(tmp_path)
        claims = other.status()["claims"]
        assert [c["agent_id"] for c in claims] == ["agent-1"]

    def test_instance_baru_bisa_release_claim_instance_lain(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        other = CoordStore(tmp_path)
        res = other.release("agent-1")
        assert res["released"] == ["a.py"]
        assert make_store(tmp_path).status()["claims"] == []

    def test_event_log_bertahan_antar_instance(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.claim(["a.py"], "agent-1", ttl_seconds=60)
        store.release("agent-1")
        other = CoordStore(tmp_path)
        assert other.events()["total"] == 2

    def test_state_dir_corrupted_direset(self, tmp_path: Path) -> None:
        (tmp_path / ".autokeren").mkdir(parents=True)
        (tmp_path / ".autokeren" / "coord.json").write_text("{bukan json", encoding="utf-8")
        store = make_store(tmp_path)
        res = store.claim(["a.py"], "agent-1", ttl_seconds=60)
        assert res["status"] == "granted"


class TestKonkurensi:
    def test_thread_race_tepat_satu_granted(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        n = 8
        barrier = threading.Barrier(n)
        results: list[str] = []
        results_lock = threading.Lock()

        def worker(i: int) -> None:
            barrier.wait()
            res = store.claim(["a.py"], f"agent-{i}", ttl_seconds=60)
            with results_lock:
                results.append(res["status"])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results.count("granted") == 1
        assert results.count("conflict") == n - 1


class TestMergeQueue:
    def test_enqueue_dan_status(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        r1 = store.queue_enqueue("main", ["api/auth.py"], "agent-1", change_id="c1")
        assert r1["status"] == "pass"
        assert r1["position"] == 1
        r2 = store.queue_enqueue("main", ["ui/theme.css"], "agent-2", change_id="c2")
        assert r2["status"] == "queued"
        r3 = store.queue_enqueue("main", ["api/auth.py", "api/session.py"], "agent-3", change_id="c3")
        assert r3["status"] == "conflict"
        assert r3["blocked_by"] == ["c1"]
        assert r3["conflicts"][0]["shared_paths"] == ["api/auth.py"]

    def test_dequeue_head_promosi_status(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        for cid, paths, agent in [
            ("c1", ["a.py"], "agent-1"),
            ("c2", ["b.py"], "agent-2"),
            ("c3", ["a.py", "c.py"], "agent-3"),
        ]:
            store.queue_enqueue("main", paths, agent, change_id=cid)
        res = store.queue_dequeue("main", "c1")
        assert res["removed"]["change_id"] == "c1"
        statuses = {e["change_id"]: e["status"] for e in store.queue_status("main")["main"]}
        assert statuses == {"c2": "pass", "c3": "queued"}

    def test_dequeue_hingga_antrian_kosong(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.queue_enqueue("main", ["a.py"], "agent-1", change_id="c1")
        store.queue_enqueue("main", ["a.py"], "agent-2", change_id="c2")
        store.queue_dequeue("main", "c1")
        statuses = {e["change_id"]: e["status"] for e in store.queue_status("main")["main"]}
        assert statuses == {"c2": "pass"}
        store.queue_dequeue("main", "c2")
        assert store.queue_status("main")["main"] == []

    def test_dequeue_change_bukan_head(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.queue_enqueue("main", ["a.py"], "agent-1", change_id="c1")
        store.queue_enqueue("main", ["b.py"], "agent-2", change_id="c2")
        res = store.queue_dequeue("main", "c2")
        assert res["queue_length"] == 1
        assert [e["change_id"] for e in store.queue_status("main")["main"]] == ["c1"]

    def test_change_id_duplikat_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.queue_enqueue("main", ["a.py"], "agent-1", change_id="c1")
        with pytest.raises(ValueError):
            store.queue_enqueue("main", ["b.py"], "agent-2", change_id="c1")

    def test_dequeue_tak_dikenal_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.queue_enqueue("main", ["a.py"], "agent-1", change_id="c1")
        with pytest.raises(ValueError):
            store.queue_dequeue("main", "c9")

    def test_queue_branch_terpisah(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.queue_enqueue("main", ["a.py"], "agent-1", change_id="c1")
        r = store.queue_enqueue("feature-x", ["a.py"], "agent-2", change_id="c2")
        assert r["status"] == "pass"
        with pytest.raises(ValueError):
            store.queue_status("main", change_id="c2")

    def test_queue_status_branch_tak_ada_ditolak(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(ValueError):
            store.queue_status("ghost-branch")

    def test_antrian_tercatat_di_event_log(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.queue_enqueue("main", ["a.py"], "agent-1", change_id="c1")
        store.queue_dequeue("main", "c1")
        kinds = [e["kind"] for e in store.events()["events"]]
        assert "queue_enqueued" in kinds
        assert "queue_dequeued" in kinds


def text(res: Any) -> str:
    return "" if res.output is None else str(res.output)


class TestCoordTools:
    def test_claim_files_granted(self, tmp_path: Path) -> None:
        tool = ClaimFilesTool(tmp_path)
        res = tool.run(paths=["a.py"], agent_id="agent-1", ttl_seconds=60)
        assert res.ok is True
        assert "granted" in text(res)
        assert "claim_id" in text(res)

    def test_claim_files_conflict_response(self, tmp_path: Path) -> None:
        tool = ClaimFilesTool(tmp_path)
        tool.run(paths=["a.py"], agent_id="agent-1", ttl_seconds=60)
        res = tool.run(paths=["a.py"], agent_id="agent-2")
        assert res.ok is True
        assert "CONFLICT" in text(res)
        assert "agent-1" in text(res)

    def test_claim_files_paths_string_dibungkus(self, tmp_path: Path) -> None:
        tool = ClaimFilesTool(tmp_path)
        res = tool.run(paths="a.py", agent_id="agent-1", ttl_seconds=60)
        assert res.ok is True
        assert CoordStore(tmp_path).status()["claims"] != []

    def test_claim_files_error_paths_kosong(self, tmp_path: Path) -> None:
        res = ClaimFilesTool(tmp_path).run(paths=[], agent_id="agent-1")
        assert res.ok is False

    def test_agent_id_default_dari_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTOKEREN_AGENT_ID", "ghost-7")
        res = ClaimFilesTool(tmp_path).run(paths=["a.py"], ttl_seconds=60)
        assert res.ok is True
        assert CoordStore(tmp_path).status()["claims"][0]["agent_id"] == "ghost-7"

    def test_agent_id_default_main_tanpa_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AUTOKEREN_AGENT_ID", raising=False)
        res = ClaimFilesTool(tmp_path).run(paths=["a.py"], ttl_seconds=60)
        assert res.ok is True
        assert CoordStore(tmp_path).status()["claims"][0]["agent_id"] == "main"

    def test_release_claim_tool(self, tmp_path: Path) -> None:
        ClaimFilesTool(tmp_path).run(paths=["a.py"], agent_id="agent-1", ttl_seconds=60)
        res = ReleaseClaimTool(tmp_path).run(agent_id="agent-1")
        assert res.ok is True
        assert '"a.py"' in text(res)
        assert CoordStore(tmp_path).status()["claims"] == []

    def test_release_claim_mempromosikan_waiter(self, tmp_path: Path) -> None:
        ClaimFilesTool(tmp_path).run(paths=["a.py"], agent_id="agent-1", ttl_seconds=60)
        ClaimFilesTool(tmp_path).run(paths=["a.py"], agent_id="agent-2", ttl_seconds=60, wait=True)
        res = ReleaseClaimTool(tmp_path).run(agent_id="agent-1")
        assert res.ok is True
        assert "promoted: ['agent-2']" in text(res)

    def test_merge_queue_tool_flow(self, tmp_path: Path) -> None:
        tool = MergeQueueTool(tmp_path)
        r = tool.run(action="enqueue", branch="main", paths=["a.py"], agent_id="agent-1", change_id="c1")
        assert r.ok is True and "PASS" in text(r)
        r = tool.run(action="enqueue", branch="main", paths=["a.py", "b.py"], agent_id="agent-2", change_id="c2")
        assert r.ok is True and "CONFLICT" in text(r)
        r = tool.run(action="status", branch="main")
        assert r.ok is True and "c1" in text(r) and "c2" in text(r)
        r = tool.run(action="dequeue", branch="main", change_id="c1")
        assert r.ok is True
        r = tool.run(action="status", branch="main", change_id="c2")
        assert r.ok is True and "PASS" in text(r)

    def test_merge_queue_tool_error(self, tmp_path: Path) -> None:
        tool = MergeQueueTool(tmp_path)
        assert tool.run(action="enqueue", branch="main").ok is False
        assert tool.run(action="dequeue", branch="main").ok is False
        assert tool.run(action="invalid", branch="main").ok is False

    def test_tools_terdaftar_di_registry(self, tmp_path: Path) -> None:
        from autokeren.tools import ToolRegistry

        reg = ToolRegistry()
        reg.register(ClaimFilesTool(tmp_path))
        reg.register(ReleaseClaimTool(tmp_path))
        reg.register(MergeQueueTool(tmp_path))
        assert set(["claim_files", "release_claim", "merge_queue"]) <= set(reg.names())
