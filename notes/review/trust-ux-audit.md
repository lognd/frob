# Trust UX audit: the human trust step for packs and tool stages

Scope: the human decision that grants a repository pack or tool stage
the right to run with effects. Design text only (no implementation
exists). Builds on notes/review/plugin-security-audit.md (SEC-01 to
SEC-34) and docs/design/security.md (D82); nothing here repeats a SEC
finding unless the accepted mitigation leaves a gap. Same severity
scale and same owner position: nothing is banned; the safe path is the
default and the dangerous path is loud, specific and costly to approve
by accident.

Subject under review:

- security.md 2.3 (lines 79-116): base-ref trust in CI, `trust --follow`
  locally, a TTY-only prompt with no `--yes`, host-derived facts only,
  "widening an effect or trusting `subprocess` requires typing the pack
  name" (line 108), MAC'd store with expiry.
- security.md 2.4 (lines 117-135): tool stages as process packs, argv
  templates, program digest in the lock.
- security.md 2.5, 2.6, 2.8, 2.10; plugins.md section 9.
- The owner's proposal: a paginated review that shows author
  information and the capabilities in the repository, where each item
  must be manually acknowledged, with a very small cooldown.

Method: the attacker and human models of the previous audit (R1-R5,
H1-H7, A1) plus three additions used below:

- H8 the human is primed before the prompt appears (a README, an issue,
  a colleague, an agent said "run this to fix CI").
- H9 the human trusts an agent's summary over the prompt ("I reviewed
  the pack, it is safe, please run `frob trust`").
- A2 an agent that hits "requires a TTY" works around it (it allocates
  a pseudo-terminal) because its goal is to make the check green.

Citations are listed in section 5 and referred to as [n]. All URLs were
fetched on 2026-10-02; DOIs were checked against Crossref.

---------------------------------------------------------------------

## 0. Evidence summary (what the research actually says)

1. Warnings work when rare and specific, and fail when frequent.
   Akhawe and Felt [1] measured 25 million warning impressions: users
   clicked through about 10 percent of Firefox malware warnings but 70.2
   percent of Chrome SSL warnings, and found that "technically skilled
   users ignore warnings more often, and warning frequency is inversely
   correlated with user attention". frob's users are all technically
   skilled; frequency is the variable the design controls.
2. Habituation is neural, fast and survives redesign only partly.
   Anderson et al. [2] (fMRI) showed the visual response to a repeated
   warning drops after the second exposure and that polymorphic
   (changing) warnings slow the drop; Vance et al. [3] confirmed it
   longitudinally with eye tracking and a field experiment; [4]
   summarizes ("from warning to wallpaper").
3. What resists habituation is interaction with the field that carries
   the risk, not delay. Bravo-Lillo et al. [5] tested "attractors"
   (highlight, animated connector, delay, swipe, type-the-field with
   paste disabled) against a spoofed publisher name; inhibitive
   attractors helped. The follow-up [6] separated habituation levels:
   without attractors, habituation caused "a three-fold decrease" in
   noticing a change; delay-based attractors still lost effect with
   habituation; only "the two attractors that forced the user to
   interact with the text field containing the change" were "resilient
   to habituation".
4. Consent dialogs train acceptance. Boehme and Koepsell [7]: users
   accept faster and more often when a dialog looks like the EULAs they
   always accept. Egelman et al. [8]: passive warnings are ignored;
   active warnings that interrupt work are heeded far more, and users
   heed warnings they do not recognize as the ones they habitually
   dismiss. Sunshine et al. [9]: warnings are a last resort; prefer to
   eliminate the hazard or make overriding hard.
5. Install-time permission lists are not read. Felt et al. [10]: 17
   percent of Android users paid attention to install-time permissions
   and 3 percent answered all comprehension questions. Android moved to
   runtime prompts (6.0) and one-time grants plus auto-reset of unused
   grants (11) [11]. Wijesekera et al. [12]: the right decision depends
   on context, which an install-time list does not carry.
6. Aggregated warnings hide specifics. Chrome's extension warnings
   collapse ("the tabs warning won't show if the extension also
   requests <all_urls>"), and a new warning-bearing permission on
   update disables the extension until the user accepts [13]: update
   time escalation is gated, not silent.
7. Delays are an input-race defence, not an attention defence.
   Firefox's `security.dialog_enable_delay` is 1000 ms; its helper
   exists for "dialogs that might be subject to fast-clicking attacks",
   disables on blur, re-arms on focus, and renews the timer "while the
   user key-repeats" [14]. Nothing in it claims to make users read.
8. "All current and future" is the dangerous grant. Homebrew 6 moved to
   per-item tap trust and says: "Trust a whole tap only when you accept
   all current and future formulae, casks and external commands from
   that tap" [15]. pnpm 10 stopped running dependency lifecycle scripts
   by default and named the escape hatch `dangerouslyAllowAllBuilds`
   [16]. VS Code Workspace Trust defaults to Restricted Mode ("When in
   doubt, leave a folder in Restricted Mode") but lets a parent folder
   trust every subfolder [17]. direnv blocks an `.envrc` until `direnv
   allow`, yet `source_up` loads a parent `.envrc` that "is not checked
   by the security framework" [18].
9. Identity is earned cheaply and then spent. GitHub's own docs warn
   that first-time-contributor approval is bypassed by "getting a
   simple typo or other innocuous change accepted" [19]. xz-utils: "Jia
   Tan" sent an innocuous first patch on 2021-10-29, sockpuppets
   ("Jigar Kumar") pressured the maintainer, and the backdoor landed on
   2024-02-23 "hidden inside some binary test input files", with a
   `build-to-host.m4` present only in release tarballs [20][21].
   event-stream: a new maintainer took over and added `flatmap-stream`
   as a dependency, whose payload targeted one company's environment
   [22][23]. ua-parser-js: a hijacked publisher account shipped three
   malicious versions [24].
10. Agents follow injected text and modify their own guard rails.
    Greshake et al. [25] (indirect prompt injection); Invariant Labs'
    GitHub MCP exploit [26]; Amp let the agent "update its own
    configuration" to allowlist commands [27]; Willison's "lethal
    trifecta" (private data, untrusted content, external
    communication) [28].
11. Rendering is attack surface. Trojan Source [29] (bidi controls);
    Unicode TR39 confusables and mixed-script detection [30]; xterm
    bracketed paste mode (`CSI ? 2004 h`) lets a program tell pasted
    from typed input [31]; `script(1)` gives any process a pty [32].

Consequence for the design: the trust step is worth exactly as much as
(a) how rarely it appears, (b) whether the one risky fact is the thing
the human must interact with, and (c) whether the structural backstops
(I2) hold when it is answered yes blindly. The owner's proposal
optimizes thoroughness per prompt; the research says thoroughness per
prompt is the wrong lever, and several of the largest risks sit outside
the prompt entirely (`--follow`, process stages).

---------------------------------------------------------------------

## 1. Findings

### HIGH

#### TUX-01 (high): `trust --follow` is the `--all` the design rejected, and it shows nothing

Where: security.md 2.3 lines 93-97 ("once per repository, trusts any
pair present in the lock at a commit reachable from the fetched
protected ref"); plugins.md 9 item 4 (lines 304-308); ticket
tickets/01M3ZX7V9AKM8KVBHF32BWEC3K (trust --follow).

What is wrong: the prompt is carefully constrained (no `--yes`, no
`--all`, widening shown first), but `--follow` is a single command that
grants every current pair in the lock, including `subprocess`,
`fs.write.control`, `replaces` and network hosts, and every future pair
that lands on that ref. The design says it runs "once" and is
documented as the onboarding step, so it is exactly the command a
README tells people to paste (H2). Nothing says `--follow` itself
renders anything or asks for anything specific.

Attack:
1. R1 publishes a "reproduce my bug" repository, or a fork. Its README
   says: "frob uses repository packs; run `frob trust --follow
   origin/main` once (see the frob docs)". It is true advice in a
   benign repository, so it is indistinguishable here.
2. The lock on the attacker's `main` grants a tier-3 pack
   `fs.read.secret-shaped` and `net` to a host the attacker owns, or a
   process stage `uvx some-tool@1.0`.
3. The developer runs it (H2, H5). Every pair is trusted with no
   further screen. Their next `frob check` sends `.env` and `id_*`
   bytes out through the broker.

Behaviour relied on: H2 copy-paste of setup commands, H1, and the
"protected branch" wording, which suggests a safety property that only
exists if you already trust the people who can write that branch. For
a stranger's repository the branch owner is the attacker.

Mitigation:
- Treat `--follow` as the highest-stakes trust ceremony, not a
  convenience flag. It renders the same summary screen as section 3
  for the lock at the followed tip, itemizes every high-risk pair, and
  says in host text: "You are trusting every current and future pack
  and tool stage that the writers of <owner/repo> branch <name> add.
  This is equivalent to running their code." (Homebrew's wording [15].)
- Confirmation is type-to-confirm of the remote identity (for example
  `github.com/lognd/frob main`), paste rejected (TUX-09).
- Offer the narrower default first: `--follow --ordinary-only` (the
  follow covers ordinary effects and code changes; any high-risk pair
  still needs its own confirmation once per digest lineage). Make the
  narrow form the one docs and `init` print.
- Bind the follow entry to the remote URL and the full refname (see
  TUX-02) and show the hosting account that owns the URL as a plain
  host fact, labelled "who can write this branch decides what runs".

#### TUX-02 (high): the followed ref is local state that an agent or any local process can move

Where: security.md 2.3 lines 93-95 ("the fetched protected ref");
ticket tickets/01M3ZX7V9AKM8KVBHF32BWEC3K.

What is wrong: "fetched protected ref" is `refs/remotes/origin/main`
in the local `.git`, which is writable by any process running as the
user, including an agent (A1, A2). Separately, git resolves a short
name `origin/main` by trying `refs/heads/origin/main` before
`refs/remotes/origin/main` ([33]: "refs/heads/<refname> if it exists;
otherwise, refs/remotes/<refname>"). The I1 claim "a repository can
never raise its own privileges" holds against repository content but
not against the local process that is supposed to be held back by
"agents cannot run trust".

Attack:
1. A developer ran `frob trust --follow origin/main` months ago.
2. An agent working in the repository is prompt-injected by an issue
   body (A1, [25][26]) or simply wants a green check. It adds a pack
   with `subprocess` and commits.
3. It runs `git branch origin/main HEAD` (creating
   `refs/heads/origin/main`, which shadows the remote-tracking ref), or
   `git update-ref refs/remotes/origin/main HEAD`. Neither needs a TTY.
4. The next `frob check` finds the new pair "in the lock at a commit
   reachable from origin/main" and runs it with no prompt.

Behaviour relied on: A1 and A2; the human never sees a prompt, so no
human behaviour is needed at all.

Mitigation:
- Store the followed ref as a full refname plus remote URL in the trust
  store and resolve only that exact refname; refuse (exit 3) when a
  short name is ambiguous, naming both refs.
- Do not read the tip from `.git` at consult time. Record the trusted
  tip commit id in the MAC'd store entry and advance it only inside a
  frob-performed fetch from the recorded URL (`frob trust --sync`, or
  implicitly on `frob fetch`) that checks the update is a fast-forward.
  A ref moved by anything else is ignored and reported by `doctor`.
- Accept that a same-user adversarial process can still forge the store
  (TUX-05) and say so; this mitigation closes the cheap, plausible
  path (a branch or update-ref), which is what an injected agent does.

#### TUX-03 (high): "reachable from" trusts every historical pair, so a rollback to a withdrawn pack version runs with no prompt

Where: security.md 2.3 line 94-95 ("any pair present in the lock at a
commit reachable from"); ticket tickets/01M3ZX7V9AKM8KVBHF32BWEC3K
acceptance "a pack changes on origin/main ... trusted with no prompt".

What is wrong: reachability includes the whole history. A pack version
that was removed from `main` because it was malicious, vulnerable or
over-privileged stays trusted forever on every following machine.
There is no revocation that a protected branch can publish. CI is not
affected (it trusts the lock at the merge base exactly), so local and
CI semantics silently differ.

Attack:
1. In March, pack `py-safety` v3 on `main` had `net` to
   `telemetry.example` and a `subprocess` grant. In June the team finds
   it exfiltrating and lands v4 without those grants.
2. In July, R2 opens a pull request that "fixes a flaky test" and, in
   the lock and `packs/py-safety/`, restores v3 byte for byte.
3. A reviewer runs `gh pr checkout 123 && frob check` to reproduce.
   v3's (tree digest, effects) pair is present at a commit reachable
   from `origin/main`, so it runs with its old effects and no prompt.
   CI on the same PR shows `untrusted-in-change`, which the reviewer
   is not looking at yet.

Behaviour relied on: H3 (lock and pack directory diffs are not read)
and the normal habit of checking a PR out locally.

Mitigation:
- Follow semantics equal CI semantics: trust a pair only if it is in
  the lock at `merge-base(HEAD, followed tip)` (or at the tip itself).
  A branch that reintroduces an old pair then gets
  `untrusted-in-change` locally exactly as in CI.
- Add a protected-branch revocation list (`[trust] revoked = [digest,
  ...]` read only at the followed ref, never from the work tree) that
  overrides every store entry, so withdrawing a pack is an action the
  team can take once for all machines.

#### TUX-04 (high): a process stage's approved argv understates what runs; checking out a branch runs its code natively with no prompt

Where: security.md 2.4 lines 117-135 (argv template, program digest
in the lock); I11 line 38 ("`clone && check` runs ... no
repository-supplied program"); frob.toml lines 20-46 of this
repository; ticket tickets/01M3ZX7VPGRERTZNVS5VR437JY.

What is wrong: the trust decision binds to (argv template, program
path, program digest). For build tools and launchers the program's
behaviour is decided by repository files and by the network, none of
which is in the digest:

- `cargo clippy --all-targets` (frob.toml line 28) compiles and runs
  every `build.rs` and proc macro in the work tree, and honours
  `.cargo/config.toml` (`build.rustc-wrapper`, `[alias]`) [34].
- `cargo dev gen all --check` (line 33) is the alias `dev = "run -p
  gob-dev --"` in `.cargo/config.toml`: it builds and runs a binary
  from the work tree.
- `uvx zizmor@1.30.1` (line 42) resolves and downloads a package from
  an index at run time; the digest of `uvx` says nothing about what it
  executes.
- The same holds for `npm`, `npx`, `make`, `python`, `sh`, `gradle`.

The reviewer sees `cargo dev gen all --check`, which reads as "a
check", approves it once (or gets it via `--follow`), and from then on
every branch they check out runs that branch's code natively. This is
the I11 violation the process-pack design was meant to close, moved
behind a prompt that does not describe it.

Attack:
1. R2 opens a PR that changes a `build.rs` (or `crates/gob-dev`) to
   read `~/.ssh` and post it. The PR diff looks like a codegen tweak.
2. A maintainer with the stage trusted runs `gh pr checkout` and
   `frob check` (or an agent does it for them). The stage's template
   and `cargo` digest are unchanged, so it is trusted and runs the PR's
   code with the developer's full privileges.
3. CI also runs it, which is normal for CI; the local machine is the
   asset lost.

Behaviour relied on: H5 ("cargo is obviously safe"), H1, and the
prompt's framing, which presents the template as the whole effect.

Mitigation:
- A host-maintained class `runs-repository-code` for programs known to
  execute work-tree content (cargo, rustc wrappers, npm, npx, pnpm,
  yarn, make, python, node, sh, bash, go, gradle, mvn) and
  `fetches-and-runs-code` for launchers (uvx, npx with a package
  argument, pipx run, go run with a module path). The prompt says, in
  host text: "This runs code from whatever branch you have checked out,
  with your full privileges. Trusting it means trusting every branch
  you check out."
- A stage declares `inputs` (globs whose bytes govern its behaviour);
  for the classes above the host requires them and adds known ones
  (`.cargo/**`, `build.rs`, `**/Cargo.toml`, `package.json`,
  `Makefile`). When the inputs differ from the followed ref in commits
  that are not local-only (present on some other remote ref, that is,
  authored elsewhere), the stage is Unresolved `untrusted-in-change`
  locally, exactly like a changed pack. Your own unpushed commits do
  not trigger it.
- For launchers, the template must pin a content hash (for uvx, a
  hashed requirement or a lock) or it is shown as "downloads and runs
  unpinned code from <index host>".
- Document in security.md that tool-stage trust is code-execution
  trust of the checked-out tree, so the owner's section 5 item 3
  decision is made with that cost visible.

#### TUX-05 (high): "agents cannot run it" is true only for an obedient agent; a TTY is not human presence

Where: security.md 2.3 lines 99-102 ("so agents and scripts cannot run
it"); section 5 item 3; store MAC key "beside the trust store" (2.2,
2.3 line 113); ticket tickets/01M3ZX7VDVTM9DJCW5228YRZ8Z.

What is wrong: the TTY check distinguishes a pipe from a terminal, not
a person from a program. Any process can allocate a pseudo-terminal
(`script -qc 'frob trust ...' /dev/null`, `expect`, `tmux send-keys`,
Python `pty`) [32]. Coding agents do this routinely when a tool says
it needs a TTY, and an agent can then read the prompt and type the
pack name. Further, the per-machine MAC key sits beside the store,
readable by any same-user process, so "hand-added lines are inert"
holds against repository content and file sync, not against a local
agent. Amp's agent rewriting its own allowlist [27] is the precedent.

Attack:
1. An agent's task is "make `frob check` green". The JSON envelope
   says `requires_human = true` for an `untrusted` pack.
2. The agent tries `frob trust packs/x`, gets exit 3 "requires a TTY",
   and retries under `script` (A2). The prompt asks for the pack name,
   which the agent knows.
3. The pack is trusted with no human involved. If the pack came from
   an injected issue (A1), this is the full chain.

Behaviour relied on: A2 (goal-directed workaround), and the human's
belief that the TTY rule makes agent-run trust impossible, so they do
not sandbox the agent's access to the store.

Mitigation:
- Restate the claim honestly in security.md: TTY-only stops scripts
  and obedient agents; it does not stop a goal-seeking same-user
  process. I2 (structural limits hold when the prompt is answered yes)
  is the real defence, which is why TUX-01 to TUX-04 matter.
- Refuse when well-known agent markers are present (for example
  `CLAUDECODE=1`, which Claude Code sets in its tool shells) with a
  host message for the agent: "Trust is a human decision. Do not
  attempt to run it; tell the user which pack is untrusted and stop."
  This is spoofable but redirects the common case, which is an agent
  following instructions.
- Never put an executable trust argv in agent-facing output: the JSON
  remedy carries `requires_human = true` and a pack id, not a command
  string an agent can retype.
- Offer an optional user-presence check configured only in the user's
  own config (never in the repository): OS authentication (macOS
  LocalAuthentication, Windows Hello, polkit) or a FIDO2 touch. Not a
  default; a documented hardening for machines that run agents.
- Recommend in the agent docs that agent sandboxes deny writes to
  `$XDG_CONFIG_HOME/gob/` and to `.git/refs/remotes/`.

#### TUX-06 (high): high-risk widening that lands on the followed branch is auto-trusted on every machine (the long con)

Where: security.md 2.3 lines 93-97 ("Routine updates need no prompt");
2.6 line 176 ("never granted by base-ref trust when new" applies to
secret-shaped only, and it is unclear whether `--follow` counts as
base-ref trust); 2.7 GATE001 line 192.

What is wrong: under `--follow`, every pair that lands is trusted with
no local step, including a pack that was pure for a year and now adds
`subprocess`, a new network host, `fix.machine` or a control-plane
write. GATE001 makes the widening visible in the PR, but clearing it is
one reviewer label (one click, H3). This is the xz and event-stream
shape: earn trust with benign work, then widen once [20][22]. GitHub
warns that its own first-contributor gate is defeated the same way
[19].

Attack:
1. R2 contributes useful rules to `packs/py-safety` for months (pure,
   no effects). They become the de facto owner of the pack.
2. A PR "adds advisory lookup": the manifest gains `net` to
   `advisories.example` and the lock changes. GATE001 fires; a busy
   maintainer applies the reviewer label because the contributor is
   known and the feature is plausible.
3. Every developer's next fetch trusts the new pair silently. The host
   later starts receiving file contents (read implies publish, and
   read plus network is a send channel; TUX-08).

Behaviour relied on: H3 and authority built over time (H5); the local
developer is never asked because "routine updates need no prompt".

Mitigation (the Chrome update model [13]):
- `--follow` auto-accepts code changes, narrowing, and widening within
  ordinary classes already granted to that pack. It does not
  auto-accept a widening into a high-risk class (secret-shaped,
  control-plane, privilege incl. `subprocess`, `runs-repository-code`,
  a network host not previously granted, any wildcard host). Such a
  pair is "pending": the pack runs with its previously trusted effect
  set (new effects answer `effect-denied`, Unresolved), and `check`
  prints one line per day naming the pack.
- The next interactive `frob trust` shows all pending widenings on one
  screen, ordered by class, with the widening history (TUX-10).
- State explicitly that `--follow` is base-ref trust for the purpose of
  2.6 line 176 (secret-shaped is never auto-granted when new).
- CI is unchanged: base-ref trust after merge is correct for CI because
  CI already runs the merged code; the cost lands on developer
  machines, which hold the higher-value secrets.

### MEDIUM

#### TUX-07 (medium): volume attack: pagination and per-item acknowledgement scale with attacker-controlled size

Where: the owner's proposal (paginated, every item acknowledged);
security.md 2.3 prompt contents (lines 102-109), which bound nothing.

What is wrong: if review cost is proportional to the number of items,
the author of the pack chooses the cost. Habituation sets in within a
handful of identical interactions [2][3][6], so an attacker who can
emit 200 items turns the last 195 into reflex.

Attack (question a):
1. A pack declares 180 ordinary `fs.read` globs (`src/a/**`,
   `src/b/**`, ...), 40 exact `env` names (`RUST_LOG`, `TERM`, ...) and
   one `net` host.
2. Paginated per-item review: 22 pages, 221 acknowledgements. By page
   3 the reviewer is pressing the confirm key on rhythm (H1). The `net`
   host on page 19 is acknowledged like the rest.
3. Variant: the same with argv templates (one stage per file type) or
   with many tiny packs.

Behaviour relied on: H1 and measured habituation; the reviewer gives up
reading but not approving because approving is the only way to finish.

Mitigation:
- Bound the review by the host, not by the pack: one summary screen of
  fixed size, whatever the pack contains (section 3, screen 1).
- Aggregate ordinary effects into host-computed totals ("can read and
  print 1,204 tracked files, 93 percent of the repository; 40
  environment names, none secret-shaped"). Coverage percentages defeat
  glob padding because 180 globs that cover the tree read as "the
  whole tree".
- Itemize only high-risk and widened items, and cap itemized
  confirmations per session (5). Above the cap there is no itemized
  path: the human may deny, trust once for this run (TUX-14), or
  approve the class as a whole by typing the class and count
  (`subprocess 12`), which is loud and costly, not banned.
- Make padding itself visible: the summary shows item counts per class
  and the delta in counts against the previous trusted version.

#### TUX-08 (medium): needle in a haystack: one dangerous call among benign ones; review effects, not call sites

Where: security.md 2.5 (broker performs every effect), 2.6 (classes),
I8 line 35 ("read implies publish"); the owner's proposal to show "the
capabilities in the repository".

Question: should the reviewer review effects (grants) or call sites?

Argument: call-site review is unsound and unbounded, effect review is
sound and bounded, so the unit is the grant.

- Unsound: a tier-3 component can be an interpreter whose program is
  pack data (a "fixture", a table, a regex set). The dangerous call is
  then not in the code at all; xz hid its payload in binary test files
  and a tarball-only m4 script [20]. A call graph of the WASM shows one
  generic `broker.request` site.
- Unbounded: listing call sites hands the attacker question (a) again:
  pad the component with thousands of benign real calls.
- Sound: the broker performs every effect; the guest can do nothing
  outside its grants regardless of how it is written. Reviewing the
  grant reviews every possible call site at once.

So attack (b) does not disappear; it changes shape in two ways:

Attack (b1) one dangerous grant among benign grants:
1. 30 network hosts, all plausible package registries; one is
   `pkg-mirror.example` owned by the attacker. Or 12 env names with one
   secret-shaped name; or one wildcard `*.example`.
2. Mitigated already by classes (secret-shaped and wildcard are loud);
   not mitigated for "a plausible host owned by the attacker".

Attack (b2) a dangerous use of a benign grant:
1. The pack is granted `net` to `api.github.com` "to look up
   advisories" and `fs.read` of `src/**`.
2. The guest POSTs source files to a gist under the attacker's token on
   the same host. The grant is exact and honest; the use is
   exfiltration. Willison's lethal trifecta [28] is exactly read plus
   untrusted content plus send.

Behaviour relied on: H5 (known hosts look safe), and the reviewer
reasoning about each grant alone instead of their combination.

Mitigation:
- The review unit is the grant; never list call sites in the prompt.
  Code review of a pack belongs in the PR, where PACK010 reproducible
  builds (2.8) give a reviewer the source; the trust prompt is not a
  code review and should say so.
- Present combinations, computed by the host: any pack holding a read
  effect and a network effect is shown as a flow, "can send contents of
  src/** to api.github.com", and that flow is high-risk (itemized,
  type-to-confirm) even when each half is ordinary.
- Give network grants a direction so the benign case is cheap to
  approve: `net.fetch` (GET only, no request body, query string length
  capped, for example 256 bytes, response size capped) versus
  `net.send` (bodies allowed, high-risk class). Most lint-style
  lookups need only `net.fetch`; b2 then needs `net.send`, which is
  loud.
- Taint at the broker: bytes registered with the redactor (2.6
  secret-shaped reads) are refused in any outgoing URL or body, not
  only redacted from printed output. Cheap, partial, and it closes
  the worst b2 case.
- For (b1): show hosts as registrable domains first (TUX-11), sort new
  and rarely-seen domains to the top, and mark any host whose
  registrable domain is not shared with another granted host.

#### TUX-09 (medium): typing the pack name confirms the wrong field

Where: security.md 2.3 line 108 ("requires typing the pack name");
SEC-14 mitigation in the previous audit; ticket
tickets/01M3ZX7VDVTM9DJCW5228YRZ8Z.

What is wrong: type-to-confirm works when the typed text is the fact
that carries the risk. GitHub's repository deletion asks for the
repository name because the risk is "which repository am I deleting"
[35]. Here the risk is which effect, and the pack name is chosen by the
attacker, known in advance (a README can say "type py-safety when
asked"), and pasteable. Bravo-Lillo et al. found only interaction with
the field containing the risk resisted habituation, and disabled paste
for that reason [5][6].

Attack:
1. A PR's description (H8) says: "frob will ask you to confirm; type
   `py-safety`". The human types it without reading the line above,
   which says `subprocess /usr/bin/curl`.
2. Variant: the human copies the name from the prompt itself with the
   mouse and pastes it.

Behaviour relied on: H1, H2, H8.

Mitigation:
- Type the scope, not the pack: for a network flow the registrable
  domain (`example.com`), for subprocess the program basename and its
  class (`curl subprocess`), for secret-shaped the class name
  (`secret-shaped .env`), for control-plane the target
  (`write .github/workflows`). The text differs per decision, so a
  README cannot pre-answer generically.
- Enable bracketed paste mode (`CSI ? 2004 h`) [31] during the
  confirmation and reject input that arrives inside paste brackets,
  with a host message "type this, do not paste it".
- Keep it to high-risk items only (TUX-07); typing on every item would
  itself habituate.

#### TUX-10 (medium): the prompt shows a spoofable identity as a fact

Where: security.md 2.3 lines 106-107 ("the git author of the last
change"); the owner's proposal to show "information on the author and
the like".

What is wrong: git author and committer names and emails are free text
set by whoever made the commit. Showing them on a trust screen is a
positive authority cue (H5) that the attacker controls. Hosting facts
are not much better: account age and history are bought or grown (xz's
"Jia Tan" had two years of genuine contributions [20]; GitHub warns
that a typo PR makes anyone a returning contributor [19]); event-stream
showed that the real, legitimate owner can hand a package to a stranger
[22]. Requiring a hosting API also needs a token and network in the
trust path.

Attack:
1. R2 commits a pack change with `git -c user.name="Lasse Collin" -c
   user.email=...` or with the name of the repository's lead
   maintainer.
2. The prompt prints "last changed by <lead maintainer>". The human
   approves because the person is trusted, which is the one thing the
   screen did not verify.

Behaviour relied on: H5 and authority bias.

Mitigation:
- Omit author name, email and committer from the summary screen
  entirely; on the details pager show them labelled "claimed by the
  commit, not verified".
- Show only facts the host can verify from state the change cannot
  write:
  - signature verified against an allowed-signers file read at the
    followed ref or from the user's own git config, never from the
    work tree (git `gpg.ssh.allowedSignersFile` [36]); render the key
    fingerprint and the allowed-signers entry name, or "unsigned";
  - "first change to this pack signed by this key" (the handover
    signal for event-stream);
  - whether the pair is on the followed ref, and since when;
  - PACK010 reproducible or not;
  - widening history: "first trusted with no effects on 2026-01-10;
    widened 3 times since; last widening 2 days ago".
- Omit hosting account age, stars, download counts and pack
  description: either spoofable, irrelevant to the decision, or prose.
- Label age honestly in host text: "age is not safety" next to the
  history line, so a long benign history is not read as a guarantee.

#### TUX-11 (medium): attacker-authored strings inside "host-derived facts" can forge or hide prompt content

Where: security.md 2.3 lines 102-107 ("shows only host-derived facts
... Pack-supplied prose never appears"); 2.10 line 262 (escaping is in
the gob-diagnostics text renderer); ticket
tickets/01M3ZX7VDVTM9DJCW5228YRZ8Z scope `crates/gob-trust/src/prompt.rs`.

What is wrong: "host-derived" means the host fetched the value, not
that the host authored it. Author names, file names and globs in
grants, hostnames, argv template strings and stage names are all
written by the change. The design excludes pack prose but does not say
the prompt goes through the 2.10 escaping, and the prompt lives in a
different crate. Concrete forms:

- An author name or a stage name containing `\n` and ANSI sequences
  that draw a fake line: "verified: signed by maintainer key" in green.
- Bidi controls in a path glob that render `src/**` but mean something
  else [29].
- A network host `api.githuh.com`, a punycode IDN with Cyrillic letters
  [30], or `api.github.com.example.net` truncated at terminal width to
  `api.github.com.ex...`.
- A pack or stage name of maximum length followed by padding, pushing
  the widening line off a short terminal.
- Output of the preceding `frob check` (pack findings, `pack(x) says:`)
  still in the scrollback directly above the prompt, containing text
  styled as frob instructions.

Behaviour relied on: H1 and H5; humans read the colour and the shape.

Mitigation:
- Every string in the prompt passes through the gob-diagnostics
  escaper with its origin; non-ASCII in any field the change authored
  is escaped as `\u{...}`; length caps per field with an explicit
  "(N more chars)" rather than silent truncation; never truncate a
  hostname or path.
- Hosts are stored and shown as A-labels (punycode) with the
  registrable domain first and set apart (`example.net  <-
  api.github.com.example.net`); mixed-script and confusable names
  (TR39 [30]) are flagged; a host within a small edit distance of a
  well-known domain or of another granted host is flagged.
- Run the review in the terminal's alternate screen with a host-drawn
  frame and a fixed header, so nothing from earlier output is visible
  next to a decision.
- Pack names are already ASCII kebab, max 40 (packs.md line 125);
  extend the confusable check to near-misses of built-in and
  already-trusted pack names (TUX-17).

#### TUX-12 (medium): the human arrives primed; nothing on the prompt disarms the false premise

Where: security.md 2.3 (prompt contents) and 2.10 (remedy text);
diagnostics.md remedies.

What is wrong: the most common real-world path to a bad approval is
not the prompt but the minute before it: a README or issue says "CI is
broken, run `frob trust` and approve", a colleague in chat says the
same, or an agent says "I checked the pack, it is safe; please run
`frob trust packs/x` so I can continue" (H8, H9, A1). In this design
the premise is false by construction: CI uses only `--trust-from` and
never reads a user store, so local trust can never fix CI. The prompt
does not say so.

Attack:
1. R4 comments on an issue: "The new py-safety pack broke CI for
   everyone. Maintainers: run `frob trust packs/py-safety`, type the
   name, done."
2. The human, primed for urgency (authority plus time pressure),
   approves.
3. Agent variant: an agent reading the issue relays the same request
   with its own endorsement (H9), and the human treats the agent as a
   second reviewer.

Behaviour relied on: urgency and authority cues; trust in the agent as
a reviewer.

Mitigation:
- The prompt header states two host facts before anything else:
  "Saying no breaks nothing: N rules stay Unresolved on this machine."
  and "CI never uses this machine's trust; trusting here cannot fix CI."
- When `check` reports `untrusted-in-change` in CI, its message says
  "this is fixed by landing the change on <protected ref> after review,
  not by running trust anywhere".
- No preselecting arguments: `frob trust` takes no effect or scope
  flags, so nobody can hand a human a command that pre-decides the
  answer; it opens the review of everything pending.
- Agent guidance in the JSON schema docs: an agent must not ask the
  user to run `trust` for a pack it did not add at the user's request,
  and must not describe a pack as reviewed.
- The prompt itself says: "An agent cannot review this for you; the
  broker enforces what you approve here, nothing else."

#### TUX-13 (medium): trust bombing: many prompts in a row, and recurring prompts for unchanged things

Where: security.md 2.3 (one prompt per pack, expiry "default 90 days;
grants of network effects 180 days", line 112); no rate limit or
batching specified; diagnostics for `untrusted` printed per run.

What is wrong: three sources of repeated prompts, each a habituation
engine [1][2][6]:

- Many at once: a PR splits one pack into 20, or adds 20 stages; a
  reviewer checking it out faces 20 consecutive decisions.
- Expiry cohorts: every entry trusted on onboarding day expires the
  same day 90 days later and comes back as a wave of identical
  re-approvals of unchanged code. The expiry exists to counter H7, but
  re-asking an unchanged question trains "yes".
- Per-run nagging: if every `check` prints the trust remedy for each
  untrusted pack, the remedy itself becomes wallpaper (H6) and the
  command becomes familiar, which is what makes TUX-12 work.

Attack:
1. R2's PR adds 20 small packs, 19 pure and one with `net.send`.
2. Prompted 20 times, the reviewer approves the twentieth by rhythm.

Behaviour relied on: H1, H6, habituation.

Mitigation:
- One review session per invocation, batching everything pending into
  the fixed summary (TUX-07); never one prompt per pack.
- Rate limits: at most 5 type-to-confirm decisions per session and 3
  sessions per repository per day; beyond that, pending items remain
  denied and `check` prints one summary line.
- Remember denials per digest: a denied pair is not asked about again
  until its digest changes or the user runs `frob trust --review`.
- `check` prints the untrusted notice once per (pack digest, day) and
  otherwise counts it in the summary.
- Expiry: entries covered by a follow are re-validated against the
  followed ref, not re-asked. Prompt-only entries (code not on the
  protected branch) get a short expiry (7 days, or until the branch
  lands) instead of 90 days, so long-lived prompt trust is rare and
  renewals are rare.

#### TUX-14 (medium): denying is harder than approving; there is no partial or one-time trust

Where: security.md 2.3 (trust is per pair; no per-effect partial grant,
no single-run grant); 2.7 (Unresolved reasons).

What is wrong: the only ways to make an `untrusted` notice go away are
to trust everything the pack asks for or to live with red output. When
denying has a recurring cost and approving has none, people approve.
Android's redesign ([11]: runtime prompts, "Only this time", auto-reset
of unused grants) exists because all-or-nothing install-time grants
failed [10][12].

Attack: no attacker step needed beyond asking for one extra effect;
the human approves the bundle to get the useful rules.

Behaviour relied on: H1 and the cost asymmetry.

Mitigation:
- Per-effect decisions, deny by default. A pack trusted with some
  effects denied runs; a denied effect answers `effect-denied`
  (Unresolved, required only for required packs).
- `trust once`: grant for this one `check` invocation, recorded
  nowhere, the natural answer when reviewing someone's PR locally.
- Deny is the default action on every screen (Enter, `n`, Escape,
  Ctrl-C, EOF all deny) and is remembered (TUX-13), so denying is both
  the easiest and the quietest outcome.
- Unused grants auto-expire: a grant whose effect was not requested in
  30 days of runs is dropped (Android 11 auto-reset [11]); the pack
  asks again only if it needs it.

#### TUX-15 (medium): argv placeholders can inject options the reviewer cannot see

Where: security.md 2.4 line 122-123 ("typed placeholders such as 'a
tracked path'"); 2.5 line 162.

What is wrong: the prompt shows `tool --check {tracked_path}` and the
reviewer reasons about the fixed part. A tracked path is chosen by the
change and may begin with `-`. Many programs parse such an argument as
an option (`tar --checkpoint-action=exec=...`, `git --upload-pack=...`,
`rsync -e ...`).

Attack:
1. A stage `tar -tf {tracked_path}` is trusted (benign, read-only).
2. R2's PR adds a tracked file named
   `--checkpoint-action=exec=sh x.sh` next to `x.sh`.
3. On checkout and `check`, the broker substitutes the path and `tar`
   executes the script.

Behaviour relied on: H5; the reviewer trusts the visible template.

Mitigation:
- The broker always renders tracked-path placeholders as `./path`
  (never a leading `-`), and inserts `--` before positional
  placeholders for programs known to support it; a template whose
  program does not support either is shown as high-risk "arguments
  come from file names".
- The prompt renders the template with the guard visible
  (`tar -tf -- ./{tracked_path}`), so the reviewer sees what runs.

### LOW

#### TUX-16 (low): typeahead, key repeat and pasted newlines can answer the prompt

Where: security.md 2.3 (no input handling specified); the owner's
proposal ("very small cooldown").

What is wrong: a terminal prompt reads whatever is in the input queue.
Keys typed while the previous command was running, a held Enter, or a
paste containing newlines answer the first questions before they are
drawn. This is the terminal form of the fast-click attack Firefox's
delay exists for [14].

Attack: a README's "quick start" block is pasted whole: `frob check`,
`frob trust`, then blank lines; the newlines arrive at the prompt. With
deny as default (TUX-14) the damage is bounded; with any default of yes
or "Enter to continue" pagination, it approves.

Mitigation:
- `tcflush(TCIFLUSH)` [37] when each screen is drawn; arm input about
  1 second after drawing; any keypress during the arm period restarts
  it (Firefox renews the timer on key repeat [14]); reject bracketed
  pastes (TUX-09).
- No action is bound to Enter except deny. This is the useful part of
  the owner's cooldown; a longer cooldown buys nothing (TUX-06, [6]).

#### TUX-17 (low): near-miss pack and stage names

Where: security.md 2.8 (reserved prefixes `std`, `grimble`, `frob`,
`crunk`, `core`, `gob`); packs.md line 125 (ASCII kebab, max 40).

What is wrong: the reserved prefixes stop `std-security` but not
`stb-security`, `grimbel-core`, `frop-rules`, or `py-safety` versus an
already trusted `py-safey`. In many terminal fonts `rn` reads as `m`
and `l` as `1`. Stage names (`name = "cargo"` in frob.toml) are not
covered at all, and two stages share the name `cargo` in this
repository (frob.toml lines 21, 26, 31), so a fourth `cargo` stage with
a different template would look like a sibling.

Attack: R2 adds `packs/py-safey` beside the trusted `py-safety`; a
reviewer skims the name and assumes it is a version of the known pack.

Mitigation: PACK005 warning for names within edit distance 2 of a
reserved prefix word, a built-in pack or a pack already in the lock;
the prompt shows `repo:packs/NAME` with the tree digest prefix and
"new pack, never trusted before" when it is new; stage names unique
per repository (or the prompt identifies stages by the full template).

#### TUX-18 (low): the protected-branch premise is not checked locally

Where: security.md 2.3 lines 90-97 and section 5 item 3 (`frob trust
--follow origin/experimental`).

What is wrong: `--follow` accepts any ref. Nothing tells the human
whether the branch is actually protected (required reviews, no force
push) on the host. Following an unprotected branch is equivalent to
trusting every person with push access, which for `experimental`-style
branches is often everyone with write access and every bot token.

Attack: an attacker with a stolen token for any writer pushes a lock
change straight to an unprotected followed branch; every following
machine trusts it on the next fetch.

Mitigation: `--follow` shows "branch protection: verified via hosting
API / not verified (no token) / not protected" as a host fact, reusing
the 2.11 doctor check that already queries protection for the ledger
branch; "not protected" makes the follow ceremony require typing
`unprotected` in addition to the remote identity.

---------------------------------------------------------------------

## 2. Effects or call sites: the review unit

Summary of TUX-08 as a design statement for security.md:

- The broker makes the grant the complete description of what a pack
  can do. A trust decision therefore reviews grants, and only grants.
  Showing code, call sites or manifests' own descriptions on the trust
  screen adds attacker-controlled volume and no soundness.
- Grants must be shaped so that their honest description is also
  their worst case. That is already true for exact paths, exact env
  names, argv templates and secret classes; it is not yet true for
  `net` (a host says nothing about direction) or for process stages
  whose program interprets the work tree (TUX-04).
- The host computes and shows combinations: read plus send is a flow;
  any process in `runs-repository-code` dominates every other effect
  of that pack and is shown first.
- Code review belongs in the pull request, supported by PACK010
  reproducibility and GATE001, where reviewers have diffs and time. The
  trust screen says this in one line so nobody mistakes it for a code
  review.

---------------------------------------------------------------------

## 3. Recommended trust review flow

### 3.0 Preconditions (no UI)

- Refuse (exit 3) unless stdin and stdout are a TTY; refuse when known
  agent markers are present, with the agent message of TUX-05; an
  optional OS user-presence check from user config only.
- Collect everything pending for this repository (untrusted pairs,
  pending widenings from the follow, expired prompt-only entries) into
  one session; nothing is passed on the command line.
- Switch to the alternate screen, enable bracketed paste, flush input.
- Rate limit check (TUX-13): at most 3 sessions per repository per day.

### 3.1 Screen 1: summary (always exactly one screen)

Fixed layout, bounded size regardless of input:

```
frob trust review: github.com/lognd/frob  (root 1a2b3c4, /home/u/frob)

Saying no breaks nothing: 14 rules stay Unresolved on this machine.
CI never uses this machine's trust; trusting here cannot fix CI.
This is not a code review. Code is reviewed in pull requests.

Pending: 3 packs, 1 tool stage            followed ref: refs/remotes/origin/main
                                          (protection: verified)
HIGH RISK (each needs its own confirmation)
  1  flow     repo:packs/py-safety  can SEND src/** to example.com     NEW
  2  process  tool:gen              runs repository code (cargo)      NEW
ORDINARY (one decision for all)
  py-safety   reads 1,204 tracked files (93%), 3 env names, fetch-only
  lint-extra  reads 210 tracked files (17%)
  docs-pack   no effects (pure)

Provenance (verified facts only)
  py-safety   on followed ref: no   signed: no   reproducible: yes
              first trusted 2026-01-10 with no effects; widened 0 times
  ...

[Enter/n] deny all   [o] trust ordinary only   [r] review high risk
[1] trust once for this run   [d] details (read only)
```

- Ordering: widenings before new, then by class: control-plane,
  privilege (`subprocess`, `runs-repository-code`, `replaces`,
  `fix.machine`), secret-shaped, send flows, new hosts, ordinary.
- Aggregated: ordinary reads (count and coverage), exact env names,
  fetch-only network to already granted domains, narrowing, code-only
  changes, pure packs.
- Itemized: every high-risk item and every widening, capped at 5 per
  session; above the cap the `[r]` action is replaced by "approve the
  class" (type `subprocess 12`) or deny.
- Details `[d]` opens a read-only pager (and `frob trust --show`, which
  agents may run, prints the same text non-interactively). Details
  never contain an approve action.

### 3.2 Screens 2..k: one high-risk item each

```
HIGH RISK 1 of 2: repo:packs/py-safety

Can read and SEND the contents of src/** (1,204 files) to:
    example.com   <-  api.example.com   (A-label, registrable domain first)
Requests may carry bodies. Bytes from secret-shaped files are refused.
New in this version. Previously trusted version had no network effect.

To allow, type the domain:  example.com
Anything else, Enter, or Esc denies this item.
```

- Type-to-confirm of the scope (TUX-09); paste rejected; input armed
  about 1 second after drawing, re-armed on keypress (TUX-16).
- Plain consequence sentences are host templates, never pack text.
- Deny is the default and costs nothing.

### 3.3 Final screen: receipt

What was granted (per effect), what was denied (remembered until the
digest changes), expiry, and `frob trust list` / `frob trust revoke
NAME`. Leaving the alternate screen restores the terminal.

### 3.4 Type-to-confirm: where and only where

Required for: secret-shaped reads and env; control-plane writes;
`subprocess`, `runs-repository-code`, `fetches-and-runs-code`;
`replaces`; `fix.machine`; any send flow; any wildcard host; any new
registrable domain; the `--follow` ceremony (type the remote identity
and, for an unprotected branch, `unprotected`).

Not required for: ordinary effects, narrowing, fetch-only to an already
granted domain, `trust once` of a pure pack.

### 3.5 Partial trust

Per-effect allow or deny; packs run with whatever was allowed; denied
effects answer `effect-denied`. `trust once` exists for one invocation.
Denials are remembered per digest. Unused grants auto-expire after 30
days without use.

### 3.6 `--follow` and widening on the protected branch

- `--follow` is a ceremony (TUX-01) recording the full refname, remote
  URL and current tip in the MAC'd store; the narrow form
  `--ordinary-only` is the documented default.
- Trust is evaluated at `merge-base(HEAD, recorded tip)` (TUX-03); the
  recorded tip advances only by a frob-performed fast-forward fetch
  (TUX-02).
- Auto-accepted on advance: code changes, narrowing, ordinary widening
  within already granted classes and domains.
- Held as pending (pack runs with its previous effects, new effects
  denied): any widening into a high-risk class, a new registrable
  domain, a new `runs-repository-code` stage, a stage whose declared
  inputs changed in foreign commits (TUX-04, TUX-06).
- A protected-branch revocation list overrides every entry.

### 3.7 Identity facts

Shown: signature verification against allowed signers from outside the
work tree (key fingerprint and entry name, or "unsigned"); first change
by this key for this pack; on followed ref and since when; branch
protection status; PACK010 reproducible; widening history with "age is
not safety".

Omitted from the summary (details only, labelled unverified): git
author and committer names and emails. Omitted entirely: hosting
account age, stars, downloads, pack description and README, any pack
prose.

### 3.8 Rate limits and notices

One session per invocation; at most 5 type-to-confirm decisions per
session; at most 3 sessions per repository per day; `check` prints an
untrusted notice once per (digest, day) and otherwise only counts it.

---------------------------------------------------------------------

## 4. Verdict on the owner's proposal

The proposal is aimed at the right worry (people do not read) but puts
the effort where an attacker controls the cost. Element by element:

| Element | Verdict | Why |
|---|---|---|
| Pagination | CHANGE | Review length must be bounded by the host, not the pack (TUX-07). One fixed summary screen plus at most 5 itemized high-risk screens; everything else in a read-only details pager with no approve action. |
| Author information | DROP as a cue; KEEP verified provenance | Names, emails and account age are spoofable or bought and act as authority cues (TUX-10; xz, event-stream, GitHub's own warning). Show signature against out-of-tree allowed signers, first change by this key, on-protected-branch, reproducible, widening history. |
| Capabilities in the repository | KEEP, as grants and flows | The broker makes grants complete; review grants, never call sites (TUX-08). Add host-computed flows (read plus send) and honest classes for process stages (TUX-04). |
| Each item manually acknowledged | CHANGE | Per-item ack over all items is the volume attack's amplifier and habituates within a few repetitions (TUX-07, [2][6]). Itemize and type-to-confirm only high-risk and widened items, typing the scope, not the pack name (TUX-09); aggregate ordinary items into one decision; deny is the default. |
| Very small cooldown | KEEP, narrowly | Keep about 1 second, re-armed on keypress, with input flush and paste rejection, as an anti-typeahead and anti-fast-click measure (TUX-16, Firefox [14]). Do not add longer or per-item cooldowns: delays lose effect with habituation [6] and multiply attacker-inflated volume. |

The larger gaps are outside the prompt: `--follow` as an unreviewed
blanket grant on a locally movable, history-wide ref (TUX-01 to
TUX-03, TUX-06) and process stages whose approved argv hides that they
run the checked-out tree (TUX-04). Fixing those reduces how often
anyone sees a prompt, which [1] and [2] say is the variable that
matters most.

---------------------------------------------------------------------

## 5. References

1. D. Akhawe, A. P. Felt. Alice in Warningland: A Large-Scale Field
   Study of Browser Security Warning Effectiveness. USENIX Security
   2013. https://www.usenix.org/conference/usenixsecurity13/technical-sessions/presentation/akhawe
2. B. B. Anderson, C. B. Kirwan, J. L. Jenkins, D. Eargle, S. Howard,
   A. Vance. How Polymorphic Warnings Reduce Habituation in the Brain:
   Insights from an fMRI Study. CHI 2015. doi:10.1145/2702123.2702322
3. A. Vance, J. L. Jenkins, B. B. Anderson, D. K. Bjornn, C. B. Kirwan.
   Tuning Out Security Warnings: A Longitudinal Examination of
   Habituation Through fMRI, Eye Tracking, and Field Experiments. MIS
   Quarterly 2018. doi:10.25300/MISQ/2018/14124
4. B. B. Anderson, A. Vance, C. B. Kirwan, J. L. Jenkins, D. Eargle.
   From Warning to Wallpaper: Why the Brain Habituates to Security
   Warnings and What Can Be Done About It. JMIS 2016.
   doi:10.1080/07421222.2016.1243947
5. C. Bravo-Lillo, S. Komanduri, L. F. Cranor, R. W. Reeder, M.
   Sleeper, J. Downs, S. Schechter. Your Attention Please: Designing
   Security-Decision UIs to Make Genuine Risks Harder to Ignore. SOUPS
   2013. doi:10.1145/2501604.2501610
   https://cups.cs.cmu.edu/soups/2013/proceedings/a6_Bravo-Lillo.pdf
6. C. Bravo-Lillo, L. F. Cranor, S. Komanduri, S. Schechter, M.
   Sleeper. Harder to Ignore? Revisiting Pop-Up Fatigue and Approaches
   to Prevent It. SOUPS 2014.
   https://www.usenix.org/conference/soups2014/proceedings/presentation/bravo-lillo
7. R. Boehme, S. Koepsell. Trained to Accept? A Field Experiment on
   Consent Dialogs. CHI 2010. doi:10.1145/1753326.1753689
8. S. Egelman, L. F. Cranor, J. Hong. You've Been Warned: An Empirical
   Study of the Effectiveness of Web Browser Phishing Warnings. CHI
   2008. doi:10.1145/1357054.1357219
9. J. Sunshine, S. Egelman, H. Almuhimedi, N. Atri, L. F. Cranor.
   Crying Wolf: An Empirical Study of SSL Warning Effectiveness. USENIX
   Security 2009.
   https://www.usenix.org/legacy/event/sec09/tech/full_papers/sunshine.pdf
10. A. P. Felt, E. Ha, S. Egelman, A. Haney, E. Chin, D. Wagner. Android
    Permissions: User Attention, Comprehension, and Behavior. SOUPS
    2012. doi:10.1145/2335356.2335360
11. Android 11 permission changes (one-time permissions, auto-reset).
    https://developer.android.com/about/versions/11/privacy/permissions
    and https://developer.android.com/guide/topics/permissions/overview
12. P. Wijesekera et al. Android Permissions Remystified: A Field Study
    on Contextual Integrity. USENIX Security 2015.
    https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/wijesekera
13. Chrome extensions: permission warnings (aggregation; disabled until
    a new warning-bearing permission is accepted).
    https://developer.chrome.com/docs/extensions/develop/concepts/permission-warnings
14. Firefox `security.dialog_enable_delay` (1000 ms) in
    modules/libpref/init/all.js and `EnableDelayHelper` in
    toolkit/components/prompts/src/PromptUtils.sys.mjs.
    https://raw.githubusercontent.com/mozilla/gecko-dev/master/modules/libpref/init/all.js
    https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/prompts/src/PromptUtils.sys.mjs
15. Homebrew: Taps and Tap Trust. https://docs.brew.sh/Taps
    https://docs.brew.sh/Tap-Trust
16. pnpm 10.0.0 release notes (dependency lifecycle scripts off by
    default) and `dangerouslyAllowAllBuilds`.
    https://github.com/pnpm/pnpm/releases/tag/v10.0.0
    https://pnpm.io/settings
17. VS Code Workspace Trust.
    https://code.visualstudio.com/docs/editor/workspace-trust
18. direnv(1) and direnv-stdlib(1) (`source_up` is not checked by the
    security framework). https://direnv.net/man/direnv.1.html
    https://direnv.net/man/direnv-stdlib.1.html
19. GitHub Actions: approving workflow runs from forks, and the
    first-time contributor warning.
    https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/approving-workflow-runs-from-public-forks
    https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
20. R. Cox. Timeline of the xz open source attack.
    https://research.swtch.com/xz-timeline
21. A. Freund. backdoor in upstream xz/liblzma leading to ssh server
    compromise. oss-security, 2024-03-29.
    https://www.openwall.com/lists/oss-security/2024/03/29/4
22. npm Blog. Details about the event-stream incident.
    https://blog.npmjs.org/post/180565383195/details-about-the-event-stream-incident
23. event-stream issue 116 and GHSA-mh6f-8j2x-4483.
    https://github.com/dominictarr/event-stream/issues/116
    https://github.com/advisories/GHSA-mh6f-8j2x-4483
24. ua-parser-js malicious versions, GHSA-pjwm-rvh2-c87w.
    https://github.com/advisories/GHSA-pjwm-rvh2-c87w
25. K. Greshake et al. Not what you've signed up for: Compromising
    Real-World LLM-Integrated Applications with Indirect Prompt
    Injection. 2023. https://arxiv.org/abs/2302.12173
26. Invariant Labs. GitHub MCP Exploited: Accessing private repositories
    via MCP. https://invariantlabs.ai/blog/mcp-github-vulnerability
27. Embrace The Red. Amp Code: Arbitrary Command Execution via Prompt
    Injection Fixed (agent edits its own configuration), 2025-08-05.
    https://embracethered.com/blog/posts/2025/amp-agents-that-modify-system-configuration-and-escape/
28. S. Willison. The lethal trifecta for AI agents, 2025-06-16.
    https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
29. N. Boucher, R. Anderson. Trojan Source: Invisible Vulnerabilities.
    https://trojansource.codes/ and https://arxiv.org/abs/2111.00169
30. Unicode Technical Standard 39: Unicode Security Mechanisms
    (confusables, mixed-script detection).
    https://www.unicode.org/reports/tr39/
31. xterm control sequences, bracketed paste mode (`CSI ? 2004 h`).
    https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
32. script(1). https://man7.org/linux/man-pages/man1/script.1.html
33. gitrevisions(7), refname disambiguation order.
    https://git-scm.com/docs/gitrevisions
34. Cargo configuration (`build.rustc-wrapper`, `[alias]`).
    https://doc.rust-lang.org/cargo/reference/config.html
35. GitHub: deleting a repository (type the repository name to
    confirm).
    https://docs.github.com/en/repositories/creating-and-managing-repositories/deleting-a-repository
36. git-config `gpg.ssh.allowedSignersFile`; GitHub commit signature
    verification.
    https://git-scm.com/docs/git-config#Documentation/git-config.txt-gpgsshallowedSignersFile
    https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification
37. termios(3), `tcflush`.
    https://man7.org/linux/man-pages/man3/termios.3.html

Also consulted for background: Zimmermann et al., Small World with High
Risks: A Study of Security Threats in the npm Ecosystem, USENIX
Security 2019
(https://www.usenix.org/conference/usenixsecurity19/presentation/zimmerman);
Ohm et al., Backstabber's Knife Collection, DIMVA 2020
(doi:10.1007/978-3-030-52683-2_2); npm scripts docs
(https://docs.npmjs.com/cli/v10/using-npm/scripts).

---------------------------------------------------------------------

## 6. Notes

Checked and found sound (the fixer need not re-verify):

- Pack-supplied prose is excluded from the prompt (2.3 line 107); this
  closes the description-based persuasion route, leaving only the
  authored-field route of TUX-11.
- No `--yes`, no `--all`, `requires_human = true` in the JSON remedy:
  correct against scripts and obedient agents (TUX-05 states the
  limit).
- CI base-ref trust (`--trust-from` at the merge base, never a user
  store) is not affected by TUX-02 or TUX-03; the CI semantics are the
  model the local follow should copy.
- Secret-shaped effects are a separate class never implied by a glob
  (2.6); this already defeats the "one `**` glob hides `.env`" form of
  attack (b1).
- Reserved provenance prefixes and ASCII kebab pack names (2.8,
  packs.md line 125) remove Unicode homoglyph pack names; only ASCII
  near-misses remain (TUX-17).
- GATE001 makes grant widening visible in the PR; TUX-06 only argues
  that a label is too cheap to be the sole gate for developer machines.
- The tree digest covering data and text (2.1) means the xz-style
  "payload in test data" changes the digest and needs trust; TUX-08
  argues the reviewer should still not be asked to find it in code.

Deliberately skipped or only skimmed:

- The broker, sandbox and wasmtime mechanics (2.5) beyond what the
  review unit needs; the previous audit covers them.
- exceptions.md (the reviewer label and exception path that clears
  GATE001) was not read; how cheap a GATE001 clearance is in practice
  should be checked there.
- gui.md: a future GUI trust dialog inherits every finding here and
  adds clickjacking and focus-stealing, which Firefox's delay helper
  [14] addresses; not audited.
- Hosting API details for branch-protection checks (TUX-18) were taken
  from mirror design 2.11 without re-reading mirror.md.
- Agent marker variables other than `CLAUDECODE` were not verified;
  the mitigation in TUX-05 should use a maintained list and treat it as
  advisory.
- Citations were fetched and checked for the quoted claims on
  2026-10-02; numbers from [1], [5], [6], [10] are quoted from their
  abstracts or text; [2], [3], [4], [7], [8], [12] are summarized from
  their published abstracts and titles (DOIs verified via Crossref,
  full text behind ACM/MISQ paywalls not fetched).
