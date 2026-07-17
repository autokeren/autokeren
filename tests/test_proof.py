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
        res = self.tool.run(action="record", proof_id="nonexistent-id", criterion_num=1, status="passed")
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
