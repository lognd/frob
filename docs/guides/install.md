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
