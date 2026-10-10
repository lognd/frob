# Keep the ledger on its own branch

How-to (Diataxis: task). By default frob commits ledger events to your code
branch, so every ticket write is a commit there. With the ticket branch the
ledger lives on a separate orphan branch, `frob-tickets`: ledger writes never
touch any checkout's index or work tree, and code branches stay code-only (no
ledger-only commits, no ticket-tree merge conflicts on pull requests). The
design is in [../design/mirror.md](../design/mirror.md) section 1.

Every `sh` block below is run against a real repository by
`crates/frob/tests/doc_commands.rs`.

## Set it up

Start from a repository where `frob init` has run and the config is committed:

```sh
mkdir demo && cd demo
git init -b main
mkdir src
printf '[package]\nname = "calc"\nversion = "0.1.0"\nedition = "2021"\n' > Cargo.toml
printf 'pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n' > src/lib.rs
printf 'target/\n.frob/\n' > .gitignore
git add -A && git commit -m "init"
frob init
git add -A && git commit -m "chore: frob init"
```

Switch the ledger to the orphan branch. `ref_mode = "orphan"` means "write the
ledger to the branch named by `[tickets] branch` (default `frob-tickets`)";
`[tickets] ref` stays your code base branch, the one `frob work` branches from
and `frob land` advances:

```sh
sed 's/ref_mode = "trunk"/ref_mode = "orphan"/' frob.toml > frob.toml.new && mv frob.toml.new frob.toml
frob ticket branch init
git add -A && git commit -m "chore: ledger on the ticket branch"
```

`ticket branch init` creates the root commit of `frob-tickets` through
plumbing, so your checkout is untouched. It also commits the branch's
`.gitattributes`, which routes ticket files to the frob merge driver. Run
`frob init` in every clone so the driver itself is configured.

## Use it

Everything works as before; only the storage moved:

```sh
frob ticket new --title "Add multiply" --scope 'src/**' --points 2 \
    --acceptance "Given two numbers, when mul runs, then it returns their product"
frob work ~Q5FEE2P
git -C ../demo-wt/Q5FEE2P ls-tree --name-only HEAD
git ls-tree -r --name-only frob-tickets
frob ticket doctor
```

The worktree is built from the code base branch, so it holds code and
`frob.toml`; the ticket file is at `_unfiled/<slug>.md` (or under its epic's
directory) on `frob-tickets`, its events under `.events/<ULID>/`.

## Push, clone and CI

Push the ledger with the code: `git push origin main frob-tickets`. A fresh
clone gets the branch with the rest of the heads, but frob reads
`refs/heads/frob-tickets`, a local branch. After cloning (and in CI, whose
checkout creates no local branches) run:

```sh no-run
git fetch origin +refs/heads/frob-tickets:refs/heads/frob-tickets
```

In GitHub Actions put that step right after `actions/checkout` (with
`fetch-depth: 0`), before `frob check`, or the TICK rules cannot read the
ledger. Protect `frob-tickets` against force pushes on the hosting side.

## Moving an existing ledger

A repository with tickets under `tickets/` on the code branch moves them with
`frob ticket migrate --to-branch` (see
[../design/navigation.md](../design/navigation.md) section 2.3). The migration
is a one-shot, verified copy that keeps every ULID and event id.
