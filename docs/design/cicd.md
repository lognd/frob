# CI/CD and deployment languages

Status: draft
Owner: grimble
Decisions: D60
Audience: contributor

Provenance: DRAFT under T-0001; decision D60 is accepted (2026-10-04).
Ownership note: grimble (family CI and DK in the crate `grimble-ci`, boundaries.md
section 2.5). Evidence:
notes/research/cicd-survey.md (1069 repositories: 249 curated developer
tools plus 820 top-starred per language; 9890 GitHub Actions workflows,
23425 jobs, 764 Dockerfiles, 389 Dependabot configs; zizmor and
actionlint run over the corpus; scripts re-runnable from the session
scratchpad, raw data kept out of the repo). Depends on
docs/design/universal-model.md and docs/design/rules.md.

## 1. What the field does

The sample is stars-ranked, not usage-ranked, and detection is YAML
heuristics, so every figure carries a few points of error. The shape is
clear anyway (percent of the 930 repositories on GitHub Actions unless
stated):

| Practice | Prevalence | Reading |
|---|---|---|
| GitHub Actions as the CI | 87.0 percent of all 1069 | the one platform worth first-class support |
| `push` and `pull_request` triggers; matrix builds; `workflow_dispatch` | 95.1, 93.1, 77.3, 71.6 | universal shape: build on both events, across OS and versions |
| every external action pinned to a commit SHA | 23.4 (58.8 percent of all `uses:` refs) | the largest gap between advice and practice |
| top-level `permissions` in every workflow | 21.6 | least privilege is rare |
| `concurrency` declared | 54.9 | half cancel superseded runs |
| `timeout-minutes` on every job | 2.6 (75 percent of jobs have none) | almost nobody bounds a hung job |
| zizmor: at least one high-severity finding | 88.9 | `unpinned-uses` 73.0, `excessive-permissions` 72.8, `artipacked` 85.8, `template-injection` 47.7 |
| provenance attestations; sigstore; SBOM; scorecard; zizmor in CI | 12.3, 5.9, 6.3, 7.2, 10.5 | supply-chain evidence is the frontier, not the norm |
| trusted publishing (OIDC) among PyPI publishers; among crates.io publishers | 72, 68 | token-less publishing has won where registries support it |
| Dockerfiles present; Helm; Terraform; Ansible; Pulumi or CDK | 38 percent of repos; 3.9; 3.7; 1.4; 0 | containers are common, infrastructure languages rare in tool repos |

What a repository cannot show, so no rule may claim it: branch
protection, required checks, the default token permission setting,
environment secrets, rulesets. Rules about these are Unresolved by
construction and say so.

## 2. What the practices protect against

| Threat or failure | Practices that address it |
|---|---|
| Compromised third-party action (supply chain) | SHA pinning, Dependabot or Renovate on actions, scorecard, zizmor |
| Token exfiltration and privilege escalation | top-level `permissions: contents: read`, job-level grants, no `pull_request_target` with head checkout, `persist-credentials: false` |
| Script injection through event data | no `${{ github.event.* }}` inside `run:`; env indirection |
| Release mistakes and forged artifacts | publish only from tags or releases, OIDC trusted publishing, provenance attestations, signing, SBOM |
| Hung or runaway CI cost | `timeout-minutes`, `concurrency` with cancel-in-progress |
| Platform regressions | OS and version matrices, MSRV jobs, cross-compilation |
| Dependency and licence drift | Dependabot, Renovate, cargo-deny, lockfiles committed |
| Docs rot and unreproducible builds | pages deploy from CI, pinned toolchains, Nix flakes, devcontainers |

## 3. Decision: bind the security tools, own the policy and consistency rules

The design goblin does not rebuild zizmor, actionlint, hadolint,
checkov, tflint, kube-linter or ansible-lint. Their checks overlap the structural
security rules almost entirely and parity would be a treadmill against
GitHub's schema. frob orchestrates them through `[[check.tool]]` stages
with JSON parsers (zizmor `--format json-v1`, actionlint `-format '{{json
.}}'`) so their findings carry frob ids, exceptions, evidence and
Unresolved semantics. Two bindings are mandatory lessons from the
corpus: actionlint's `runner-label` noise needs the repository's custom
labels passed in, and a tool that lags the GitHub schema returns
Unresolved, not a violation.

grimble owns (family CI and DK) what those tools cannot see: presence and policy rules that a
repository decides (which permissions, which timeouts, publish only from
tags, OIDC required) and cross-file consistency between CI and the
repository (the toolchain pinned in CI equals rust-toolchain.toml; the
lint command in CI equals the one frob runs; a workflow that publishes a
crate exists for every publishable crate; Dependabot covers every
ecosystem present). These are joins over the universal model between
the workflow language and the manifests (CI012 reads the manifests
through the F2 manifest adapter, grimble-model.md 9.8), which is
exactly the cross-language structure the universal model exists for.

## 4. CI/CD files as languages in the universal model

GitHub Actions YAML: a workflow is a `unit(kind=workflow)` with
`group(order=concurrent)` of jobs; each job is a `unit` with
`group(order=sequence)` of steps; `uses:` is `apply(kind=instantiate)`
whose head resolves to an external identity (owner/repo@ref) with
status Must when SHA-pinned, May when tag-pinned (the referent can
move); `needs:` is `apply(kind=dependency)`; triggers are entrypoints
(`attr(on)`); `permissions`, `concurrency`, `timeout-minutes` are
`attr` nodes; `${{ }}` expressions are a `region(kind=embedded,
lang=actions-expr)` with references into the event context (a scope
the adapter models as an external, May-status scope); `run:` bodies are
`region(kind=embedded, lang=shell)` and shell is a language with
string-code opaqueness (universal-model.md 4.6). Reusable workflows and
composite actions are units in other artifacts; `secrets: inherit` is a
flow edge the model can see.

Dockerfile: one `unit` per stage (`FROM ... AS name`), `FROM` is
`apply(kind=instantiate)` to an image identity (Must when digest-pinned,
May for tags, Unknown for `latest`), `COPY --from` is a dependency edge
between stages, `RUN` is an embedded shell region, `USER`, `EXPOSE`,
`HEALTHCHECK` are attributes.

Terraform and Helm: resources and templates are units; references are
Must inside a module, May across providers until schemas are loaded;
both need an external binary or provider schema for anything beyond
F2, which is why they are bound rather than owned.

Fidelity targets: GitHub Actions F3 first (a CST-preserving YAML
reader with the `gha-expr` and shell islands as regions; the survey,
section 9.4) and F4 once comments and pin comments bind to targets,
Dockerfile F3 (own adapter, small grammar), Terraform and Helm F1 through tree-sitter with
bound tools for the rest.

## 5. The CI and DK rule families

Each rule names its threat, a decidable predicate over the U encoding
in section 4, its polarity (universal-model.md 4.2), a default severity
and who implements it. Corpus rates are in the research note
(notes/research/cicd-survey.md section 9.3, the numbering authority:
ids are permanent, D32). A repository overrides severity with
`[rules.<id>] severity` (there is no separate severity table). Every
threshold and list is a materialized knob under `[ci]` in
`grimble.toml`. The survey's severity "note" is Advisory here.

| Id | Rule and predicate | Polarity | Default | Implemented by |
|---|---|---|---|---|
| CI001 | pinned-ref: no external `uses:` whose ref is not a 40-hex SHA unless the owner is in `allow_tag_pins_for` | P+ | Warn | bind zizmor `unpinned-uses`; grimble fallback |
| CI002 | permissions-declared: a workflow with no top-level `permissions` and not every job declaring `permissions` | P- | Warn | grimble |
| CI003 | no-top-level-write: top-level `permissions` contains a `write` scope or `write-all` | P+ | Warn | grimble (zizmor overlaps) |
| CI004 | concurrency-on-pr: a push or pull_request workflow with no `concurrency` at workflow or job level | P- | Advisory | grimble |
| CI005 | job-timeout: a job (not a reusable-workflow call) without `timeout-minutes`, or above `max_timeout` | P- | Advisory | grimble |
| CI006 | no-prt-head-checkout: a `pull_request_target` or `workflow_run` workflow with a checkout whose ref or repository names the PR head | P+ | Error | bind zizmor `dangerous-triggers`; grimble fallback |
| CI007 | no-event-interpolation-in-run: a `run:` text containing an expression whose context is in the `contexts` set (title, body, head ref, commit message and similar); a lexical scan of the opaque shell payload (universal-model.md 2.2) | P+ | Error (narrow set), Advisory (broad) | bind zizmor `template-injection` |
| CI008 | publish-only-from-tag: a registry publish step in a workflow triggered by pull_request, pull_request_target or an untagged push | P+ | Warn | grimble (`registries` vocabulary) |
| CI009 | publish-via-oidc: a publish job for a trusted-publishing registry that uses a token-named secret and lacks `id-token: write` | P+ | Advisory (Warn in strict) | grimble |
| CI010 | checkout-no-persist: `actions/checkout` without `persist-credentials: false` in a workflow that uploads artifacts or runs third-party code | P+ | Advisory | bind zizmor `artipacked` |
| CI011 | prt-least-token: a `pull_request_target` workflow without explicit read-only `permissions` | P- | Error | grimble |
| CI012 | ci-repo-consistency: toolchain pin file versus workflow toolchain, `rust-version` versus the matrix, Dependabot ecosystems versus manifests, CODEOWNERS covering `.github/**`, frob verbs versus workflow commands | P0 | Warn | grimble (the unique join, through the F2 manifest adapter) |
| CI013 | no-secrets-inherit: a job calling an external reusable workflow with `secrets: inherit` | P+ | Advisory | bind zizmor `secrets-inherit` |
| CI014 | gha-syntax-and-schema: any actionlint finding other than an unknown runner label when labels are not configured | P+ | Warn | bind actionlint; Unresolved on schema lag |
| CI015 | action-currency: an external action from an archived repository or on an end-of-life Node runtime (an offline table; "pin behind the latest release" is covered by Dependabot or Renovate presence under CI012, and an opt-in online check is `frob audit --online`, open question 3) | P+ | Advisory | bind zizmor `archived-uses` and actionlint |
| CI016 | trust-from-protected-ref: a `pull_request_target` or `workflow_run` workflow runs frob, grimble or crunk with any trust other than `--trust-from` a protected ref (security.md 2.11, D82) | P+ | Error | native |
| DK001 | docker-non-root: the final stage has no `USER` other than root or 0 | P- | Advisory | grimble or hadolint DL3002 |
| DK002 | docker-base-pinned: an external `FROM` without an `@sha256:` digest | P+ | Off (opt-in; needs automation) | grimble |
| DK003 | docker-no-latest: an external `FROM` with no tag or `:latest` | P+ | Warn | grimble or hadolint DL3006 and DL3007 |
| DK004 | docker-no-pipe-to-shell: a `RUN` text in which `curl` or `wget` output is piped to `sh` or `bash`; a lexical scan of the opaque shell payload; allowlist by URL host | P+ | Advisory | grimble or hadolint |

Terraform, Helm, Kubernetes and Ansible: bind checkov, tflint,
kube-linter and ansible-lint; nothing is owned there until a
repository in the fleet needs it.

## 6. Where this lands

CI and DK are grimble families (D4 of the 2026-10-04 consistency pass,
README D63): the placement test of boundaries.md holds because these
rules make sense in a repository with no tickets, docs policy or release
process. They are implemented in a new crate `grimble-ci`; NEAT stays in
`grimble-lints`. The GitHub Actions and Dockerfile adapters live in
gob-languages behind features `actions` and `dockerfile`, with
gob-symbols adapters producing the U terms. frob orchestrates through
the sibling contract (grimble-model.md 9.5) and through `[[check.tool]]`
stages. The adapters are milestone-2 tickets after gob-ir (build-test-ci.md,
Milestone 2 item 7); this repository adopts zizmor and actionlint
through frob's `[[check.tool]]` stage first, before the adapters exist,
with their JSON parsers and id maps in frob-check.

## 7. Open questions for the owner

1. Default severities: should CI006 and CI007 (injection and token
   theft) be Error from the start even though a quarter of top
   repositories would fail, or Warn with a ratchet?
2. Should frob ship a generated "CI baseline" for new repositories
   (`frob init --ci`: pinned actions, read-only permissions, timeouts,
   concurrency, OIDC publish templates per ecosystem), given that the
   survey shows the defaults are what most repositories never fix?
3. CI015 needs the network to know the latest release; keep it offline-
   Unresolved and rely on Dependabot presence, or allow an opt-in online
   check?
