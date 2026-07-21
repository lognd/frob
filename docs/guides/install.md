<!-- frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug); file is docs/** in intent" -->

# Installing frob (T-0133)

frob ships as one pure-Python package (`frob`) plus two optional Rust/PyO3
native extensions built with maturin: `frob-core` (smart-dup's R3+ rungs --
tree-edit-distance and beyond) and `strata-core` (the real parser for
`.strata` design files, used by `frob.lang`, `frob.graph`, `frob check`,
`frob outline`, `frob xref`, and friends). Neither extension is a hard
dependency of `frob` -- every code path that needs one degrades to a typed
`Result.Err` (never a crash, never an exception) when it is missing. This is
the contract T-0133 hardens: a bare `uv tool install frob` must always work.

## Bare install (no natives)

```bash
uv tool install frob
```

Gets you: the full CLI, tickets, gates, doc-drift checking, xref, outline,
graph build, and Python/TypeScript/Rust/C/C++ parsing -- everything except
the two features above. `.strata` files are still *listed* by
`supported_extensions()` (the graph still sees they exist -- they are not
silently invisible to coverage or xref) but each one fails to parse with
`LangError.NativeParserUnavailable`, logged once at debug level per file,
not warning-spam. `frob-core`-only dup rungs (R3+) turn off; R1/R2 and every
other `frob.dup` rung are pure Python and still run.

`ruff` and `ty` (the tools `frob check`'s Python-language stage shells out
to) are real `[project]` dependencies (T-0142), so a bare install is fully
functional for Python repos out of the box -- no separate `pip install
ruff ty` step needed. Should any check-stage tool still be missing from
`PATH` (a non-Python stage's `cargo`/`clang-tidy`/`npx`, or a `ruff`/`ty`
shadowed by a broken shim), the corresponding stage reports a typed
failing `ToolResult` ("tool unavailable: `<name>` -- install it or use
`make install-tool`") instead of crashing -- a missing tool is always a
loud, visible failure in the `frob check` summary, never a silent skip.

## Full install (with natives)

Native extensions have no published wheels (no PyPI project -- they are
local maturin path packages under `frob-core/` and `strata-core/` in this
repo, not standalone publishable artifacts yet; see "why not a pip extra"
below). To get them into a `uv tool install`'d environment, build from
source and install them as `--with` deps of the same tool venv:

```bash
git clone https://github.com/lognd/frob
cd frob
make install-tool
```

`make install-tool` runs:

```bash
uv tool install --force --reinstall . --with ./strata-core --with ./frob-core
```

Requires a Rust toolchain (`cargo`) on `PATH` -- `uv` invokes maturin's
PEP 517 build backend for each local path dependency, which needs `cargo`
to compile the extension. If `cargo` is absent, this fails loudly (unlike
`make core`'s best-effort skip for the dev venv) since the whole point of
running this target is to get the natives.

## Editable dev install

```bash
pip install -e .        # or: make install
make core                # builds+installs frob-core and strata-core in-place
```

`make core` is best-effort: it skips (with a warning, not a failure) when
`cargo` is not on `PATH`, since most `frob.dup`/`frob.lang` functionality
does not need it.

## Why not `pip install "frob[strata]"`?

`[project.optional-dependencies]` extras resolve through the same index
`pip`/`uv` would install `frob` from -- they need a real published
distribution (a wheel on PyPI, or at minimum a VCS/path URL baked into the
extra itself, which breaks the moment the extra is installed outside this
repo's checkout). `frob-core` and `strata-core` are not published anywhere;
declaring them as an extra with a local relative path (`frob-core @
file://./frob-core`) only resolves when installing from a checkout at that
exact relative location, which silently breaks for anyone who does
`pip install frob` from PyPI. `--with <path>` on `uv tool install` sidesteps
this because the path is supplied at install time by whoever is running the
command, from whatever checkout they have on disk -- it is a valid install
mechanism today, not a placeholder for something better.

Publishing `frob-core`/`strata-core` as real wheels to PyPI (one abi3 wheel
per supported platform via `maturin build --release`, then a normal
`[project.optional-dependencies]` extra pinned to the published version) is
the correct long-term fix and is explicitly out of scope for T-0133 -- filed
as follow-up work, not attempted here.

## CI contract

`.github/workflows/ci.yml` has a dedicated job that installs the bare wheel
(no natives) into a clean venv and runs `frob --help` plus `frob check`
against a tiny fixture repo, to catch any future import-time regression of
the standalone binary before it ships (the T-0077 hard-import bug T-0133
fixes was exactly this: `import strata_core` at module scope in
`frob.lang._walk_strata`, uncaught until someone ran the standalone tool
outside a dev checkout).

## Loud failure when `.strata` is used without natives (T-0316)

A repo that has never opted into `design/**` (no `.strata` files) is
completely unaffected by a missing `strata_core` -- `frob.gates.sys_gate`
never even imports `frob.strata` for such a repo (T-0135's opt-in check
runs first). But a repo that DOES have `.strata` files under its
`[strata].design_dir` and is missing the native extension must never look
like a clean pass. Two surfaces enforce this:

- `frob check`: `sys_gate` reports the load failure as its own `SYS004`
  ERROR-severity `Violation` naming the file and the exact
  `NativeExtensionUnavailable` message (`src/frob/gates/__init__.py`'s
  `_sys004`) -- this fails the `gates` tool and the overall `frob check`
  exit code, it does not silently degrade to a 0-violation pass.
- `frob sys audit` / `frob sys plan` / `frob sys doc`: `_load_audit_model`
  (and its `plan`/`doc` siblings in `src/frob/app/sys_runner.py`) log the
  same typed error per failing design file and `sys.exit(1)` -- they never
  print a report and exit 0 on a load failure.

Both paths are covered end-to-end (a real subprocess `python -m frob ...`
invocation, not just a monkeypatched unit test) by
`tests/system/test_cli_native_missing.py`, which shadows the real
`strata_core` extension via `PYTHONPATH` with
`tests/fixtures/fake_no_native/strata_core.py` (a module whose only body is
`raise ImportError(...)`) to reproduce exactly what a natives-less `uv tool
install frob` sees. It asserts: (1) a repo with `.strata` under `design/`
exits nonzero from both `frob check` and `frob sys audit` and names
`SYS004`/`NativeExtensionUnavailable` in the output; (2) a repo with no
`design/` dir at all exits 0 unaffected -- the T-0135 opt-in guarantee, not
just the loud-failure one.

## Detecting a stripped native install (the "reinstall wiped my wheel"
gotcha)

`uv tool install --force --reinstall . --with ./strata-core --with
./frob-core` (`make install-tool`) is a one-shot install: the `--with`
local-path deps are resolved and installed alongside `frob` into that tool
venv AT THAT MOMENT. A later plain `uv tool upgrade frob` or `uv tool
install --force --reinstall frob` (no `--with` flags) reinstalls only the
pure-Python `frob` distribution into the same venv and does NOT re-add the
`--with` extras -- it silently strips `strata_core`/`frob_core` back out,
regressing to the bare-install posture with no warning at install time.
This is the exact failure mode the T-0316 FROBLEMS report describes
("bit mid-campaign when a reinstall wiped the manually-added wheel").

Until `frob-core`/`strata-core` are published as real wheels (see "Why not
`pip install \"frob[strata]\"`?" above -- still out of scope, tracked as a
follow-up ticket), there is no install-time guard against this: `uv tool
upgrade`/`uv tool install --force --reinstall` on a bare `frob` spec is a
valid way to ask for exactly that (upgrade `frob`, natives excluded), so
frob cannot distinguish "the user wants natives gone" from "the user forgot
`--with`" at install time. The check that CAN and does catch it is the
loud-failure guarantee above: the next `frob check`/`frob sys audit` run
against a repo with `.strata` files fails immediately with a named
`SYS004`/`NativeExtensionUnavailable`, rather than silently going quiet --
treat that failure as the signal to re-run `make install-tool`, not a
regression to chase in application code.

## `frob doctor`: native-extension diagnosis (T-0319)

To check natives are present without waiting to hit the `SYS004`/dup gate
above, run:

<!-- frob:describes src/frob/__main__.py::_add_doctor_parser -->
```bash
frob doctor
```

This imports `frob_core` and `strata_core` and reports each one's
availability (and version, when the module exposes one). When either is
missing it prints the exact remediation -- `make core` (build in-place) or
`make install-tool` (reinstall the CLI with natives bundled) -- and exits
1, so it is scriptable as a preflight check (e.g. in CI or a postinstall
hook), not just a human-readable report. `frob doctor --json` emits the
same `DoctorReport` as machine-readable JSON. This supersedes the manual

```bash
python3 -c "import strata_core, frob_core" \
  && echo "natives present" || echo "natives MISSING -- run: make install-tool"
```

check as the first-class CLI surface for the same diagnosis (T-0317).
