# grimble user guide: model files, check, fmt and the first rules

Status: current
Owner: grimble
Decisions: none
Audience: user

Tutorial (Diataxis: learning). You will describe a small program as a model
(nodes, a flow between them, a capability grant), run `grimble check` against
it, read the findings and fix them. It takes about ten minutes and needs `git`
and `grimble` ([install](../../README.md#install)). The example code is Rust;
grimble also reads Python, TypeScript, C#, CSS and HTML.

Every command block below marked `sh` is run against a real repository by the
test `crates/frob/tests/it/doc_commands.rs`, so it stays true.

## Words you need

- **Model**: a tree of `.grmb` files that says what the system is meant to be:
  who owns which files, what may flow where, which capabilities a part may
  use. grimble checks the repository against it.
- **Node**: a part of the system. It `owns` files or symbols by glob, has a
  trust level (`trusted` below) and `may` grants capability atoms such as
  `fs.read`. Anything not granted is denied.
- **Flow**: data moving from one node to another, with a `label` (here
  `Secret` or `Public`) and a `rate`. A node's `clearance` is the highest label
  it may hold.
- **Boundary**: a point where a label changes, for example `declassify`.
- **Rule family**: rules share an id prefix (`MDL`, `SYS`, `CAP`, `FLOW`, ...).
  `--only` selects by family or by single id.

## 1. Make a repository and initialise grimble

```sh
git init -b main
mkdir src design
printf '/// Read the notes file.\npub fn run() -> String {\n    std::fs::read_to_string("notes.txt").unwrap_or_default()\n}\n' > src/lib.rs
git add -A && git commit -m "seed"
grimble init
git add -A && git commit -m "chore: grimble init"
```

`init` is safe to repeat. It writes `grimble.toml` with every knob at its
default, ignores `.grimble/` and seeds `design/model.grmb`:

```text
grimble = "2";
module model;
```

The first line is the version header, the second names the module. The
`[grimble] models` key in `grimble.toml` lists the root model files (default
`design/model.grmb`); other `.grmb` files are loaded only when a root
`include`s them (MDL019 names the ones nothing reaches). `grimble doctor
--text` shows how each model file parsed and the state of `grimble.toml`.

## 2. First check

```sh
grimble check --text
```

An empty model passes with nothing to report. `check` prints the findings and
exits 1 when any is at or above `fail_on` (default `error`; override with
`--fail-on error|warn|advisory|none`). Add `--text` for a human view, or pipe
the output for the JSON envelope.

## 3. Write a model

Replace the model with two nodes and a flow. It is written compactly on
purpose:

```sh
cat > design/model.grmb <<'EOF'
grimble = "2";
module model;
node app : trusted {
  owns "src/**";
}
node store : trusted {
  clearance Public;
  owns "design/**";
  owns "grimble.toml";
  owns ".gitignore";
}
flow save : app -> store {
  label Secret;
  rate 1 req/s;
}
EOF
grimble fmt --check || test $? -eq 1
grimble fmt
grimble fmt --check
```

`grimble fmt` rewrites every `.grmb` file in its canonical (alpha-normal)
form; `--check` only reports and exits 1 on a difference, which is what you
run in CI. Here the first `--check` reports the file, `fmt` fixes it, and the
second `--check` is clean.

## 4. Read the findings

```sh
grimble check --text || test $? -eq 1
```

Two things come back. A `FLOW001` error: the flow `save` carries `Secret`
into `store`, whose clearance is `Public`, and nothing declassifies it. And a
`CAP001` error: `src/lib.rs` reads a file, and `app` has no `fs.read` grant.
Findings print as `path:line:col: severity RULE message`; a finding with no
single source line prints without a location.

Use `--only` to look at one family or one id while you work; each rule has a
page under [../reference/rules/](../reference/rules/):

```sh
grimble check --text --only FLOW || test $? -eq 1
grimble check --text --only CAP001 || test $? -eq 1
grimble check --text --only MDL
```

## 5. Fix them

The data really is allowed to leave: declare a boundary that lowers the label,
and grant the capability the code uses.

```sh
cat > design/model.grmb <<'EOF'
grimble = "2";
module model;

node app : trusted {
  owns "src/**";
  may fs.read;
}

node store : trusted {
  clearance Public;
  owns "design/**";
  owns "grimble.toml";
  owns ".gitignore";
}

flow save : app -> store {
  label Secret;
  rate 1 req/s;
}

boundary scrub declassify save : Secret -> Public;
EOF
grimble fmt
grimble check --text
git add -A && git commit -m "feat: model the app and store"
```

The check now exits 0. What remains is a `SYS004` warning (the flow binds no
code on either end yet) and an unresolved `SYS013` edge (a call grimble could
not place between owners); neither fails the gate unless you raise `fail_on`. `[grimble] strict = true`
promotes SYS001 and SYS005 to errors.

## The rule families an adopter turns on first

Everything below runs in a plain `grimble check`; the knobs are in
[../reference/config.md](../reference/config.md) under `[grimble]`.

| Family | What it catches | Start here |
|---|---|---|
| `MDL` | The model itself is malformed: syntax errors, bad references (MDL006), a missing include (MDL002), unreachable files (MDL019), no root (MDL021). | Always on; fix these first. |
| `SYS` | Model and code disagree: files nobody owns (SYS001), a binding that matches no code (SYS004), public units no node owns (SYS005, needs `[grimble] modeled`). | `strict = true` turns SYS001 and SYS005 into errors. |
| `CAP` | Code uses a capability its node does not grant (CAP001) or a node grants one nothing uses (CAP002). | Add `may ATOM;` to the node, or remove the use. |
| `FLOW` | A label above the destination's clearance (FLOW001), an endorse missing on a flow into a higher-trust node (FLOW002), no rate on a foreign flow (FLOW003). | Add a `boundary`, change a `clearance`, or add a `rate`. |
| `CLAIM` | A `claim` (`noflow`, `reach`) that the declared flows refute (CLAIM001). | Write claims for the guarantees you care about. |
| `CYCLE`, `LARGE`, `DEAD` | Architecture: crates that import each other, functions longer than `large_lines` (default 400), unreferenced private functions. | Tune `[grimble] large_lines`; 0 turns LARGE001 off. DUP001 (copied blocks) is tuned by `dup_min_tokens` (50) and `dup_min_occurrences` (3). |
| `PATH` | Code that hard-codes host paths or joins paths with a literal separator. | Pass paths as their own arguments. |

Each rule has a generated page under
[../reference/rules/](../reference/rules/) with a firing and a clean example.

## When something is refused

A usage error such as `E-CHECK-ONLY` names the bad `--only` value; an unknown
word is neither a family nor an id. `grimble doctor --text` is the first thing
to run when `check` says a model file did not parse.

## Where next

- `grimble --help` and `grimble check --help`: every verb and flag.
- [../reference/config.md](../reference/config.md): every `grimble.toml` key.
- [../design/grmb-spec.md](../design/grmb-spec.md): the full `.grmb` language.
