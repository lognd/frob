# frob format

`ruff check --fix` + `ruff format`, write mode: the frob-native replacement
for the Makefile's `format`/`lint-fix`/`all` targets (T-2251).

## Usage

<!-- frob:describes src/frob/app/pyfmt_runner.py::run -->
```bash
frob format                        # ruff check --fix (all rules) + ruff format, cwd
frob format src/                   # same, over a specific path
frob format --select-imports-only  # ruff check --fix --select I (import sort only) + ruff format
```

Both stages run write mode -- files are rewritten in place, never previewed.
Exits nonzero if either stage fails.

## Relationship to `frob check --fix-ruff` and `frob fmt`

The default (no-flag) path delegates to
`frob.check._python._run_ruff_autofix` (T-2320/T-2252), the same primitive
`frob check --fix-ruff` runs -- `frob format` (no flags) and `frob check
--fix-ruff` do the identical full-rule-set write pass. `frob format` exists
as its own top-level verb because the Makefile's `format:`/`lint-fix:`/
`all:` targets need a plain, memorable one-word replacement, and because
`format:`'s narrower `--select I` scope (`--select-imports-only`) has no
equivalent on `frob check` today.

`frob fmt` (a different, pre-existing subcommand, T-0441) canonicalizes
`frob:` directive comment line-wrapping -- it has nothing to do with Python
source formatting. Do not confuse the two.

## Makefile target mapping (T-2244)

| Makefile target | frob equivalent |
|---|---|
| `format` (`ruff check --fix --select I` + `ruff format`) | `frob format --select-imports-only` |
| `lint-fix` (`ruff check --fix` [all rules] + `ruff format`) | `frob format` |
| `all` (core + format + typecheck) | `frob natives build && frob format --select-imports-only && frob check --only ty` |
