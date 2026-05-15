# Pitfalls Research — v1.4 Library Mode Delivery

**Domain:** Pytest plugin packaging for third-party operator installation (CLI-first → library-first inversion)
**Researched:** 2026-05-15
**Confidence:** HIGH on integration-with-other-plugins pitfalls (well-documented in pytest-asyncio / pytest-xdist / pytest-sugar source + issue trackers); HIGH on the four repo-specific pitfalls (_isolation, _preflight, MCPTF_CONFIG_FILE, banned-imports test) — verified against current `src/` and `tests/conftest.py`; MEDIUM on the codegen-output-path-in-site-packages chain — failure modes inferred from PEP 561 + standard wheel install semantics, not from an operator repro.

## Scope

These pitfalls are specific to **shipping `mcp_test_framework` as an importable pytest plugin that auto-loads via `[project.entry-points.pytest11]`** in an arbitrary operator's repo. They are NOT generic Python packaging advice. The framework currently runs entirely under our own `tests/conftest.py` with hand-wired `pytest_plugins = ["mcp_test_framework.fixtures"]`, our own pyproject defaults, and our own asyncio/marker config — every one of those will become a contention point in v1.4 when an arbitrary operator's `pyproject.toml`, `conftest.py`, and other plugins enter the picture.

---

## Critical Pitfalls

### Pitfall 1: _preflight autouse fires in the operator's framework-self-test session — HIGH

**What goes wrong:**
`fixtures.py:_preflight` is `autouse=True, scope="session"`. The instant the operator's pytest loads `mcp_test_framework.fixtures` as a plugin via the pytest11 entry point, every pytest session — including the operator running `pytest tests/test_my_business_logic.py` with no contract tests selected — will trigger preflight. Preflight calls `pytest.exit(returncode=2)` if Ollama is unreachable or the MCP server command is not on PATH. The operator who just wanted to run their own unit tests gets `MCP command 'uvx' not found on PATH; next: ...` and a non-zero exit code from a test run that doesn't even touch the MCP framework.

The current `_session_needs_preflight` predicate guards on `tests/contract/` / `tests/sdet/` nodeid prefixes — but those prefixes are **this repo's layout**, not the operator's. An operator who puts contract tests under `tests/mcp_contract/` or just registers them inline in `tests/conftest.py` will see preflight short-circuit (silently skipping the gate they wanted) OR preflight will fire on tests that have nothing to do with MCP.

**Why it happens:**
The autouse + session-scope combo plus a hard-coded path prefix is a CLI-mode-only invariant. In CLI mode, our subprocess wrapper guarantees `tests/contract/` exists in the launched session. In library mode, the operator owns the test tree.

**How to avoid:**
1. **Replace the path-prefix predicate with a `register()`-driven activation flag.** The framework keeps a module-level `_REGISTRATIONS` list (populated by `register(...)`); `_preflight` short-circuits when the list is empty.
2. **Make preflight opt-in via marker or an explicit `enable_preflight=True` kwarg** on `register()`. Default behavior: no preflight unless the operator says they want it.
3. **Never call `pytest.exit()` from an auto-loaded plugin fixture.** It can preempt the operator's unrelated tests. Use `pytest.skip()` at the parametrize-time hook instead, or raise during the gated test only.

**Warning signs:**
- Operator installs the package, runs `pytest`, gets a session-abort from preflight on a test they never wrote.
- Test for: dogfood the plugin in a fixture-only sample repo with NO contract tests collected; assert `pytest` exit code 0.

**Phase to address:** Phase 1–2 (`register()` design + plugin activation). Must NOT ship Phase 3 (extract contract tests) before this is fixed.

---

### Pitfall 2: `MCPTF_CONFIG_FILE` env var leaks across the operator's tool ecosystem — HIGH

**What goes wrong:**
`config.py` and `fixtures.py:config` read `MCPTF_CONFIG_FILE` as a path pointer. The operator's CI may export `MCPTF_CONFIG_FILE` for one project (the homelab-mcp test rig); a sibling project in the same CI runner that uses our package as a library inherits the env var and silently loads a config from another project's tree. Worse: the typo-silent-fail memory entry (`project_mcptf_config_file_silent_fail`) shows env-var-driven config has already burned us once in CLI mode. In library mode, where the operator never **set** the env var (their CI did), this gets harder to debug, not easier.

The seed says library-mode operators pass config as `register()` kwargs — but the env var is still **read** by `Config()` via `settings_customise_sources`. So both paths active simultaneously = precedence collision.

**Why it happens:**
Memory entry `project_dotenv_silently_beats_config` and `project_mcptf_config_file_silent_fail` — both v1.2 fixes — addressed the CLI side. Library mode adds a third precedence axis (`register()` kwargs) without removing the env-var path.

**How to avoid:**
1. **In library mode, ignore `MCPTF_CONFIG_FILE` entirely.** When `register()` is called, the kwargs ARE the config — no env var read, no YAML overlay unless explicitly requested.
2. **Rename the env var to be project-namespaced** (`MCPTF_HOMELAB_CONFIG_FILE` or document that operators MUST namespace their CI env). The current `MCPTF_*` prefix is global to the framework; in library mode every operator project shares the same namespace.
3. **Document precedence as: `register()` kwargs > `register(config_file=...)` > raises; env vars are CLI-mode only.**
4. **Fail loud, not silent**, if both `register(...)` kwargs AND `MCPTF_CONFIG_FILE` are set in the same session — that combo is almost certainly a misconfiguration, not an intentional override.

**Warning signs:**
- Operator's CI runs two pytest jobs back-to-back; the second one picks up the first's env-exported `MCPTF_CONFIG_FILE`.
- Operator reports "I called `register(tools=[...])` but it's running tools from some other config file."
- Test for: in the dogfood test, set `MCPTF_CONFIG_FILE=/nonexistent` AND call `register(tools=["x"])`; assert the session either fails loud or honors `register()` and ignores the env var.

**Phase to address:** Phase 1 (config-source design). Must be decided BEFORE any docs mention `register()` examples.

---

### Pitfall 3: Pytest plugin auto-load races with the operator's pytest-asyncio config — HIGH

**What goes wrong:**
Once `[project.entry-points.pytest11]` is wired, the operator's pytest loads `mcp_test_framework.fixtures` automatically. The framework's session-scoped async fixtures (`mcp_client`, `judge`, `_preflight`) all use `loop_scope="session"`. The framework's own pyproject pins `asyncio_default_fixture_loop_scope = "session"`. The operator's pyproject may pin `asyncio_default_fixture_loop_scope = "function"` (the pytest-asyncio default in earlier versions) OR may not set it at all (relying on per-test loops). Result:

- Operator has function-scope default + framework session-scope async fixtures = **"asyncio fixture with wider loop scope than its dependents" warnings**, or worse, runtime `RuntimeError: got Future attached to a different loop` on teardown.
- Operator running `asyncio_mode = "auto"` (still common in older repos): the framework's `@pytest_asyncio.fixture` markers still work, but operator-side tests without `@pytest.mark.asyncio` are auto-promoted, and the AnyIO conflict warning in pytest-asyncio docs fires.

Compounding factor: `_preflight` is autouse session-scoped async — it pulls the operator into session-scoped event loop semantics whether they wanted it or not.

**Why it happens:**
pytest-asyncio strict mode is **per-project-config**, not negotiable between plugin and host. The framework can't dictate `asyncio_default_fixture_loop_scope` to the operator's project; setting it in framework code is impossible. The pytest-asyncio docs explicitly call strict mode "intended for projects that want to support multiple asynchronous programming libraries" — but the framework currently **assumes** session-scope-as-default, which is a project config, not a framework primitive.

**How to avoid:**
1. **Declare framework-side async fixtures with explicit `loop_scope="session"` on every `@pytest_asyncio.fixture`** (already done — verified in `fixtures.py`), AND document that operators MUST set `asyncio_default_fixture_loop_scope = "session"` in their `pyproject.toml`. Detect at session-start if this is unset and emit an actionable error.
2. **Provide a `pytest_configure` hook on the plugin** that reads `config.getini("asyncio_default_fixture_loop_scope")` and warns/errors if it's not `"session"`. Friendly fail-fast.
3. **Compatibility doc section: "pytest-asyncio coexistence"** — show the exact ini block the operator needs, plus a snippet for projects using anyio's pytest plugin instead (recommend they keep strict mode for both).
4. **Never warn-then-degrade.** If the operator's config is incompatible, abort with a clear error message; don't silently run with broken loop scoping.

**Warning signs:**
- Operator reports flaky teardown errors like `Future attached to a different loop`.
- Operator's CI suddenly hangs at session teardown after installing the framework.
- Test for: a sample-operator-repo CI matrix testing combinations of `asyncio_mode = strict|auto` × `loop_scope = function|session` × `pytest-asyncio versions 0.23, 1.0, 1.3`.

**Phase to address:** Phase 2 (pytest plugin entry point). Plugin self-check at `pytest_configure` is the cheapest possible insurance.

---

### Pitfall 4: Codegen output written to `site-packages/` (read-only, blown away on `pip install --upgrade`) — HIGH

**What goes wrong:**
`cfg.sdet.generated_root` is a required Pydantic field today. In CLI mode the operator sets it explicitly in their `config.yaml` (typically `tests/_generated/` next to their tests — Phase 21.1 enforced this). In library mode the operator may:

- (a) **Not set it at all.** `register()` is called without a `generated_root` kwarg; Pydantic raises a missing-required-field error. The error message references `config.yaml` — but in library mode there IS no config.yaml. Operator is confused.
- (b) **Pass a relative path** like `"tests/_generated"`. The framework resolves it from `os.getcwd()` at codegen time. CI may run pytest from a non-repo-root cwd (monorepo with `cd packages/foo && pytest`); the generated tree lands in `packages/foo/tests/_generated/`, but the operator imports from `tests/_generated/` at the monorepo root. ImportError on `<Tool>Params`.
- (c) **Default the framework to `<package_install_dir>/generated/`** — i.e., `site-packages/mcp_test_framework/generated/`. This writes to a directory that pip will **wipe** on the next `pip install --upgrade mcp-test-framework`, the operator's IDE won't index it (gitignored OR outside their workspace), the operator's pyright/mypy won't type-check it, and on a properly configured prod environment site-packages is read-only.
- (d) **Codegen succeeds, but the import path in generated test files** is `from <some_path> import <Tool>Params` — if that path is filesystem-derived rather than module-derived, the operator's `register()`-injected tests can't import their typed params.

The seed (SEED-015 sub-item, surfaced 2026-05-13) calls this out as a known design question. The fix is non-trivial because D-09 of Phase 17 enforces "stringly-typed `tool("name")` must resolve to a real importable module" — wherever codegen writes, `register()` must teach the import machinery to find it.

**Why it happens:**
Phase 17/21.1 made `sdet.generated_root` operator-controlled to fix the CLI-mode "no SUT-specific code in src/" violation. But the fix assumed operator-controlled = config.yaml. Library mode breaks that assumption: there is no config.yaml.

**How to avoid:**
1. **Default `generated_root` to `<cwd>/tests/_generated/`** when called via `register()` without an explicit kwarg, AND only when `<cwd>/tests/` exists (otherwise raise with a friendly message asking the operator to specify).
2. **Resolve `generated_root` to an absolute path at `register()` time, not at codegen time.** Capture `Path.cwd()` at registration, not at first use; this freezes the path against later `os.chdir` calls.
3. **Forbid writing under `site-packages/`.** At codegen entry: if the resolved path is under any directory in `sys.path` that contains the installed `mcp_test_framework` package, abort with operator-tone error: "refusing to write generated code into the package install location; set `generated_root` to a path inside your repo."
4. **Add a stale-codegen-on-upgrade test.** When the operator upgrades the framework, the generated `<Tool>Params` classes need re-regenerating. The framework should stamp generated files with `# generated against mcp_test_framework==X.Y.Z` and warn at session start if it doesn't match the installed version.
5. **Generated path must be operator-importable**. Either (a) `register()` invokes `importlib.util.spec_from_file_location` to load the generated module at runtime (works already in `mcp_session` per Phase 21.1 RELOC-02), or (b) emit an `__init__.py` and instruct the operator to add `tests/` to their `rootdir` / `pythonpath` ini setting.

**Warning signs:**
- Operator runs `pip install --upgrade mcp-test-framework` and their next pytest session fails with `ModuleNotFoundError`.
- Operator's pyright/mypy reports "could not resolve import" for generated classes.
- Test for: integration test that (1) installs the wheel into a tempdir venv, (2) runs codegen, (3) `pip install --upgrade --force-reinstall` the wheel, (4) re-runs codegen, (5) asserts generated tree is still in operator's repo.

**Phase to address:** Phase 4 (codegen output path in library mode). Must land in the same milestone as `register()` — codegen and register are coupled.

---

### Pitfall 5: Fixture-name collisions with the operator's existing fixtures — HIGH

**What goes wrong:**
The framework currently exports fixtures named `config`, `mcp_client`, `judge`, `target_tool`, `tool_config`, `_isolated_home`, `_preflight`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`. Of those, **`config` is a guaranteed collision** — virtually every non-trivial pytest project has a fixture named `config` for their own settings, ENV, app config, etc. `tool_config` is also likely to collide (any project that has a "tool" abstraction). `judge` is a less likely but still plausible collision (legal-tech projects, automated grading, etc.).

When fixtures collide between plugin and conftest, pytest silently picks the closest scope (operator's conftest wins, per the docs we verified). The framework's tests-that-need-our-`config`-fixture silently get the operator's `config` fixture, type-check fails or worse silently-succeeds-with-wrong-data.

GitHub issue pytest-dev/pytest#3966 documents this as a known pytest defect: "pytest silently chooses the wrong fixture when two plugins declare a fixture with the same name."

**Why it happens:**
The framework's current fixture names predate library-mode delivery. In CLI mode there's only ONE conftest (ours); no collision possible. In library mode there are TWO+ conftests (operator's + auto-loaded plugin), and the operator's wins by default.

**How to avoid:**
1. **Namespace all public fixtures with an `mcp_` prefix.** `config` → `mcp_config`, `judge` → `mcp_judge`, `target_tool` → `mcp_target_tool`, `tool_config` → `mcp_tool_config`. Private fixtures keep their `_` prefix and are not re-aliased (operator should not depend on them).
2. **`mcp_session` already follows this convention** (Phase 17/18 — the SDET fixture is already namespaced). Apply consistently to the contract surface in v1.4.
3. **Keep one un-prefixed alias for backwards compat in CLI mode**, deprecated with a warning when imported.
4. **Add a banned-fixture-name regression test**: integration test installs a sample-operator repo with a `config` fixture in its `conftest.py`, runs the framework's contract pass, asserts the framework's fixture (not the operator's) was used.

**Warning signs:**
- Operator reports "the framework's tests fail with a strange type error from my own code."
- The framework's tests pass in our repo but fail in the operator's because the operator's `config` fixture returns a different object.
- pytest's `--fixtures` output lists the same fixture name in two places.

**Phase to address:** Phase 2 (plugin entry point + fixture surface design). This is the most-likely-to-bite pitfall in the entire milestone; the fix is also the cheapest if done before any operator-facing docs ship.

---

### Pitfall 6: `register()` called at wrong scope or wrong time — HIGH

**What goes wrong:**
`register()` is documented in SEED-015 as a function call at module scope in `tests/conftest.py`. But operators will:

- (a) **Call it inside a test function** — `def test_my_thing(): register(...); ...`. By then pytest collection is over; injected parametrize is a no-op or raises.
- (b) **Call it inside a fixture body** — same problem; even later in the lifecycle.
- (c) **Call it from a non-conftest module** like `tests/test_mcp.py` directly. Pytest's collection rules mean the test module is imported AFTER `pytest_collection_modifyitems`, so any parametrize injection is too late.
- (d) **Call it multiple times in different conftests** (nested conftests in a monorepo). What happens? Both registrations get appended to `_REGISTRATIONS`? Or the second silently overrides the first?
- (e) **Call it from a thread or async context** — `register()` mutates module-level state; concurrent calls race.

This is the canonical "wrong scope for plugin registration" mistake — pytest-bdd, hypothesis, pytest-django all have docs sections dedicated to it.

**Why it happens:**
The seed shows the happy-path example. Operators new to pytest plugins don't intuit the collection-phase model. The framework imports cleanly from anywhere — `register()` doesn't fail loud when called late, it just silently fails to inject.

**How to avoid:**
1. **`register()` must validate it's called during pytest's collection phase.** Use `pytest.hookimpl` introspection: at call time, check whether `pytest_collection_modifyitems` has already fired; if so, raise with a clear error pointing to `tests/conftest.py`.
2. **`register()` must validate caller is in a `conftest.py`.** Inspect `sys._getframe().f_globals["__file__"]`; if it doesn't end in `conftest.py`, raise with an actionable message ("call register() from your tests/conftest.py").
3. **Multiple `register()` calls — define the semantics.** Two reasonable defaults: (a) raise on the second call (force single registration), (b) merge configs deterministically and document the rules. Option (a) is safer for a Stable API; option (b) supports monorepos with nested test trees.
4. **Document the activation flow as a hard contract** in `docs/LIBRARY-MODE.md`; mirror it in the docstring of `register()`.

**Warning signs:**
- Operator reports "register() didn't seem to do anything; my contract tests aren't running."
- Operator reports "register() was called twice and now I have duplicate tests."
- Test for: try every wrong location (inside test, inside fixture, after collection, in non-conftest module); assert each raises a clear error.

**Phase to address:** Phase 1 (`register()` API design). Validating the call site is part of the API contract.

---

### Pitfall 7: `register(**kwargs)` becomes an unstable Stable API — HIGH

**What goes wrong:**
SEED-015 declares `register()` Stable v1.3+ with "Kwargs match `config.yaml` keys 1:1." Today's config has `ollama`, `mcp_server`, `homelab`, `sdet`, `judge_timeout_seconds`, `version`, `tools` — eight top-level keys. Following the seed literally:

```python
register(
    server_command=["uvx", "my-mcp"],
    tools=["foo", "bar"],
    judge="ollama://127.0.0.1:11434/qwen3:0.6b",
)
```

These kwargs are NOT 1:1 with the config.yaml. `server_command` flattens `mcp_server.command + args`; `judge` flattens `ollama.base_url + ollama.model`; `tools=[...]` is a list, but config's `tools` is a dict-of-ToolConfig. Once shipped as Stable, any disagreement between the kwarg surface and config.yaml becomes a backward-compat burden.

Worse: if `register()` accepts `**kwargs` it leaks every Pydantic field rename as an API break. And if it returns a Pydantic Config object directly, that object's structure becomes part of the API.

**Why it happens:**
The instinct on a new API is to mirror the existing config schema. The result is two schemas that drift apart.

**How to avoid:**
1. **Define `register()` kwargs as explicit, typed, named arguments — no `**kwargs`.** Every kwarg is a deliberate semver commitment.
2. **Internally, build a `Config` from those kwargs.** The Pydantic model is an implementation detail; `register()`'s signature is the public API.
3. **Add a `RegisterParams` dataclass / TypedDict** as the documented kwarg surface; expose it in `__all__`.
4. **Lock the v1.4 kwarg list and freeze it.** Future config additions either get a new kwarg with a default (backward-compat-safe) OR get an explicit `register_v2()` factory.
5. **`register(config_file: Path)` as the escape hatch.** For operators with complex config, accept a `config_file=` kwarg pointing at a YAML; this lets the YAML schema evolve without breaking `register()`'s signature.
6. **Mark `register()` `@stable` only after one milestone of soak.** Ship in v1.4 as "Stable v1.5+" — that's one milestone of real operator usage before locking semver.

**Warning signs:**
- A v1.5 PR proposes "rename kwarg `server_command` → `command`" and breaks every operator.
- `register()` signature has grown to >10 kwargs.
- Operators on Stack Overflow ask "what's the difference between `register(judge_url=...)` and `register(ollama=...)`?"
- Test for: pin the signature in a docstring-included `signature(register)` snapshot test that fails if the kwarg list changes.

**Phase to address:** Phase 1 (`register()` API design). Critical because this kwarg list **must be locked before docs ship**.

---

### Pitfall 8: Domain UI plugin hijacks the operator's terminal — HIGH

**What goes wrong:**
SEED-015 §"What stays / what moves" calls the domain UI an opt-in pytest plugin (`mcp_test_framework.report`). Today the UI is rendered by `_runner.py` from JUnit XML after a subprocess pytest run. In library mode, the UI must hook into pytest's reporting machinery (`pytest_runtest_logreport`, `pytest_sessionfinish`).

Common failure modes:
- **`mcp_test_framework.report` is auto-loaded** (auto-discovery via pytest11 entry point) and **silently replaces** the operator's TerminalReporter. Operator who installed pytest-sugar / pytest-rich / pytest-html sees broken output. (pytest-sugar already handles this conflict via DeferredXdistPlugin — they explicitly guard `if xdist_loaded and is_worker: skip`. The framework would need similar.)
- **Under pytest-xdist**: workers emit domain UI lines independently → multiplexed gibberish in the master terminal. Per pytest-xdist docs, execnet does not transfer worker stdout, and `-s` doesn't work; the domain UI's print calls from workers may be dropped entirely.
- **In CI** (Jenkins, GitHub Actions): terminal width detection breaks; the UI's color codes pollute log files; tab characters break ANSI parsing.
- **With `pytest-html`**: domain UI output is duplicated (once on stdout, once in HTML report) or missing from one location.

**Why it happens:**
A reporter plugin that replaces (rather than augments) the terminal reporter is intrusive by design. Auto-discovery via pytest11 entry point compounds the issue because the operator never opted in.

**How to avoid:**
1. **The domain UI plugin must be `-p mcp_test_framework.report` opt-in, NOT pytest11-autoloaded.** Either ship it as a separate entry point the operator references explicitly, or use the `enabled_by` mechanism (custom ini option that defaults to disabled).
2. **The default `register()` behavior must be: don't touch terminal output.** Operator's native pytest output is preserved; framework tests show up under their natural pytest IDs.
3. **xdist coexistence**: emit the domain UI from a single master-only `pytest_sessionfinish` hook reading JUnit-like in-memory data, not from per-test `pytest_runtest_logreport` on workers. (Pattern is the same as pytest-sugar's `DeferredXdistPlugin`.)
4. **Disable UI under CI environment detection** by default (`CI=true` env, no TTY). Operator can re-enable via `--mcp-domain-ui=force`.
5. **`pytest-html` coexistence**: write domain UI to a separate file/stream that pytest-html can pick up, or expose a hook the html plugin can render.

**Warning signs:**
- Operator pastes broken terminal output to an issue; characters interleaved, lines truncated.
- Operator's CI log files have unreadable ANSI codes.
- Test for: matrix CI run combining `register()` × `pytest-xdist -n 2` × `pytest-sugar` × `pytest-html`; assert no exception, both reports populated.

**Phase to address:** Phase 5 (domain UI as plugin). Critically: DO NOT ship the domain UI as autoloaded; defer plugin registration to explicit operator opt-in.

---

### Pitfall 9: Black-box rule (`ruff TID251` + `sys.modules` guard + banned-imports test) breaks in a wheel install — HIGH

**What goes wrong:**
The black-box rule has three enforcement legs (CLAUDE.md):

1. **`ruff TID251`** — `[tool.ruff.lint.flake8-tidy-imports.banned-api] "homelab_mcp" = ...` in `pyproject.toml`. **Ships in our `pyproject.toml`, NOT in the wheel.** Operators who install the wheel never run our ruff config. The lint rule provides ZERO protection in operator environments.
2. **`sys.modules` guard** in `tests/conftest.py:pytest_configure`. **`tests/` is not packaged** (and shouldn't be) — wheel includes only `src/mcp_test_framework/`. So this guard is also gone in operator environments.
3. **Banned-imports test** in our `tests/framework/`. Also gone from the wheel.

In library mode, an operator could `pip install mcp-test-framework` AND `pip install homelab-mcp` in the same venv; the framework's runtime code could in principle import from `homelab_mcp` — but more importantly, **the black-box rule's enforcement mechanism doesn't exist in the operator's environment.** We claim the framework is black-box, but our claim is enforced only in our own dev loop.

The real risk isn't homelab-mcp specifically (`pyproject.toml` line 69 bans it by name — but only in our repo); it's that any **future** SUT-specific bleed in the framework's `src/` can no longer be caught by our existing mechanism, because the mechanism is project-config-only.

**Why it happens:**
The current black-box mechanism was designed when "the framework" and "the test rig" were the same repo. Library mode separates them; the lint and the runtime guard no longer cover all framework execution sites.

**How to avoid:**
1. **Move the `sys.modules` guard from `tests/conftest.py` into the library's runtime** (`src/mcp_test_framework/_black_box_guard.py` called from `register()`). The guard runs in every operator's pytest session because it's in `src/`, which ships in the wheel.
2. **Keep the lint rule** as a dev-time gate; it still catches our own regressions before release. Add a CI gate that runs `ruff check` against our own `src/` on every PR.
3. **Add a build-time gate**: before publishing the wheel, run a static-analysis pass over the built wheel's contents asserting no `homelab_mcp` references (or any specific SUT name banned by SEED-022). Use `ast.walk` on every `.py` file in the wheel.
4. **Document the SEED-022 contract in the wheel**, not just our planning docs. Operators reading our installed package's docstring / `__init__.py` should see "this framework contains zero SUT-specific code; if you find any, file a bug."
5. **Banned-imports test → expand to a published-wheel-introspection test** that downloads our own published wheel, unpacks it, runs `ast.parse` on every file, asserts the ban.

**Warning signs:**
- A future plan proposes adding a `homelab_mcp_helper.py` to `src/`; the lint rule catches it, but a similar slip on a different SUT name (say `proxmoxer`) goes unnoticed.
- An operator reports "the framework imports something specific to my SUT when I install it."
- Test for: build wheel locally, install into a fresh venv, AST-walk the installed `site-packages/mcp_test_framework/`, assert no string match for any name in a banned list.

**Phase to address:** Phase 2–3 (plugin entry point + contract test extraction). The `sys.modules` guard must move BEFORE Phase 3 lands — that's when SUT-specific bleed risk goes up.

---

## Moderate Pitfalls

### Pitfall 10: Missing `py.typed` marker breaks operator's pyright/mypy — MEDIUM

**What goes wrong:**
Verified: `src/mcp_test_framework/py.typed` does NOT exist in the current repo (Glob returned no files). Per PEP 561, type checkers (mypy, pyright) silently ignore types from any package that doesn't ship a `py.typed` marker. Operators using pyright/mypy who import `mcp_test_framework.contracts.register` see `Unknown` types or "module is installed, but missing library stubs or py.typed marker" errors. The framework's careful Pydantic typing is invisible.

The whole v1.3 SDET surface investment in typed `<Tool>Params` / `<Tool>Response` is wasted if the operator's type checker can't see the public surface that imports them.

**Why it happens:**
PEP 561 is a quiet requirement; nothing in the CLI-mode dev loop catches it because we run pytest, not pyright, against the installed wheel.

**How to avoid:**
1. **Ship `src/mcp_test_framework/py.typed`** (empty file) AND **include it in `[tool.hatch.build.targets.wheel]`** so it's in the wheel.
2. **Include `py.typed` in every subpackage** that operators import from (`src/mcp_test_framework/contracts/py.typed`, `src/mcp_test_framework/test_code/py.typed`).
3. **Add a wheel-introspection test** asserting `py.typed` is in the built wheel.
4. **Run pyright/mypy against a fixture operator repo as a CI gate** before publish — catches drift.

**Warning signs:**
- Operator opens issue: "pyright doesn't know what `register()` returns."
- Operator's IDE shows no autocomplete for framework imports.

**Phase to address:** Phase 6 (packaging/distribution). Cheap fix; high downstream value.

---

### Pitfall 11: SEED-023 rename leaves stale `sdet` imports in operator's generated code — MEDIUM

**What goes wrong:**
SEED-023 renames the `sdet` surface to `test_code`. Affected:
- `src/mcp_test_framework/sdet/` → `src/mcp_test_framework/test_code/`
- `cfg.sdet.generated_root` → `cfg.test_code.generated_root` config schema break
- Generated file imports: `from mcp_test_framework.sdet import ToolResponse` → `from mcp_test_framework.test_code import ToolResponse`
- CLI command `gen-sdet-classes` → `gen-test-classes`
- `--sdet` flag → `--test-code`
- `tests/sdet/` discovery scope

The pitfall: v1.3 operators (if any exist by v1.4 ship; even the framework's own dogfood counts) have **generated files on disk** with `from mcp_test_framework.sdet import ToolResponse`. Pure rename = ImportError for all of them. They MUST re-run `gen-test-classes` to refresh imports, but they don't know that until the test breaks.

Config schema break (`cfg.sdet.*` → `cfg.test_code.*`) compounds the issue — operator with a v1.3 config.yaml gets a Pydantic missing-field error that doesn't point them at the rename.

**Why it happens:**
SEED-023 captures the rename scope but acknowledges it as "Medium-Large" and notes the rename could leave artifacts behind. Doing a clean rename in `src/` without operator-side migration tooling means operators with v1.3 generated code are broken.

**How to avoid:**
1. **Ship a `mcp_test_framework.sdet` compat shim for one milestone** that re-exports from `mcp_test_framework.test_code` with a `DeprecationWarning`. Drop in v1.5.
2. **Config schema migration**: support BOTH `sdet:` and `test_code:` keys in v1.4 with `sdet:` emitting a deprecation warning; drop `sdet:` in v1.5. (Pattern: v1.2 already did this with the `version: 1 → 2` migration.)
3. **`gen-test-classes` first-run check**: if `<generated_root>/<server_slug>/` contains files with `from mcp_test_framework.sdet` imports, regenerate them and emit a one-line "regenerated against new test_code namespace" notice.
4. **Document the rename in CHANGELOG and on the `register()` docstring** so operators upgrading from v1.3 see it immediately.
5. **Sequence the rename BEFORE the public-API freeze.** SEED-023 already says this; reinforce in roadmap.

**Warning signs:**
- v1.3 operator (or the framework's own dogfood that wasn't regenerated) hits `ModuleNotFoundError: mcp_test_framework.sdet`.
- v1.3 config.yaml with `sdet:` key fails to load against v1.4.

**Phase to address:** Phase 7 (SEED-023 rename). Must happen BEFORE Phase 8 (v1.4 public-API freeze) so the rename is in the locked surface, not after.

---

### Pitfall 12: CLI/library mode coexistence drift — features added to one mode silently absent in the other — MEDIUM

**What goes wrong:**
After v1.4 ships both modes, future plans may add a feature to one mode and forget the other. Example: a v1.5 plan adds `--debug` to the CLI but doesn't add a `debug=True` kwarg to `register()`. Documentation drifts. Operators on one mode hit features that the other mode lacks; switching modes mid-project means rewriting tests.

The current architecture has CLI as the only mode; every feature lands in `cli.py` + `_runner.py`. Library mode introduces a parallel surface (`register()` + plugin hooks); without enforcement, parallel features land in only one.

**Why it happens:**
Two implementations of the same feature; no test asserts parity. Code-review eyeballs miss the second mode.

**How to avoid:**
1. **Parity test matrix**: every feature flag, env var, or behavior accessible via the CLI MUST have an equivalent path via `register()` and vice versa. Encode this in a CI test that enumerates CLI flags from Typer's introspection and `register()` kwargs from `inspect.signature`, asserts overlap.
2. **Single source of truth for the option list.** Define a `RegisterParams` dataclass; CLI flags are auto-generated from it via Typer; `register()` accepts the same dataclass.
3. **Documentation contract**: every README example that shows the CLI must show the library-mode equivalent in a tab/side-by-side block. Lint the README for unbalanced examples.
4. **Demote CLI features explicitly in v1.4** — anything CLI-only must be flagged "CLI-mode-only" in `--help` text, otherwise default-add to `register()`.

**Warning signs:**
- A v1.5 phase mentions adding a flag but `register()` isn't in the plan.
- README has 5 CLI examples and 1 library-mode example.

**Phase to address:** Phase 8 (parity gate). Add the parity test before locking v1.4 public API.

---

### Pitfall 13: Wheel contains `tests/` or planning docs — MEDIUM

**What goes wrong:**
`[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` (verified in `pyproject.toml` line 100). The current config restricts the wheel to `src/`, which correctly excludes `tests/` and `.planning/`. **Verify-only pitfall** — but easy to break in v1.4.

Common ways v1.4 breaks this:
- Adding `tests/contract/test_mcp_tool_contract.py` as importable fixtures via re-export → tempting to ship under `src/mcp_test_framework/tests/`.
- Adding `[tool.hatch.build.targets.wheel.sources]` mappings during refactor.
- Adding an `include` glob that captures `*.md` files (planning artifacts).

**How to avoid:**
1. **Wheel-content snapshot test**: in CI, build the wheel, unpack it, assert the file list matches a frozen manifest. Any new file in the wheel forces a deliberate update.
2. **Documented in `pyproject.toml`** what should NOT ship: planning artifacts, internal tests, dogfood configs, `_runner.py` test helpers.
3. **Verify `py.typed` IS shipped** (per Pitfall 10) — same manifest test covers both directions.

**Warning signs:**
- Wheel size grows by >50% in one release.
- Operator reports import paths like `from mcp_test_framework.tests.contract import X`.

**Phase to address:** Phase 6 (packaging).

---

### Pitfall 14: Entry-point name collisions with other "mcp" packages on PyPI — MEDIUM

**What goes wrong:**
The distribution name `mvp-test-framework` (verified `pyproject.toml` line 2 — typo'd `mvp` instead of `mcp`) and the script name `mcp-test-framework` (line 21) create namespacing risk:
- Another MCP package on PyPI registers `mcp-test` or `mcp-tester` script names → install conflict.
- pytest11 entry-point name `mcp_test_framework` (or whatever we choose) could collide with future MCP testing packages.
- Import-time hook `pytest_configure` is called for every loaded plugin; multiple `mcp_*` plugins could trip each other.

The current dist name `mvp-test-framework` is itself a footgun — operators install `pip install mcp-test-framework` expecting it to work and get "package not found." The MVP-not-MCP naming mismatch leaked into the distribution name back in v1.0; v1.4 publishing makes it operator-visible.

**Why it happens:**
PyPI is a global namespace; pytest plugins are auto-loaded by name. Both layers need deliberate uniqueness.

**How to avoid:**
1. **Rename the distribution from `mvp-test-framework` to `mcp-test-framework` before any v1.4 publish.** This is a one-time renaming; reserve the new name on PyPI. Leave a deprecation shim under the old name for one milestone.
2. **PyPI-name-availability check**: before publish, query PyPI for the chosen name + close variants; document the chosen name in `pyproject.toml`.
3. **Pytest plugin entry-point name**: use a long-enough name that's unlikely to collide (`mcp_test_framework`, not `mcp` or `mcp_test`).
4. **Reserve adjacent names**: optionally reserve `mcp_contract_test`, `pytest_mcp` on PyPI to prevent typosquatting.

**Warning signs:**
- Operator: "pip install mcp-test-framework gave me the wrong package."
- pytest emits "WARNING: plugin mcp_test_framework already registered" because of a name collision.

**Phase to address:** Phase 6 (packaging) + Phase 9 (release prep). Rename gate is the first blocker.

---

### Pitfall 15: README / docs source-of-truth drift across modes — MEDIUM

**What goes wrong:**
v1.2 already had operator-vs-framework persona drift in the README (memory entry `project_doc_scrub_planning_artifacts`). v1.4 doubles the surface: now there are CLI-mode examples AND library-mode examples in the same docs. Operators copy the wrong one for their context; getting "I tried to call `mcp-test-framework run` from `tests/conftest.py`" reports.

Sub-failure modes:
- `docs/SDET-AUTHORING.md` (Phase 21 artifact) has CLI-mode examples that no longer apply post-rename.
- README's "Sample green run" (SEED-015 §"trigger_when" calls this out as a canary) is in CLI form; library mode needs a parallel snippet.
- `CLAUDE.md` describes CLI commands as authoritative; library-mode operators reading it get confused.

**Why it happens:**
Doc surface grows faster than refactoring discipline. Two modes = two snippet trees; no enforcement they stay in sync.

**How to avoid:**
1. **One mode is canonical in the README** (the seed says library mode). CLI mode demotes to an "Appendix: CLI usage" section.
2. **Every code block in the README has a `<!-- mode: library -->` or `<!-- mode: cli -->` HTML comment.** Lint the README to ensure both modes have at least one example for every documented feature.
3. **`docs/LIBRARY-MODE.md`** is the primary library-mode reference, mirrored in CLAUDE.md.
4. **Apply `project_doc_scrub_planning_artifacts` discipline**: planning-ID regex sweep before any doc release.
5. **Re-capture sample outputs after the rename** (SEED-023 — `docs/TEST-CODE-AUTHORING.md`).

**Warning signs:**
- Operator: "the README example doesn't match the API I'm calling."
- README contains both `mcp-test-framework run` AND `register(...)` examples in the same flow without indicating which mode.

**Phase to address:** Phase 9 (docs).

---

## Minor Pitfalls

### Pitfall 16: Operator's `pytest -k`, `-m`, `--collect-only` quirks under injected parametrize — LOW

**What goes wrong:**
`register()` will inject parametrized tests at collection time. Operator runs `pytest -k 'my_test'` expecting to filter their own tests; framework-injected tests still get collected (just filtered). Collection time is non-trivial when the injection triggers an MCP handshake. Same for `--collect-only` — the operator wanted a quick collection preview, gets a 30s subprocess spawn.

**How to avoid:**
Cache the discovered tool list across collections (current Phase 07 `_DISCOVERED_TOOL_NAMES` cache pattern); skip MCP subprocess spawn entirely under `--collect-only` and emit placeholder parametrize ids.

**Phase to address:** Phase 3.

---

### Pitfall 17: `register()` runs MCP discovery synchronously at conftest-import time — LOW

**What goes wrong:**
The current `_discover_tools` is async and called via `asyncio.run` (verified `tests/conftest.py:_resolve_tool_names`). In library mode, calling `register()` at conftest-import time means a synchronous MCP subprocess spawn during pytest's bootstrap, which blocks `pytest --version` and IDE pytest collection.

**How to avoid:**
Defer the subprocess spawn to `pytest_collection_modifyitems` (already the case via `pytest_generate_tests`); ensure no MCP I/O fires during `register()`'s own call frame.

**Phase to address:** Phase 1 (register) + Phase 3 (contract extraction).

---

### Pitfall 18: `_isolation.py` is correctly subprocess-only — VERIFIED NOT A PITFALL

**What was suspected:** the prompt flagged `_isolation.py`'s HOME/USERPROFILE redirect as potentially HIGH-severity in library mode.

**Verification (read `_isolation.py` + `fixtures.py` + `mcp_client.py`):**
`_build_isolated_env` returns a dict that is passed ONLY to `mcp.client.stdio.StdioServerParameters(env=...)`. It does NOT call `os.environ[...] = ...` on the test process. `tempfile.TemporaryDirectory(prefix="mcp-test-fw-")` allocates a tempdir; `HOME` / `USERPROFILE` in the returned dict point at it, but **only the spawned MCP subprocess sees the overrides**.

The operator's pytest process keeps its real `HOME`. No pollution. **This is not a library-mode pitfall.**

**The actual related risk** (worth a one-line callout, not a section): if a future refactor accidentally migrates the HOME redirect to `os.environ.update(...)` at fixture setup, it WOULD hijack the operator's process env. **Add a regression test**: in `tests/framework/`, assert that after `mcp_client` fixture setup, `os.environ["HOME"]` equals the operator's real HOME (use `monkeypatch.setenv` to set a sentinel before fixture import; assert it's unchanged after).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Re-use `Config` Pydantic model as `register()` return type | Less code; one schema | Pydantic field renames become API breaks; every internal config change is a public-API change | Never. Use a separate `RegisterParams` dataclass even if it duplicates field names. |
| Auto-load domain UI plugin via pytest11 | Operator gets nice output by default | Operator can't disable; hijacks pytest-sugar/-rich/-html; broken under xdist | Never for a Stable-API plugin. |
| Skip `py.typed` because "it's a test framework, who'd type-check it" | One less file to ship | Operator's pyright shows `Unknown` for every framework import; type investment from v1.3 is invisible | Never. Cost is zero. |
| Keep `tests/contract/` as the canonical contract test location, no extraction to `src/` | No Phase 3 refactor | Operators in library mode can't run contract tests; ships breaks the entire milestone | Never (this IS Phase 3). |
| Keep `MCPTF_CONFIG_FILE` as a library-mode config source "for convenience" | CI scripts can flip behavior via env | Repeats the v1.2 silent-fail pitfall in a new mode | Only if library mode treats env-var-set + `register()`-kwargs-set as a hard error. |
| Mirror config.yaml schema 1:1 in `register()` kwargs | Apparent consistency | Every config refactor breaks `register()`; pidgeonholes flatten kwargs (e.g. `judge` flattening `ollama.base_url + ollama.model`) into ambiguous strings | Only if `register(config_file=...)` is the documented escape hatch for power users. |
| Skip the wheel-introspection CI test | Faster CI | First v1.4.1 patch release accidentally ships `tests/` or breaks the wheel; operator finds out via traceback | Never; CI cost is <30s. |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Operator's `pytest-asyncio` config | Assume our `loop_scope="session"` works against operator's `asyncio_default_fixture_loop_scope = "function"` | Detect at `pytest_configure`; fail-fast with actionable error |
| Operator's `pytest-xdist` | Domain UI prints from workers, stdout drops them | Render UI only at `pytest_sessionfinish` from the master, gated on `is_xdist_master` |
| Operator's `pytest-sugar` / `pytest-rich` | Auto-register a TerminalReporter that conflicts with operator's chosen reporter | Don't replace TerminalReporter; emit at `pytest_sessionfinish` only |
| Operator's `pytest-django` | `pytest-django`'s `db` fixture is autouse-via-marker; our `_preflight` autouse session-scope clashes | Detect django plugin via `config.pluginmanager.has_plugin('django')`; document interaction; consider not-autouse for our preflight |
| Operator's `pytest-mock` | Operator's `mocker` fixture is per-test; framework's session fixtures must not be auto-mocked | No action needed if fixtures are sufficiently namespaced (Pitfall 5); document |
| Operator's `pytest-html` | Domain UI written to stdout duplicates in HTML report | Domain UI is opt-in only; don't fire by default |
| Operator's `pyproject.toml` `[tool.pytest.ini_options]` | Operator overrides `testpaths`, `addopts`, `asyncio_mode` | Read but don't mutate operator's config; document required ini settings |
| Operator's CI `MCPTF_CONFIG_FILE` env | Leaks across sibling CI jobs | Library mode ignores it; document loud |
| `pip install --upgrade` | Codegen output wiped if it lives in `site-packages` | Forbid writing under `site-packages` at codegen entry (Pitfall 4) |
| Operator's `ruff` config | Operator's ruff doesn't ban `homelab_mcp`; framework's own lint rule doesn't ship | Runtime `sys.modules` guard in `src/` (not `tests/`); operator's lint config is their choice (Pitfall 9) |

---

## "Looks Done But Isn't" Checklist

- [ ] **`register()` API**: lots of operator-facing surface, but pinned signature snapshot test exists?
- [ ] **`register()` API**: every kwarg documented in docstring AND in `docs/LIBRARY-MODE.md` AND in the README?
- [ ] **Pytest plugin entry point**: declared in pyproject AND verified via wheel-introspection test (built wheel actually exposes it)?
- [ ] **Fixture namespace**: every public fixture has the `mcp_` prefix; `tests/framework/` regression test asserts no un-prefixed names in `__all__`?
- [ ] **`py.typed` marker**: file exists, hatchling includes it in the wheel, downstream pyright test passes?
- [ ] **CLI/library parity**: every CLI flag has a `register()` kwarg AND vice versa; parity test enforces?
- [ ] **Domain UI**: opt-in, not autoloaded; tested under pytest-xdist + pytest-sugar + CI (no TTY)?
- [ ] **Codegen output path**: defaults sensibly when called via `register()`; refuses to write under `site-packages`; stamped with framework version?
- [ ] **Preflight gate**: doesn't fire when no framework tests are collected; doesn't fire in pure-framework-self-test sessions; explicit opt-in?
- [ ] **`MCPTF_CONFIG_FILE`**: ignored in library mode OR hard-errors when combined with `register()` kwargs?
- [ ] **SEED-022 enforcement in the wheel**: black-box guard runs from `src/`, not `tests/`; AST-walk-the-wheel test catches SUT-specific name leaks?
- [ ] **SEED-023 rename**: compat shim ships for one milestone with `DeprecationWarning`; config schema accepts both `sdet:` and `test_code:` with warning on the old form?
- [ ] **Distribution rename**: `mvp-test-framework` → `mcp-test-framework` on PyPI; deprecation shim at old name?
- [ ] **README**: library-mode example FIRST; CLI demoted to appendix; planning-ID regex sweep clean?
- [ ] **Carry-forward UATs**: README §SDET-scenarios PASS sample re-captured under new namespace?

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Preflight fires in operator's unrelated test session | LOW | Hot-patch release that gates preflight on `_REGISTRATIONS` non-empty; one-line fix |
| Fixture name collision | MEDIUM | Rename collided fixture with `mcp_` prefix; document migration in CHANGELOG; ship compat alias for one milestone |
| `register()` kwarg breakage post-Stable | HIGH | Add deprecation shim accepting old kwarg with warning for one full milestone; ship `register_v2()` if more than 2 kwargs broken in one release |
| Codegen output landed in `site-packages` | HIGH | Operator manual `pip uninstall` + reinstall + rerun codegen with correct path; document in CHANGELOG; future release refuses to write to `site-packages` |
| Wheel missing `py.typed` | LOW | Patch release; add wheel-content snapshot test |
| Domain UI hijacks operator's terminal | MEDIUM | Patch release demoting from autoload to opt-in `-p` flag; document in CHANGELOG |
| `MCPTF_CONFIG_FILE` leak | MEDIUM | Hot-patch making library mode ignore the env var; document loud |
| SEED-023 rename broke v1.3 operators | HIGH | Backport compat shim; add migration script `mcp-test-framework migrate-v1.3-to-v1.4` |
| Distribution rename `mvp` → `mcp` confused operators | MEDIUM | Keep old name as deprecation shim re-exporting from new name for one full milestone |

---

## Pitfall-to-Phase Mapping

Suggested phase numbers — orchestrator will finalize in roadmap.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. `_preflight` autouse fires unwanted | Phase 1 (`register()` design) | Sample-operator-repo test: pytest with no contract tests → exit 0 |
| 2. `MCPTF_CONFIG_FILE` leak in library mode | Phase 1 (config-source design) | Test: set env var + call `register()`; assert hard-error or env-var-ignored per chosen policy |
| 3. pytest-asyncio loop-scope conflict | Phase 2 (plugin entry point) | `pytest_configure` self-check + sample-operator-repo CI matrix |
| 4. Codegen writes to `site-packages` / wrong cwd | Phase 4 (codegen output path) | Wheel-install + codegen + `pip --upgrade` integration test |
| 5. Fixture name collision | Phase 2 (plugin entry point + fixture surface) | Sample operator with own `config` fixture; assert framework uses its own |
| 6. `register()` wrong call site | Phase 1 (`register()` API) | Every wrong-location test raises actionable error |
| 7. `register()` kwarg surface unstable | Phase 1 (`register()` API freeze) | Signature snapshot test pinned |
| 8. Domain UI hijacks terminal | Phase 5 (domain UI plugin) | CI matrix: register × xdist × sugar × html |
| 9. Black-box rule breaks in wheel | Phase 2–3 (move sys.modules guard to src/) | Wheel-introspection AST-walk test |
| 10. Missing `py.typed` | Phase 6 (packaging) | Wheel-content snapshot test + downstream pyright run |
| 11. SEED-023 rename leaves stale imports | Phase 7 (rename) | v1.3-to-v1.4 migration test with frozen v1.3 generated fixture |
| 12. CLI/library mode drift | Phase 8 (parity gate) | CI test enumerating CLI flags + `register()` kwargs |
| 13. Wheel contains `tests/` | Phase 6 (packaging) | Wheel-content snapshot test |
| 14. Entry-point name collision / dist rename | Phase 6 (packaging) + Phase 9 (release) | PyPI name-availability pre-check |
| 15. README/docs drift | Phase 9 (docs) | README mode-comment lint + planning-ID regex |
| 16. `pytest -k` / `--collect-only` overhead | Phase 3 (contract extraction) | `pytest --collect-only` performance budget |
| 17. `register()` blocks at conftest-import | Phase 1 (`register()` API) | Time `register()` call; no I/O inside its frame |
| 18. `_isolation.py` HOME hijack (verified not a pitfall, regression test only) | Phase 3 | Regression test asserting `os.environ["HOME"]` unchanged after fixture setup |

---

## Sources

Verified against:
- `src/mcp_test_framework/fixtures.py` (read; confirmed `_preflight` autouse session-scope + path-prefix predicate)
- `src/mcp_test_framework/_isolation.py` (read; confirmed HOME redirect is subprocess-only, not test-process env mutation)
- `src/mcp_test_framework/config.py` (read; confirmed `MCPTF_CONFIG_FILE` env-var path + `Config` Pydantic model)
- `src/mcp_test_framework/sdet/__init__.py` (read; confirmed public surface `ToolCallError, ToolResponse, mcp_session, tool`)
- `tests/conftest.py` (read; confirmed sys.modules guard lives in test tree, not in src/)
- `pyproject.toml` (read; confirmed dist name `mvp-test-framework`, script name `mcp-test-framework`, no `py.typed`, ruff TID251 only in our config, wheel scope `src/mcp_test_framework`)
- `.planning/PROJECT.md` (read; confirmed Constraints, Key Decisions, SEED-022 enforcement)
- `.planning/seeds/SEED-015-library-mode-delivery.md` (read; confirmed register() API surface intent)
- `.planning/seeds/SEED-022-framework-primitives-sdet-safety-principle.md` (read; confirmed black-box enforcement contract)
- `.planning/seeds/SEED-023-rename-sdet-surface-to-test-code.md` (read; confirmed rename blast radius)

External sources (HIGH confidence; documented in linked sources):
- pytest official docs — plugin discovery, fixture precedence ([docs.pytest.org/writing_plugins](https://docs.pytest.org/en/stable/how-to/writing_plugins.html))
- pytest issue tracker — fixture name collision is silent ([pytest-dev/pytest#3966](https://github.com/pytest-dev/pytest/issues/3966))
- pytest-asyncio docs — strict mode coexistence ([pytest-asyncio Concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html))
- pytest-xdist docs — `-s` doesn't work; worker stdout dropped ([pytest-xdist known limitations](https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html))
- pytest-sugar source — `DeferredXdistPlugin` pattern for terminal reporter coexistence ([pytest-sugar GitHub](https://github.com/Teemu/pytest-sugar/blob/main/pytest_sugar.py))
- PEP 561 — `py.typed` marker semantics ([PEP 561](https://peps.python.org/pep-0561/))
- AnyIO docs — `auto` mode conflict; recommend `strict` ([AnyIO testing](https://anyio.readthedocs.io/en/stable/testing.html))

Memory entries cited:
- `project_mcptf_config_file_silent_fail` — v1.2 precedent for Pitfall 2
- `project_dotenv_silently_beats_config` — v1.2 precedent for Pitfall 2
- `project_doc_scrub_planning_artifacts` — v1.2 precedent for Pitfall 15
- `project_v1_1_skip_bug` — precedent for collection-time vs runtime filtering (Pitfall 16)
- `project_vibe_coded_persona` — informs Pitfall 6/8 (don't assume operator pytest fluency)

---
*Pitfalls research for: v1.4 Library Mode Delivery (pytest plugin packaging)*
*Researched: 2026-05-15*
