# ESTATE rollout: the Makefile core one-line native-build shim

T-1031, the "estate rollout via fleet at close" follow-up named in
T-0735's user directive as part of the natives-build epic (T-0732's
per-repo `CARGO_TARGET_DIR`/`maturin develop` drift, T-0864's landed
`frob natives build` subcommand, T-0865's landed scaffold template +
drift check). This is the per-repo recipe an agent (or a human) follows
to convert a sibling repo's Makefile native-extension build step to the
one-line shim, and the record of what this repo did on 2026-07-28 to
kick that off across the fleet -- mirroring
`docs/guides/estate-capability-migration.md`'s T-1071 shape exactly (a
sibling-repo rollout this repo cannot perform directly, routed instead
via `frob fleet route`, T-0573).

This repo (`frob`) cannot edit sibling repos directly -- worktree agents
here have no write access outside this clone's own tree. The deliverable
from this ticket is entirely FROB-SIDE: the routed tickets landed via
`frob fleet route`, which writes straight into the target repo's own
ledger, plus this recipe so whichever agent picks up each routed ticket
does the actual Makefile/`frob.toml` edit consistently.

## Why this migration exists

Before T-0864/T-0865, a repo building a Rust/pyo3 native extension had no
shared convention for the "build it into the venv" step: each repo
hand-rolled its own `uv run maturin develop [--uv] [--release]` call
directly inside an `install`/`build`/`dev` Makefile target, and any
`CARGO_TARGET_DIR` sharing (to avoid N independent multi-minute cold
Rust builds across N worktrees of the same clone) was reinvented, or not
done at all, per repo -- the exact T-0732 drift class this epic exists
to retire. `frob natives build` (this repo's own subcommand) centralizes
that: it reads a repo's own `frob.toml` `[[native]]` entries, is
best-effort when the Rust toolchain is absent, and owns the shared
git-common-dir-keyed `CARGO_TARGET_DIR` mechanism itself, so a repo's
Makefile only ever needs the one-line
`# frob:managed-block BEGIN makefile-core-shim ... END`-wrapped `core:`
target `frob scaffold apply` installs -- no repo hand-rolls the
maturin/`CARGO_TARGET_DIR` logic itself once this lands.

This repo itself is already compliant, verified at T-0735's close: this
repo's own `Makefile` `core:` target is exactly the one-line shim
(`uv run frob natives build`), scaffold-managed.

## Per-repo recipe

1. Confirm the sibling repo actually builds a Rust/pyo3 Python native
   extension at all (`Cargo.toml` present AND `pyo3`/`maturin` referenced
   from its `pyproject.toml`/Makefile) -- a repo with no native extension
   (nothing to build into the venv) or a NON-Python native target (e.g. a
   `wasm-bindgen` WebAssembly crate, a different toolchain entirely) has
   nothing to route here; leave it untouched.
2. Add a `[[native]]` entry to that repo's own `frob.toml` for each
   extension currently built by hand (crate name, module name -- mirror
   this repo's own `frob.toml` `[[native]]` shape as a reference).
3. Run `frob scaffold apply` in that repo to install/update the managed
   `core:` Makefile target (creates the
   `# frob:managed-block BEGIN makefile-core-shim ... END` block reading
   `uv run frob natives build`, same shape as this repo's own).
4. Point wherever that repo's `install`/`build`/`dev` targets currently
   call `maturin develop` by hand at the new `core:` target instead,
   removing the direct maturin/`CARGO_TARGET_DIR`-juggling logic those
   targets used to own.
5. Run `frob doctor` in that repo to confirm the scaffold is current and
   `frob natives build` (via the new `core:` target) still builds the
   extension(s) cleanly.
6. Commit referencing the routed ticket's id, no separate write-up
   needed beyond that ticket's own Done report.

## 2026-07-28 fleet sweep (T-1031)

Every sibling in `fleet.toml` was checked for a `Cargo.toml` building a
Rust/pyo3 Python native extension with a hand-rolled `maturin develop`
call in its Makefile. Six repos (`graphite`, `typani`, `lograder`,
`aprog-public`, `aprog-private`, `logand.app`) have no such extension --
`logand.app`'s one `Cargo.toml` (`wasm-ascii/`) targets `wasm-bindgen`
(WebAssembly), a different toolchain entirely, not a Python native this
shim builds -- nothing to route, left untouched. The other two
(`lithos`, `feldspar`) both hand-roll `uv run maturin develop [--uv]`
directly inside their own `install`/`build` targets and have no
`[[native]]` entry in their own `frob.toml` yet, and each got a routed
ticket via `frob fleet route` (T-0573), landing directly in that repo's
own `tickets.md`, scoped to `Makefile`/`frob.toml`, kind `docs` (a
build-plumbing convention change, not new capability), body pointing
back at this guide's per-repo recipe above:

| Sibling | Routed ticket (filed 2026-07-28, kind `docs`, scope `Makefile`+`frob.toml`) | Hand-rolled maturin calls found |
|---|---|---|
| lithos | T-0077 | `install`, `dev` targets (`uv run maturin develop --uv`, `--watch`), `build` (`maturin build --release`) |
| feldspar | T-0027 | `install`, `install-regolith`, `build` targets (`uv run maturin develop`) |

Ticket ids are as returned by `frob fleet route` (`fleet: routed T-XXXX
into <repo>`) at call time -- they are that sibling's own ids, in that
sibling's own numbering space, unrelated to this repo's own ticket ids.
Each sibling's own `tickets.md` is the source of truth for the ticket's
current state going forward; this table is a point-in-time record of
what was routed and why, not a live status mirror.

## Not done here (explicitly deferred, not silently dropped)

`lithos`'s `build`/`fuzz`/`bench`/`test-rs`/`clean` targets exercise the
Rust workspace directly (`cargo build --release`, `cargo bench`, ...)
independent of the venv-facing `maturin develop` step this shim replaces
-- those are a different concern (direct cargo workflows, not "build the
extension into a venv for Python to import") and are not part of this
rollout; the routed ticket's scope is deliberately narrow to the
`install`/`dev`/`build`-target maturin calls and the new
`[[native]]`/`core:` wiring, not a wholesale Makefile rewrite.
