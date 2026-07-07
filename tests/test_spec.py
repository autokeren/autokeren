"""Tests for Spec-Driven Auto-Planning."""
from __future__ import annotations

from pathlib import Path

from autokeren.spec.planner import InterviewSession, SpecPlanner, SpecPlan


def test_interview_session_basic():
    s = InterviewSession(request="build a CLI", questions=["Q1", "Q2", "Q3"])
    assert not s.is_complete
    assert s.current_question() == "Q1"
    nxt = s.answer("A1")
    assert nxt == "Q2"
    assert s.current == 1
    nxt = s.answer("A2")
    assert nxt == "Q3"
    nxt = s.answer("A3")
    assert nxt is None
    assert s.is_complete


def test_interview_format_qa():
    s = InterviewSession(request="test", questions=["Q1", "Q2"])
    s.answer("A1")
    s.answer("A2")
    qa = s.format_qa()
    assert "Q1" in qa
    assert "A1" in qa
    assert "Q2" in qa


def test_spec_plan_progress():
    plan = SpecPlan(request="test", steps=["s1", "s2", "s3", "s4"])
    assert plan.progress == 0.0
    plan.mark_done(0)
    assert plan.progress == 25.0
    plan.mark_done(1)
    plan.mark_done(2)
    assert plan.progress == 75.0


def test_spec_plan_mark_done_idempotent():
    plan = SpecPlan(request="test", steps=["s1", "s2"])
    plan.mark_done(0)
    plan.mark_done(0)
    assert len(plan.completed_steps) == 1


def test_spec_plan_mark_done_out_of_range():
    plan = SpecPlan(request="test", steps=["s1"])
    plan.mark_done(5)
    plan.mark_done(-1)
    assert len(plan.completed_steps) == 0


def test_spec_plan_save(tmp_path: Path):
    plan = SpecPlan(request="test", plan_md="# Plan", technical_md="# Tech")
    plan.save(tmp_path)
    assert (tmp_path / "plan.md").exists()
    assert (tmp_path / "technical-plan.md").exists()
    assert (tmp_path / "plan.md").read_text() == "# Plan"


def test_spec_planner_default_questions():
    planner = SpecPlanner(router=None, num_questions=10)
    session = planner.start_interview("build a web app")
    assert len(session.questions) == 10
    assert session.questions[0] == "Apa tujuan utama dari project ini?"


def test_spec_planner_generate_plan_no_router():
    planner = SpecPlanner(router=None, num_questions=5)
    planner.start_interview("build something")
    assert planner.session is not None
    for _ in range(5):
        planner.session.answer("answer")
    plan = planner.generate_plan()
    assert plan is not None
    assert plan.request == "build something"


def test_spec_planner_generate_plan_not_complete():
    planner = SpecPlanner(router=None, num_questions=3)
    planner.start_interview("test")
    assert planner.session is not None
    planner.session.answer("A1")
    plan = planner.generate_plan()
    assert plan is None
