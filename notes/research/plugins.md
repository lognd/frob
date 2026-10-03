# Plugin mechanisms for frob and grimble: evidence for the tier choice

Status: research note, 2026-10-02. ASCII only. Not a design doc; it feeds a
future docs/design/plugins.md. Inputs: docs/design/packs.md (section 1.3: packs
are data, never code), rules.md (two rule tiers, one pass, per-file cache),
universal-model.md (U, the 47-query interface), grmb-spec.md.

Method and honesty about sources. The research brief named WebSearch and
WebFetch; neither tool was available in this session. Sources were fetched with
curl (raw GitHub files, the GitHub REST API, project docs sites) and two local
measurements were run in the scratchpad (pluggy 1.6.0 and pytest 9.0.3 on
CPython 3.10.12, WSL2). Every number is tagged:

- [measured] run locally in this session.
- [fetched] read in a primary source this session; URL given.
- [verify] from the author's background knowledge or inference; NOT checked in
  this session. Treat as a hypothesis to confirm with a benchmark before it
  carries a design decision.

Coverage statement (Phase-2 style). Sections requested: 1 wasm hosts, 2 native
dylibs, 3 out-of-process, 4 declarative rule systems, 5 loadable language
support, 6 distribution and trust, 7 Rust built-in/plugin path, plus the owner
addition (pytest/pluggy). Fetched and verified in depth: wasmtime docs and PRs,
ruff, oxlint, Nushell, tree-sitter wasm feature, dylint README, pluggy and
pytest (measured). Covered from background knowledge only and flagged [verify]:
dprint, Zed, Typst, Extism, Lapce, Spin, wasmer, wasm3, abi_stable, stabby,
Bevy, Semgrep, ast-grep, CodeQL, Souffle, DDlog, stack-graphs, Rego, ESLint,
Biome, sigstore internals. Nothing is "not covered", but about half the
per-system numbers are [verify]. The single biggest gap: no published number
exists (that I found) for host-interpreted query plan versus handwritten Rust on
lint predicates; section 7 gives a measurement plan instead of a number.

---------------------------------------------------------------------------
## 0. Executive summary (read this first)

Recommended tiers (details and reasons in section 12):

- Tier 0, compiled in: the kernel (U operators, 47 queries, detector KINDS, rule
  framework, pack loader) and the standard library of rules written in Rust with
  the `#[derive(Rule)]` of rules.md. Registered through `inventory`, exactly
  like third-party plugins will be (the pytest "everything is a plugin" lesson).
- Tier 1, data packs (TOML, already designed in packs.md): atoms, detectors,
  vocabularies, claim templates, matrix-build excuse templates. No code, no
  sandbox needed, digest-pinned in a lockfile.
- Tier 2, declarative rule packs executed by the host: universal rules over U
  (a small predicate/query language compiled to a plan) and language rules as
  tree-sitter queries or gob-pattern patterns. Built-in declarative rules
  compile to the SAME plan bytes (include_bytes) that disk packs load.
  This is where nearly all third-party rules should live.
- Tier 3, arbitrary-code rules: WebAssembly components (wasmtime, WIT-typed
  hook specs), AOT-compiled and cached by digest, epoch-bounded, deny-by-default
  capabilities, batch-per-file interface (one boundary crossing per file or per
  rule, never per node). Opt-in, lockfile-pinned, off by default in CI unless
  listed.
- Tier 4, language adapters: declarative first (tree-sitter grammar as .wasm or
  linked-in, plus node-types.json, tags.scm/locals.scm-style mapping files, and
  a TSG-like binding description), wasm only for the hard residue. Native
  grammars for the ~10 languages we ship; wasm grammars for the long tail.
- Rejected: Rust dylib/cdylib plugins (no stable ABI, unsandboxed, UB, version
  lockstep), embedded scripting interpreters (PyO3, Lua, JS) as the main path,
  out-of-process IPC per node/per call, and a general Datalog engine as the
  rule language for v1.

Five most decision-relevant numbers (full table in section 10):

1. Wasmtime host/guest call overhead is tens of nanoseconds, not microseconds:
   the C-API "call a nop" path was optimized to within ~15 ns of the faster
   variant [fetched: https://github.com/bytecodealliance/wasmtime/pull/3319];
   typed Rust calls are cheaper [verify]. Per-file batching makes it irrelevant;
   per-AST-node crossing would make it dominant.
2. Epoch interruption costs about 10 percent of guest execution speed; fuel
   costs more [fetched: wasmtime docs/examples-interrupting-wasm.md].
3. Cross-boundary AST transfer, not execution, is what kills plugin speed:
   Oxlint 48 ms with no JS plugin, 236 ms with one trivial JS plugin, ESLint
   4,116 ms (multi-threaded 3,710 ms) on vuejs/core [fetched:
   https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html], after Oxc built
   "raw transfer" (the Rust memory layout is the wire format) and lazy
   deserialization to get there. A 5x slowdown from one tiny plugin is the cost
   of a poor boundary even with heroic engineering.
4. pluggy hook dispatch (the pytest model) costs 0.65 us with zero
   implementations, ~0.9 us with one, ~3.3 us with ten, ~4.2 us with ten plus a
   wrapper, versus 0.06 us for a plain Python call [measured, CPython 3.10].
   The takeaway for Rust is not the number but the shape: dispatch is per hook
   call, hooks are coarse, and the cost is amortized by making each hook do real
   work.
5. Ruff (the canonical fast Python linter) still has no third-party plugins:
   FAQ says "does not yet support third-party plugins" and points to open meta
   issue #283 (opened with the explicit worry that setuptools-style auto-enable
   is a flake8 problem to avoid) [fetched:
   https://github.com/astral-sh/ruff/blob/main/docs/faq.md,
   https://github.com/astral-sh/ruff/issues/283]. The only in-tree attempt is
   an unmerged RFC PR embedding free-threaded CPython via PyO3, which states that
   per-AST-node Python calls on a GIL interpreter are "so slow as to be
   somewhat pointless" [fetched:
   https://github.com/astral-sh/ruff/pull/21415].

Still missing (no source found): interpreted plan vs handwritten Rust gap, and a
published wasm-vs-native tree-sitter parse slowdown. Section 7 and 8 propose
benchmarks to produce them in an afternoon each.

---------------------------------------------------------------------------
## 1. pytest and pluggy in depth (owner addition)

### 1.1 What it is

pytest is built on pluggy, a small (~2 kLOC) hook library extracted from pytest
and shared by tox, devpi, datasette, others. pluggy's concepts:

- Project name: a string tying markers together. `HookspecMarker("pytest")`,
  `HookimplMarker("pytest")`. A function is a hook only if marked with the
  project's marker.
- Hook specification (`@hookspec`): a function signature with a docstring and
  an empty body. It defines the NAME and the ARGUMENT NAMES a hook may request.
  Options: `firstresult=True`, `historic=True`, `warn_on_impl=...`,
  `warn_on_impl_args=...`.
- Hook implementation (`@hookimpl`): a function whose name matches a spec and
  whose parameters are a SUBSET of the spec's parameters (by name). Options:
  `tryfirst`, `trylast`, `wrapper` (new style generator), `hookwrapper` (old
  style), `optionalhook` (no error if the spec is missing), `specname`.
- PluginManager: owns the registry of plugin objects (modules or class
  instances), the spec registry, and `pm.hook`, a namespace of `HookCaller`
  objects, one per hook name.
- Calling convention: keyword arguments only (`pm.hook.pytest_foo(a=1, b=2)`).
  The caller passes everything; each implementation receives only the argument
  names it declared. This is the single most important design property: the
  ABI is "named arguments", so a spec can add arguments without breaking old
  implementations, and implementations pay only for what they ask for.
- Collecting results: by default the call returns a LIST of every
  implementation's non-None return value, in call order (LIFO registration
  order, adjusted by tryfirst/trylast). With `firstresult=True`, calling stops at
  the first non-None result and returns it (used for things like
  `pytest_collect_file`-style "who claims this?" and `pytest_runtest_protocol`).
- Ordering: later-registered plugins run first (LIFO); `tryfirst` moves an impl
  toward the front, `trylast` toward the back; wrappers always enclose the
  non-wrapper impls. Among equals, order is registration order reversed, and
  that is the number-one source of "ordering surprises".
- Wrappers: old `hookwrapper=True` generators `outcome = yield; outcome.get_result()`
  and new `wrapper=True` (pluggy 1.2+) generators `result = yield; return result`
  where exceptions propagate into the generator by normal Python semantics and a
  wrapper may replace the result. Used for setup/teardown around a hook call
  (timing, capture, tracing). pluggy also supports `PluginManager.enable_tracing`
  and `add_hookcall_monitoring` for debugging dispatch.
- Historic hooks (`historic=True`): the call is remembered; implementations
  registered LATER are invoked with the remembered calls on registration
  (`pytest_configure`, `pytest_plugin_registered`). This solves "plugin loaded
  after startup event" without ordering requirements on plugin loading.
- Validation: `pm.register(plugin)` checks each hookimpl against its spec:
  an impl arg not in the spec is a `PluginValidationError` at registration time;
  an impl for an unknown hook name (with the marker) errors at `check_pending()`
  unless `optionalhook=True`. So errors are loud, early, and name the plugin.
  Plugins can define NEW hooks by registering a hookspec namespace; pytest
  exposes this as the `pytest_addhooks(pluginmanager)` hook (the hook that adds
  hooks).

### 1.2 Everything is a plugin

pytest core features are plugins registered through exactly the same manager.
Measured: `_pytest.config.default_plugins` has 30 entries (mark, main, runner,
fixtures, helpconfig, python, terminal, debugging, unittest, capture, skipping,
legacypath, tmpdir, monkeypatch, recwarn, pastebin, assertion, junitxml,
doctest, cacheprovider, setuponly, setupplan, stepwise, unraisableexception,
threadexception, warnings, logging, reports, faulthandler, subtests)
[measured, pytest 9.0.3]. Five are "essential" (mark, main, runner, fixtures,
helpconfig) and cannot be disabled sensibly. `pytest.hookspec` defines ~52
`pytest_*` hook names [measured: count of `pytest_`-prefixed names in
`_pytest.hookspec`, an approximation]. A trivial run with `--trace-config`
reports 42 registered plugins (30 builtins plus conftest, entry points such as
anyio and any installed, plus helper objects like the config and session)
[measured: grep count of "PLUGIN registered"].

Consequence: the terminal reporter, the assertion rewriter, the cache, junit
output, capture, and tmpdir are each a module with `pytest_*` functions.
`-p no:terminal` removes the reporter; `-p no:cacheprovider` removes the
cache. Features are disabled and replaced by name, which is both the extension
story and the testing story: the same hook surface that third parties use is the
surface the core uses, so it is battle-tested and cannot rot.

### 1.3 Discovery and loading

In order of loading (approximately):

1. Built-in plugins (the default_plugins list above).
2. `PYTEST_ADDOPTS` / command-line `-p name` (early load, before option parsing,
   so a plugin can add options). `-p no:name` blocks a plugin by registration
   name, including entry-point plugins.
3. Setuptools entry points in group `pytest11` of installed distributions,
   auto-loaded unless `PYTEST_DISABLE_PLUGIN_AUTOLOAD` is set. Zero-config
   activation: `pip install pytest-xdist` turns it on.
4. `PYTEST_PLUGINS` environment variable (comma-separated module names).
5. `conftest.py` files, discovered per directory as collection descends. A
   conftest's hooks apply only to tests at or below its directory (hooks are
   registered as local plugins; `HookProxy`/`_getconftestmodules` constructs
   per-directory hook callers by filtering plugins to those whose conftest
   path is an ancestor of the node). `pytest_plugins = ["mod"]` inside a
   conftest or test module loads further plugins; at non-root conftest this is
   deprecated, because it registers globally (the scoping confusion).
6. `-c`/ini `addopts` and `pytest_plugins` in the rootdir conftest.

Assertion rewriting: plugins loaded via entry points get their modules
registered for assert rewriting before import (`pytest.register_assert_rewrite`).
This is the one place pytest really does import-system magic.

### 1.4 Fixtures as an extension point

Fixtures are not pluggy hooks; they are a second, data-flow extension mechanism
built on top. A fixture is a function decorated with `@pytest.fixture(scope=...)`
with parameters that name other fixtures (dependency injection by argument name,
the same trick as hook argument subsetting). Scopes: function, class, module,
package, session. Overriding: a fixture defined closer to the test (same module,
then conftest in a nearer directory, then plugin, then built-in) shadows one with
the same name; the override can request the fixture it overrides. Fixture
lookup is by node ID and directory ancestry, so directory scoping is the
organizing principle. `autouse`, `params`, and `yield` for teardown round it out.

Transfer note: this is the pattern for "the plugin supplies a value to a rule",
for us: a rule asks for `Q::PublicApi` and the framework supplies it, exactly
what `needs(Q::PublicApi, Q::Doc)` already is in rules.md. We have reinvented
fixtures-by-name; keep the by-name property.

### 1.5 Configuration hooks

`pytest_addoption(parser, pluginmanager)` registers command-line options and ini
keys (`parser.addini(name, help, type, default)`); `pytest_configure(config)` and
`pytest_unconfigure` bracket the session; `config.getini`, `config.getoption`
read them; `pytest_cmdline_main`, `pytest_load_initial_conftests`,
`pytest_collection_modifyitems`, `pytest_generate_tests` (parametrization) and
the `pytest_runtest_*` protocol are the main flow hooks. An unknown ini key
produces a warning (PytestConfigWarning) and `--strict-config` upgrades it to
an error, mirroring our `deny_unknown_fields` stance.

### 1.6 Performance profile

Measured here (CPython 3.10.12, pluggy 1.6.0, 200k calls, keyword args):

| scenario | us per hook call |
|---|---|
| plain Python function call | 0.06 |
| hook with 0 implementations | 0.65-0.69 |
| 1 implementation (non-firstresult) | 0.97 |
| 10 implementations | 3.28 |
| 10 implementations plus one wrapper | 4.23 |
| firstresult, first impl answers (10 registered) | 0.92 |

[measured]. About 0.3 us fixed overhead per call plus ~0.3 us per implementation.
That is ~15x a bare call but small against what a hook body does (a test run is
milliseconds). pytest keeps dispatch cheap by: (a) resolving the impl list once
at register time (HookCaller keeps pre-sorted `_hookimpls`; registration inserts
by tryfirst/trylast classification, so no sorting per call); (b) precomputing
each impl's `argnames` tuple at registration, so the call builds the argument
tuple by name lookup, no signature inspection at call time; (c) per-directory
`HookProxy` objects are cached per path, so conftest-filtered dispatch does not
re-filter every call; (d) hooks that are called per item are few and coarse.
Startup is a different story: `import pytest` costs ~55 ms cumulative [measured
with -X importtime], and a one-test run takes 0.13-0.29 s wall [measured,
three runs: 0.29, 0.15, 0.16; with logging, terminal, cache plugins disabled
0.13] versus 0.02 s for bare `python -c pass`. Most of that is imports and
collection, not dispatch.

### 1.7 Known costs and pain points (sourced from experience; [verify] for details)

- Import-time cost scales with installed plugins: every `pytest11` entry point is
  imported at startup whether or not the run uses it (e.g. a coverage or django
  plugin is imported even when running a pure unit test). Mitigation is
  `-p no:...` or `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, i.e. opt-out, which is the
  wrong default (and exactly flake8's problem that ruff #283 calls out).
- Ordering surprises: LIFO registration plus tryfirst/trylast plus wrappers; two
  plugins both claiming `tryfirst` fall back to registration order, which depends
  on entry-point iteration order (non-deterministic across environments).
- conftest scoping confusion: hooks in a conftest are directory scoped for
  per-item hooks but process-global for session-level hooks like
  `pytest_addoption` and `pytest_configure` (those run for any conftest
  reachable at startup; a non-root conftest's `pytest_addoption` may be too late).
  `pytest_plugins` in non-root conftest is deprecated for this reason.
- Version compatibility: hook specs are the compat surface. Adding args to a spec
  is non-breaking (impls take a subset). Removing or renaming is breaking and
  pytest uses `warn_on_impl` and deprecation warnings across releases. Third
  party plugins pin `pytest>=X` and break on major bumps anyway; the hook set is
  large (52 in core) and many hooks pass mutable internal objects (`Item`,
  `Session`, `Config`), which makes the real ABI the whole object model.
- Global mutable state and monkeypatching: plugins freely monkeypatch each other
  and the interpreter; capture and assertion rewriting rely on import hooks and
  `sys` replacement.
- Error attribution: a hook exception is raised with a traceback through pluggy;
  `PluginValidationError` names the plugin, but runtime failures need
  `--trace-config`/`-p pytester` to debug.

### 1.8 What transfers to a Rust tool with wasm and declarative packs

Transfers (keep these):

1. Standard library as plugins on the same mechanism. Our built-in rule families
   (DRIFT, COV, SYS, CAP, ...) register through the same `RuleMeta` registry a
   third-party pack uses; the built-in data packs (core-effects etc.) are
   ordinary packs that happen to ship embedded. No privileged back door. This is
   the strongest transfer and costs nothing at runtime.
2. Typed hook specifications as the plugin ABI. Express the plugin surface as a
   WIT world (wasm) plus a Rust trait (native) generated from one source of
   truth: `world lint-rule { import host; export check: func(ctx, unit) -> findings }`.
   A spec is versioned; args are NAMED records, so adding a field is
   non-breaking (WIT records and variants have evolution rules; use
   `option<T>` for additions) [verify exact WIT evolution rules]. Mirrors
   pluggy's "impl takes a subset of args".
3. Hook argument subsetting = `needs(...)`. Already present. Extend: a plugin
   declares which U queries and capabilities it requests; the host materializes
   only those and refuses applicability when the adapter lacks them.
4. Loud load-time validation. Check every plugin against specs at load: unknown
   hook, unknown query, wrong arity, wrong WIT world version -> a named error
   before any run. Equivalent of `PluginValidationError`. Add a `frob doctor
   plugins` that does this without running rules.
5. Directory-scoped local plugins (conftest). A `.grimble/plugins/` or
   `frob.toml [[plugin.local]]` in a subtree applies only to files below it, which
   fits the monorepo design (monorepo.md). Keep it strictly declarative-or-wasm
   (no code run at discovery) and explicitly scoped; do NOT repeat the
   session-global/dir-local split: every hook is either per-file (dir scoped) or
   per-run (root only), declared in its spec, and a non-root plugin that
   declares a per-run hook is a load error rather than a silent no-op.
6. firstresult and wrapper semantics. firstresult maps to "claim" hooks:
   "which adapter parses this file", "which pack supplies the detector for
   (atom, lang)". Make claim hooks first-class with an explicit priority number
   and a deterministic tie-break (pack name then digest), because
   registration-order tie-break is the pytest pain point. Wrapper semantics map
   to rule decorators around a check (timing, exceptions applying, quarantine,
   ratchet) done by the HOST in Rust, not exposed to wasm.
7. Historic hooks. Maps to "pack loaded later still sees events": less needed
   for batch lint; skip unless the daemon/LSP mode needs it (then a replay of
   `on_snapshot` for a newly enabled pack).
8. Entry-point discovery maps to the pack lockfile, with the opposite default.
   pytest auto-loads everything installed; we load ONLY what the lockfile
   names, by content digest. Same ergonomic goal (one place declares plugins),
   but explicit opt-in (ruff #283's first requirement, and ESLint flat config's
   explicit `plugins: {}`).
9. `-p no:name` maps to `--disable-pack name` / `[packs] disable = [...]`, and
   PYTEST_DISABLE_PLUGIN_AUTOLOAD maps to the default.
10. `pytest_addoption`/ini maps to a pack's declared config schema, validated
    like every grimble table (deny_unknown_fields; unknown key is a PACK
    error), surfaced in the generated config docs and JSON schema.
11. Fixtures by name with directory-nearest override maps to pack/vocab
    override: a repo-level vocabulary or detector shadows a pack's of the same
    id, with the override visible in `frob packs show` (never silent).
12. `--trace-config` maps to `frob packs trace`: which packs, which digests,
    which hooks registered in what order.

Does not transfer (reject):

- Dynamic Python monkeypatching, mutable shared object graphs passed to hooks,
  and "plugins patch each other". A wasm component sees only values passed
  across the boundary; the host mutates nothing on its behalf. This is a
  feature.
- Import side effects at plugin load (module-level code runs). A pack load must
  execute nothing; wasm instantiation runs only `start`/initialization in the
  sandbox, under epoch limits, and ideally is deferred until first use
  (lazy instantiate).
- Assertion rewriting style import hooks.
- Auto-activation from installation (entry points).
- Registration-order-dependent ordering. Use explicit priorities.
- Passing the entire object model as the ABI (pytest's Item/Session). Our ABI
  must be a bounded query interface (the 47 queries) plus plain values.
- Python-level performance assumptions: pluggy's ~1 us per hook call is fine
  for ~50 coarse hooks; for us the coarse unit is per-file or per-rule, and
  crossing a wasm boundary is ~tens of ns plus data transfer, so same shape,
  better constants, as long as we never make the hook per-node.

One architectural caution: pytest's hook count (52 core hooks plus hundreds
across the ecosystem) is the reason its ABI is hard to change. Keep the
number of host-visible hook specs small (target under 12: claim_file,
parse_file, derive_u, query_facts, check_rule, detect_atom, expand_template,
render_finding, plus lifecycle), and let the DATA vocabulary (queries, atoms)
grow instead of hooks.

---------------------------------------------------------------------------
## 2. WebAssembly plugin hosts in Rust tools

### 2.1 Wasmtime specifics (the likely host)

Component model and WIT. Wasmtime supports the component model (WIT, canonical
ABI, `wasmtime::component`, `bindgen!` generating typed Rust bindings from a
.wit world). Types cross the boundary by value through linear memory using the
canonical ABI (strings and lists are copied, records flattened; resources are
handles). WASI preview 2 (wasip2) is the standard capability surface (fs,
sockets, clocks, random, cli) [verify current status: wasip2 stable since Wasmtime
~v18-19, WASI 0.3 async in progress].

AOT compilation. `Engine::precompile_module` / `precompile_component` and
`Module::serialize` produce a native-code artifact (.cwasm); load with
`Module::deserialize` (unsafe: must be trusted bytes) or `deserialize_file`
(mmap, lazily paged). Docs: pre-compiling "removes compilation from the critical
path", "less memory usage... lazily mmapped", and Wasmtime can be built without
Cranelift to only run pre-compiled artifacts for a smaller attack surface
[fetched: docs/examples-pre-compiling-wasm.md]. The serialized artifact embeds
a compatibility check: wasmtime version, target triple, and the engine config
flags that affect codegen (e.g. enabled wasm features, memory config,
Cranelift flags); deserialization with a mismatching engine fails with an error
rather than UB [verify exact fields; the intent is documented in
Engine::precompile_* docs]. Cache key therefore: (wasm digest, wasmtime version,
target triple, relevant config hash). Wasmtime also has a built-in disk cache
(`Config::cache_config_load`, TOML-configured, keyed by module hash and
compiler settings) [verify].

Compile cost (the thing AOT removes). Cranelift compiles wasm at roughly tens of
MB/s of wasm per core order of magnitude [verify]; a 1-5 MB rule plugin
(typical for a Rust-compiled, wasm-opt'ed component with a regex or tree-sitter
dependency) compiles in the low hundreds of milliseconds to a few seconds
[verify]. Winch (baseline compiler) compiles much faster at slower code
[verify]. Rule: never JIT in a CI path; compile once at pack install
(`frob packs add` or `frob packs build`) and cache under `.frob/cache/wasm/`.

Instantiation. Per-instance cost depends on the allocator. The pooling
allocator pre-reserves virtual memory slots, tables and stacks (`PoolingAllocationConfig`);
with copy-on-write memory images (memfd + madvise, PR 3697) an instantiate-run-
reset cycle avoids address-space locks and is designed for microsecond-scale
instantiation [fetched design: https://github.com/bytecodealliance/wasmtime/pull/3697;
the figure "~5 microseconds per instantiate" appears in Bytecode Alliance
material [verify]]. For a lint tool this is overkill: we instantiate each
plugin once per worker thread (or once per process) and call it many times.
Instance reuse API (PR 3691, an experimental `instantiate_reusable`/`reset`) was
benchmarked as the fastest way to call into wasm when you rarely re-instantiate
[fetched: https://github.com/bytecodealliance/wasmtime/pull/3691]; whether it
merged in that form is [verify]. Use `InstancePre` (pre-resolved imports,
`Linker::instantiate_pre`) so each instantiation skips import resolution.

Call overhead per boundary crossing. Wasmtime's `TypedFunc::call` is the fast
path (no dynamic type checks); the dynamic `Func::call`/C API `wasmtime_func_call`
was optimized so that a "call a nop function" benchmark is within on the order
of 15 ns of the alternative design [fetched PR 3319]. Order of magnitude:
10-50 ns per host-to-guest call and similar for guest-to-host through a
`Linker::func_wrap` import [verify; consistent with PR 3319 but not a direct
measurement]. Component-model calls add canonical-ABI lifting and lowering:
cost scales with bytes copied and with allocation (strings and lists call the
guest's `cabi_realloc`), so a call returning a list of 100 findings costs far
more than a nop call [verify magnitude: hundreds of ns to a few us]. A
Spin/Wasmtime-ecosystem microbenchmark shows component calls are an order of
magnitude slower than core calls with scalar args [verify; no URL].

Bounded execution. Two mechanisms, both fetched from wasmtime's
docs/examples-interrupting-wasm.md:
- Fuel: deterministic (same program, same input, same trap point) but "more
  overhead on execution".
- Epoch interruption: "measured at around a 10% slowdown", cheap, but wall-time
  based and therefore non-deterministic. Mechanism: the engine's epoch counter
  is incremented by a timer thread (`Engine::increment_epoch`), the compiled
  code checks it at loop back-edges and function entries, and
  `Store::set_epoch_deadline` plus `epoch_deadline_trap` or a callback decides.
For lint: epoch for a per-file timeout (e.g. 200 ms soft, kill at 2 s); fuel
only in test/CI "deterministic mode" when reproducibility of timeouts matters.
Also `StoreLimits` (`ResourceLimiter`) caps memory, tables, and instances.

Shared memory and batching strategies. Cheap patterns, in descending order:
(1) Per-file batch: the host writes the file's facts (a flat U term arena, see
2.4) into the guest's linear memory once, the guest returns a flat findings
buffer. One or two crossings per (file, plugin). (2) Per-run batch: send all
files, return all findings (best throughput, worst latency and memory).
(3) Host-implemented queries: the guest calls imported functions
(`query_callees(node_id)`) a bounded number of times; each costs a host call
(~tens of ns plus canonical-ABI copies). (4) Zero-copy via a shared arena: host
allocates a region in guest memory with a stable layout (fixed-width ids, offsets
instead of pointers, `#[repr(C)]` structs) so the guest reads U directly; this
is the "raw transfer" idea of Oxc (section 4.10) applied to wasm, and the same
reason swc moved plugins to rkyv (2.3). Avoid: per-node callbacks across the
boundary; JSON/string serialization of trees.

Memory limits: wasm32 is 4 GiB addressable per instance, which is fine; many
instances with the pooling allocator reserve large virtual ranges (default
slots are on the order of 4 GiB virtual each; the pool is virtual memory not
RSS) [verify] which matters on WSL or constrained CI with strict
`ulimit -v`. Disk-guard memory: the .cwasm cache is of the order of 2-4x the
wasm size [verify].

### 2.2 dprint (wasm formatter plugins)

Mechanism: dprint (Rust, by David Sherret) loads formatter plugins as .wasm
(wasm-bindgen free, a small hand-rolled ABI using wasmer originally, moved to
wasmtime for AOT compile cache) [verify host choice]. Plugins are referenced by
URL plus checksum in dprint.json (`"https://plugins.dprint.dev/typescript-0.xx.wasm@<sha256>"`
in the plugin list; the `@checksum` suffix is optional but recommended)
[verify]. Plugins are downloaded and cached, compiled once and the compiled
module cached on disk; later runs load from cache. There are also "process
plugins" for languages where wasm is unavailable (a child process speaking a
stdin/stdout protocol), added because some formatters cannot target wasm.
Interface: a versioned plugin schema (schema version number in the wasm,
checked by the host) with exports for `get_plugin_info`, `format`, `set_config`;
host calls are per-FILE (file text in, formatted text out), which is exactly the
coarse batching we want. Sandboxing: wasm memory isolation; plugins get no fs or
net; the host passes text. Distribution: plugins.dprint.dev and GitHub releases;
`dprint config add` updates pins. Performance: dprint reports being faster than
Prettier by a wide margin and the wasm plugin overhead is "negligible vs format
time" [verify]. Lessons: (1) a stable, small, versioned schema number on the
plugin and the host rejecting mismatches; (2) coarse per-file calls; (3) URL
plus checksum pinning in the config file; (4) a process-plugin escape hatch
exists for what wasm cannot do (this is the tier-3 residue); (5) the compiled
cache is the key startup optimization.

### 2.3 swc (wasm plugins, AST serialization, rkyv)

Mechanism: swc plugins are Rust crates compiled to wasm32-wasi, loaded by the
swc host (wasmtime; earlier wasmer, switched around 2023 [verify]). The host
serializes the whole AST with `rkyv` (zero-copy-ish archive format) into guest
memory, the plugin deserializes (or accesses archived form), transforms, and
serializes back. Interface/ABI: the plugin ABI is tied to the swc_core version
AND the rustc/wasm toolchain: plugins must be built against the same
`swc_core` as the host or the AST layout differs and loading fails or panics.
This was the main user pain: version lockstep, "plugin compatibility table", and
frequent "failed to invoke plugin" errors after upgrades [verify; widely
reported]. Evidence of ongoing ABI churn: PR #11100 introduced a "flexible
serialization encoding for AST" and PR #11198 switched the plugin ABI to it,
explicitly marked "BREAKING CHANGE ... breaking changes on the plugin abi and
api" [fetched: https://github.com/swc-project/swc/pull/11198; closed, not
merged as a PR, outcome [verify]]. Another PR optimizes the rkyv implementation
of `Atom` (string interning type) for the same boundary [fetched title: PR
10840]. Lesson: serializing a rich, evolving AST across the boundary makes the
AST the ABI, which is the most fragile choice. Performance: swc plugin
transforms are slower than native swc passes but faster than Babel plugins; the
cost is dominated by (de)serialization of the full AST per plugin, scaling with
file size and number of plugins [verify no published number found]. Distribution:
npm packages containing .wasm; the user lists plugins in .swcrc with options as
JSON. Sandboxing: wasm plus WASI limited; no fs by default except preopened.
For us: do NOT make the whole U/AST the plugin ABI; pass a versioned, flat,
query-oriented view, and keep the AST serialization format owned by the host
with an explicit version in the plugin world name.

### 2.4 Zed extensions (wasm components, WIT)

Mechanism: Zed extensions are Rust crates compiled to wasm32-wasip2 (earlier
wasm32-wasi) using a `zed_extension_api` crate whose WIT world (versioned,
e.g. `since_v0.x.0`) defines imports (host functions: download file, run
command, worktree read) and exports (language server command, slash commands,
etc.). Host: wasmtime component model with async. Language support (grammars,
queries) is data in the extension: `languages/<lang>/{config.toml,highlights.scm,
brackets.scm,outline.scm,...}` plus a tree-sitter grammar referenced by git
repo and commit in `extension.toml`, which Zed builds to wasm and loads
[verify]. Capabilities: extension.toml declares needed capabilities (e.g.
`process:exec`, `download_file`, `npm:install`) with allowed patterns in
Zed settings `granted_extension_capabilities`; deny by default [verify]. Distribution:
a central zed-industries/extensions repo (git submodules, CI builds), versioned
by extension.toml, with a compatibility window of API versions that Zed
supports (the host keeps multiple `since_vX` worlds, supporting old extensions
for a window) [verify]. Lessons: (1) the WIT world is versioned by NAME and the
host keeps several old worlds alive, which is a workable compat policy; (2)
grammar plus queries as data plus code only where needed is the right split
(directly our tier 4); (3) capability declaration with user grant is the
right default-deny UX; (4) startup: extensions are compiled on install
(Cranelift) and cached; early Zed versions had startup stalls due to
compilation [verify]. Numbers: none found.

### 2.5 Typst plugins (wasm)

Typst (document compiler) loads wasm "plugins" via the `plugin("file.wasm")`
function: a deliberately MINIMAL protocol: the module exports plain functions
taking and returning byte buffers (integers for lengths, host-provided
`wasm_minimal_protocol_send_result_to_host` and `write_args_to_buffer`
imports) so any language can implement it; the `wasm-minimal-protocol` crate
provides the Rust macro [verify]. Interpreted with `wasmi`, an interpreter, not
a JIT (Typst chose a pure-Rust interpreter for portability, WebAssembly-in-wasm
build, and small attack surface) [verify]. Sandbox: no WASI imports at all;
pure computation. Lessons: (1) an absurdly small ABI (bytes in, bytes out)
gets a lot of authors and languages; (2) deny-everything is easy when the
protocol has no imports; (3) a wasm interpreter (wasmi) is a viable embedded
host where startup matters more than throughput: wasmi is typically 5-20x slower
than Cranelift-compiled wasm but starts in microseconds and has no JIT memory
[verify]. A middle path for us: bytes-in/bytes-out plugins (a flat findings
buffer) are the lowest-common-denominator ABI to offer next to the WIT one.

### 2.6 Extism

Extism is a cross-language plugin framework over wasm (wasmtime in the Rust host
SDK; hosts for many languages; PDKs for Rust, Go, JS, Python, C#, Zig, ...). ABI:
a tiny "kernel" wasm module manages a shared memory arena; plugin exports are
`fn(input bytes) -> output bytes` called by name, with host-function imports for
extension; config and vars are string/KV maps; HTTP and fs are opt-in
(`allowed_hosts`, `allowed_paths`); per-call timeouts via epoch interruption;
`Manifest` lists wasm sources by URL or path with an optional `hash` (sha256
verify) [verify details]. Cost: bytes in/out copy per call, plus a JSON or
protobuf encode by convention; per-call overhead is in the microsecond range
[verify]. Lessons: it generalizes the Typst/dprint "bytes-in bytes-out +
manifest with hash + allowlists" pattern. For us it is a design reference, not a
dependency: it is not typed (no WIT) and adds its own kernel, so a direct
wasmtime + WIT host is leaner and gets type-checked specs (the pluggy lesson:
specs must be typed).

### 2.7 Lapce

Lapce (Rust editor) plugins are wasm (WASI, wasmtime) with a plugin volt
manifest (volt.toml); a plugin can spawn a language server as a native process
(the plugin downloads and runs it) [verify]. Lessons: wasm for glue and
metadata, native subprocess for heavy lifting, which is the same split dprint
made. Practical state: smaller ecosystem [verify]; mostly cautionary on how
much adoption depends on authoring cost and a stable API.

### 2.8 Fermyon Spin

Spin (Wasmtime-based serverless framework) is the main production example of
the component model plus WIT with `bindgen!`, the pooling allocator tuned for
many short-lived instances, and AOT precompilation at deploy time
[verify specifics]. Spin documents sub-millisecond cold starts (the "under a
millisecond" claim) for wasm instantiation [verify; no number fetched]. Lessons
relevant to us: instantiate-per-request is cheap with pooling; `InstancePre` is
the pattern; component adapters (WASI preview1 to preview2) are a build-time
dependency to manage. Spin's "variables" and `allowed_outbound_hosts` are a
manifest-declared capability model (deny by default) worth copying.

### 2.9 wasmer and wasm3 (contrast)

- wasmer: multiple backends (Singlepass, Cranelift, LLVM), its own WASIX
  extension (non-standard POSIX threads/sockets), headless mode with
  pre-serialized artifacts. LLVM backend gives the best peak speed but heavy
  compile and a large dependency [verify]. Component model support has lagged
  wasmtime's [verify]. Verdict: wasmtime is the reference implementation for
  WIT/component and WASI p2; wasmer's non-standard extensions reduce
  portability.
- wasm3: a fast wasm INTERPRETER in C (~4-15x slower than JIT, tiny, no JIT
  memory), project effectively in maintenance mode [verify]. Verdict: not for
  lint rules; mentioned as the contrast of interpreter vs compiler. If a pure
  interpreter is wanted (Typst-style), use wasmi (active, Rust) [verify].

### 2.10 Summary of wasm-host lessons

1. Coarse calls (per file, per rule) with flat, versioned data win every time
   (dprint, Typst, Extism). Per-node calls lose (swc history, Oxlint
   alternative-API note, ruff PyO3).
2. Make the ABI small; the AST-as-ABI (swc) breaks every release.
3. AOT-compile at install; key the cache by wasm digest plus engine fingerprint.
4. Capabilities are declared in a manifest and denied by default; grants are
   recorded in the lockfile or config (Zed, Spin, Extism).
5. A native-process escape hatch exists in dprint, Lapce, Zed (language
   servers): wasm cannot do everything; offer it as an explicit, louder tier or
   decline.
6. Keep old WIT world versions loadable for a window (Zed).

---------------------------------------------------------------------------
## 3. Native dynamic loading in Rust

### 3.1 The problem

Rust has no stable ABI: struct layout, enum layout, trait object vtables, and
`String`/`Vec` internals are unspecified and may change between compiler
versions and even between builds with different flags. A `cdylib` can export a
C ABI (`extern "C"`, `#[repr(C)]`), but then everything crossing the boundary
must be C-compatible; a `dylib` (Rust ABI) requires the plugin and host to be
built with the exact same rustc version and dependency versions. Allocators and
panics across the boundary are UB. Loading through `libloading` (a thin
dlopen/LoadLibrary wrapper) is `unsafe` on every symbol lookup. Also: shared
statics and `TypeId` differ between copies of the same crate in host and plugin
(a Rust type "from the same crate" is not the same type), thread-locals,
`Drop` of host-allocated memory in the plugin, and so on.

### 3.2 abi_stable and stabby

- abi_stable (by rodrimati1992): a library of `#[repr(C)]` stable-layout
  versions of std types (`RString`, `RVec`, `RBox`, `RHashMap`...), `StableAbi`
  derive, "prefix types" that allow adding fields at the end of a vtable/module
  without breaking old loaders, and a root-module loading protocol with version
  checks and layout checking at load time (it compares type layouts to detect
  mismatches). Runtime checks catch many but not all incompatibilities;
  `unsafe` remains inside. Maintenance has been intermittent; it was a heavy
  dependency in compile time [verify].
- stabby (ZettaScale, used in Zenoh): a similar idea with niche optimization
  and a layout "id" computed at compile time, a more compact stable ABI,
  supports trait objects with stable vtables [verify].
Both let you write Rust on both sides with checked layouts, but both still
require the plugin to be a native binary built per platform, run with full
process privileges, and both constrain you to their type vocabulary.

### 3.3 Who does it and why many left

- Bevy: dynamic linking (`bevy/dynamic_linking`) is a DEV-ONLY compile-time speed
  feature (link bevy as a dylib); not for distributing plugins; Bevy plugins
  are plain Rust crates compiled into the app [verify].
- rustc compiler plugins (`#![plugin]`, `rustc_plugin`, `plugin_registrar`):
  deprecated and removed from stable (the "plugin" feature was feature-gated,
  deprecated in 2018-2019 and removed in 2023 [verify]) because they exposed
  compiler internals and blocked evolution. Replaced by proc macros (stable,
  compiled to a dylib but with a stable token-stream API), plus tools that link
  against rustc_driver (Clippy, Miri, Dylint) which require a pinned nightly
  toolchain.
- Nushell: early plugins were native binaries with JSON-RPC over stdio, not
  dylib; the project never shipped in-process dylib plugins for lack of a stable
  ABI [verify history]; see section 4 (out-of-process) for the current design.
- Others: Zed moved from "not at all" to wasm; Lapce wasm; Helix has no plugin
  system yet (wants Steel/scheme or wasm) [verify].
Why abandoned: (1) UB risk and crashes taking down the host; (2) version
lockstep: a plugin built with rustc N does not load in host built with rustc
N+1 unless pinned; (3) unsandboxed: a plugin has full process authority, so a
third-party lint pack is a supply chain RCE with no mitigation; (4) per-OS and
per-arch build matrices for plugin authors; (5) no way to cache or verify
behavior (cannot gate on capabilities); (6) macOS notarization and Windows
DLL load issues for downloaded libraries.

### 3.4 Dylint (the one live example for linters)

Dylint (Trail of Bits) runs Rust lints from dynamic libraries. Constraints
fetched from its README (https://github.com/trailofbits/dylint):
- A lint library is a `cdylib` built with the SAME nightly toolchain that Dylint
  uses for the target crate; the library file name encodes the toolchain (e.g.
  `libname@nightly-YYYY-MM-DD-target.so`), and Dylint searches for files of
  that form [fetched: README "Library requirements"].
- Libraries are fetched from git or crates and BUILT by Dylint on the user's
  machine ("Dylint downloads and builds each entry, similar to how Cargo
  downloads and builds a dependency") [fetched].
- Libraries are configured through `dylint.toml` keyed by library name
  [fetched]; they receive `--cfg=dylint_lib="NAME"` so code can allow lints
  conditionally [fetched].
- Each lint library links rustc internals (`rustc_lint`) so it is tied to
  unstable compiler APIs; "lint libraries" are only for Rust source.
Lesson: this works because dylint is a Rust-only tool whose rule API IS rustc's
internal HIR/MIR, with all of its churn, and users accept building on install.
For a multi-language tool that wants prebuilt, sandboxed, cacheable packs, it
is the wrong shape. Clippy is the opposite pole: lints compiled into the
binary, upgraded with the toolchain, no external rules at all. The two
coexist: Clippy for the standard library of lints, Dylint for org-private
lints, which suggests a tier split (built-in versus out-of-tree) identical to
our tiers 0 and 3, but with wasm instead of rebuilding.

Verdict: reject native dylibs for plugins. Use `libloading`-free design.

---------------------------------------------------------------------------
## 4. Out-of-process plugins

### 4.1 Nushell

Nushell plugins are separate executables the engine spawns; a handshake sends
the encoding as the first bytes (`\x04json` or `\x07msgpack`), then messages
flow over the child's stdin/stdout, with stderr passed through
[fetched: https://www.nushell.sh/contributor-book/plugin_protocol_reference.html:
"Currently two encoding types are supported: json and msgpack"; the Rust
`nu-plugin` crate exports `JsonSerializer` and `MsgPackSerializer`,
https://github.com/nushell/nushell/blob/main/crates/nu-plugin/src/lib.rs].
The docs state MessagePack "should be preferred where possible if performance is
desired" and byte arrays are inefficient in both [fetched]. The protocol is
versioned (`Hello` with a protocol version and features, compatibility checked
by semver of the nu-plugin crate), signatures are declared by the plugin
(`Signature` command descriptions), values are Nu `Value`s, and it supports
streaming (`ListStream`/`ByteStream`) and engine calls back from plugin to
engine. Plugins are registered with `plugin add <path>` and `plugin use`, with a
persisted registry file (plugin.msgpackz) caching the signatures so startup does
not spawn every plugin [verify]. Plugins are persistent processes (the
"plugin gc" option stops idle plugins after N seconds) so the spawn cost is paid
once per session [verify]. Sandboxing: none beyond OS process isolation; a plugin
is a trusted native executable. Per-call IPC cost: a pipe round trip with
MessagePack encode/decode is on the order of tens of microseconds (two context
switches plus a syscall pair) [verify: not fetched; typical Linux pipe
ping-pong is 5-20 us]. Lessons: out-of-process is robust (a crash does not kill
the host), language-agnostic, and easy to author, but it is 2-3 orders of
magnitude per call slower than in-process wasm, so the unit of work must be
coarse, and the sandbox is the OS, not the protocol.

### 4.2 LSP-style servers

Language servers speak JSON-RPC over stdio with Content-Length framing; per
message cost is dominated by JSON (de)serialization and context switches, tens
to hundreds of microseconds [verify]. The protocol tolerates this because
requests are per user action, not per AST node. LSP's own lesson on versioning:
capabilities negotiation at `initialize` (client and server advertise
capabilities, each side uses the intersection). That is a direct model for our
`needs(...)` versus adapter capability declaration. Not a model for per-file
lint hot paths, but a good one for the OPTIONAL tier "external analyzers"
already handled by the bound-tool stages in rules.md section 4.

### 4.3 Buf and protoc plugins

protoc plugins are executables `protoc-gen-NAME` that read a serialized
`CodeGeneratorRequest` on stdin and write a `CodeGeneratorResponse` on stdout:
one process spawn per invocation, one request containing ALL files and
descriptors, one response. Buf extends this with remote plugins (hosted
registries, WASM plugins in the Buf registry since 2024 [verify]) and "buf
check plugins" (custom lint rules for `buf lint` distributed as WASM via the
Buf Plugin Framework `bufplugin-go`, which runs plugins with wazero
[verify]). Lessons: (1) one big batched request per invocation (the
whole-compilation unit) amortizes spawn and IPC to nothing; (2) typed request
and response messages as the ABI (protobuf) with additive evolution rules;
(3) Buf moved lint plugins to wasm for sandboxing and portability, the same
destination as this note [verify the date and runtime].

### 4.4 Cost summary

Process spawn: ~1-5 ms on Linux for a small native binary, more with a runtime
(Python 20-50 ms, Node 40-80 ms) [verify; the Python figure is consistent with
the measured 0.02 s for `python3 -c pass` here: [measured] 20 ms]. So a per-run
spawn is fine, a per-file spawn is not, a per-node IPC call is catastrophic.

---------------------------------------------------------------------------
## 5. Declarative rule systems (host-executed)

Common property: the rule author supplies DATA; the host engine is compiled
Rust/C++/OCaml and executes it, giving near-native speed, easy sandboxing (no
code), and static analysis of rules (e.g. which node kinds a rule can match, so
the engine can prefilter). The costs: expressiveness ceilings and a new
language to learn.

### 5.1 Semgrep

YAML rules with `pattern` (code-shaped patterns with metavariables `$X`, `...`),
`patterns` (and), `pattern-either`, `pattern-not`, `pattern-inside`,
`metavariable-regex`, `metavariable-comparison`, taint mode (`pattern-sources`,
`pattern-sinks`, `pattern-sanitizers`), plus `fix`, `message`, `severity`,
`languages`, `metadata`. Engine: semgrep-core in OCaml parsing with
tree-sitter into a generic AST (AST_generic, ~30 languages), matching with a
unification-based matcher; rules are preprocessed for prefiltering: extracting
required literal strings/regexes per rule so files that cannot match are skipped
before parsing (the "may-match" optimization using a fast regexp or trigram
filter) [verify]. Speed: tens of thousands of lines per second per core for
common rule sets; the OSS engine is intra-file, taint and cross-function are in
the paid engine [verify]. Registry: semgrep.dev/r, rules as YAML in git; rule
IDs and a registry with versioning by `semgrep-rules` repo commit; Semgrep
Supply Chain etc. are separate. Authoring cost: very low (a pattern looks like
the code). Lessons: (1) pattern-in-the-target-language is the best authoring UX
(our gob-pattern is the same idea; ast-grep and Semgrep prove it); (2)
prefiltering by cheap literal extraction is what makes thousands of rules
tractable; (3) the generic AST (a universal model) is how one rule works for
many languages with per-language "may not apply" cases, the same as our U
(Semgrep's generic AST is the closest prior art to U); (4) the expressive limit
is hit by taint and cross-file, where they went to an engine feature, not user
code, plus a `metavariable-analysis` escape [verify].

### 5.2 ast-grep

Rust CLI using tree-sitter. Rule YAML: `id`, `language`, `rule:` with atomic
(`pattern`, `kind`, `regex`), relational (`inside`, `has`, `follows`,
`precedes`, with `stopBy`), composite (`all`, `any`, `not`, `matches`) rules,
`constraints` on metavariables, `utils` (reusable named rules), `transform`
(string ops on captures) and `fix`. Patterns are parsed once into a tree-sitter
pattern structure and matched by AST structural comparison; rules compile to
a matcher tree; a `kind` prefilter lets the scanner dispatch by node kind
(`potential_kinds`) so each node is tested only against rules that can match its
kind [verify: this is in ast-grep-core as `potential_kinds`]. Speed: parallel
per-file with `ignore` + rayon; ast-grep claims to handle large repos in seconds
and is written to be a "tree-sitter + Rust" tool [verify; benchmark number not
fetched]. Distribution: rules live in the repo (`sgconfig.yml`, `ruleDirs`);
no registry; sharing is by copy or git. ast-grep also supports "custom
languages" via dynamic-loaded tree-sitter grammars (`customLanguages` in
sgconfig.yml, loading a `.so`/`.dylib` built from a grammar with
`tree-sitter-loader`) [verify], and a napi/pyo3 library API. Lessons: this is
the nearest implementation to the planned gob-pattern engine; the three
relational operators (`inside`, `has`, `follows`) cover most structural lint;
the prefilter by node kind is cheap and effective; no registry means no trust
problem and no discovery.

### 5.3 CodeQL

QL, an object-oriented logic language, compiled by the QL compiler through
several IRs (QL -> DIL -> RA, relational algebra) to optimized relational
queries run by an evaluator over a DATABASE extracted per codebase (the
extractor builds a relational database of the AST, CFG, data flow facts).
Evaluation is bottom-up Datalog-style with semi-naive evaluation, magic sets
and join-order optimization, and results cached by predicate across queries
[verify]. Speed: analysis time on large repos is minutes to hours (database
creation dominates); not an interactive lint [verify]. Packs: `qlpack.yml`
with name, version, dependencies, `library: true`, `suites`; `codeql pack
install` writes `codeql-pack.lock.yml` locking transitive dependency versions;
`codeql pack publish` pushes to GitHub Container Registry (GHCR) as OCI
artifacts; a pack published has all dependencies' resolved versions in the
bundle [verify]. Compiled query packs (`codeql pack create`/`bundle`)
include precompiled query plans (`.qlx` files), so users need not compile
[verify]. Authoring cost: high (a logic language, but powerful). Lessons: (1)
pack format with lockfile, semver, library vs query packs, published as
registry artifacts is the polished model of section 6; (2) ship PRECOMPILED
query plans in the pack so the consumer's cost is load-only (precisely the
include_bytes/plan-from-disk design of section 7); (3) the extract-then-query
split mirrors our "assemble snapshot once, then rules are pure functions"; (4)
too slow and too heavy for per-file incremental lint, so Datalog as v1 rule
engine is out, as a possible later engine for repo-wide rules (cycle, dead
symbol) where it is a natural fit.

### 5.4 Souffle and DDlog

Souffle: a Datalog engine; programs are synthesized to C++ (compile with a C++
compiler, then run) or interpreted; strong performance on large relations (used
for Doop pointer analysis, security analysis at Oracle/others) [verify]. Plans
are specialized with indexes selected at compile time, which is where its speed
comes from; the interpreter mode is several times slower than the compiled mode
(order 2-10x [verify]). DDlog (VMware research, Differential Datalog): compiles
Datalog to a Rust program built on differential-dataflow, for INCREMENTAL
evaluation (insert/delete facts, get delta outputs) [verify]; archived/no longer
maintained since ~2022 [verify]. Lessons: for repo-wide graph rules a Datalog
formulation is expressive and fast but requires compile-to-native (a toolchain
dependency at rule-load time, which contradicts the "load a pack and run" goal)
or an interpreted evaluator (slower). Incremental evaluation (DDlog,
differential dataflow, also salsa) matches our "persist per-file findings keyed
by digest" design with a coarser, cheaper granularity; we already have that and
do not need Datalog to get incrementality. An embedded Datalog crate (`ascent`,
`crepe` are macro-compiled-into-Rust Datalog; `datafrog` is a library;
`ddlog` is archived) is an option for repo-scope rules compiled INTO the
binary (tier 0), not loaded [verify the crate features].

### 5.5 stack-graphs and tree-sitter-graph (TSG)

tree-sitter-graph is a DSL for constructing a graph from a tree-sitter parse
tree: `(function_definition name: (identifier) @name) { node def; attr (def)
type = "pop_symbol", symbol = (source-text @name) ... edge ... }`: stanzas of
a tree-sitter query pattern plus statements that create nodes, edges and
attributes with scoped variables. stack-graphs (GitHub, powering precise code
navigation on github.com) uses TSG files per language to describe name binding
(scopes, definitions, references, imports) as a graph of push/pop symbol nodes;
name resolution is path finding over the graph, incremental per file
(`stack-graphs` stores per-file partial paths in a DB so cross-file resolution
reuses precomputed partial paths) [verify]. TSG is therefore a declarative
FORM of a binding discipline: one `.tsg` file per language, evaluated by the host
over the concrete tree. Cost: TSG execution is a tree-walk with query matches,
fast enough for indexing at GitHub scale (per-file ms); resolution is a
separate path-search cost [verify]. Status: GitHub archived the stack-graphs
repository in 2025 [verify], and language TSGs were written for a handful of
languages only (Python, JS/TS, Java) with huge effort; authoring cost is high.
Lessons: (1) it is the existence proof that a binding discipline can be data;
(2) authoring cost, not execution, killed breadth (3 or 4 languages after 3+
years); (3) so do not make "write a TSG" the only way to add a language; offer
a coarse declarative tier (tags.scm/locals.scm style) for 80 percent and keep
the full binding discipline for languages that matter (relevant to binding.md
and universal-model.md's annotate-or-be-opaque rule).

### 5.6 tree-sitter queries (.scm)

S-expression patterns with captures `@name`, predicates `#eq?`, `#match?`,
`#any-of?`, quantifiers `*+?`, alternation `[...]`, anchors `.`, negated fields
`!field`; compiled by `Query::new` into a state machine over the parse
table's symbols, matched incrementally with a `QueryCursor` during a tree walk.
Cost: query compilation is milliseconds for small queries but can be tens to
hundreds of milliseconds for large, highly alternating queries (the highlights
queries of big grammars) [verify]; matching cost is roughly linear in tree size
times active pattern states, usually a small fraction of parse time per query
[verify]; the known pathological case is deeply nested optional/quantified
patterns causing many concurrent states (`QueryCursor::set_match_limit`
exists to bound this) [verify]. Query predicates `#match?` run a regex per
candidate, which dominates for regex-heavy queries; general predicates not
understood by the library are exposed to the host via
`QueryPredicate`. For linting, the right use: one combined Query per language
containing all language-tier rules (a pattern index maps match to rule id), so
one traversal serves all rules, or one Query per rule if isolation matters.
Combining all rules into one query yields the same effect as ast-grep's kind
dispatch. In Rust, `tree_sitter::Query` is Send/Sync-able per thread
(QueryCursor is per thread) and can be built once at startup or cached.
Lessons: query-as-rule is the simplest, fastest declarative tier and is what
rules.md already adopts for language rules; the derive-time compile check in
rules.md section 2 is the right guard.

### 5.7 Rego / OPA

Rego (Datalog-inspired policy language). Execution paths: a tree-walking
interpreter (default), partial evaluation (`opa eval --partial`, compile policy
with known data into residual queries), and compile to WASM
(`opa build -t wasm`) giving a self-contained module with a documented ABI
(`opa_eval`, `opa_malloc`, JSON in and out through linear memory) loadable in any
wasm runtime; and newer `opa build -t plan` (an IR "plan" format, JSON, for
building new backends) [verify]. Bundles (`opa build` -> .tar.gz with manifest
and data) distributed from an HTTP service and verified by JWT signature
(bundle signing) [verify]. Speed: OPA authors publish microseconds to tens of
microseconds per simple policy decision for the interpreter with the rule
index, and the wasm target is comparable or somewhat slower than the Go
interpreter for small policies and faster for heavy computation [verify; the
wasm-vs-Go comparison is mentioned in OPA docs "Policy Performance"]. Lessons:
(1) a stable "plan" IR as the artifact decouples authoring language from
executors; (2) wasm ABI = JSON in/out is simple but costs serialization
(their docs note it); (3) bundle signing and manifests are the right trust
mechanism for declarative artifacts; (4) rule indexing (build a decision tree
over equality predicates so that most rules are skipped without evaluation) is
what makes an interpreter fast: relevant to our U rules, which should declare
`needs` and the node kinds they care about for a first-stage index.

### 5.8 Clippy versus Dylint, and ruff's refusal

Clippy: ~800 lints compiled into one binary against rustc internals; zero
extension story by design (rustc's internal APIs are unstable); cost is fully
native. Dylint: see section 3.4.

Ruff: Astral's FAQ says "Ruff does not yet support third-party plugins, though a
plugin system is within-scope for the project. See #283" and re-implements the
popular Flake8 plugins (~800+ rules) in Rust instead [fetched:
https://github.com/astral-sh/ruff/blob/main/docs/faq.md lines ~105, 259]. Issue
#283 (open) lists the design concerns by the original proposer: explicit opt-in
(avoid flake8's auto-enable via setuptools), a fix API, deterministic plugin
order given that plugins change source, per-plugin configuration without
conflicts, and packaging Rust extensions [fetched]. The only code path is an
UNMERGED RFC stack, "[ruff][ext-lint]", whose PR 3 embeds CPython via PyO3: it
reports that a GIL interpreter serializes execution and that the lock/unlock
overhead on short spurts of Python (the workload of "run a rule on each AST
node") is "so slow as to be somewhat pointless", so it requires a free-threaded
CPython 3.13/3.14 build behind a non-default feature, with weaker isolation
(rules can mutate shared Python state) [fetched:
https://github.com/astral-sh/ruff/pull/21415]. "The reasons Astral gives"
(explicit statement of rationale beyond the FAQ and the PR) I did not find in
this session; the observable reasons are: speed (per-node dynamic calls are
catastrophic), the cost of a stable AST ABI, the isolation story, and that
shipping everything built-in keeps them fast and consistent. Lessons: the most
successful fast linter chose "everything built in" and the community pressure
for plugins still persists after years; the in-tree attempt chose an embedded
scripting runtime and found per-node crossings unacceptable. This supports
tiers 1-2 (data and declarative, run by the host) as the primary extension
path, and strictly batched wasm for code.

### 5.9 ESLint flat config plugins

Plugins are JS objects (`plugins: { name: plugin }`) with `rules`, `configs`,
`processors`, `meta`; explicit import in `eslint.config.js` (flat config, default
in v9) replaces string-based discovery by name (`eslint-plugin-*` resolved
from node_modules). Rules are JS modules with `create(context)` returning
visitor functions keyed by selector (esquery selectors like
`CallExpression[callee.name="eval"]`). ESLint dispatches by selector through a
single traversal with a node-type indexed emitter (so all rules share one walk).
Speed: ESLint is about 85x slower than Oxlint on vuejs/core (4,116 ms vs 48 ms
[fetched Oxc post]) and its multithread mode (`--concurrency=auto`) gives only
10 percent in that benchmark (3,710 ms) [fetched]. Lessons: (1) explicit config
import (not discovery) won; (2) selector-keyed visitors over one shared
traversal is the right dispatch pattern (also tree-sitter query pattern index);
(3) a JS ecosystem of thousands of rules accumulates because authoring is
trivial in the host language, which is the argument for a very low authoring
cost for ours.

### 5.10 Biome and GritQL plugins

Biome (Rust, linter/formatter) 2.0 added "linter plugins" written in GritQL
(`.grit` files), registered in `biome.json` `plugins: ["./rule.grit"]`; they
match code patterns with `register_diagnostic(span=$x, message="...",
severity="warn")`; execution is by Biome's embedded Grit engine (the
`grit-pattern-matcher` / `biome_grit_patterns` crates), host-interpreted, JS/CSS
supported first [verify; the plugins docs page was fetched but the extract hit
a tool limit, so claims are from background knowledge: https://biomejs.dev/linter/plugins/].
Grit (Honeycomb->Grit.io) is a query language that compiles patterns like
`` `console.log($msg)` => `logger.info($msg)` `` into matchers over tree-sitter
trees with a Datalog-ish clause model and rewrites [verify]. Performance:
Biome says plugins are slower than native rules but still fast [verify, no
number]. Lessons: a major Rust linter chose "declarative pattern language
executed by the host" as its first plugin mechanism instead of JS or wasm, for
exactly the speed and safety reasons here; native rules written in Rust stay
unpluginable (they are compiled in). Expressiveness limits are acknowledged
(diagnostics only; no type info).

### 5.11 Oxc JS plugins (raw transfer)

Fetched facts from https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html: Oxlint
runs JS plugins with an ESLint-compatible API plus a faster alternative API.
Mechanism: "raw transfer": the Rust AST's native memory layout IS the
serialization format (the AST is built in an arena with a known layout, copied
as bytes into a buffer, and JS reads fields through typed arrays with lazily
constructed node objects), "cuts the cost of serialization to zero" and
"laziness dramatically reduces the other side" (deserialization) and GC
pressure; objects are created only for nodes a rule touches (e.g. only
ClassDeclaration nodes if a rule visits only those). Benchmark on vuejs/core,
MacBook Air M3: ESLint 4,116 ms, ESLint multithreaded 3,710 ms, Oxlint 48 ms,
Oxlint with a simple JS plugin 236 ms ("still 15x faster than ESLint even using
ESLint's multi-threaded runner") [fetched]. The post says performance was not
the focus of that preview and "multiple x speed-ups" were planned [fetched];
the later "JS Plugins Alpha" post followed (fetched only as an index entry).
Lessons: (1) the boundary, not the guest language, is the dominant cost; (2)
design the host data structure so that the guest can read it in place
(arena, fixed layout, offsets) and materialize lazily; (3) a dispatch API
that lets the host skip nodes the plugin does not care about (selector/visitor
keys with the "alternative API") is what lets a slow guest not see the whole
tree; (4) even the best case is ~5x the pure-native time for one trivial rule
(236/48), which sets expectations for any non-native code tier: if we want <20
percent overhead over built-ins, rules must be host-executed (tier 2) or wasm
batch (tier 3) with in-place reads, never a callback per node.

### 5.12 SWC versus Babel plugin cost

Babel plugins are JS visitors in-process with the JS AST (no boundary), so the
Babel plugin cost is just JS execution, but Babel itself is slow (parse plus
traverse in JS). SWC plugins as wasm pay serialization of the whole AST per
plugin per file (rkyv) but run optimized native code; the net result is "SWC
plugins faster than Babel plugins, slower than SWC built-ins" with the cost
growing with plugin count (each plugin re-deserializes) [verify, no benchmark
fetched]. Lessons: avoid per-plugin full-AST round trips: run all plugins of a
phase against one shared in-place view, and let each return a diff (findings
or edits), not a mutated tree.

### 5.13 Summary

Every fast tool above either (a) executes declarative rules in the host
(ast-grep, Semgrep, Biome/Grit, CodeQL packs with precompiled plans,
tree-sitter queries), or (b) refuses plugins (Ruff, Clippy), or (c) pays a heavy
engineering cost to make a guest-language boundary cheap (Oxc raw transfer,
swc rkyv). That ordering is the evidence for tiers 2 before 3.

---------------------------------------------------------------------------
## 6. Loadable language support

### 6.1 tree-sitter grammars as wasm

tree-sitter grammars compile to wasm (`tree-sitter build --wasm`, using
wasi-sdk or emscripten or Docker) producing a module that exports the language
function and uses the library's side-module ABI. Consumers:
- web-tree-sitter (JS bindings: the core runtime is itself compiled to wasm, and
  grammar wasm modules are dynamically linked into it with `Language.load`)
  [fetched README: https://github.com/tree-sitter/tree-sitter/blob/master/lib/binding_web/README.md].
- The Rust crate with the `wasm` feature, which embeds wasmtime via
  `wasmtime-c-api` and lets a native `Parser` run a wasm-compiled grammar:
  `Parser::set_wasm_store(WasmStore::new(&engine))` then
  `store.load_language("javascript", wasm_bytes)`; grammars may be loaded from
  different stores sharing one `WasmEngine` [fetched:
  https://github.com/tree-sitter/tree-sitter/blob/master/lib/binding_rust/README.md
  lines 101-130; feature `wasm = ["std", "wasmtime-c-api"]` in
  lib/Cargo.toml line 42]. Only the grammar's lexer and external scanner run as
  wasm; the parse table interpretation (the generic parser) stays native, so
  the slowdown applies to lexing and scanner callbacks, not all of parsing
  [verify against tree-sitter docs; this is how the wasm feature is described
  in source comments].
- Zed: grammars are wasm; Zed compiles grammar repos to wasm and loads them
  with this wasm feature (explaining the feature's existence) [verify].
- Neovim: parsers are native .so files built by `nvim-treesitter` or shipped by
  packages; `vim.treesitter.language.add` can load wasm grammars with
  `vim.treesitter.language.add` in newer versions (0.10 experimental wasm
  support via `--wasmtime`) [verify].
- Helix: `hx --grammar fetch` and `hx --grammar build` clone and compile
  grammars into native `.so`/`.dll` in `runtime/grammars/`, loaded via
  `libloading` at runtime [verify]; hence dynamic loading of native grammar
  libraries, risk accepted because grammars are generated C with a tiny stable C
  ABI (`tree_sitter_<lang>()` returning a `TSLanguage*`, versioned by
  `LANGUAGE_VERSION`), which is the one case where native dlopen is
  ABI-stable.
- The Rust `tree-sitter-loader` crate (used by the CLI and ast-grep custom
  languages) compiles and loads native grammars.

Cost of wasm versus native parsing: I found no published, citable benchmark in
this session. Order-of-magnitude expectation: lexing and scanner code compiled
to wasm under Cranelift runs at 1.2-2x native time (typical wasm-vs-native
SPEC-like ratios of 1.1-2.0x [verify]); incremental costs from the boundary
(the host exposes the input callback and lexer API through imports; the
C-API wasm store crossing is a function pointer call); tree-sitter's own wasm
feature PR/discussion mentions a 2-3x slowdown for wasm-based parsing versus
native [verify, this is a recollection, not a fetched statement]. For lint
purposes parse time is a small fraction of total in a cached run (a warm run
re-parses only changed files), so a 2-3x grammar slowdown on the long tail
languages is acceptable; for the ~10 core languages use native grammars linked
into the binary. Proposed local benchmark (not run here, to respect the disk
guard and the no-large-build rule): parse a 1 MB JS/Rust file with the native
crate and with the wasm crate feature using the same grammar; record
median-of-10 times and RSS.

Binary and startup cost: linking N native grammars into the binary costs roughly
0.3-2 MB each (generated parse tables; large for C++ and Rust grammars)
[verify]; wasm grammars cost the same on disk as .wasm (~100 KB-1.5 MB) plus
.cwasm AOT cache, and need `WasmStore` instantiation per thread per grammar
(microseconds with the pooling allocator, but compile on first load unless
cached: Cranelift of a 1 MB grammar wasm is ~0.1-0.5 s [verify]).

### 6.2 Declarative adapter descriptions

What is declarative today:
- `node-types.json` (generated by tree-sitter): a machine-readable schema of
  every node kind, its fields (with `types`, `multiple`, `required`), its
  children, subtypes (supertypes), and whether named. It is exactly the
  "denominator" needed to check an adapter mapping for coverage: every named
  node kind in the grammar must be mapped, mapped to opaque, or listed as
  deliberately ignored (a falsifiable completeness claim, matching the
  hierarchical-thinking rule). Use it to generate an adapter skeleton and to run
  a coverage test.
- `tags.scm`: queries with captures `@definition.function`, `@name`,
  `@reference.call`, `@doc` that define symbol definitions and references for
  code navigation (the "tags" crate/`tree-sitter-tags`); a coarse symbol table
  per language with no scoping.
- `locals.scm`: captures `@local.scope`, `@local.definition`,
  `@local.reference` for scope-aware highlighting; a coarse binding discipline
  (lexical scope only, same-file).
- `highlights.scm`, `injections.scm`, `folds.scm`, `indents.scm`, `outline.scm`
  (editor features; not needed by us).
- stack-graphs `.tsg` (section 5.5): the full binding discipline.
A declarative adapter for U then has layers: (1) node-types.json for coverage,
(2) a mapping file from tree-sitter kinds/fields to U operators and role
attributes expressed as query-to-op rules (a `.scm` with captures named by U
roles, e.g. `@u.function.name`), (3) a locals.scm-like scope description for
binding, (4) optionally a TSG for full binding, (5) wasm code only when the
language needs semantic computation (macro expansion, type inference), which
should in practice go through "bound tool" stages instead (rules.md section 4).
The annotate-or-be-opaque doctrine of universal-model.md 4.6 gives the escape
valve: whatever the declarative adapter cannot express is marked opaque and
yields Unresolved rather than a wrong answer.

---------------------------------------------------------------------------
## 7. Distribution, versioning, trust

### 7.1 Prior art summary

| system | unit | version | lock | integrity | signing | capabilities |
|---|---|---|---|---|---|---|
| CodeQL packs | qlpack, OCI artifact on GHCR | semver + ranges in qlpack.yml | codeql-pack.lock.yml | registry digest [verify] | GitHub provenance [verify] | none (queries are pure, but custom extractors run code) |
| Semgrep registry | YAML rule files, rulesets | git commit of semgrep-rules; `--config p/xyz` | none by default (rules fetched at run) | HTTPS only [verify] | none [verify] | none (no code) |
| crates.io / cargo | crate | semver | Cargo.lock (checksum of .crate sha256) | sha256 in the index | none native; `cargo vet`, sigstore efforts | build.rs and proc macros unsandboxed |
| npm | tarball | semver | package-lock integrity (sha512) | sri hash | npm provenance (sigstore) since 2023 | install scripts unsandboxed |
| dprint | wasm by URL | version in URL | checksum suffix in config | sha256 | none | wasm sandbox |
| Zed | extension repo | extension version + API since_v | n/a | git commit pin | n/a | declared and user-granted |
| OPA bundles | tar.gz + manifest | revision string | n/a | file digests in .signatures.json | JWT bundle signing | policy is pure |
| Buf | module/plugin on BSR | commit/tag | buf.lock with digest | digest | n/a | wasm sandbox [verify] |
| Deno/JSR | module | semver | deno.lock with hashes | sha256 | JSR provenance via sigstore [verify] | permission flags --allow-* (deny by default) |

### 7.2 Mechanisms to adopt

- Content digest identity. A pack's identity is `blake3` or `sha256` of its
  canonical bytes; the lockfile records `{name, version, digest, source,
  fetched_at}`. The packs.md "registry drift-lock" already pins by digest;
  extend to wasm components and compiled plans: the cache key is the digest.
- Lockfiles with content digests for transitive dependencies: Cargo.lock,
  package-lock, codeql-pack.lock.yml, deno.lock, buf.lock all converge on
  "name, exact version, digest". A pack that depends on another pack's vocab
  pins it exactly (packs.md already forbids ranges in pack versions; keep).
- Signatures. Sigstore (cosign keyless): signing with an OIDC identity,
  certificate from Fulcio, entry in the Rekor transparency log; verification
  checks the signature, the certificate identity (e.g. a GitHub Actions workflow
  URL), and log inclusion. npm provenance, PyPI attestations (PEP 740) and
  GitHub artifact attestations use it. For packs: optional `signature` field plus
  `[trust] identities = ["https://github.com/org/repo/.github/workflows/release.yml@refs/tags/*"]`;
  verification offline-capable with a bundled trust root (TUF) [verify the exact
  offline story]. Default policy: digest pin is mandatory; signature is
  required only for wasm (code) packs when the repo sets `require_signed`.
- Capability declarations, deny by default. A pack manifest declares the
  capabilities its code tier needs: `fs.read` (scoped paths), `net` (hosts), `env`,
  `exec` (command allowlist), `clock`, `random`. Defaults deny; the REPO's
  config grants, and the grant is recorded in the lockfile alongside the digest,
  so changing capabilities or digest is a reviewable diff. Prior art: Deno
  permissions, Zed `granted_extension_capabilities`, Spin `allowed_outbound_hosts`,
  Extism `allowed_hosts`/`allowed_paths`, WASI preopens (fs access = list of
  preopened dirs). For lint plugins the right default is NONE: a rule is a pure
  function from the snapshot slice to findings, needs no fs, net, clock or
  randomness (also needed for determinism and cacheability: results keyed by
  (file digest, rule id, rule version, side-input digest) requires purity). Mark
  any pack that requests non-pure capabilities as non-cacheable and visibly
  so.
- Data-only packs are safe to fetch by URL (packs.md 1.3); wasm packs are safe
  to RUN under wasm isolation but not safe to TRUST for findings (they can
  lie: suppress findings). Hence signatures and review matter more for
  suppression-capable code than for sandboxing.
- Registry: not v1. A git-URL plus digest model (like dprint, ast-grep) needs no
  infrastructure; a registry (OCI/GHCR like CodeQL, or a crates-style index) is a
  v2 convenience. The std library ships embedded.
- Reproducibility: lock the wasmtime version and engine config fingerprint in
  the AOT cache metadata, not in the lockfile (cache is derived data).

---------------------------------------------------------------------------
## 8. Rust-specific: one execution path for built-in and plugin rules

### 8.1 Design

Goal: built-in declarative rules and third-party declarative rules go through
exactly the same executor, differing only in where the compiled plan bytes
come from.

```
 source (rule text: query/pattern/predicates)
    -> parse -> typecheck against U schema and grammar node-types.json
    -> lower to PLAN (versioned binary IR; postcard/rkyv/bincode, with a header
       {plan_format, u_schema_version, grammar_id, needs, node-kind prefilter})
    -> bytes
 built-in:  build.rs or xtask compiles at build time ->
            static PLAN_X: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/x.plan"));
 external:  loaded from pack file at `.frob/packs/<digest>/x.plan`
            (compiled at `frob packs add` and cached keyed by digest + plan_format)
 both:      Plan::load(&[u8]) -> Result<Plan, PlanError> -> Executor::run(plan, cx)
```

Details and reasons:
- The plan IR must be versioned and rejected on mismatch (CodeQL .qlx,
  OPA plan, tree-sitter LANGUAGE_VERSION precedent). A mismatch is a loud
  `PACK`-family error naming the pack and expected version, never a silent
  fallback.
- Zero-copy load: use `rkyv` (validate with `bytecheck` for external bytes,
  `access_unchecked` for embedded bytes since they were produced by our own build)
  or a hand-rolled flat layout with `&[u8]` slices. For plans that are small
  (kilobytes), `postcard` deserialization is microseconds and simpler; choose
  by measurement; rkyv's validation cost is an extra pass [verify magnitudes].
- Embedded plans mean "std library as plugins": the executable's built-in packs
  are listed in the same registry (`inventory::submit!(BuiltinPack{..})`), and
  `frob packs list` shows them with `origin = builtin`, digest equal to the
  digest of the embedded bytes, so a repo may pin the std pack digest (and a
  binary upgrade that changes it surfaces as drift, which is the existing
  packs.md drift-lock).
- Plan caching keyed by digest: compile once from source to plan (cache key
  `blake3(source) + compiler_version + u_schema_version`), store under
  `.frob/cache/plans/`. For wasm, the .cwasm cache key is `blake3(wasm) +
  wasmtime_version + target + engine_config_hash`. Findings cache (already
  designed): `(file digest, rule id, rule version, side-input digest)`, where
  rule version for plugin rules is the pack digest, so changing a pack
  invalidates exactly its findings.
- Executor shape: one combined dispatch structure per language, built at startup
  from all enabled plans: a pattern index by node kind (ast-grep
  `potential_kinds`, ESLint selector index, OPA rule indexing, tree-sitter
  pattern index) so each node is visited once and tested only against plans that
  can match, preserving "one pass".
- Handwritten Rust rules (tier 0) implement the same `Rule` trait and receive
  the same `Cx`. A declarative rule is internally a `PlanRule` struct
  implementing `Rule` by running the executor, so the framework cannot tell them
  apart; wasm rules are a `WasmRule` struct implementing `Rule` via the batch
  call. One trait, three impls; the pytest "plugins are plugins" principle.
- Build-time check (rules.md): compile every embedded query against its grammar
  in a generated test; the same checker runs at `frob packs add` for externals.

### 8.2 Gap between host-interpreted plan and handwritten Rust

Honest answer: I found no published measurement for lint predicates specifically.
Indirect evidence and expectations:

- ast-grep, tree-sitter queries, Semgrep, Biome/Grit are all host-interpreted
  matchers and are the speed leaders of their respective fields (ast-grep scans
  repos in seconds [verify]); Ruff's handwritten rules are faster still per rule
  but the dominant cost for both is parsing and traversal, not predicate
  evaluation, once a kind prefilter is present.
- Rough model (hypothesis [verify]): handwritten Rust predicate on an arena AST:
  1-20 ns per candidate node; interpreted plan with a prefilter by node kind and
  precompiled operand slots: 20-200 ns per candidate (a 3-10x predicate
  slowdown), but only candidate nodes (typically 1-5 percent of nodes) pay it, so
  whole-run difference for a typical rule set is under 1.5x of handwritten and
  often under 10 percent because parse and I/O dominate. Regex predicates
  (`#match?`) dominate in both, equalizing them.
- Observed ordering from boundary-crossing cases (hard numbers fetched): Oxlint
  native 48 ms versus one trivial JS rule 236 ms (about 5x) [fetched], which
  bounds what a poorly-batched guest costs, and gives a ceiling for "interpreted"
  being far better than "guest code with per-node crossings".
- Proposed benchmark (one afternoon, in a scratch crate, not run here under the
  no-cargo constraint): implement three representative predicates (a callee-name
  vocabulary match, a "public fn without doc comment", a nesting-depth
  threshold) three ways over the same tree-sitter tree: (a) handwritten
  `for node in cursor`; (b) tree-sitter `Query` with a predicate; (c) the plan
  interpreter; (d) a wasm component batch rule reading the same flat arena.
  Measure ns/candidate and ns/file over a 5k-file corpus with criterion; compare
  to parse time per file. Decision rule: accept tier 2 if (c)/(a) at whole-run
  level is under 1.3x; accept tier 3 if (d)/(a) is under 3x with per-file
  batching.

---------------------------------------------------------------------------
## 9. Per-system comparison table

Scale: perf (relative to compiled-in), safety (isolation/trust), portability
(one artifact runs everywhere), authoring cost (low is good).

| mechanism | example | perf vs built-in | safety | portability | authoring cost | notes |
|---|---|---|---|---|---|---|
| compiled-in Rust | Clippy, Ruff | 1.0x | trusted | n/a | high (Rust, release) | std library tier |
| Rust cdylib/dylib | Dylint, abi_stable, stabby | ~1.0x | none (full process authority, UB across ABI) | poor (per rustc, per OS) | high | reject |
| wasm component, per-file batch | dprint, Zed, Spin | ~1.1-2x guest compute [verify] plus tens of ns per crossing | strong (memory isolation, no ambient authority, epoch limits) | excellent (one .wasm, per-host AOT) | medium-high (Rust to wasm, WIT) | tier 3 |
| wasm per-node callbacks | swc-like full-AST ABI, Oxlint JS | 5x+ (Oxlint 236/48 [fetched]) | strong | good | medium | avoid shape |
| wasm interpreter (wasmi) | Typst | 5-20x [verify] | strong | excellent | medium | fallback for tiny rules |
| embedded script (PyO3, Lua, JS) | ruff ext-lint RFC | "so slow as to be pointless" per node on GIL [fetched] | weak to medium | medium | low | reject as main path |
| out-of-process stdio | Nushell, LSP, protoc | spawn ms; per call tens of us [verify] | OS process only | good (any language) | low-medium | external tools tier only |
| declarative pattern YAML | Semgrep, ast-grep | ~1-1.5x [verify] | very strong (data) | excellent | very low | tier 2 |
| tree-sitter query (.scm) | rules.md language tier, nvim, helix | ~1-1.3x [verify] | very strong | excellent | low | tier 2 |
| query language to plan, host exec | CodeQL (heavy), OPA, Grit | 1-10x depending on engine [verify] | very strong | excellent | medium-high | tier 2 universal predicate language |
| Datalog compiled to native | Souffle, ascent, crepe | ~1x if compiled in; needs toolchain if external | trusted compile step | poor external | medium | tier 0 only, repo-scope rules |
| data tables (TOML) | packs.md | n/a (lookup) | strongest | excellent | lowest | tier 1 |
| pytest-style hooks, in-process Python | pluggy | 0.6-4 us per hook call [measured] | none | n/a | lowest | architecture lessons only |

---------------------------------------------------------------------------
## 10. Quantitative summary (best available numbers)

| quantity | value | status and source |
|---|---|---|
| Wasmtime host<->guest call, nop | order 10-50 ns; within ~15 ns of the faster variant in C API benchmark | [fetched PR 3319] plus [verify] for absolute |
| Component-model call with strings/lists | hundreds of ns to few us, scales with bytes copied | [verify] |
| Epoch interruption overhead | ~10 percent | [fetched wasmtime docs] |
| Fuel overhead | "more than epochs" (commonly 2x or more) | [fetched qualitative; magnitude verify] |
| AOT instantiate (pooling + CoW) | microseconds (about 5 us quoted) | [fetched design PR 3697; figure verify] |
| Cranelift compile | ~tens of MB/s wasm; 1-5 MB module: 0.1-several s | [verify] |
| Deserialize .cwasm (mmap) | sub-millisecond to few ms | [verify] |
| Guest compute vs native | 1.1-2x | [verify, widely reported] |
| Tree-sitter wasm grammar parse vs native | 2-3x slower recollection; no published benchmark found | [verify] |
| pluggy hook dispatch | 0.65 us (0 impls), 0.97 us (1), 3.28 us (10), 4.23 us (10+wrapper); plain call 0.06 us | [measured] CPython 3.10.12, pluggy 1.6.0 |
| pytest startup, 1 trivial test | 0.15-0.29 s; 0.13 s with 3 builtins disabled; `import pytest` ~55 ms; bare python 20 ms | [measured] |
| pytest builtin plugins | 30 default, 5 essential, ~52 core hook names; 42 registered in a trivial run | [measured] |
| Oxlint no plugin / one JS plugin / ESLint / ESLint MT | 48 ms / 236 ms / 4,116 ms / 3,710 ms (vuejs/core, M3) | [fetched oxc.rs] |
| Nushell plugin encoding | json or msgpack; msgpack recommended for performance | [fetched] |
| Pipe IPC round trip | 5-20 us; process spawn 1-5 ms (native), 20 ms (python measured) | [verify]; [measured] for python |
| Interpreted plan vs handwritten Rust, whole run | hypothesis under 1.3x with a kind prefilter | [verify]; benchmark proposed in 8.2 |
| Free-threaded PyO3 rule host | works, "surprisingly good", GIL build "pointless" | [fetched PR 21415, qualitative] |

---------------------------------------------------------------------------
## 11. Lessons digest (cross-cutting)

1. The boundary is the cost. Oxlint with a single JS rule is 5x slower than none;
   Ruff's PyO3 experiment found per-node calls pointless; swc keeps breaking its
   ABI because it serializes the full AST. Batch per file or per rule.
2. Data and declarative first. The tools that stayed fast and safe (Ruff,
   Clippy) refused plugins; the ones that added plugins fast (Biome/Grit,
   ast-grep, Semgrep) chose declarative patterns executed by the host.
3. Typed, small, versioned plugin spec (pluggy hookspec, WIT world, dprint
   schema number); the host accepts old versions for a window (Zed).
4. Opt-in by explicit config and digest (ESLint flat config, ruff #283,
   dprint checksum, lockfiles), never auto-activation by install.
5. Capability declaration with deny-by-default; for lint, pure functions.
6. AOT cache keyed by digest plus engine fingerprint.
7. Std library as plugins on the same mechanism (pytest default_plugins; our
   built-in packs).
8. Authoring cost determines breadth (stack-graphs TSG: 3-4 languages in years;
   Semgrep pattern: hundreds of rules in months). Keep tier 2 authoring close to
   the target language.
9. Deterministic ordering with explicit priorities; pytest's LIFO plus
   tryfirst/trylast plus entry-point order is the cautionary tale.
10. Escape hatches exist everywhere (dprint process plugins, Zed language
    servers): wasm is not the end of the story; offer the bound-tool stage.

---------------------------------------------------------------------------
## 12. Recommendation: tiers

### Tier 0: compiled-in standard library (Rust)

- Contents: kernel, the `#[derive(Rule)]` families (DRIFT, COV, CYCLE, ...), the
  executor, loader, built-in data and declarative packs embedded.
- Mechanism: `inventory` registration; a `BuiltinPack` registry; everything the
  std library does goes through the public registration API (pytest lesson), so a
  CI test that registers one of the built-in rules from an out-of-crate test pack
  proves there is no back door.
- Repo-wide graph rules that need heavy algorithms (cycles, dead symbols, dup
  clone rungs): handwritten Rust or an in-process macro-Datalog (ascent/crepe)
  compiled into the binary, not loaded.

### Tier 1: data (atoms, detectors, vocabularies, claim templates, matrix-build excuse templates)

- Mechanism: the existing TOML pack format of packs.md, digest-pinned in the
  lockfile, loadable from URL or path, no code. Matrix-build excuse templates
  are data (a template with typed holes and a constraint on which cells it can
  excuse) validated by the kernel (CAP004 excused-but-used stays a kernel rule).
- Performance: lookup tables; vocabularies compiled into a hash map or
  Aho-Corasick/FST at load, cached by digest; startup cost negligible.
- Safety: nothing to sandbox; only schema validation (PACK005 unknown keys).
- Reason: this is where the most third-party contribution and the highest trust
  concern live (an atom or an excuse changes verdicts), and it needs no
  execution at all.

### Tier 2: declarative rules executed by the host

- Language rules: tree-sitter queries and gob-pattern patterns (already in
  rules.md). Combine per-language into one dispatch (kind-indexed).
- Universal rules over U: a small declarative predicate language over the 47
  queries (select nodes via query, filter via comparisons, aggregate counts,
  emit findings with a message template), compiled to a versioned PLAN IR.
  Deliberately not Turing complete and not a general Datalog in v1; if
  expressiveness demands it, add relational joins later as plan operators.
- One execution path: built-in declarative rules are compiled by build.rs into
  plan bytes included with `include_bytes!`; disk packs ship the same bytes
  (precompiled at `frob packs add`, CodeQL .qlx precedent) or source
  recompiled and cached by digest. `Rule` trait object per plan.
- Safety: pure data; deterministic; cacheable; bounded by operator budgets
  (max matches, max steps).
- Reason: evidence in sections 5 and 8: the fast tools do this, near-native speed
  is plausible, authoring cost is low, no sandbox needed.

### Tier 3: arbitrary-code rules and detectors (wasm components)

- Mechanism: wasmtime component model; WIT world `frob:rule/check@1.x`; the
  guest exports `check(batch) -> findings` for one file or one repo scope;
  the host provides U facts as a flat, versioned arena in guest memory (offsets,
  fixed layout, lazily read) and a minimal set of imports (query lookups by id).
- Bounded execution: epoch interruption (~10 percent cost) with per-file timeout;
  StoreLimits for memory; fuel in deterministic CI mode.
- Capabilities: deny by default, declared in the pack manifest, granted in the
  repo config and recorded in the lockfile; the default grant set is empty (pure).
  Findings are cached by pack digest only if the pack declares purity.
- Distribution: pack = manifest + .wasm (+ optional precompiled .cwasm per
  platform as a cache hint, never trusted without engine-fingerprint match and a
  digest check; AOT is recompiled locally by default). Signature optional,
  mandatory when `[trust] require_signed`.
- Performance expectation: guest compute 1.1-2x, crossing tens of ns, per-file
  batch, so tier 3 rules should be within 2-3x of a built-in for the same logic
  [verify with the benchmark of section 8.2]. Startup: precompile at install;
  load with `deserialize_file`; instantiate once per worker thread via
  `InstancePre`.
- Authoring: a `frob-plugin-sdk` crate with a derive macro mirroring
  `#[derive(Rule)]` and a `cargo component` template; a bytes-in/bytes-out
  fallback ABI (Typst/Extism style) for non-Rust authors [optional].
- Reason: the only mechanism that gives arbitrary code, sandboxing, portable
  artifacts and near-native speed together (section 2). Optional and off by
  default; most users never need it.

### Tier 4: language adapters

- Declarative first: tree-sitter grammar (native for the ~10 shipped languages,
  wasm via the tree-sitter `wasm` feature for the long tail) plus node-types.json
  coverage check plus a mapping file (query to U operators and role attributes)
  plus locals-style scope rules for binding; optional TSG-like description for
  precise binding on languages that merit it. Residual semantic computation goes
  through bound-tool stages (rules.md section 4) or a wasm adapter component
  exporting `derive_u(tree) -> u-terms`.
- Performance: native grammars at full speed; wasm grammars 2-3x [verify] on
  parse only, acceptable for the long tail; adapter mapping queries cost like any
  tier 2 rule.
- Reason: the adapter is the largest surface and authoring cost determines
  language breadth (stack-graphs lesson); declarative mapping plus coverage
  against node-types.json gives a falsifiable completeness check and a low
  entry cost; unmapped constructs become opaque, producing Unresolved not wrong
  answers (universal-model.md 4.6).

### What to reject, and why

1. Rust cdylib/dylib/abi_stable/stabby plugins: no stable ABI, UB, version
   lockstep, no sandbox, per-platform builds, supply-chain RCE (section 3).
   Revisit never; wasm covers the use case.
2. Embedded Python/JS/Lua interpreters as the primary rule host: per-node
   crossing is prohibitively slow (ruff PyO3 finding, Oxlint 5x), isolation weak,
   deployment heavy.
3. Out-of-process IPC for in-loop rules: per-call tens of us and spawn ms; keep
   it for external tools only (bound-tool stages, LSP-ish analyzers).
4. AST-as-ABI serialization (swc): the plugin ABI would change with every U
   revision. Plugins see the 47-query interface and a versioned flat arena.
5. Auto-discovery by installation (pytest11 entry points, flake8): replaced by
   lockfile opt-in.
6. A general Datalog (CodeQL/Souffle-style) as the v1 rule language: heavy,
   slow to author, toolchain or interpreter cost; reconsider for repo-scope
   rules later, compiled in (ascent/crepe) first.
7. Wasmer/wasm3 as hosts: wasmtime has the component model, WASI p2, and the
   Bytecode Alliance maintenance; wasm3 is an interpreter in maintenance mode
   (use wasmi if an interpreter is ever needed).
8. Per-node wasm hooks or per-node plugin callbacks of any kind.
9. Registration-order-dependent plugin ordering and global mutable plugin
   state: explicit priorities, deterministic tie-break.
10. A registry service in v1: git URL plus digest plus lockfile is enough;
    revisit at the point of third-party ecosystem demand.

### pytest-derived requirements folded into the design

- R1 Built-ins register through the public mechanism (CI-enforced).
- R2 Hook/spec set is small (<12), typed (WIT plus generated Rust trait), args by
  name, additive evolution only; breaking changes bump the world version and
  old worlds stay loadable for one release window.
- R3 Load-time validation of every plugin against the specs, with the plugin
  name in the error; `frob packs doctor`.
- R4 Directory-scoped local packs, with per-file versus per-run hooks declared
  and enforced (a per-run hook in a non-root local pack is a load error).
- R5 Explicit lockfile opt-in replaces entry-point discovery; `disable` list
  replaces `-p no:`; `frob packs trace` replaces `--trace-config`.
- R6 Deterministic ordering: explicit integer priority plus (pack name, digest)
  tie-break; claim hooks (firstresult analog) are first-class; wrapper analogs
  (timing, quarantine, ratchet) are host-side only.
- R7 Per-pack config schema validated with deny_unknown_fields; an unknown key
  names the pack.
- R8 Import-time cost lesson: load lazily. Parse manifests eagerly (cheap),
  deserialize plans and instantiate wasm only when a rule from that pack is
  applicable to a file in the run; show pack load time in `--timings`.
- R9 Override by nearest scope for vocabularies and detectors, visible in
  `frob packs show`.

### Open questions for the owner

1. Is a wasm tier required for v1, or can it ship at milestone 3 after tiers 0-2
   and 4-declarative? (Recommendation: design the WIT world and manifest in v1,
   ship the host after the plan executor.)
2. Which U predicate language syntax for tier 2 universal rules: TOML-embedded
   expressions, a pattern syntax like gob-pattern extended to U terms, or a tiny
   Datalog-like rule syntax compiled to plans?
3. Should AOT .cwasm artifacts ever be distributed, or always compiled locally
   (recommendation: always local, cache by digest; shipping native code
   artifacts reintroduces trust questions)?
4. Is a lint rule allowed to suppress or downgrade other rules' findings? If
   yes, plugins that do so need the strongest trust class.

### Benchmarks to run before committing (each under a day, none run here)

B1 wasmtime: nop call, call returning 100 findings via component model, per-file
batch, with epoch on and off; instantiate with and without pooling and
InstancePre; .cwasm deserialize time for a 2 MB component.
B2 tree-sitter: native versus wasm grammar parse of 1 MB and 10 KB files (JS or
Rust), cold and warm.
B3 plan interpreter versus handwritten versus tree-sitter Query versus wasm batch
for three representative predicates over a 5k-file corpus (section 8.2).
B4 rkyv versus postcard plan load, validated and unchecked.

## Source index (plain URLs; all fetched this session unless marked)

- https://docs.astral.sh/ruff/faq/ and https://github.com/astral-sh/ruff/blob/main/docs/faq.md
- https://github.com/astral-sh/ruff/issues/283
- https://github.com/astral-sh/ruff/pull/21415
- https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html
- https://github.com/bytecodealliance/wasmtime/blob/main/docs/examples-pre-compiling-wasm.md
- https://github.com/bytecodealliance/wasmtime/blob/main/docs/examples-interrupting-wasm.md
- https://github.com/bytecodealliance/wasmtime/pull/3319
- https://github.com/bytecodealliance/wasmtime/pull/3691
- https://github.com/bytecodealliance/wasmtime/pull/3697
- https://github.com/swc-project/swc/pull/11198 and pull/11100, pull/10840 (titles only), issues/2175
- https://github.com/trailofbits/dylint (README)
- https://www.nushell.sh/contributor-book/plugin_protocol_reference.html
- https://github.com/nushell/nushell/blob/main/crates/nu-plugin/src/lib.rs
- https://github.com/tree-sitter/tree-sitter/blob/master/lib/binding_rust/README.md
- https://github.com/tree-sitter/tree-sitter/blob/master/lib/Cargo.toml
- https://github.com/tree-sitter/tree-sitter/blob/master/lib/binding_web/README.md
- https://biomejs.dev/linter/plugins/ (downloaded; extract failed, claims [verify])
- pluggy: https://pluggy.readthedocs.io/ (local installed pluggy 1.6.0 and pytest 9.0.3 used for measurement; docs file downloaded from https://raw.githubusercontent.com/pytest-dev/pluggy/main/docs/index.rst but not quoted)
- Not fetched, from background knowledge: dprint (https://dprint.dev/plugins/), Zed (https://zed.dev/docs/extensions), Typst (https://typst.app/docs/reference/foundations/plugin/), Extism (https://extism.org), Lapce (https://lapce.dev), Spin (https://developer.fermyon.com/spin), CodeQL (https://docs.github.com/en/code-security/codeql-cli), Semgrep (https://semgrep.dev/docs), ast-grep (https://ast-grep.github.io), Souffle (https://souffle-lang.github.io), stack-graphs (https://github.com/github/stack-graphs), OPA (https://www.openpolicyagent.org/docs), ESLint (https://eslint.org/docs/latest/extend/plugins), abi_stable (https://docs.rs/abi_stable), stabby (https://docs.rs/stabby), sigstore (https://docs.sigstore.dev), Buf (https://buf.build/docs)
