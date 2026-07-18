# Test runner entries

<!-- frob:describes src/frob/testing/_models.py::RunnerSpec -->

## What it is and where it lives

`frob test` selects touched tests from the obligation graph and dispatches
each to a per-language runner. The registry is the `[[test.runner]]` table
in `frob.toml`, parsed into `RunnerSpec` (`src/frob/testing/_models.py`)
by `load_runners` (`src/frob/testing/_runners.py`). Full worked examples
(including the T-0128 multi-runner-per-language, `cwd`-scoped routing
case) already live in `docs/modules/testing.md#runner-registry-frobtoml-testrunner`
-- this guide is a thin pointer into that existing, actively-maintained
reference rather than a duplicate.

## Add-an-entry recipe (new runner)

1. Add a `[[test.runner]]` table to `frob.toml`:
   ```toml
   [[test.runner]]
   language = "rust"
   command = "cargo test"
   cwd = "strata-core"    # one crate per runner entry when multiple crates exist
   ```
2. If the language already has a runner and the new one is scoped to a
   different `cwd` (a second crate, a monorepo subpackage), add it as a
   SECOND `[[test.runner]]` entry for that language rather than editing
   the existing one -- `frob test` routes by `(language, cwd)` pair.
3. No code change is required for a new `[[test.runner]]` entry itself --
   `load_runners` is fully data-driven.

## Drift-locks that fire

- `NoRunner`: a language with selected (touched) tests but zero matching
  runner entries is a hard error, not a silent skip.
- `UnroutedItem`: a touched test file's directory does not unambiguously
  match exactly one runner's `cwd` scope (ambiguous multi-runner routing)
  is also a hard error.
- Both are runtime `frob test` failures, not `frob check` gate rules --
  there is no static drift-lock catching a missing runner before you
  actually run `frob test` against a diff that touches that language.

## Worked example

See `docs/modules/testing.md#runner-registry-frobtoml-testrunner`
directly: it walks the exact T-0128 diff that added a second Rust runner
scoped to `strata-core` alongside the top-level Rust runner.

## Common mistakes

- Forgetting `cwd` when a repo has more than one crate/package per
  language -- `frob test` runs the command from the repo root by default,
  so a runner with no `cwd` set against a nested crate fails with the
  underlying tool's own "no manifest found" error, not a frob-level
  message.
- Adding a runner for a language with no touched-test selection support in
  `frob.lang` yet -- `frob test` can dispatch to any shell command, but
  the touched-set SELECTION step (which tests changed) still needs a
  `frob.lang` walker for that language; see
  `docs/guides/extending/language-grammar-handlers.md`.

## See also

- `docs/modules/testing.md` -- full runner registry reference, selection
  algorithm, and worktree-correct git semantics.
