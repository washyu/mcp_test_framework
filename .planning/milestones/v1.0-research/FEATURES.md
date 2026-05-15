# Feature Research

**Domain:** MCP server testing framework (pytest-based, with LLM-as-judge)
**Researched:** 2026-05-04
**Confidence:** MEDIUM-HIGH

This document maps the feature landscape for MCP server testing tools and the adjacent ecosystems
that inform what users will expect: contract/schema testing (Schemathesis, Pact), LLM evaluation
(DeepEval, RAGAS, promptfoo, MCP-Eval), and the MCP-specific tooling that already exists
(MCP Inspector, mcp-server-tester, mcp-testing-framework, MCPTools, MCP-Bench). Findings are
categorized as **table stakes**, **differentiators**, or **anti-features**, with each item tagged
**MVP** or **post-MVP** to align with the project's narrow MVP scope (one server, one tool,
judge-only, pytest-default output).

---

## Existing MCP Testing Tools (Lay of the Land)

| Tool | Type | What it does | Notable features |
|---|---|---|---|
| **MCP Inspector** ([modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector)) | Official, Anthropic-maintained | Web UI + CLI for interactive testing of MCP servers | stdio/SSE/HTTP transports, tools/resources/prompts panels, "CLI mode" for CI compliance checks |
| **MCP Python SDK testing utilities** ([pypi mcp](https://pypi.org/project/mcp/)) | Official, Anthropic | Provides `stdio_client`, in-memory transport for unit tests | What the project's `McpTestClient` wraps |
| **mcp-server-tester** ([r-huijts](https://github.com/r-huijts/mcp-server-tester)) | Community, Node | Auto-discovers tools, generates tests via Claude, runs validations | Validation rules: `contains`, `matches`, `hasProperty`, `equals`, `arrayLength`; outputs console/JSON/HTML/Markdown; happy/edge/error case generation |
| **mcp-testing-framework** ([L-Qun](https://github.com/L-Qun/mcp-testing-framework)) | Community, Node | Cross-model evaluation: tests how OpenAI/Gemini/Claude/Deepseek choose and call tools | YAML config (`testRound`, `passThreshold`, `modelsToTest`), batch runs, custom provider plugin interface |
| **MCP-Eval** (mcp-agent ecosystem; what `pytest-mcp` on PyPI surfaces toward) | Community, Python | "Pytest-style framework for evaluating MCP servers"; task-based async tests with metric collection (latency, tokens, cost, tool calls); auto-generates baseline test suites; rich console + JSON CI reports | The closest spiritual cousin to what this project is building |
| **MCPTools** ([f/mcptools](https://github.com/f/mcptools)) | Community, Go | CLI-only client/inspector — list, call, scan configs across stdio/HTTP | Prior art for CLI-first ergonomics |
| **MCP-Bench** ([Accenture/mcp-bench](https://github.com/Accenture/mcp-bench)) | Academic benchmark | Benchmarks LLM agents over 28 servers / 250 tools for tool selection, planning, multi-hop execution | Evidence that *agent-side* benchmarking is a separate concern from *server-side* contract testing |
| **mcp-scan / Cisco MCP Scanner / MCPHammer** | Community, security | Scans MCP servers for prompt injection, tool poisoning, cross-origin escalation | Security scanning is a distinct use case; uses LLM-as-judge as one of three engines |
| **FastMCP test client** ([gofastmcp.com/servers/testing](https://gofastmcp.com/servers/testing)) | Server-framework-bundled | In-process test client for FastMCP servers | Different problem: testing your *own* server during development, not black-box testing third-party servers |

**Observation:** No dominant Python-native, pytest-native, *server-agnostic*, *judge-augmented*
framework exists. MCP-Eval is the closest, but it's task/agent-oriented (does the agent succeed
at a task?) rather than contract-oriented (does the tool's schema/description/output conform?).
Node/Go tools (mcp-server-tester, MCPTools) target a different language ecosystem. The MCP
Inspector is interactive/manual. **There is room for a pytest-native, contract-and-quality test
pack focused on schema correctness, description quality, and output conformance.**

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unprofessional.

| Feature | Why Expected | Complexity | MVP? | Notes |
|---|---|---|---|---|
| **stdio transport via official `mcp` SDK** | The dominant MCP transport; protocol compliance non-negotiable | LOW | **MVP** | Already specified — `stdio_client` context manager only |
| **Connect & list tools** | Every MCP tool (Inspector, MCPTools, mcp-server-tester) does this; if you can't list tools, you can't test them | LOW | **MVP** | Spec'd as `list_tools()` + `mcp-test-framework list-tools` subcommand |
| **Schema structural validation** | JSON-Schema correctness is the most basic conformance check; ecosystem pattern from Schemathesis/Pact | LOW | **MVP** | Spec'd: name/description present, `inputSchema.type=="object"`, `required` ⊆ `properties`, every property has type+description |
| **Tool invocation with arguments** | Cannot test a tool without calling it | LOW | **MVP** | Spec'd as `call_tool(name, arguments)` returning `CallToolResult` |
| **Pytest as the test runner** | Python-native, strongest test-runner ecosystem; mirrors DeepEval's positioning ("Pytest for LLM apps") | LOW | **MVP** | Spec'd; `pytest-asyncio` strict mode |
| **CLI entry point that exits non-zero on failure** | CI/CD integration baseline; every framework researched does this | LOW | **MVP** | Spec'd: `mcp-test-framework run` wraps pytest, propagates exit code |
| **Configuration via env vars + file** | Twelve-factor expectation; every comparable tool supports YAML/TOML + env | LOW | **MVP** | Spec'd: env vars first, optional `config.yaml` overlay, CLI flags override |
| **Verbose / quiet flags** | Pytest convention (`-v`, `-q`); every CLI test tool exposes them | LOW | **MVP** | Inherit from pytest; spec mentions `LOG_LEVEL=DEBUG` gating Ollama log noise |
| **Test selection by keyword (`-k`)** | Pytest convention; spec'd in `mcp-test-framework run [-k EXPRESSION]` | LOW | **MVP** | Free via pytest passthrough |
| **Graceful timeout/error handling for external services** | Ollama or MCP server can hang — tests must fail cleanly, not deadlock | MEDIUM | **MVP** | Spec'd: `asyncio.timeout` wraps subprocess + HTTP; bad JSON ≠ crash, just fail |
| **Pass/fail with reasoning from the judge** | LLM-as-judge tools (Promptfoo `llm-rubric`, DeepEval G-Eval, Langfuse) all return both a score and a justification — opaque pass/fail erodes trust | MEDIUM | **MVP** | Spec'd: `JudgeResult { passed, score, reasoning, raw_response }` |
| **Constrained JSON judge output** | Best practice across LLM-eval frameworks; Ollama's `format: json` makes it free | LOW | **MVP** | Spec'd: `format: json` + `stream: false` on `/api/chat` |
| **Categorical integer rubric (1–5)** | Industry consensus: integers with explicit anchors > floats > 1–10 scales (research from Monte Carlo, Confident AI, Patronus) | LOW | **MVP** | Spec'd: 1–5 score, threshold `>= 4` |
| **README with setup + run instructions** | Acceptance-criteria item; baseline OSS expectation | LOW | **MVP** | Spec'd as acceptance criterion #5 |
| **Dependency installation via standard tool** | `uv sync` for Python today; users won't tolerate bespoke install scripts | LOW | **MVP** | Spec'd; `uv` already pinned |

### Differentiators (Competitive Advantage)

Features that set this framework apart. Map directly to the project's "Plant Seed" direction
and the gaps in existing tooling.

| Feature | Value Proposition | Complexity | MVP? | Notes |
|---|---|---|---|---|
| **Description-quality testing as a first-class category** | No existing MCP tool tests this. Research (arxiv 2602.18914) confirms description quality directly determines tool selection probability — it's a real engineering concern, not cosmetic | MEDIUM | **MVP** | Spec'd: `test_description_clarity`, `test_description_disambiguation`, `test_parameters_are_self_explanatory` — this is the core differentiator |
| **Disambiguation rubric** ("could an agent tell this from a similarly-named tool?") | Concrete operational definition of "good description" that competitors lack | MEDIUM | **MVP** | Spec'd; can become a published rubric template |
| **Three-category framing** (schema / description / output) | Clear mental model competitors don't articulate; mirrors test-pyramid logic — deterministic-first, LLM-augmented-second | LOW | **MVP** | Spec'd; this is the documentation/brand story |
| **Local LLM judge by default (Ollama)** | Zero API cost, no key management, fully offline-capable; differentiates from DeepEval/promptfoo defaults that assume hosted models | LOW | **MVP** | Spec'd: Ollama at `127.0.0.1:11434` with `qwen3.6:latest` |
| **Black-box principle** (never imports server source) | Forces framework reusability; explicit contrast to FastMCP's in-process testing | LOW | **MVP** | Spec'd as constraint; documenting it loudly is the differentiator |
| **LLM-generated test inputs from schema/description/output** | The "Plant Seed" — schemathesis-style fuzzing but driven by an LLM that reads intent from descriptions, not just JSON Schema constraints | HIGH | **post-MVP** | Spec'd as Phase 2; framework seams (`OllamaJudge`, schema-aware `McpTestClient`, fixture discovery) must accommodate without rewrites |
| **Pluggable judge backend** | OpenAI-compatible endpoints, hosted Anthropic, custom providers — pattern from L-Qun's framework's `IApiProvider` | MEDIUM | **post-MVP** | Listed as Future Work in spec; design the `OllamaJudge` interface so a `JudgeBackend` Protocol is a natural extraction |
| **Generic conformance test pack** (works against any MCP server out of the box) | "pytest-mcp" branding promise; ship a parameterizable conftest that any user can point at their server | MEDIUM | **post-MVP** | Listed as Future Work; MVP's single-tool hardcoding is the explicit narrowing |
| **Multi-tool / multi-server runs** | Real users have N tools per server; mcp-server-tester and mcp-testing-framework both support this | MEDIUM | **post-MVP** | Explicit Out-of-Scope for MVP; design fixtures so adding parametrization is mechanical |
| **HTTP & SSE transport support** | Hosted MCP servers increasingly use these; stdio-only is a known limitation | MEDIUM | **post-MVP** | Out-of-scope for MVP; abstract transport selection in `McpTestClient` so adding is additive |
| **Snapshot/golden-file response testing** | Established pattern (snapshottest, syrupy, pytest-regressions, pytest-verify) for regression testing of API responses; valuable for "did the tool's output shape change?" | MEDIUM | **post-MVP** | No existing MCP tool ships this; aligns naturally with output-conformance category |
| **Property-based / fuzz test generation from `inputSchema`** | Schemathesis's killer feature for OpenAPI; directly portable to MCP `inputSchema` (also JSON Schema) | HIGH | **post-MVP** | Could be folded into the LLM-input-generation seed or run alongside it (Hypothesis-based deterministic + LLM-driven semantic) |
| **JUnit XML / JSON / Markdown / Allure output** | CI dashboard expectation; industry-standard JUnit XML is the lingua franca; CTRF (Common Test Report Format) is the modern JSON option | LOW | **post-MVP** | Explicit Out-of-Scope for MVP (local-CLI only); pytest gives `--junitxml` for free when needed |
| **`list-tools` / `discover-server` / `dry-run` subcommands** | MCPTools and MCP Inspector establish this as the discoverability pattern users expect | LOW | partially **MVP** | Spec'd: `list-tools` is MVP; `discover-server` (capabilities + transports) and `dry-run` (validate config without running tests) are natural post-MVP additions |
| **Cost / latency / token-usage metrics** | MCP-Eval makes this central; useful when judges run against paid APIs | MEDIUM | **post-MVP** | Free for Ollama (latency only); becomes important when pluggable backends land |
| **Best-of-N judge consensus / self-consistency** | Reduces judge variance — DeepEval/Patronus document this pattern | MEDIUM | **post-MVP** | Explicit Out-of-Scope for MVP; spec says "revisit only if flakiness materially affects signal" |
| **Auto-generated baseline test suite** | mcp-server-tester and MCP-Eval both do this — given a server, generate happy/edge/error cases | HIGH | **post-MVP** | Subset of the LLM-input-generation seed |
| **Web UI / dashboard** | Listed as Future Work | HIGH | **post-MVP** | Explicit Out-of-Scope for MVP |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for *this* framework's positioning.

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Importing/reading the server's source code for "smarter" tests** | Could give richer assertions ("this matches the function signature in your code") | Breaks the black-box principle; couples framework to one server impl; defeats reusability — the project's reusability hinges on never doing this | Treat the server strictly as a subprocess; richer assertions come from parsing the server's *declared* schema, not its source |
| **Testing agent behavior** ("does Claude pick the right tool?") | MCP-Bench and L-Qun's framework both do this; intuitively appealing | Different problem: that benchmarks the *agent*, not the server's contract. Conflating the two muddies the value proposition and balloons scope to multi-LLM API key management | Stay in the contract-testing lane. Point users at MCP-Bench / mcp-testing-framework for agent-side eval. Tagline: "We test the server. They test the agent." |
| **Stateful / destructive tool testing** (write operations, side effects) | Real tools mutate state; users will ask | Test isolation, idempotency, rollback, and fixtures-per-test become hard problems; a single bad call can corrupt user data | Read-only tools only for the foreseeable future; document the constraint loudly. State-aware testing is a separate product |
| **Performance / load testing** | YAML-driven load testing for MCP exists ([democratizequality post](https://democratizequality.substack.com/p/introducing-performance-testing-load)) | Different concern, different tooling (locust, k6, vegeta); muddies focus | Defer; recommend k6 or locust for users with that need |
| **Security testing** (prompt injection, tool poisoning) | mcp-scan, MCPHammer, mcpscan.ai all do this | Security scanning is its own discipline with different threat models, signatures, and update cadences | Defer; integrate with mcp-scan's output rather than re-implement |
| **Best-of-N / retries by default** | "Make flaky judges less flaky" | Hides the actual signal — if the judge is flaky on description quality, that's *real signal* about a vague description | Single-shot judging in MVP; surface variance via raw response logging when debugging |
| **Multi-LLM judge comparison built-in** | mcp-testing-framework does this | Forces API-key management, billing concerns, multi-provider abstractions early; explodes the surface area | Pluggable backend (post-MVP) lets users do this themselves; framework stays opinionated |
| **Web UI** | "Nicer than terminal output" | Operator burden, hosting concerns, security; pytest text output + JUnit XML is the universal contract for CI dashboards | Defer; emit JUnit XML when CI dashboards are a real need |
| **Schema generation FROM tests** ("write tests, get a schema") | Theoretically symmetric to property-based testing | Inverts the protocol — MCP tools *publish* their schemas; the framework's job is to *validate* them | Keep direction one-way: schema is source of truth, tests assert against it |

---

## Feature Dependencies

```
[stdio MCP transport] (SDK)
    └─requires─> [Tool listing]
                     └─requires─> [Schema validation] ──> [Description-quality judging]
                                          └──────> [Tool invocation] ──> [Output conformance]

[Pytest runner] ─enables─> [CLI entry point] ─enables─> [CI/CD integration]
                                                            └─enhanced-by─> [JUnit XML output] (post-MVP)

[OllamaJudge (concrete)] ──refactor──> [JudgeBackend Protocol] (post-MVP)
                                              └─enables─> [Pluggable backends] (OpenAI-compatible, etc.)
                                              └─enables─> [Best-of-N consensus]

[Schema-aware McpTestClient] ──enables──> [LLM-generated test inputs] (the Plant Seed)
                                                  └─enables─> [Auto-generated baseline test suite]
                                                  └─enhanced-by─> [Property-based fuzzing from inputSchema]

[Single tool, single server] ──parametrize──> [Multi-tool runs] ──parametrize──> [Multi-server runs]

[Black-box subprocess] ──conflicts──> [In-process / source-importing tests]
```

### Dependency Notes

- **Schema validation gates description-quality judging:** the judge is fed `name`, `description`,
  `inputSchema` as context. If the schema is malformed, the judge prompt is incoherent. Run
  schema tests first (also faster — fail fast on the cheap deterministic checks).
- **Tool invocation gates output conformance:** can't validate a response shape without a response.
- **The `OllamaJudge` concrete class is the seed for the `JudgeBackend` Protocol:** keep its
  interface narrow (`async def judge(rubric, subject, context) -> JudgeResult`) so extracting a
  Protocol later is a no-op refactor, not a rewrite.
- **Schema-aware `McpTestClient` enables LLM-driven test generation:** the Plant Seed milestone
  (LLM-generated inputs) requires the client to expose tool schemas to the judge. This is already
  how MVP works (schema flows into the description-judge prompt) — extending to "judge generates
  arguments" reuses the same data flow.
- **Multi-tool / multi-server are pure parametrization:** if MVP fixtures are session-scoped on
  `target_tool` (singular), promoting to a parametrized fixture over a list of tools is a small,
  mechanical change. This is what "framework seams should make this easy to add later" means
  in practice.
- **Black-box and source-importing conflict:** these can't coexist. Picking black-box up front
  prevents an entire class of accidental couplings.

---

## MVP Definition

### Launch With (v1) — exactly the spec

Ruthlessly minimum. One server, one tool, three test categories, pytest-default output.

- [x] **stdio MCP client wrapper** (`McpTestClient`) — essential transport
- [x] **`list_tools` + `get_tool` + `call_tool`** — core operations
- [x] **Schema structural validator** (7 deterministic checks) — Category 1
- [x] **Ollama judge** with `JudgeResult` Pydantic model + `format: json` + score-1-to-5 rubric — Category 2 backbone
- [x] **Three description-quality rubrics** (clarity, disambiguation, parameter docs) — the differentiator
- [x] **Output conformance tests** (call with `{}`, validate `CallToolResult` shape, parse JSON / match output schema) — Category 3
- [x] **Pytest fixtures** (`mcp_client`, `judge`, `target_tool`, `config`), session-scoped
- [x] **Config loading** (env vars → optional YAML overlay → CLI flags)
- [x] **CLI entry point** (`mcp-test-framework run`, `list-tools`, `version`) — pytest passthrough for `run`
- [x] **Timeout + error handling** (`asyncio.timeout`, malformed-JSON → test fail not crash)
- [x] **README** with setup, configuration, run instructions
- [x] **`uv sync` clean install**

**Ship criterion:** all six acceptance criteria from the spec hold against `homelab-mcp` /
`list_registered_servers`.

### Add After Validation (v1.x)

Trigger: MVP green against `homelab-mcp`, ready for second user / second tool.

- [ ] **Multi-tool parametrization** — promote `target_tool` to a list; trigger: testing 2+ tools on the same server
- [ ] **`discover-server` subcommand** — print full server capabilities (tools + resources + prompts), not just tools; trigger: users ask "what else does my server expose?"
- [ ] **`dry-run` flag** — validate config and connect-but-don't-test; trigger: CI debugging needs
- [ ] **JUnit XML output** (free via `pytest --junitxml`); trigger: first CI integration where someone wants a Tests tab
- [ ] **Generic conformance test pack** — parametrizable tests that any user can point at any MCP server with zero code; trigger: second external user
- [ ] **Pluggable judge backend** (`JudgeBackend` Protocol; OpenAI-compatible adapter) — trigger: someone wants to use Claude/GPT as judge instead of Ollama

### Future Consideration (v2+)

Trigger: clear product-market fit signals.

- [ ] **LLM-generated test inputs from schema/description/output** — the Plant Seed; the natural v2 headline feature
- [ ] **Property-based fuzzing from `inputSchema`** (Hypothesis integration) — complements LLM-driven generation with deterministic edge cases
- [ ] **Snapshot/golden-file response testing** — regression detection on tool outputs
- [ ] **HTTP and SSE transports** — once stdio is rock-solid and there's demand for hosted servers
- [ ] **Multi-server runs** — once multi-tool is solid
- [ ] **Cost / latency / token-usage metrics** — once pluggable judges land
- [ ] **Best-of-N judge consensus** — only if single-shot judging proves materially flaky
- [ ] **Stateful tool testing** (with setup/teardown contracts) — large surface area, defer until requested by paying users
- [ ] **JSON / Markdown / Allure output** — beyond JUnit XML, only if there's pull
- [ ] **Security testing integration** — wrap or interop with mcp-scan rather than reinvent

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| stdio client + list/call tools | HIGH | LOW | **P1 (MVP)** |
| Schema structural validator | HIGH | LOW | **P1 (MVP)** |
| Ollama judge + JudgeResult | HIGH | MEDIUM | **P1 (MVP)** |
| Three description rubrics | HIGH | LOW | **P1 (MVP)** — the differentiator |
| Output conformance tests | HIGH | LOW | **P1 (MVP)** |
| Pytest fixtures + CLI run/list-tools | HIGH | LOW | **P1 (MVP)** |
| Config loading (env + YAML) | MEDIUM | LOW | **P1 (MVP)** |
| Timeout + error handling | HIGH | MEDIUM | **P1 (MVP)** |
| README | HIGH | LOW | **P1 (MVP)** |
| LLM-generated test inputs | HIGH | HIGH | **P2 (v2 headline)** |
| Multi-tool parametrization | MEDIUM | LOW | **P2** |
| Generic conformance test pack | HIGH | MEDIUM | **P2** |
| Pluggable judge backend | MEDIUM | MEDIUM | **P2** |
| JUnit XML output | MEDIUM | LOW | **P2** |
| HTTP / SSE transports | MEDIUM | MEDIUM | **P2** |
| Snapshot / golden-file tests | MEDIUM | MEDIUM | **P3** |
| Property-based fuzzing | MEDIUM | HIGH | **P3** |
| Best-of-N judge consensus | LOW (until proven needed) | MEDIUM | **P3** |
| Cost/latency metrics | MEDIUM | MEDIUM | **P3** |
| Auto-generated baseline tests | MEDIUM | HIGH | **P3** (overlaps Plant Seed) |
| Web UI | LOW | HIGH | **P3 (likely never)** |
| Stateful/destructive tests | LOW | HIGH | **P3 (likely never)** |
| Source-code importing | NEGATIVE | LOW | **anti-feature, never** |

**Priority key:** P1 = launch (MVP). P2 = next 1–2 milestones after MVP green. P3 = defer until clear demand.

---

## Competitor Feature Analysis

| Feature | mcp-server-tester (Node) | mcp-testing-framework (Node, L-Qun) | MCP Inspector (Anthropic) | MCP-Eval / pytest-mcp (Python) | Schemathesis | DeepEval / promptfoo | **This Framework (planned)** |
|---|---|---|---|---|---|---|---|
| Language | Node | Node | Node + React | Python | Python | Python / Node | **Python** |
| Pytest-native | No | No | No | Yes (claims pytest-style) | Yes | Yes (DeepEval) / No | **Yes** |
| Transports | stdio | stdio + SSE URLs | stdio + SSE + HTTP | (mcp-agent transports) | n/a (HTTP API) | n/a | **stdio (MVP); HTTP/SSE post-MVP** |
| Schema validation | Rule-based (`hasProperty` etc.) | n/a | Manual via UI | Yes (some) | Property-based from OpenAPI | n/a | **7 deterministic structural checks (MVP)** |
| Description-quality testing | No | No | No | No (focus is task success) | n/a | Generic LLM-rubric metrics — but no MCP-specific framing | **Yes — three dedicated rubrics (clarity, disambiguation, parameter docs)** ← differentiator |
| Output conformance | Rule-based assertions | Implicit via task pass/fail | Manual | Yes | Yes (schema-driven) | n/a | **Yes — `CallToolResult` shape + JSON parse + output-schema match** |
| LLM-as-judge | Used to *generate* tests | Used as agent under test (multi-LLM) | No | Yes (eval on agent traces) | No | Yes (G-Eval, llm-rubric, RAGAS metrics) | **Yes — Ollama, single-shot, score 1–5, threshold ≥4** |
| LLM as test-input generator | Yes (Claude generates cases) | n/a | No | Yes (auto-baseline) | Yes (Hypothesis-driven, deterministic) | n/a | **Post-MVP (Plant Seed)** |
| Local LLM by default | No (uses Anthropic API) | No (BYO API keys per provider) | n/a | Configurable | n/a | Configurable | **Yes — Ollama default** ← differentiator |
| Output formats | console / JSON / HTML / Markdown | report dir | n/a (interactive) | rich console + JSON | JUnit + custom | varied | **MVP: pytest default; post-MVP: JUnit XML** |
| YAML config | Yes | Yes | n/a | Yes | Yes | Yes | **Yes (env + YAML overlay)** |
| CLI subcommands | `--init`, `--list`, `--servers` | `init`, `evaluate` | CLI mode for CI | rich CLI | extensive CLI | extensive CLI | **MVP: `run`, `list-tools`, `version`. Post-MVP: `discover-server`, `dry-run`** |
| Black-box principle | Yes | Yes | Yes | Yes | Yes (treats API as black box) | Yes | **Yes — explicit constraint** ← differentiator (vs. FastMCP in-process testing) |
| Multi-server / multi-tool | Yes | Yes | One at a time | Yes | n/a | n/a | **MVP: single. Post-MVP: yes** |

**Where this framework wins (planned):**
1. **Python + pytest-native.** Closes a real gap; the Node tools don't fit Python users' workflows.
2. **Description quality as a first-class testing category** with concrete operational rubrics (clarity / disambiguation / parameter-self-explanatoriness) — nobody else frames it this way.
3. **Local-first judge (Ollama).** Zero API cost, zero key management, offline-capable.
4. **Black-box principle stated as a brand commitment**, not just an implementation detail.

**Where this framework defers (intentionally):**
1. Multi-server/tool, transports beyond stdio — fast-follow features, not MVP.
2. Output formats beyond pytest default — pytest's `--junitxml` is one flag away when needed.
3. Agent-side benchmarking — explicitly someone else's problem (MCP-Bench, mcp-testing-framework).

---

## LLM-as-Judge Pattern Summary (Table-Stakes Requirements)

Cross-referencing Promptfoo, DeepEval, RAGAS, Langfuse, Confident AI, Monte Carlo, Patronus,
and W&B's published guidance, **the table-stakes feature set for an LLM judge** is:

1. **Structured output** — JSON, ideally with provider-side constraint (Ollama `format: json`,
   OpenAI structured outputs). The MVP spec already does this.
2. **Score + reasoning** — pass/fail alone doesn't survive review; need the model's justification.
   The MVP `JudgeResult` already has `reasoning` and `raw_response`.
3. **Categorical integer scoring with anchored levels** — 1–5 with descriptions of what each
   level means beats both binary pass/fail (loses signal) and 1–10 floats (high variance).
   The MVP uses 1–5; the rubric prompts should explicitly anchor each level for best results.
4. **Low temperature** — consistency across runs. The spec doesn't pin this; **add temperature: 0
   (or near-zero) to the Ollama request**. (Worth raising as an implementation note for the
   build phase.)
5. **Strict evaluator persona** in system prompt — the MVP spec already does this:
   "You are a strict technical evaluator…"
6. **Graceful failure on parse error** — malformed JSON from the model → a `JudgeResult` with
   `passed=False` and the raw response logged, not a crash. Spec'd.
7. **Rubric-as-prompt-context, subject-as-evaluation-target separation** — keep the rubric
   reusable across subjects. The `OllamaJudge.judge(rubric, subject, context)` signature
   already enforces this.

**Differentiator opportunities** (beyond table stakes):
- **Best-of-N or self-consistency voting** — defer to post-MVP per spec; only pursue if signal
  proves flaky.
- **Calibration against human-labeled examples** — the gold standard for trusting a judge
  (Patronus, Confident AI guidance); future-work, requires dataset.
- **Chain-of-thought separation** — let the model reason in a `reasoning` field separate from
  the `score`; the MVP `JudgeResult` already structures this. Good.

---

## Sources

### Official MCP / Anthropic
- [Model Context Protocol — Inspector docs](https://modelcontextprotocol.io/docs/tools/inspector)
- [modelcontextprotocol/inspector (GitHub)](https://github.com/modelcontextprotocol/inspector)
- [mcp Python SDK (PyPI)](https://pypi.org/project/mcp/)
- [Introducing the Model Context Protocol — Anthropic](https://www.anthropic.com/news/model-context-protocol)
- [Understanding MCP servers — Model Context Protocol](https://modelcontextprotocol.io/docs/learn/server-concepts)

### MCP Testing Tools (community)
- [r-huijts/mcp-server-tester (GitHub)](https://github.com/r-huijts/mcp-server-tester)
- [L-Qun/mcp-testing-framework (GitHub)](https://github.com/L-Qun/mcp-testing-framework)
- [pytest-mcp (PyPI)](https://pypi.org/project/pytest-mcp/) (MCP-Eval surface)
- [haakco/mcp-testing-framework (GitHub)](https://github.com/haakco/mcp-testing-framework)
- [f/mcptools (GitHub)](https://github.com/f/mcptools)
- [Top MCP servers for test automation — TestGuild](https://testguild.com/top-model-context-protocols-mcp/)
- [How to test MCP server — Testomat.io](https://testomat.io/blog/mcp-server-testing-tools/)
- [MCP Tools vs Official MCP Inspector — fka.dev](https://blog.fka.dev/blog/2025-03-27-mcp-inspector-vs-mcp-tools/)
- [Stop Vibe-Testing Your MCP Server — jlowin.dev](https://jlowin.dev/blog/stop-vibe-testing-mcp-servers)
- [Unit Testing MCP Servers — MCPcat](https://mcpcat.io/guides/writing-unit-tests-mcp-servers/)
- [Testing your FastMCP Server — gofastmcp.com](https://gofastmcp.com/servers/testing)

### MCP Security Tools (anti-feature reference)
- [invariantlabs-ai/mcp-scan (GitHub)](https://github.com/invariantlabs-ai/mcp-scan)
- [cisco-ai-defense/mcp-scanner (GitHub)](https://github.com/cisco-ai-defense/mcp-scanner)
- [praetorian-inc/MCPHammer (GitHub)](https://github.com/praetorian-inc/MCPHammer)
- [mcpscan.ai](https://mcpscan.ai/)
- [npm-audit for MCP security — Stytch](https://stytch.com/blog/mcp-scan/)

### MCP Research (description quality, agent benchmarks)
- [Smell-Aware Evaluation of MCP Server Descriptions (arXiv 2602.18914)](https://arxiv.org/html/2602.18914)
- [MCP-Bench (arXiv 2508.20453)](https://arxiv.org/abs/2508.20453)
- [Accenture/mcp-bench (GitHub)](https://github.com/Accenture/mcp-bench)

### LLM Evaluation Frameworks
- [confident-ai/deepeval (GitHub)](https://github.com/confident-ai/deepeval)
- [Promptfoo LLM Rubric docs](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/)
- [LLM-as-a-Judge — Langfuse](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [LLM-as-a-judge complete guide — Evidently AI](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- [LLM-As-Judge: 7 Best Practices — Monte Carlo](https://www.montecarlodata.com/blog-llm-as-judge/)
- [LLM-as-a-Judge — Confident AI](https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method)
- [LLM As a Judge — Patronus](https://www.patronus.ai/llm-testing/llm-as-a-judge)
- [DeepEval / RAGAS / Phoenix Judges in MLflow](https://mlflow.org/blog/third-party-scorers)
- [Promptfoo vs DeepEval vs RAGAS — genai.qa](https://genai.qa/blog/promptfoo-vs-deepeval-vs-ragas/)
- [DeepEval alternatives 2026 — Braintrust](https://www.braintrust.dev/articles/deepeval-alternatives-2026)
- [Exploring LLM-as-a-Judge — W&B](https://wandb.ai/site/articles/exploring-llm-as-a-judge/)

### Schema & Contract Testing
- [Schemathesis](https://schemathesis.io/)
- [schemathesis/schemathesis (GitHub)](https://github.com/schemathesis/schemathesis)
- [Pact docs](https://docs.pact.io/faq/convinceme)
- [Pactflow — Schema-based contract testing](https://pactflow.io/blog/contract-testing-using-json-schemas-and-open-api-part-3/)
- [Contract vs Schema Testing — Pactflow](https://pactflow.io/blog/contract-testing-using-json-schemas-and-open-api-part-1/)
- [Schemathesis property-based testing — DZone](https://dzone.com/articles/schemathesis-property-based-testing-for-api-schema)

### Pytest CLI & Output
- [pytest documentation — output management](https://docs.pytest.org/en/stable/how-to/output.html)
- [pytest documentation — JUnit XML](https://docs.pytest.org/en/stable/_modules/_pytest/junitxml.html)
- [pytest plugin list](https://docs.pytest.org/en/stable/reference/plugin_list.html)
- [Useful pytest plugins — pytest-with-eric](https://pytest-with-eric.com/pytest-best-practices/pytest-plugins/)

### Snapshot / Golden-File Testing
- [snapshottest (PyPI)](https://pypi.org/project/snapshottest/)
- [pytest-regtest (PyPI)](https://pypi.org/project/pytest-regtest/)
- [Pytest Regressions Data: Golden File Updates 2025 — johal.in](https://johal.in/pytest-regressions-data-golden-file-updates-2025/)
- [Snapshot Testing in Python with pytest-verify — DEV Community](https://dev.to/metahris/snapshot-testing-in-python-with-pytest-verify-1bgo)

---
*Feature research for: MCP server testing framework (pytest-based, judge-augmented)*
*Researched: 2026-05-04*
