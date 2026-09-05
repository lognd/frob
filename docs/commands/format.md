# frob format

The consolidated formatting verb (T-3906): `--code` runs `ruff check --fix`
+ `ruff format` (T-2251, the frob-native replacement for the Makefile's
`format`/`lint-fix`/`all` targets), `--directives` runs the `frob:`
directive comment canonical-form pass (T-0441, formerly the standalone
`frob fmt` subcommand). Neither flag given runs both.

`frob fmt` still works as a DEPRECATED alias for frob format --directives
(sunset 2026-12-01, ticket T-3911) -- see "Relationship to `frob fmt`"
below.

## Usage

<!-- frob:describes src/frob/app/pyfmt_runner.py::run -->
```bash
frob format                        # both halves, write mode, cwd
frob format src/ tests/            # same, over specific paths (T-3312: a list)
frob format --code                 # ruff only: check --fix (all rules) + ruff format
frob format --directives           # frob: directive canonicalization only
frob format --check                # preview only, for whichever half(ves) ran; exits 1 if anything would change
frob format --code --select-imports-only  # ruff check --fix --select I (import sort only) + ruff format
```

Write mode (the default) rewrites files in place. `--check` (T-3906: new --
previously only the directive half had this) previews without writing and
exits nonzero if anything is non-canonical/unformatted, for whichever
half(ves) ran. `--json` emits a JSON report instead of the human-readable
one.

## Relationship to `frob check --fix-ruff` and `frob fmt`

The code half's default (no `--select-imports-only`) path delegates to
`frob.check._python._run_ruff_autofix`/`_run_ruff` (T-2320/T-2252), the same
primitives `frob check --fix-ruff` runs -- frob format --code (no other
flags) and `frob check --fix-ruff` do the identical full-rule-set write
pass. `frob format` exists as its own top-level verb because the Makefile's
`format:`/`lint-fix:`/`all:` targets need a plain, memorable one-word
replacement, and because `format:`'s narrower `--select I` scope
(`--select-imports-only`) has no equivalent on `frob check` today.

`frob fmt` (T-0441) used to be a separate subcommand for the directive half
and was, confusingly, the SAME WORD as `frob format` for a DIFFERENT
operation -- and only `fmt` had `--check`. T-3906 folded it into this verb
as `--directives`, following the `explore`/`quality`/`design`/`ops`
consolidation precedent (T-1238/T-1567/T-1568/T-1569): the group keeps
every member usable standalone (`--code`/`--directives`), and `frob fmt`
itself keeps working, unchanged, as a deprecated alias for frob format
--directives through its sunset window (2026-12-01, ticket T-3911) --
every existing invocation, script, and remedy string naming `frob fmt`
keeps working until then.

## Makefile target mapping (T-2244, T-3906)

`format:`/`lint-fix:` pass `--code` explicitly to keep their
pre-consolidation ruff-only scope -- without it, `frob format` also
canonicalizes `frob:` directive comments.

| Makefile target | frob equivalent |
|---|---|
| `format` (`ruff check --fix --select I` + `ruff format`) | frob format --code --select-imports-only |
| `lint-fix` (`ruff check --fix` [all rules] + `ruff format`) | frob format --code |
| `all` (core + format + typecheck) | `frob natives build && frob format --code --select-imports-only && frob check --only ty` |
