# Autokeren Proof — Build Week 2026 Handoff

## Objective

Build a meaningful Build Week extension to the existing Autokeren OSS CLI. Submit in the Developer Tools track as **Autokeren Proof**: a recovery-first coding workflow that turns a task into verifiable release evidence.

The project must not be presented as if all of Autokeren was created during the hackathon. Autokeren began on 2026-07-04. The Build Week submission period began on 2026-07-13 09:00 PT, which is 2026-07-13 23:00 WIB.

## Product Positioning

One-line pitch:

> Autokeren Proof turns an AI coding task into a verifiable release capsule: acceptance criteria, executable evidence, and a clear SHIP, BLOCKED, or NEEDS_HUMAN_REVIEW verdict.

Problem:

Coding agents can produce a convincing diff while leaving uncertainty around tests, deployment, security, and whether the requested outcome actually works. Developers still have to assemble proof manually.

Target user:

Solo developers and small product teams using an agent to change and deploy an application.

Core demo narrative:

1. A user asks the agent to implement a change with explicit acceptance criteria.
2. GPT-5.6 with Codex implements the change.
3. Autokeren Proof records objective evidence for every criterion: test, lint, e2e, endpoint, or human-review check.
4. The terminal renders a release card and verdict.
5. A failed criterion blocks the release; existing checkpoint/rewind capability enables safe recovery.

This is a focused product story. Do not present the submission as a general collection of existing CLI features.

## Eligibility and Evidence

- Owner states that all current Autokeren code is their original work.
- Existing OSS/pip/pipx distribution is allowed. It must be disclosed as a pre-existing project.
- Existing projects are eligible only when meaningfully extended during the submission period.
- The extension must be built using Codex and GPT-5.6. Use one primary Codex session for most core work, then retain its `/feedback` Session ID.
- Current repository commits show work during the period, including GPT-5.6 support on 2026-07-17. That alone is not the meaningful extension; Autokeren Proof must be.

Required README disclosure:

```md
## Build Week 2026 extension

Autokeren existed before OpenAI Build Week and is distributed under the MIT license.
Autokeren Proof was built during the submission period with Codex and GPT-5.6.
It adds an evidence-led release workflow: acceptance criteria, recorded verification,
and a SHIP/BLOCKED/NEEDS_HUMAN_REVIEW release verdict.

### What existed before the hackathon

- Agent loop, tool system, checkpoints/rewind, security scanning, review, and TUI.

### What was built during the hackathon

- [List specific files, commands, tests, and demo artifact here.]
```

## Git Strategy

Current branch created: `hackathon/autokeren-proof`.

1. Find and tag the final commit before 2026-07-13 23:00 WIB, for example `build-week-baseline-2026`.
2. Make all extension commits on `hackathon/autokeren-proof` with conventional commits.
3. Do not rewrite existing history or manipulate dates.
4. Before submission, merge the finished branch into `main` so the public repository URL contains the working project.
5. Add this document and a concise Build Week section to `README.md`.

## Minimum Viable Feature Set

Implement a native `ProofTool`, registered with the normal `ToolRegistry`, and a `/proof` slash-command wrapper.

### Data model

Persist a proof run as JSON under:

```text
.autokeren/proofs/<proof-id>.json
```

Suggested structure:

```json
{
  "id": "proof-20260717T120000Z",
  "title": "Checkout validation is ready to ship",
  "created_at": "2026-07-17T12:00:00+00:00",
  "source_commit": "optional git SHA",
  "criteria": [
    {
      "text": "Invalid email returns a validation error",
      "status": "passed",
      "evidence": "python3 -m pytest demo/tests -q: 4 passed",
      "verified_at": "2026-07-17T12:01:00+00:00"
    }
  ]
}
```

Allowed criterion statuses:

- `pending`
- `passed`
- `failed`
- `blocked`
- `manual_review`

Verdict logic:

- any `failed` or `blocked` => `BLOCKED`
- otherwise any `manual_review` => `NEEDS_HUMAN_REVIEW`
- all `passed` => `SHIP`
- otherwise => `IN_PROGRESS`

### Tool actions

Tool name: `proof`.

- `plan`: accepts a title and a list of acceptance criteria; creates a proof run.
- `record`: updates one criterion with a status and evidence string.
- `report`: returns the release card for an ID.
- `list`: lists stored proof runs and their verdict.

The first version should record evidence, not execute arbitrary commands. Existing `shell`, test, deploy, Camofox, and checkpoint tools already perform execution. That separation prevents the evidence ledger from silently becoming an unsafe shell executor.

Example release card:

```text
AUTOKEREN PROOF — SHIP
proof-20260717T120000Z | Checkout validation is ready to ship

✓ 1. Invalid email returns a validation error [passed] — python3 -m pytest demo/tests -q: 4 passed
✓ 2. The signup page works in browser [passed] — Camofox: submit invalid email shows validation message
✓ 3. No high severity security finding [passed] — /security demo/app.py: no findings
```

### Slash command UX

Implement:

```text
/proof plan <title> | <criterion 1> | <criterion 2>
/proof list
/proof report <proof-id>
/proof record <proof-id> <criterion-number> <status> | <evidence>
```

Keep parser forgiving, display Indonesian runtime output, and preserve English documentation for judges.

## Recommended Architecture

Files expected:

```text
autokeren/tools/proof.py       # ProofTool, persistence, verdict, formatted report
autokeren/tools/__init__.py    # export ProofTool
autokeren/cli.py               # registry registration and /proof handler
tests/test_proof.py            # direct unit tests using tmp_path
docs/BUILD_WEEK_2026_HANDOFF.md
README.md                      # concise Build Week section
```

`ProofTool` should receive `project_root: Path` in its constructor. Do not change the signature of existing tools.

Register it in `build_registry()` in `autokeren/cli.py`:

```python
reg.register(ProofTool(project_root))
```

Use `from __future__ import annotations` and strict type-safe code. Do not add code comments unless necessary. UI text should follow existing Indonesian conventions.

## Tests

Create `tests/test_proof.py` with at least:

1. `plan` rejects missing title or criteria.
2. `plan` creates a JSON run in a temporary project root.
3. all criteria recorded as passed returns `SHIP`.
4. a failed criterion returns `BLOCKED`.
5. a manual-review criterion returns `NEEDS_HUMAN_REVIEW` unless blocked.
6. invalid proof ID / criterion number / status returns an error.
7. `list` returns the persisted runs.
8. registry exposes the `proof` tool after `build_registry()`.

Run:

```bash
ruff check .
mypy autokeren
python3 -m pytest
```

Note: in the current environment, direct `pytest` could not import `autokeren`, but `python3 -m pytest` collected and passed 243 tests. Before submission, ensure plain `pytest` works in a clean install too.

## Demo Artifact

Create a small deterministic demo application under a clearly named directory such as `examples/proof-demo/`.

It should have a real, visible defect or missing feature, plus tests that prove the fix. Good choice: a tiny checkout/signup endpoint where invalid email previously succeeds, then the agent adds validation.

Demo requirements:

- starts locally with a documented command;
- tests do not make external calls;
- has a replayable proof JSON or demo script so judges can evaluate without an OpenAI API key;
- uses a real GPT-5.6/Codex session while building the core feature, shown in the video;
- shows a failed proof first, then repair, then final `SHIP`.

Avoid a fake demo that only prints canned status. The test command and artifact should substantiate the card.

## README Submission Checklist

The final README needs:

- one-line value proposition;
- installation for macOS/Linux/Windows;
- supported Python/platforms;
- fast start and demo command;
- testing command;
- no-key replay/demo option;
- Build Week disclosure above;
- how Codex accelerated the work;
- exact product and engineering decisions made by the human;
- how GPT-5.6 and Codex contributed;
- `/feedback` Session ID placeholder replaced before submit;
- MIT license and third-party attribution if any.

## Three-Minute Video Script

Use English narration and a public YouTube upload.

1. `0:00–0:15`: Problem: an agent can write code, but a diff is not proof it is safe to release.
2. `0:15–0:35`: Introduce Autokeren Proof and show acceptance criteria.
3. `0:35–1:15`: Show GPT-5.6/Codex implementing the change and creating the proof plan.
4. `1:15–1:50`: Run a test/e2e check that fails; card becomes `BLOCKED`.
5. `1:50–2:25`: Show repair, test/e2e passing, and evidence being recorded.
6. `2:25–2:45`: Show final `SHIP` card and checkpoint/rewind relationship.
7. `2:45–3:00`: Explain human decisions and what Codex/GPT-5.6 accelerated.

Do not spend video time listing all pre-existing Autokeren features.

## Deadline Checklist

- Register on Devpost.
- Request credits if still before the official cutoff.
- Build and test the meaningful extension.
- Obtain `/feedback` Codex Session ID.
- Commit and push branch, merge to `main` before submit.
- Record and upload public video under three minutes.
- Add public repository URL, English description, installation, and test access.
- Submit before 2026-07-21 17:00 PDT / 2026-07-22 07:00 WIB.

## Current State

- Branch `hackathon/autokeren-proof` exists.
- Quality baseline before new changes: `ruff check .` passed; `mypy autokeren` passed for 99 source files; `python3 -m pytest` passed 243 tests.
- No Autokeren Proof implementation files have been successfully written yet because the workspace patch helper failed with a sandbox `bwrap` error. Resume implementation from the architecture and tests above.
