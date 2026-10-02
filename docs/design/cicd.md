# CI/CD and deployment languages

Status: DRAFT under T-0001, for owner review. Evidence:
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

frob does not rebuild zizmor, actionlint, hadolint, checkov, tflint,
kube-linter or ansible-lint. Their checks overlap the structural
security rules almost entirely and parity would be a treadmill against
GitHub's schema. frob binds them through `[[check.tool]]` stages with
JSON parsers (zizmor `--format json-v1`, actionlint `-format '{{json
.}}'`) so their findings carry frob ids, exceptions, evidence and
Unresolved semantics. Two bindings are mandatory lessons from the
corpus: actionlint's `runner-label` noise needs the repository's custom
labels passed in, and a tool that lags the GitHub schema returns
Unresolved, not a violation.

frob owns what those tools cannot see: presence and policy rules that a
repository decides (which permissions, which timeouts, publish only from
tags, OIDC required) and cross-file consistency between CI and the
repository (the toolchain pinned in CI equals rust-toolchain.toml; the
lint command in CI equals the one frob runs; a workflow that publishes a
crate exists for every publishable crate; Dependabot covers every
ecosystem present). These are joins over the universal model between
the workflow language and the manifests, which is exactly the
cross-language structure frob exists for.

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
flow edge frob can see.

Dockerfile: one `unit` per stage (`FROM ... AS name`), `FROM` is
`apply(kind=instantiate)` to an image identity (Must when digest-pinned,
May for tags, Unknown for `latest`), `COPY --from` is a dependency edge
between stages, `RUN` is an embedded shell region, `USER`, `EXPOSE`,
`HEALTHCHECK` are attributes.

Terraform and Helm: resources and templates are units; references are
Must inside a module, May across providers until schemas are loaded;
both need an external binary or provider schema for anything beyond
F2, which is why they are bound rather than owned.

Fidelity targets: GitHub Actions F4 (own adapter), Dockerfile F3 (own
adapter, small grammar), Terraform and Helm F1 through tree-sitter with
bound tools for the rest.

## 5. The CI and DK rule families

Each rule names its threat, a decidable predicate over the U encoding
in section 4, its polarity, the measured violation rate in the corpus,
and its false-positive risk (full table in the research note, section
8). Severities default to Warn; a repository promotes them through
`[gates.severity]`. Every threshold and list is a materialized knob
under `[ci]`.

| Id | Rule | Owner | Corpus | Notes |
|---|---|---|---|---|
| CI001 | pinned-ref: every external `uses:` is a commit SHA (local and same-repo refs exempt) | bind zizmor `unpinned-uses`; frob fallback | 76.5 percent violate | knob `allow_tag_pins_for` for verified publishers |
| CI002 | permissions-declared: top-level `permissions` present in every workflow | frob | 78 percent violate | P- |
| CI003 | no-top-level-write: top-level grants are read-only; writes are job-level | frob (zizmor overlaps) | | |
| CI004 | concurrency-on-pr: `pull_request` workflows declare `concurrency` with cancel | frob | 45 percent violate | cost rule, Advisory by default |
| CI005 | job-timeout: every job has `timeout-minutes` (knob `max_timeout`) | frob | 75 percent of jobs | |
| CI006 | no-pull_request_target-head-checkout | bind zizmor `dangerous-triggers` | 26 repos | Error by default |
| CI007 | no-event-interpolation-in-run: no `${{ github.event.* }}` or other attacker-controlled contexts in `run:` | bind zizmor `template-injection` | 280 repos on the broad list | knob `contexts` |
| CI008 | publish-only-from-tag: steps that publish to a registry run only on tag or release triggers | frob | | registry step vocabulary knob |
| CI009 | publish-via-oidc: PyPI and crates.io publishing uses trusted publishing, no long-lived token | frob | 28 to 32 percent of publishers violate | |
| CI010 | checkout-no-persist: `persist-credentials: false` where the token is not needed later | bind zizmor `artipacked` | 85.8 percent | Advisory |
| CI011 | pull_request_target-least-token | frob | | |
| CI012 | ci-repo-consistency: toolchain, lint and test commands, publishable crates, Dependabot ecosystems match the repository | frob (unique) | | the cross-language join |
| CI013 | no-secrets-inherit to third-party reusable workflows | frob | | |
| CI014 | gha-syntax-and-schema | bind actionlint | | Unresolved on schema lag |
| CI015 | action-currency: pinned SHA behind the latest release beyond `max_age_days` | frob via Dependabot or Renovate presence; direct check needs network and is Unresolved offline | | |
| DK001 | non-root USER in the final stage | frob | | |
| DK002 | no `latest` tag in FROM | frob | | |
| DK003 | digest-pinned base images | frob | | |
| DK004 | no pipe-to-shell (`curl ... | sh`) in RUN | frob | | shell region scan, May |

Terraform, Helm, Kubernetes and Ansible: bind checkov, tflint,
kube-linter and ansible-lint; frob owns nothing there until a
repository in the fleet needs it.

## 6. Where this lands

CI and DK are frob families (work accounting of the repository's own
automation), not grimble families; grimble may later lint architecture
constraints over the CI graph (which jobs may deploy where) as a data
pack. The GitHub Actions and Dockerfile adapters are milestone-2
tickets after gob-ir; the tool bindings for zizmor and actionlint can
land earlier as `[[check.tool]]` entries with JSON parsers, which this
repository should adopt for its own CI first.

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
