from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from autokeren.config import Config
from autokeren.memory import MemoryManager
from autokeren.tools.proof import ProofTool
from autokeren.cli import build_registry


class TestProofTool(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.tool = ProofTool(self.project_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_plan_rejects_missing_title_or_criteria(self) -> None:
        res1 = self.tool.run(action="plan", title="", criteria=["test"])
        self.assertFalse(res1.ok)
        self.assertIn("membutuhkan parameter", res1.error or "")

        res2 = self.tool.run(action="plan", title="Release", criteria=[])
        self.assertFalse(res2.ok)

    def test_plan_creates_json_run_in_temp_project(self) -> None:
        res = self.tool.run(action="plan", title="Test Release", criteria=["Crit 1", "Crit 2"])
        self.assertTrue(res.ok)
        assert res.output is not None
        proof_id = res.output["proof_id"]

        file_path = self.project_root / ".autokeren" / "proofs" / f"{proof_id}.json"
        self.assertTrue(file_path.exists())

        data = json.loads(file_path.read_text())
        self.assertEqual(data["id"], proof_id)
        self.assertEqual(data["title"], "Test Release")
        self.assertEqual(len(data["criteria"]), 2)
        self.assertEqual(data["criteria"][0]["text"], "Crit 1")
        self.assertEqual(data["criteria"][0]["status"], "pending")

    def test_verdict_all_passed_returns_ship(self) -> None:
        res_plan = self.tool.run(action="plan", title="SHIP test", criteria=["Crit 1"])
        assert res_plan.output is not None
        proof_id = res_plan.output["proof_id"]

        res_rec = self.tool.run(
            action="record",
            proof_id=proof_id,
            criterion_num=1,
            status="passed",
            evidence="looks good",
        )
        self.assertTrue(res_rec.ok)
        assert res_rec.output is not None
        self.assertEqual(res_rec.output["verdict"], "SHIP")

    def test_verdict_failed_returns_blocked(self) -> None:
        res_plan = self.tool.run(action="plan", title="BLOCKED test", criteria=["Crit 1", "Crit 2"])
        assert res_plan.output is not None
        proof_id = res_plan.output["proof_id"]

        self.tool.run(action="record", proof_id=proof_id, criterion_num=1, status="passed", evidence="ok")
        res_rec = self.tool.run(
            action="record",
            proof_id=proof_id,
            criterion_num=2,
            status="failed",
            evidence="broken test",
        )
        self.assertTrue(res_rec.ok)
        assert res_rec.output is not None
        self.assertEqual(res_rec.output["verdict"], "BLOCKED")

    def test_verdict_manual_review_returns_needs_human_review(self) -> None:
        res_plan = self.tool.run(action="plan", title="Review test", criteria=["Crit 1", "Crit 2"])
        assert res_plan.output is not None
        proof_id = res_plan.output["proof_id"]

        self.tool.run(action="record", proof_id=proof_id, criterion_num=1, status="passed", evidence="ok")
        res_rec = self.tool.run(
            action="record",
            proof_id=proof_id,
            criterion_num=2,
            status="manual_review",
            evidence="verify visually",
        )
        self.assertTrue(res_rec.ok)
        assert res_rec.output is not None
        self.assertEqual(res_rec.output["verdict"], "NEEDS_HUMAN_REVIEW")

    def test_invalid_arguments_returns_error(self) -> None:
        res = self.tool.run(action="record", proof_id="proof-nonexistentid", criterion_num=1, status="passed")
        self.assertFalse(res.ok)
        self.assertIn("tidak ditemukan", res.error or "")

        res_plan = self.tool.run(action="plan", title="Invalid crit test", criteria=["Crit 1"])
        assert res_plan.output is not None
        proof_id = res_plan.output["proof_id"]

        res_err = self.tool.run(action="record", proof_id=proof_id, criterion_num=5, status="passed")
        self.assertFalse(res_err.ok)

    def test_list_returns_persisted_runs(self) -> None:
        self.tool.run(action="plan", title="Run A", criteria=["Crit A"])
        self.tool.run(action="plan", title="Run B", criteria=["Crit B"])

        res_list = self.tool.run(action="list")
        self.assertTrue(res_list.ok)
        self.assertIn("Run A", str(res_list.output))
        self.assertIn("Run B", str(res_list.output))

    def test_registry_exposes_proof_tool(self) -> None:
        cfg = Config()
        memory = MemoryManager(self.project_root / ".ak-memory.json")
        registry = build_registry(cfg, self.project_root, memory)
        self.assertIn("proof", registry.names())

    def test_replay_renders_correctly(self) -> None:
        proof_data = {
            "id": "proof-123456",
            "title": "Replay Title",
            "created_at": "2026-07-17T12:00:00Z",
            "criteria": [
                {"text": "Crit A", "status": "passed", "evidence": "some evidence", "verified_at": "2026-07-17T12:01:00Z"}
            ]
        }
        json_path = self.project_root / "test-replay.json"
        json_path.write_text(json.dumps(proof_data))

        res = self.tool.run(action="replay", proof_id=str(json_path))
        self.assertTrue(res.ok)
        self.assertIn("AUTOKEREN PROOF REPLAY", str(res.output))
        self.assertIn("Replay Title", str(res.output))

    def test_record_status_validation(self) -> None:
        res_plan = self.tool.run(action="plan", title="Status Test", criteria=["Crit 1"])
        assert res_plan.output is not None
        proof_id = res_plan.output["proof_id"]

        res_ok = self.tool.run(action="record", proof_id=proof_id, criterion_num=1, status="passed")
        self.assertTrue(res_ok.ok)

        res_err = self.tool.run(action="record", proof_id=proof_id, criterion_num=1, status="super_invalid")
        self.assertFalse(res_err.ok)
        self.assertIn("tidak valid", res_err.error or "")

    def test_proof_id_path_traversal_protection(self) -> None:
        # report traversal rejection
        res_report = self.tool.run(action="report", proof_id="../outside")
        self.assertFalse(res_report.ok)
        self.assertIn("ID proof tidak valid", res_report.error or "")

        # record traversal rejection
        res_record = self.tool.run(action="record", proof_id="proof-../../../outside", criterion_num=1, status="passed")
        self.assertFalse(res_record.ok)
        self.assertIn("ID proof tidak valid", res_record.error or "")

    def test_replay_validation(self) -> None:
        # Invalid format (list instead of dict)
        json_path = self.project_root / "test-replay-invalid.json"
        json_path.write_text(json.dumps([{"text": "some criteria"}]), encoding="utf-8")
        res = self.tool.run(action="replay", proof_id=str(json_path))
        self.assertFalse(res.ok)
        self.assertIn("harus berupa object/dictionary", res.error or "")

        # Missing criteria
        json_path.write_text(json.dumps({"id": "proof-1"}), encoding="utf-8")
        res2 = self.tool.run(action="replay", proof_id=str(json_path))
        self.assertFalse(res2.ok)
        self.assertIn("harus mengandung list 'criteria'", res2.error or "")

        # Invalid criterion dict structure
        json_path.write_text(json.dumps({"id": "proof-1", "criteria": ["not-a-dict"]}), encoding="utf-8")
        res3 = self.tool.run(action="replay", proof_id=str(json_path))
        self.assertFalse(res3.ok)
        self.assertIn("harus berupa object/dictionary", res3.error or "")

        # Invalid status in criterion
        json_path.write_text(json.dumps({
            "id": "proof-1",
            "criteria": [{"text": "Crit A", "status": "invalid_status"}]
        }), encoding="utf-8")
        res4 = self.tool.run(action="replay", proof_id=str(json_path))
        self.assertFalse(res4.ok)
        self.assertIn("memiliki status 'invalid_status' yang tidak valid", res4.error or "")

    def test_replay_verdict_verifications(self) -> None:
        # BLOCKED verdict
        json_path = self.project_root / "test-replay-blocked.json"
        json_path.write_text(json.dumps({
            "id": "proof-blocked",
            "title": "Blocked Run",
            "criteria": [{"text": "Crit A", "status": "blocked"}]
        }), encoding="utf-8")
        res_blocked = self.tool.run(action="replay", proof_id=str(json_path))
        self.assertTrue(res_blocked.ok)
        self.assertIn("BLOCKED", str(res_blocked.output))

        # NEEDS_HUMAN_REVIEW verdict
        json_path_mr = self.project_root / "test-replay-mr.json"
        json_path_mr.write_text(json.dumps({
            "id": "proof-mr",
            "title": "Manual Review Run",
            "criteria": [{"text": "Crit A", "status": "manual_review"}]
        }), encoding="utf-8")
        res_mr = self.tool.run(action="replay", proof_id=str(json_path_mr))
        self.assertTrue(res_mr.ok)
        self.assertIn("NEEDS_HUMAN_REVIEW", str(res_mr.output))

    def test_proof_schema_enum(self) -> None:
        enum_list = self.tool.parameters["properties"]["action"]["enum"]
        self.assertIn("replay", enum_list)

    def test_atomic_write(self) -> None:
        # Verify atomic write leaves a clean valid file
        res_plan = self.tool.run(action="plan", title="Atomic Test", criteria=["Crit 1"])
        assert res_plan.output is not None
        proof_id = res_plan.output["proof_id"]

        file_path = self.tool.proofs_dir / f"{proof_id}.json"
        self.assertTrue(file_path.exists())

        # Repeated record calls
        for i in range(5):
            res_rec = self.tool.run(action="record", proof_id=proof_id, criterion_num=1, status="passed", evidence=f"run {i}")
            self.assertTrue(res_rec.ok)
            # Should be valid JSON
            content = json.loads(file_path.read_text(encoding="utf-8"))
            self.assertEqual(content["criteria"][0]["status"], "passed")
            self.assertEqual(content["criteria"][0]["evidence"], f"run {i}")
