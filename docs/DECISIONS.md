# Architecture Decision Records (ADR)

Key decisions, kenapa dipilih, dan tradeoffs.

---

## ADR-001: Python untuk CLI (bukan Go/Node)

**Status:** Accepted
**Date:** June 2026

**Context:** Butuh CLI yang cepat iterate, rich ecosystem, dan gampang kontribusi.

**Decision:** Python 3.11+.

**Tradeoffs:**
- ✅ Cepat develop, rich ecosystem (httpx, rich, pydantic)
- ✅ Dev Indonesia kebanyakan kenal Python
- ❌ Lebih lambat dari Go buat CLI startup
- ❌ Distribution ribet (pip vs binary)

---

## ADR-002: Dual Auth Mode (Platform vs Direct)

**Status:** Accepted
**Date:** June 2026

**Context:** User bisa pakai platform autokeren (API key) atau CF credentials sendiri.

**Decision:** Config `auth.mode = "platform" | "direct"`. Platform mode kirim ke `api.developers.autokeren.com`, direct mode kirim ke CF API langsung.

**Tradeoffs:**
- ✅ Flexibility: user punya pilihan
- ✅ Platform mode = ga perlu CF account
- ✅ Direct mode = full control, no middleman
- ❌ Code complexity: 2 code path
- ❌ Model ID mapping: platform pakai alias, direct pakai @cf/...

---

## ADR-003: API Gateway sebagai Proxy (bukan direct CF binding di CLI)

**Status:** Accepted
**Date:** June 2026

**Context:** CLI bisa langsung call CF Workers AI API, atau via API gateway.

**Decision:** Platform mode selalu via API gateway. CLI ga pernah pegang CF credentials.

**Tradeoffs:**
- ✅ Security: CF token stay di server
- ✅ Rate limiting & usage tracking centralized
- ✅ Bisa ganti model tanpa update CLI
- ❌ Extra latency (1 hop)
- ❌ API gateway = single point of failure

---

## ADR-004: Workers AI return OpenAI format

**Status:** Discovered
**Date:** July 2026

**Context:** Workers AI `env.AI.run()` return response dalam format OpenAI (`choices[0].message.content`), bukan format lama (`result.response`).

**Decision:** API gateway ekstrak dari `result.choices[0].message`.

**Impact:** Kalau CF ubah format lagi, perlu update dispatch.ts.

---

## ADR-005: Tool Calls Forwarding

**Status:** Accepted
**Date:** July 2026

**Context:** CLI kirim `tools` array ke API gateway. Gateway perlu forward ke Workers AI.

**Decision:** Gateway forward `body.tools` dan `body.tool_choice` ke `env.AI.run()`. Response `tool_calls` di-map dari `tc.function.name` dan `tc.function.arguments`.

**Tradeoffs:**
- ✅ Model tau tools, output proper tool_calls (bukan text)
- ✅ Agent loop jalan bener (loop, execute, iterate)
- ❌ Streaming + tool calls mungkin ga full support di semua model

---

## ADR-006: D1 per Project (bukan shared)

**Status:** Accepted
**Date:** July 2026

**Context:** User butuh database isolation. Bisa 1 D1 shared dengan `user_id` column, atau D1 terpisah per project.

**Decision:** D1 terpisah per project (`autokeren-proj-{project_id}`).

**Tradeoffs:**
- ✅ Full isolation — user A ga bisa akses data user B
- ✅ Gampang backup/restore per project
- ✅ Gampang delete project (drop database)
- ❌ Lebih banyak databases (CF D1 limit: 50 per account free)
- ❌ Cross-project query sulit

**Mitigation:** CF D1 limit bisa di-raise dengan plan.

---

## ADR-007: Open Source CLI, Closed Source Platform

**Status:** Accepted
**Date:** July 2026

**Context:** CLI bisa di-open source, tapi API gateway & dashboard contain CF credentials dan business logic.

**Decision:**
- Open source: CLI (`autokeren/` package), tools, mermaid renderer, selector
- Closed source: API gateway, web dashboard, admin panel, D1 schema

**Tradeoffs:**
- ✅ Trust: user bisa audit CLI code
- ✅ Community: dev bisa kontribusi tools
- ✅ Marketing: "open source AI CLI buatan Indonesia"
- ❌ Platform logic ga transparan (tapi ini standar industri)

---

## ADR-008: Mermaid Renderer — Visual Boxes + Arrows

**Status:** Accepted
**Date:** July 2026

**Context:** Model output mermaid diagram sebagai ```mermaid block. Butuh render di terminal.

**Decision:** 
1. Coba inline image (iTerm2/kitty protocol) kalau terminal support
2. Fallback: chafa ANSI art
3. Fallback: visual box-drawing (┌─┐│└┘▼)
4. Fallback: text arrows (──→)

**Tradeoffs:**
- ✅ Terminal modern (WezTerm, kitty): gambar asli inline
- ✅ Terminal biasa: visual boxes masih bagus
- ❌ Layout algorithm simple (BFS levels, bukan graphviz)
- ❌ Complex graphs (>15 nodes) mungkin berantakan
