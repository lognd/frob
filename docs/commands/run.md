# frob run / frob build

One declared home for a project's workflow commands: `frob.toml`'s
`[commands]` table, executed by <!-- frob:waive DOC006 reason="frob run/build dispatch through frob.__main__._dispatch and are not yet registered in _build_parser's subcommand tree; T-4811 wires them in, after which this waiver is removable" -->`frob run <name>`. <!-- frob:waive DOC006 reason="frob run/build dispatch through frob.__main__._dispatch and are not yet registered in _build_parser's subcommand tree; T-4811 wires them in, after which this waiver is removable" -->`frob build` is a thin
alias that always resolves the `build` entry, so it never carries build
logic of its own.

## Public API

<!-- frob:describes src/frob/app/run_runner.py::run -->
<!-- frob:describes src/frob/app/run_runner.py::run_build -->
<!-- frob:describes src/frob/app/run_runner.py::load_commands -->
<!-- frob:waive DOC004 reason="frob run/build dispatch through frob.__main__._dispatch and are not yet registered in _build_parser's subcommand tree; T-4811 wires them in, after which this waiver is removable" -->
```bash
frob run test              # run the `test` entry (or frob's native default)
frob run check              # run the `check` entry
frob run check --dry-run    # print the resolved sequence, run nothing
frob build                  # delegate to the `build` entry
frob build --dry-run        # print build's resolved sequence, run nothing
```

## Commands table

A name maps to EITHER a single shell-free command or an ordered sequence
of steps:

```toml
[commands]
fmt = ["ruff", "format", "."]
lint = ["ruff", "check", "."]
test = ["pytest", "-q"]
check = ["fmt", "lint", "test"]
```

`fmt`/`lint`/`test` are each a single literal argv (no shell involved --
each array element is one argv token, exactly as `subprocess.run` would
take it). `check` composes the other three by name: a bare array of
strings is read as a sequence of entry-name references when every one of
its elements matches a declared entry; otherwise it is one literal argv.
A step can also be written as a nested array to mix a literal command
into a sequence directly, e.g. `check = [["ruff", "check", "."], "test"]`.

## Native defaults

`test`, `lint`, `format`, and `check` resolve to frob's own native verbs
when a project declares no `[commands]` entry for them at all, so a
Python project using frob's own tooling need declare nothing. `build` has
no native fallback: a project with no `build` entry gets a clear error
naming that it is undeclared, not a silent no-op.

## Execution semantics

- steps run in declared order; the first non-zero exit stops the whole
  run, and the error names that step's index and its command;
- every step is logged with its index, its command, and its duration;
- `--dry-run` prints the fully resolved sequence and runs nothing --
  no subprocess is spawned.

## Cycle refusal

An entry that references itself, directly or through another entry, is
refused when `frob.toml` is loaded -- before <!-- frob:waive DOC006 reason="frob run/build dispatch through frob.__main__._dispatch and are not yet registered in _build_parser's subcommand tree; T-4811 wires them in, after which this waiver is removable" -->`frob run`/<!-- frob:waive DOC006 reason="frob run/build dispatch through frob.__main__._dispatch and are not yet registered in _build_parser's subcommand tree; T-4811 wires them in, after which this waiver is removable" -->`frob build` ever
executes anything -- and the error names the full reference path
(e.g. `a -> b -> a`).

## Error types

<!-- frob:describes src/frob/app/run_runner.py::RunError -->
<!-- frob:describes src/frob/policy/_models.py::CommandsError -->
`CommandsError` covers loading/resolving `[commands]` (a malformed entry,
or a reference cycle); `RunError` covers execution (an unknown command
name, or a step that exited non-zero).

## Relationship to derived wrappers

Generated wrapper targets (a scaffolded project's `Makefile`/`make.bat`,
T-4760) only ever invoke `frob run <name>`; they never expand a sequence
inline, so a sequence has exactly one home: the `[commands]` table.
