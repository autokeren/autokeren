# Project Journey — autokeren

Timeline milestones & learning. Update tiap fase major.

---

## Phase 0: Concept (Q1 2026)
**Goal:** Pernah kepikiran bikin CLI AI coding khusus Cloudflare stack.

**Decisions:**
- Pilih Python (bukan Go/Node) karena cepat iterate & rich ecosystem
- Pilih Cloudflare Workers AI karena edge di SIN (cepat buat Indonesia)
- Dual auth mode: platform (developers.autokeren.com) vs direct (CF sendiri)

---

## Phase 1: CLI Core (June 2026)
**Goal:** Basic agent loop yang bisa baca-tulis file, run shell, deploy.

**Done:**
- Agent loop: model call → tool dispatch → iterate
- 18 tools: file, shell, search, git, camofox, cf_deploy, tmux, memory, todo
- Model layer: CloudflareModel dengan dual auth, router dengan fallback
- Config: YAML, pydantic validation, --init flow
- UI: rich-based, opencode-style (inline streaming, ⏺ tool marker, ✓ result)
- Permission system: y/a/n per tool
- Session: save/resume, compact, context tracking
- 57 tests, ruff clean, mypy strict

**Learned:**
- Workers AI streaming format berbeda dari OpenAI SSE — perlu adapt
- Kimi K2.6 suka output tool calls sebagai text kalau tools ga di-forward
- pty.openpty() wajib buat shell tool biar isatty=true (wrangler butuh TTY)

---

## Phase 2: Platform API (Q2 2026)
**Goal:** API gateway buat inference + API key management.

**Done:**
- API gateway worker (`api.developers.autokeren.com`)
- OpenAI-compatible endpoint: `/v1/chat/completions`
- API key validation via D1
- Usage tracking (request count + token estimation)
- Rate limiting (daily, KV-based)
- Model management via admin panel (D1-backed)
- 7 models: kimi-code, kimi-2.6, glm-5.2, glm-flash, llama-4-scout, gemma-4, nemotron
- Tool calls forwarding (tools → env.AI.run, response mapping)
- Web dashboard: API key create/revoke, usage stats

**Key bugs fixed:**
- Workers AI return OpenAI format (`choices[0].message`), bukan `result.response`
- `tool_calls` mapping: name & arguments ada di `tc.function`, bukan `tc` langsung
- Streaming usage tracking: ga bisa clone().json() SSE, pakai estimation

---

## Phase 3: DX Polish (July 2026) ← CURRENT
**Goal:** Developer experience yang bikin orang betah.

**Done:**
- Mermaid diagram renderer (visual boxes + arrows di terminal)
- Interactive model selector (fetch dari API, nomor + enter)
- Error handling di agent loop (ga diam pas API error)
- CLI open source ready (README, CONTRIBUTING, AGENTS.md, CI/CD)

**In Progress:**
- Dokumentasi lengkap (runbook, roadmap, decisions)
- Per-minute rate limiting (burst protection)

---

## Phase 4: PaaS — Project Deploy (Q3 2026) ← NEXT
**Goal:** User deploy app tanpa akun CF, 3 menit jadi.

**Plan:**
- API: `POST /v1/projects` → auto-provision D1 + R2
- API: `POST /v1/projects/:id/deploy` → wrangler deploy dengan bindings
- CLI tools: `create_project`, `deploy_project`
- Agent prompt: "buat toko sepatu" → generate code + create + deploy otomatis
- Dashboard: project list, D1 viewer, R2 browser, deploy logs

**Target demo:**
```
kamu: buatin toko sepatu dengan CS responsif
  ↓ 3 menit
✅ https://toko-sepatu-abc123.workers.dev live
  - D1: products table
  - R2: foto sepatu bucket
  - AI: CS chatbot (kimi-2.6)
```

---

## Phase 5: GitHub Integration (Q3 2026)
**Goal:** Connect repo, auto-deploy on push.

**Plan:**
- GitHub OAuth di developers.autokeren.com
- Webhook listener: push to main → build + deploy
- Dashboard: repo list, deploy history, rollback

---

## Phase 6: Growth & Open Source (Q4 2026)
**Goal:** Adoption + community.

**Plan:**
- Open source CLI di GitHub
- Dokumentasi publik (developers.autokeren.com/docs)
- Community: Discord/Telegram buat dev Indonesia
- Apply Cloudflare funding program

---

## Phase 7: Monetization (Q1 2027)
**Goal:** Pro tier, sustainable.

**Plan:**
- Pro tier: custom domain, more projects, more AI requests
- Team plan: shared projects, collaboration
- Marketplace: template gallery (toko online, blog, portfolio, dll)
