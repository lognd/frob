# Security of packs, plugins, tool stages and the mirror

Status: current
Owner: gob
Decisions: D82
Audience: contributor

Provenance: ACCEPTED (D82, ticket ~AR02B3E), from the pessimistic audit
notes/review/plugin-security-audit.md (34 findings: 4 critical, 17 high,
10 medium, 3 low). The owner decisions on three judgment calls are section 5.
Applies to frob, grimble and crunk; the shared pieces live in gob crates.

Owner position: nothing is banned. Repository packs may run WASM and be
granted any effect. Safety comes from making the safe path the default
and the dangerous path loud, scoped, expiring, or dependent on state the
attacker cannot write.

The audit assumed real behaviour, and so does this design: people click
yes without reading, copy-paste commands from READMEs, issue comments and
diagnostics, approve pull requests that only touch lock files, config or
binaries, run checks in CI on fork pull requests, trust official-looking
names, ignore warnings that appear every run, and never rotate tokens or
revoke trust. A coding agent is also a user: it runs any command a remedy
suggests and reads attacker-controlled text as instructions.

## 1. Invariants

Each is checkable, and every finding of the audit violates at least one.
The critical findings are closed by I1, I3, I4 and I11.

| Id | Invariant | Closes |
|---|---|---|
| I1 | A repository can never raise its own privileges. Trust, effect grants, `replaces`, gate policy and executable configuration take effect only from state the tree under evaluation cannot write: the per-machine trust store, or a protected base ref read from git objects. | SEC-03, 04, 06, 15, 19 |
| I2 | No prompt is ever the only defence. Every prompt is backed by a structural limit (scope, sandbox, base-ref trust, expiry) that holds when it is answered yes without reading. | SEC-17 |
| I3 | Trust binds to every byte that can change behaviour or text: the pack tree digest covers code, data, text and everything included. | SEC-01 |
| I4 | Nothing executable or decision-bearing is loaded from a place the repository can write. Derived state lives outside the work tree and is authenticated. | SEC-02, 21, 26 |
| I5 | Plugins name nothing by string. Files, ranges, commands and URLs a plugin influences are host handles validated by the host; the host owns path resolution and never follows symlinks for a plugin. | SEC-08, 09, 15 |
| I6 | The control plane is never writable by a plugin: configuration, locks, packs, CI definitions, `.git`, hooks, the trust store, caches. | SEC-10, 15 |
| I7 | Plugin output is data, never instructions. Plugin text never fills a remedy, a help command, a link target, a fix path or a control sequence, and every text field carries its origin. | SEC-16, 18 |
| I8 | Read implies publish. Anything a plugin can read it can print into check output; grants are presented and redacted on that basis. | SEC-11, 12 |
| I9 | A plugin that did not finish is never a pass for a pack the repository marked required, and a change cannot add new Unknowns on a P+ rule in the files it touches without failing CI. | SEC-05 |
| I10 | Effects are exact, least-privilege and expiring; widening is louder than narrowing; secret-shaped scopes are a separate class. | SEC-09 to 14 |
| I11 | `clone && check` runs no repository-supplied native code and no repository-supplied program; repository WASM runs only inside the sandbox worker. | SEC-02, 04, 07, 20 |
| I12 | Parties outside the repository's writers (tracker users, issue authors) can never fail the code gate or write ledger fields that bound scope or acceptance. | SEC-18, 27 |
| I13 | Every security-relevant decision (trust, grants, replacements, excuses, NotApplicable claims, declarations, overrides) is counted in the summary and diffable between base and head. | SEC-06, 19, 20, 31 |

## 2. Mechanisms

### 2.1 The pack tree digest (I3)

A Merkle digest (blake3) over every file of a pack directory or archive:
normalized relative path, file type, executable bit and exact bytes,
including the manifest, GRL, WASM, grammars, mapping and scope files,
data, and all documentary and explain text, plus the tree digests of the
packs it includes or depends on. Symlinks, hardlinks, device files and
paths escaping the pack root are a load error (PACK005); a file present
but not hashed cannot exist because the loader hashes every file.

Trust entries, grants and every cache key bind to the tree digest. The
semantic item and pack digests of packs.md 2.5 remain, only as the
noise-free input of PACK001 drift reporting: a documentation edit does
not re-lock, but it does change the tree digest and so needs trust again.

### 2.2 Derived state outside the work tree (I4)

- Executable derived state (plans, compiled WASM `.cwasm`, compiled
  grammars) lives under `$XDG_CACHE_HOME/<product>/`, keyed by tree
  digest plus engine fingerprint, never by path, and never in the work
  tree.
- Decision-bearing caches (parse payloads and findings) stay per
  worktree in `.frob/cache.sqlite` and `.grimble/cache.sqlite` (D38),
  which keeps the warm path within its 2 s budget, but every row is
  MAC'd with the per-machine key (a keyed blake3, microseconds per row)
  and scoped by the engine fingerprint; a row without a valid MAC is a
  miss. Together with the tracked-state guard below and CI ignoring
  in-tree caches, a committed or planted cache row can never turn a red
  check green (consistency pass D85).
- Every entry carries an HMAC under a per-machine key stored beside the
  trust store; an entry with no valid MAC is discarded and rebuilt. A
  shipped `.cwasm` is therefore never loaded. Plan bytes from disk are
  always fully validated; unchecked access only for plans embedded with
  `include_bytes!`.
- Location (~TX6YZZE): executable derived state is in the per-user
  cache directory, not under the git common dir that holds the check
  cache (~TSK0M4Y): the common dir is shared by every worktree and
  writable by tool stages. `gob_trust::StateStore` writes entries as
  magic, MAC, length, payload (MAC over kind, id and payload, so a moved
  file fails), via temp file, fsync and rename, mode 0600 in 0700
  directories. Truncated, malformed or badly MAC'd entries are deleted
  and reported as `Discarded`; a missing key regenerates and so
  invalidates every old entry. The key is the per-machine key in the
  per-user config directory, never in the repository or the cache
  directory. On Windows both live under the per-user `%APPDATA%` and
  `%LOCALAPPDATA%`, whose default ACL admits only the owner, SYSTEM and
  administrators (no explicit ACL: the crate forbids `unsafe`). The
  store refuses a root inside the work tree.
- Guard: if git tracks any state or cache directory (`.frob/`,
  `.grimble/`, `.crunk/`), the run refuses with exit 3
  (`E-STATE-TRACKED`) naming the files.
- CI mode (`--base` or `CI=true`) ignores any in-tree cache. CI caching
  of compiled artefacts across trust boundaries is a cicd.md finding
  unless the MAC key comes from a secret pull-request jobs do not get.
- Each pack file is read once into memory; digest, trust check, compile
  and instantiation use that buffer. Cache writes are temp file plus
  rename and self-verify on read (TOCTOU, SEC-26).

### 2.3 Trust (I1, I2): base-ref trust first, prompts last

One trust model for every repository-supplied thing that executes or
gains a privilege: tier-3 packs, WASM grammars, effect grants,
`replaces`, and tool stages (2.4). Shared crate `gob-trust`, used by
frob, grimble and crunk.

- **Base-ref trust in CI.** `check --trust-from <ref>` trusts exactly the
  (tree digest, effects) pairs present in the lock at `<ref>` (the merge
  base with a protected branch, read from git objects, never from the
  work tree). A pack added or changed by the change under test runs
  with no effects and no privileges; its affected rules report
  Unresolved `untrusted-in-change`, which is required in CI. There is no
  other CI trust flag, and CI never reads or writes a user store.
- **Follow a protected branch locally, as a ceremony** (TUX-01 to
  TUX-03, TUX-06, TUX-18). `trust --follow` is a one-time review, not a
  blanket grant: it records the full refname, the remote URL and the
  current tip in the MAC'd store, and the person types the remote
  identity (and `unprotected` when branch protection is not verified).
  The documented default is `--follow --ordinary-only`. The recorded tip
  advances only through a fast-forward fetch performed by frob from the
  recorded URL (`trust --sync`, or implicitly on `frob fetch`); a ref
  moved by anything else is ignored and reported by `doctor`, so an
  agent cannot trust its own pack by creating a local branch. Trust is
  evaluated at `merge-base(HEAD, recorded tip)`, never "anything
  reachable", so reverting to a withdrawn pack version prompts again.
  On advance: code-only changes, narrowing, and ordinary widening within
  already granted classes and domains are accepted; any widening into a
  high-risk class, a new registrable domain, a new
  `runs-repository-code` stage, or a stage whose declared inputs changed
  in foreign commits is held pending (the pack runs with its previous
  effects, the new ones denied) until a person reviews it, as browsers
  do for extension updates that ask for more. A revocation list on the
  protected branch overrides every entry.
- **The review** (section 2.12) runs only on a TTY, never with a known
  agent marker in the environment (for example `CLAUDECODE=1`; the
  refusal tells the agent to stop and tell the user which pack is
  untrusted), has no `--yes`, `--all` or scope flags, and is reached
  only through `frob trust` with no arguments that pre-decide the
  answer. The JSON remedy for `untrusted` carries `requires_human =
  true` and a pack id, never a command line. Stated honestly (TUX-05):
  the TTY check stops scripts and obedient agents, not a goal-seeking
  process running as the same user; the structural limits of I2 are the
  real defence. Machines that run agents may enable an OS presence check
  (polkit, Windows Hello, macOS authentication, a FIDO2 touch) in the
  user's own config, and agent sandboxes should deny writes to
  `$XDG_CONFIG_HOME/gob/` and `.git/refs/remotes/`.
- **The store.** `$XDG_CONFIG_HOME/gob/trust.toml`; repository identity
  is the canonical root path plus root commit id plus remote URL (all
  must match); each entry records who, when and an expiry (default 90
  days; grants of network effects 180 days) and is MAC'd so hand-added
  lines are inert. `trust list`, `trust revoke`; `doctor` reports
  expired entries and a group- or world-writable store. Denials are
  remembered per digest; grants unused for 30 days expire. `trust
  --show` prints the pending review non-interactively (agents may run
  it); it has no approve action.

### 2.4 Tool stages are process packs (I11)

`[[check.tool]]` stages and `subprocess` effects run programs outside
any sandbox, so they enter the same trust model:

- A stage or process grant is an argv template (fixed program, fixed
  flags, typed placeholders such as "a tracked path"), never a bare name
  or a shell string.
- The program is resolved at trust time to an absolute path outside the
  work tree (a `$PATH` entry inside the work tree is refused) and its
  digest recorded in the lock of the product that declares the stage
  (`frob.lock` for `frob.toml` stages, `grimble.lock` for
  `grimble.toml`); a different binary is untrusted.
- It runs with a scrubbed environment, `GIT_CONFIG_NOSYSTEM=1`, no `-c`
  passthrough, stdin closed.
- **Honest classes** (TUX-04). Programs known to execute work-tree
  content (cargo, rustc wrappers, make, npm, pnpm, yarn, python, node,
  sh, bash, go, gradle, mvn) are class `runs-repository-code`; launchers
  that download and run code (uvx, npx with a package, pipx run, go run
  with a module path) are `fetches-and-runs-code` and must pin a content
  hash or are shown as "downloads and runs unpinned code from HOST". The
  review says in host text: this runs code from whatever branch you
  have checked out, with your full privileges. Such stages declare
  `inputs` (globs whose bytes govern behaviour; the host adds known ones
  such as `build.rs`, `**/Cargo.toml`, `.cargo/**`, `package.json`,
  `Makefile`); when inputs changed in commits authored elsewhere (present
  on another remote ref), the stage is Unresolved `untrusted-in-change`
  locally. Your own unpushed commits do not trigger it. In CI such
  stages run only in jobs without secrets for pull requests from forks.
- **Placeholders cannot inject options** (TUX-15): tracked-path
  placeholders render as `./path`, `--` is inserted before positional
  placeholders where the program supports it, and the review shows the
  template with these guards; a program supporting neither is
  high-risk "arguments come from file names".
- Until trusted (store or base ref), the stage is Unresolved
  `untrusted` with the trust command, exactly like a WASM pack. This
  includes this repository's own stages (`cargo dev gen --check` and the
  like): a maintainer runs `frob trust --follow origin/experimental`
  once (owner decision, section 5).

### 2.5 The sandbox worker and the effect broker (I5, I6, I10, I11)

- Tier-3 components and third-party WASM grammars run in a separate
  worker process that holds no secrets: empty environment, no inherited
  descriptors but one pipe, and an OS sandbox where available (Linux
  seccomp plus Landlock with no file access and no network; macOS
  sandbox profile; Windows job object at low integrity). Only the WASM
  features the WIT world needs are enabled (no threads, shared memory
  or SIMD unless measured necessary). Defence in depth assumes wasmtime
  escapes will happen.
- Granted effects are performed by the parent process (the broker) on
  the worker's request:
  - **Reads** beneath the root without following symlinks (`openat2`
    with `RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS` on Linux, component-wise
    `O_NOFOLLOW` elsewhere), over tracked files only (the git index,
    never ignored or untracked files), refusing files with a link count
    above 1, case-insensitive matching on case-insensitive file systems.
  - **Writes** beneath the root, tracked or new files only, never the
    control plane (2.6), reported with byte counts.
  - **Network**: HTTPS only, certificate validation, redirects off by
    default and re-checked per hop, DNS resolved once per request and
    refused for loopback, link-local, private and metadata ranges
    unless an IP range is granted, size and time caps; exact hostnames,
    with `*.host` a separate, loudly rendered form.
  - **Environment**: exact names only, answered from the broker; the
    worker never sees the real environment.
  - **Processes**: argv templates only (2.4).
- Resource caps before results cross back: findings per file, bytes per
  message, total output bytes, module size, function count, compile
  time, memory, epoch time, a step counter for tier-2 plans, regex size
  and nesting limits at load. Any breach is Unresolved `budget`.
- wasmtime carries a "known vulnerable below" floor in the binary;
  `doctor` and, at most once a day, the summary say so when tier 3 runs
  on an outdated binary.

### 2.6 Effect classes (I6, I8, I10)

| Class | Examples | Rules |
|---|---|---|
| ordinary | `fs.read` of `src/**`, `env` `RUST_LOG`, `net` `api.example.com` | declared exactly, trusted per 2.3, presented as "can read and print X" |
| secret-shaped | `fs.read.secret-shaped` (`.env*`, `*.pem`, `*.key`, `id_*`, `.npmrc`, `.pypirc`, `.netrc`), `env.secret` (`*TOKEN*`, `*SECRET*`, `*KEY*`, `*PASSWORD*`, `ACTIONS_*`, `AWS_*`, `AZURE_*`, `GOOGLE_*`, `NPM_*`, `CARGO_REGISTRY_*`, `SSH_AUTH_SOCK`) | a separate named effect, never implied by a glob, never granted by base-ref trust when new; every byte read is registered with the gob-log redactor and redacted from all output |
| control plane | `fs.write.control` over `.git/**`, `grimble.toml`, `frob.toml`, locks, `packs/**`, CI definitions (from the cicd adapter registry), `CODEOWNERS`, state and cache directories, the trust store | never satisfied by a glob, never by CI trust; `.git/**`, the trust store and caches are not grantable at all |
| privilege | `replaces = "ID"`, `fix.machine`, `subprocess` | trusted like effects even for pure packs; listed in the prompt |

Read implies publish: the trust prompt and docs say "can read and print".

### 2.7 An honest gate (I9, I13)

- **Required packs.** `[[packs.enable]] required = true` (materialized,
  per pack, and per rule). For a required pack the Unresolved reasons
  `untrusted`, `untrusted-in-change`, `budget`, `trap`, `effect-denied`
  and `pack-unavailable` are required, with matching `RequiredReason`
  variants (PACK006 gets one too).
- **No new unknowns.** The base side is computed from git objects (a
  gob-git snapshot of the base tree, no checkout), only for the files the
  change touches and only for P+ rules, and cached in the findings cache
  by (base commit, engine), so the cost is proportional to the change.
  `check --base REF` (CI) fails on any new
  Unresolved for a P+ rule in a changed file. Existing Unresolved stay
  non-failing so adoption is never blocked.
- **GATE001 policy-weakened** (Error, required): with `--base`, the
  effective policy is computed at base and head (packs and their paths,
  severities, disabled rules, `fail_on*`, `[compute]`, excludes, grants,
  `replaces`, trust settings, new NotApplicable claims from repository
  adapters, new in-source declarations that a P+ security verdict
  depends on) and each weakening is one finding naming old and new
  value. Cleared only by an exception with a ticket (exceptions.md);
  strengthening is silent. `config diff --base REF`
  prints the delta. `init` recommends CODEOWNERS for the control plane.
- The summary separates "Unresolved because a plugin did not finish"
  from "Unresolved because the code is undecidable", so nobody filters
  both together.

### 2.8 Packs as reviewable code

- A repository tier-3 pack carries its source and build recipe
  (`pack build` records toolchain and source tree digest).
  `packs verify --rebuild` rebuilds and compares; CI runs it when a pack
  changes. A binary not reproduced from in-repository source is
  **PACK010 unreproducible-binary** (Error by default; downgrading it is
  a GATE001 weakening). Not banned; loud.
- External packs are vendored and then treated as repository packs for
  every trust purpose, shown as `ext:HOST/NAME`. Fetch verifies the tree
  digest before extraction, refuses absolute, `..`, symlink, hardlink
  and device entries, caps size and file count, HTTPS only, redirects
  only within the declared host. Signatures stay optional;
  `[packs] require_signed` is a materialized knob and prompts show
  "unsigned" plainly.
- Provenance is always shown with a host prefix (`builtin:`,
  `repo:packs/NAME`, `ext:HOST/NAME`). Pack names starting with `std`,
  `grimble`, `frob`, `crunk`, `core` or `gob` are reserved for built-in
  packs (PACK005 elsewhere). A pack's `config_tables` may declare only
  `[packs.NAME]` (PACK005).
- Std GRL to Rust codegen runs as `cargo dev gen rules` (never
  `build.rs`); GEN001 regenerates and byte-compares in a clean CI job on
  the protected branch; the generated module carries
  `#![forbid(unsafe_code)]` and a grimble node with no grants, so any
  ambient effect in it is CAP001; the conformance test (plugins.md 6.1)
  also runs on an adversarial corpus with randomized paths.

### 2.9 replaces and adapters

- `replaces` is a privilege (2.6). The replaced std rule keeps running
  as a shadow: a finding it produces that the replacement does not is
  Unresolved `replaced-divergence`, required for security-relevant
  families. Replacing a kernel-integrity rule (PACK, CAP004, GATE) is
  impossible in CI by construction (intended: CI never passes the flag);
  locally it needs `--allow-replace ID` on every invocation, so it cannot arrive in
  a pull request. A new `replaces` is a GATE001 weakening.
- WASM grammars are trust-gated like tier 3, run in the worker under
  budgets (a parse over budget makes the file opaque, Unresolved
  `budget`), and query compilation and execution are budgeted. An
  adapter may not claim an extension or language id already claimed
  (PACK004); a repository adapter's NotApplicable claims are listed in
  the fidelity report and counted by GATE001; a NotApplicable claim for
  an atom owned by another pack is PACK005.
- In-source declarations are marked `by-declaration` in the matrix and
  JSON; they may add targets where the adapter answered Unknown but
  never remove a target the adapter found.
- Nested `grimble.toml` files load only when the root lists them
  (`[workspace] members`, materialized) or the user passes the root
  explicitly; vendored, ignored and submodule paths never trigger
  nested loading.

### 2.10 Text, findings and fixes (I5, I7)

- **Handles, not names.** A plugin finding names a file handle from the
  subject set of that call plus byte ranges validated against the file;
  snippets render only from the in-memory snapshot of tracked,
  non-ignored files the run already parsed, never from a fresh disk
  read. Secondary spans only in files the plugin was given.
- **Escaping.** The text renderer (gob-diagnostics) escapes every C0 and
  C1 control except newline, and every bidi and invisible formatting
  character, everywhere. Other non-ASCII is escaped as `\u{...}` in
  text originating from packs, the tracker or the ledger, and shown as
  is in source snippets (owner decision, section 5). JSON keeps exact strings.
  Interactive diffs show invisible characters as escapes.
- **Origin.** Every text field carries `origin` (`host`, `std`,
  `pack:NAME`, `source`, `tracker`, `ledger`); text mode prefixes
  non-host text (`pack(py-safety) says:`).
- **Remedies are host-only.** `remedy`, `help` commands and fix commands
  are produced only from host templates with host-filled arguments.
  Plugin URLs print as plain text with the host name first, never as
  terminal hyperlinks. First-occurrence teaching (diagnostics.md 5)
  applies to std rules only; pack explain text is shown on request,
  fenced and labelled. The JSON schema docs tell agents that text with
  an origin other than `host` or `std` is data, never instructions.
- **Fixes.** A plugin edit is (file handle from the subject set, byte
  range inside the finding's primary span, replacement text); anything
  else is dropped and reported. Plugin fixes are at most
  `maybe-incorrect` unless the pack holds `fix.machine`. No plugin fix
  may touch the control plane at any applicability. Fixes carry
  `origin`; agent guidance is to apply only `origin = std` machine
  fixes automatically.
- Findings from effectful packs are not cached across runs unless the
  effect inputs (fetched bytes digest) are in the cache key; JSON marks
  them `effect-derived`.

### 2.11 The mirror and the ledger (I12)

The mirror's security design is mirror.md section 3 (from the
adversarial audit notes/review/mirror-audit.md and the TLA+ model in
docs/design/models/mirror/). The points that matter for I12:

- The mirror job holds the tracker credentials and runs only from the
  default branch's workflow on schedule or dispatch, with credentials in
  an environment restricted to that branch; a push to the ticket branch
  never runs a secret-bearing job (mirror.md 3.1).
- Markers count only in the bot-authored creation revision of an issue
  body and carry a MAC bound to the repository; any other issue carrying
  a marker is **MIR003 spoofed-marker** (Advisory) and ignored
  (mirror.md 3.3).
- Tracker edits never block anything; they are reverted and captured as
  proposals by reference, keyed by tracker event id, capped and
  expiring; an outsider can add at most one proposal per issue and
  field per day, and contested fields stop the revert war (mirror.md
  3.4, 3.5).
- `frob ticket proposals accept` requires a TTY and no agent marker,
  shows the escaped diff, refuses unmapped identities, and never changes
  scope, acceptance, evidence or links (mirror.md 3.5).
- `doctor` (and a TICK rule) checks through the hosting API that the
  ledger branch forbids force pushes and deletion: an Error where the
  API answers, Unresolved otherwise.
- Agent briefs render ledger text with `origin = ledger`; commands an
  agent brief suggests are limited to `[evidence] allowed_tools`.
- CI rules: running a check with any trust other than `--trust-from` a
  protected ref inside a `pull_request_target` or `workflow_run`
  workflow is CI016 (Error; joins CI006 and CI011 in cicd.md).

### 2.12 The trust review a person sees (from the trust UX audit)

Evidence: notes/review/trust-ux-audit.md (18 findings, 37 references
including warning-habituation research and the xz-utils, event-stream,
ua-parser-js, VS Code workspace trust, Android and browser-extension
cases). The principle: how rarely a prompt appears matters more than
how thorough each prompt is, and the length of a review must be set by
the host, never by the pack.

- **Review grants, never call sites** (TUX-08). The broker performs only
  granted effects, so the grant is the complete description of what a
  pack can do; one dangerous call among a thousand benign ones is one
  line, "can send src/** to example.com". The host computes flows (a
  read grant plus a send grant is shown as a flow) and shows
  `runs-repository-code` first because it dominates every other effect.
  Code is reviewed in pull requests; the review says so in one line.
- **Screen 1, the summary, is always exactly one screen** (TUX-07): the
  repository identity, three host facts first ("Saying no breaks
  nothing: N rules stay Unresolved on this machine", "CI never uses this
  machine's trust", "This is not a code review"; TUX-12), then high-risk
  items (each needing its own confirmation), then ordinary items
  aggregated into one decision, then verified provenance. Ordering:
  widenings before new; then control plane, privilege (`subprocess`,
  `runs-repository-code`, `replaces`, `fix.machine`), secret-shaped,
  send flows, new hosts, ordinary. Actions: deny all (the default on
  Enter), trust ordinary only, review high risk, trust once for this
  run, details (a read-only pager with no approve action).
- **High-risk screens, at most five per session**, one item each, with
  type-to-confirm of the risky scope itself (the domain, the program,
  the secret class), never the pack name (TUX-09). Above five, the only
  options are approving the whole class by typing it with its count, or
  denying. Consequence sentences are host templates. Required for:
  secret-shaped reads and environment, control-plane writes,
  `subprocess`, `runs-repository-code`, `fetches-and-runs-code`,
  `replaces`, `fix.machine`, any send flow, any wildcard host, any new
  registrable domain, and the `--follow` ceremony. Not required for
  ordinary effects, narrowing, fetch-only to an already granted
  domain, or trusting a pure pack once.
- **Deny is as easy as approve** (TUX-14): per-effect allow or deny;
  packs run with what was allowed and denied effects answer
  `effect-denied`; `trust once` for one invocation; a receipt screen
  lists what was granted and denied, expiry, and the revoke command.
- **Input hygiene** (TUX-16): the review runs in the terminal's
  alternate screen with a host-drawn frame; buffered input is flushed;
  bracketed paste is enabled and pasted text is rejected; each decision
  arms about one second after drawing and re-arms on any keypress. No
  longer or per-item cooldowns: delays habituate and multiply with
  attacker-inflated volume.
- **Identity: verified facts only** (TUX-10). Shown: signature
  verification against allowed signers kept outside the work tree (key
  fingerprint and entry, or "unsigned"), the first change by that key
  to this pack, whether and since when it is on the followed ref, branch
  protection status, PACK010 reproducibility, and the widening history
  with the note "age is not safety". Git author and committer names are
  only in details, labelled unverified. Hosting account age, stars,
  downloads and any pack prose never appear.
- **Text in the review** (TUX-11, TUX-17): every string passes the
  2.10 escaper with its origin; fields authored by the change escape
  non-ASCII; long fields say "(N more chars)" instead of truncating
  silently, and hosts and paths are never truncated; hosts are shown as
  A-labels with the registrable domain first and set apart; mixed-script
  and confusable names, near-misses of known domains and of built-in or
  already trusted pack names are flagged; a new pack says "new pack,
  never trusted before" with its digest prefix.
- **Rate limits** (TUX-13): one review session per invocation, at most
  five type-to-confirm decisions per session, at most three sessions per
  repository per day; `check` prints an untrusted notice once per
  (digest, day) and otherwise only counts it. In CI, an
  `untrusted-in-change` message says it is fixed by landing the change
  on the protected branch after review, not by running trust anywhere.

The owner's proposal, element by element (owner request 2026-10-04,
verdicts from the audit, adopted):

| Element | Decision |
|---|---|
| pagination | changed: one fixed summary screen plus at most five high-risk screens; the pack's size never sets the review's length |
| author information | dropped as a cue; verified provenance shown instead |
| capabilities in the repository | kept, as grants and host-computed flows |
| manual acknowledgement of each item | changed: only high-risk and widened items, by typing the scope; ordinary items share one decision; deny is the default |
| small cooldown | kept narrowly: about one second, re-armed on keypress, against typeahead and accidental input |

## 3. Finding index

Every audit finding, its decision and where it is specified. "Accepted"
means the audit's mitigation is adopted as written in the section named.

| Finding | Severity | Decision | Section |
|---|---|---|---|
| SEC-01 digest misses code | critical | accepted | 2.1 |
| SEC-02 executable caches in tree | critical | accepted | 2.2 |
| SEC-03 CI trust flag | critical | accepted: base-ref trust only | 2.3 |
| SEC-04 tool stages outside trust | critical | accepted: process packs | 2.4 |
| SEC-05 failures are passes | high | accepted | 2.7 |
| SEC-06 change controls its gate | high | accepted: GATE001 | 2.7 |
| SEC-07 wasmtime only defence | high | accepted: worker and broker | 2.5 |
| SEC-08 snippet rendering reads any file | high | accepted | 2.10 |
| SEC-09 fs.read escapes | high | accepted | 2.5, 2.6 |
| SEC-10 fs.write control plane | high | accepted | 2.6 |
| SEC-11 output is an effect | high | accepted | 2.6 |
| SEC-12 env grants leak | high | accepted | 2.5, 2.6 |
| SEC-13 network scoping | high | accepted | 2.5 |
| SEC-14 subprocess by name | high | accepted | 2.4 |
| SEC-15 plugin fixes | high | accepted | 2.10 |
| SEC-16 text injection | high | accepted; escaping option A (owner) | 2.10 |
| SEC-17 trust fatigue | high | accepted | 2.3 |
| SEC-18 mirror adoption | high | accepted; tracker edits reconciled, never blocking (owner) | 2.11 |
| SEC-19 replaces | high | accepted | 2.9 |
| SEC-20 adapters | high | accepted | 2.9 |
| SEC-21 committed derived state | high | accepted | 2.2 |
| SEC-22 resource exhaustion | medium | accepted | 2.5 |
| SEC-23 external packs as data | medium | accepted | 2.8 |
| SEC-24 unreviewable binaries | medium | accepted: PACK010 | 2.8 |
| SEC-25 codegen | medium | accepted | 2.8 |
| SEC-26 TOCTOU | medium | accepted | 2.2 |
| SEC-27 ledger and mirror.toml | medium | accepted | 2.11 |
| SEC-28 trust store | medium | accepted | 2.3 |
| SEC-29 nested configs | medium | accepted | 2.9 |
| SEC-30 provenance spoofing | medium | accepted | 2.8 |
| SEC-31 declarations narrow P+ | medium | accepted | 2.9, 2.7 |
| SEC-32 config_tables collision | low | accepted | 2.8 |
| SEC-33 cached effectful findings | low | accepted | 2.10 |
| SEC-34 wasmtime vetting | low | accepted | 2.5 |

### 3.1 Trust UX audit index

| Finding | Severity | Section |
|---|---|---|
| TUX-01 --follow as a blanket grant | high | 2.3 |
| TUX-02 movable local ref | high | 2.3 |
| TUX-03 history-wide reachability | high | 2.3 |
| TUX-04 tool stages run checked-out code | high | 2.4 |
| TUX-05 TTY is not human presence | high | 2.3 |
| TUX-06 long-con widening on the protected branch | high | 2.3 |
| TUX-07 volume attack | medium | 2.12 |
| TUX-08 needle in a haystack | medium | 2.12 |
| TUX-09 typing the pack name | medium | 2.12 |
| TUX-10 spoofable identity | medium | 2.12 |
| TUX-11 forged strings in facts | medium | 2.12 |
| TUX-12 primed human | medium | 2.12 |
| TUX-13 trust bombing | medium | 2.12 |
| TUX-14 deny harder than approve | medium | 2.12 |
| TUX-15 placeholder option injection | medium | 2.4 |
| TUX-16 typeahead and paste | low | 2.12 |
| TUX-17 near-miss names | low | 2.12 |
| TUX-18 protection not checked locally | low | 2.3 |

## 4. New ids

| Id | Kind | Meaning |
|---|---|---|
| GATE001 | Error, required | policy-weakened between base and head |
| MIR003 | Advisory | an issue carries a ticket marker the mirror did not create |
| PACK010 | Error | a repository WASM binary is not reproduced from its source |
| PACK009 | retired | was the directory-scoped per-run-hook error; never reused |
| `E-STATE-TRACKED` | guard, exit 3 | git tracks a state or cache directory |
| Unresolved reasons | `untrusted`, `untrusted-in-change`, `budget`, `trap`, `effect-denied`, `pack-unavailable`, `replaced-divergence` | required for required packs |

## 5. Owner decisions (2026-10-04)

1. **Tracker edits.** Not a blocking finding anywhere; reconciled
   deterministically by field ownership with every edit captured as a
   proposal (mirror.md 3.4).
2. **Escaping.** Option A: controls, bidi and invisible characters are
   always escaped; other non-ASCII is escaped only in text from packs,
   the tracker and the ledger; source snippets show as they are.
3. **This repository's own tool stages** need the one-time trust step;
   the owner performs it on this machine. The review flow a person sees
   is section 2.12, from the second audit (attention and social
   engineering attacks).
