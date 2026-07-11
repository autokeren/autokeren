# Roadmap — autokeren

Prioritas feature, quarter by quarter.

---

## Q3 2026 — PaaS Foundation

### P0: Project Deploy (core)
- [ ] API: `POST /v1/projects` — create project + provision D1 + R2
- [ ] API: `POST /v1/projects/:id/deploy` — deploy Worker dengan auto-bindings
- [ ] API: `GET /v1/projects` — list user projects
- [ ] API: `GET /v1/projects/:id` — project detail (D1, R2, URL, status)
- [ ] CLI tool: `create_project` — call API, simpan project info
- [ ] CLI tool: `deploy_project` — send Worker code, return URL
- [ ] Agent prompt update: otomatis create + deploy pas user minta app
- [ ] D1 table: `projects` (id, user_id, name, d1_id, r2_bucket, worker_name, url, status)

### P0: Per-minute Rate Limiting
- [ ] KV sliding window per API key
- [ ] Free: 10 req/menit, Pro: 50 req/menit
- [ ] 429 response dengan Retry-After header

### P1: Dashboard Project View
- [ ] Project list page
- [ ] Project detail: D1 tables, R2 files, deploy logs
- [ ] Deploy history dengan rollback button

### P1: Worker Template System
- [ ] Template: Static site (HTML/CSS/JS)
- [ ] Template: API server (Hono/itty-router)
- [ ] Template: Full-stack (HTML + API + D1 + AI)
- [ ] Template: Chat app (AI-powered)
- [ ] Template: E-commerce (products + cart + CS bot)

---

## Q4 2026 — Growth & Open Source

### P0: Open Source CLI
- [ ] Public GitHub repo
- [ ] LICENSE (MIT)
- [ ] PyPI publish (`pip install autokeren`)
- [ ] Documentation site (developers.autokeren.com/docs)
- [ ] Getting started guide
- [ ] Example projects

### P0: GitHub Integration
- [ ] GitHub OAuth connect di dashboard
- [ ] Webhook: push to main → auto deploy
- [ ] Branch preview deploy (`*.preview.autokeren.com`)
- [ ] Deploy status check di GitHub (commit status)

### P1: CLI Improvements
- [ ] Multi-agent (parallel tool execution)
- [ ] Context retrieval (embeddings + Vectorize)
- [ ] Voice input (Whisper API)
- [ ] Plugin system (custom tools)

### P2: Community
- [ ] Discord/Telegram buat dev Indonesia
- [ ] Template marketplace
- [ ] Hackathon: "30 hari deploy bareng autokeren"

---

## Q1 2027 — Monetization

### P0: Pro Tier
- [ ] Payment gateway (Midtrans/Xendit)
- [ ] Pro subscription ($9/mo atau Rp 99rb/mo)
- [ ] Custom domain support
- [ ] Team collaboration

### P1: Enterprise
- [ ] Self-hosted option (on-prem CF account)
- [ ] SSO (Google Workspace)
- [ ] Audit log
- [ ] SLA 99.9%

### P2: AI Improvements
- [ ] Fine-tuned model buat Indonesian context
- [ ] Multi-modal (image input)
- [ ] Code search across all user projects

---

## Backlog (future)

- [ ] Mobile app (React Native dashboard)
- [ ] VS Code extension
- [ ] Cursor integration
- [ ] Custom domain marketplace
- [ ] Edge database replication (multi-region)
- [ ] WebSocket support (real-time apps)
- [ ] Cron triggers (scheduled tasks)
- [ ] Queue consumers (background jobs)

---

## Done

### July 2026
- [x] Mermaid diagram renderer (visual boxes + arrows)
- [x] Interactive model selector (API-backed)
- [x] Error handling di agent loop
- [x] Tool calls forwarding di API gateway
- [x] 7 model terbaru (kimi-code, glm-5.2, nemotron, dll)
- [x] D1-backed model management
- [x] AGI Fase 1: Dynamic Tool Synthesis (Hot-loading dari `.ak-tools/`)
- [x] AGI Fase 2: Local-First Memory Store & TF-IDF Semantic VSM Search
- [x] AGI Fase 3: Continuous Lifelong Daemon (Log Tailing & File Watcher)
- [x] AGI Fase 4: Self-Refactoring & Self-Evolution Loop

### June 2026
- [x] CLI v0.4: 18 tools, streaming, session, memory
- [x] API gateway: AI inference + API key + usage tracking
- [x] Web dashboard: API key management
- [x] Admin panel: model management
- [x] Open source prep: README, CONTRIBUTING, CI/CD
