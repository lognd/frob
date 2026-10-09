# CI/CD and deployment survey: what the most used open-source projects do, and what frob should lint

Status: research input for build-test-ci.md and rules.md (a candidate CI rule family). ASCII only.
Date of data: 2026-10-02 (GitHub default branches as of that day). Nothing here ran cargo or frob.

## 0. Honest status line

- Universe (denominator): 1069 repositories sampled, 249 curated developer tools and
  infrastructure projects ("tools" below) plus 820 top-by-stars repositories per primary language
  ("libs/apps" below). 972 (90.9%) show any CI; 930 (87.0%) use GitHub Actions; 9894 workflow
  files were downloaded and 9890 parsed (4 failed YAML parse). All numbers below are against
  these denominators and every table says which one.
- Blocked / not done: (a) the sample is smaller than "the 1000 most used" in the sense that it is
  stars-ranked, not usage-ranked (no download-count source was used); (b) zizmor refused to audit
  35 of the 930 workflow directories (configuration or YAML-anchor errors, "fatal: no audit was
  performed"), so zizmor finding rates are over 895 audited repositories, not 930, and I report
  them over 930 (a slight undercount); (c) hadolint, checkov, tflint, kube-linter and ansible-lint
  were NOT run (not installed; no network install attempted beyond zizmor and actionlint); (d)
  Dockerfile bodies were fetched for 409 of 473 repositories that have a Dockerfile (depth <= 2,
  at most 3 files per repository, test/fixture/example paths excluded); (e) 17 repositories had
  truncated recursive trees (nixpkgs, linux, llvm-project, rust-lang/rust and others), for those
  the root tree plus `.github` and `.github/workflows` listings were used, so deployment-language
  directory counts (Helm, Terraform, k8s) are lower bounds for them.
- Pending: 0 repositories (all 1069 trees fetched, 0 tree errors after one retry of webpack/webpack).
  Curated checklist: 250 names, 244 resolved as asked, 5 renamed, 1 not found (section 1.3).
- Phase-2 verdict: coverage of the declared sample is complete; coverage of the declared goal
  ("1000 most used") is approximate and star-biased. Detection of practices is regex/YAML
  heuristics; each prevalence is a point estimate with a few points of classification error (the
  "test" detector in particular is loose, see 2.4). Settings that live outside the repository
  cannot be seen at all (section 8).

Headline numbers (details follow):

1. GitHub Actions is the CI of 87.0% of the sample (96.4% of tools, 84.1% of libs/apps); any
   detected CI 90.9%; 11.6% run GHA plus a second system; legacy-only systems (Travis, AppVeyor,
   CircleCI, Azure) are a few percent each.
2. `actions/checkout` appears in 98.7% of GHA repositories, `push` and `pull_request` triggers in
   95.1% and 93.1%, a test step in ~90%, matrix builds in 77.3%, `workflow_dispatch` in 71.6%.
3. Hardening is the opposite picture: only 23.4% of repositories SHA-pin every external action
   (though 58.8% of all `uses:` references are SHA-pinned), only 21.6% declare top-level
   `permissions` in every workflow, only 54.9% declare `concurrency`, 37.1% have any
   `timeout-minutes`, 2.6% have them on every job.
4. 73.0% of repositories trip zizmor `unpinned-uses` (high severity), 72.8% `excessive-permissions`,
   85.8% `artipacked`, 47.7% `template-injection`, 28.2% `dangerous-triggers`; 827 of 930 have at
   least one high-severity zizmor finding.
5. Supply-chain evidence is rare outside the very top: provenance/attestation 12.3%, sigstore 5.9%,
   SBOM 6.3%, OpenSSF scorecard 7.2%, zizmor in CI 10.5% (28.3% of tools), actionlint in CI 4.9%.

Rule candidates (section 9): CI001 pinned-ref, CI002 permissions-declared, CI003 no-top-level-write,
CI004 concurrency-on-pr, CI005 job-timeout, CI006 no-prt-head-checkout, CI007 no-event-interpolation-in-run,
CI008 publish-only-from-tag, CI009 publish-via-oidc, CI010 checkout-no-persist, CI011 prt-least-token,
CI012 ci-repo-consistency (cross-file joins), plus DK001..DK004 for Dockerfiles. Recommendation: bind
zizmor and actionlint through a tool stage, own the small join/policy rules, do not reimplement the
security audit corpus.

## 1. Sample

### 1.1 Construction

Scripts and raw data live under the session scratchpad
`<scratchpad>/cicd/`
(never in the repo): `01_sample.py` (sample), `02_fetch.py` (trees and workflow bodies),
`03_lint.py` (zizmor and actionlint), `04_analyze.py` (feature extraction to `features.json`),
`05_stats.py` (tables to `stats.txt`), `06_perwf.py` (per-workflow rule violation rates to `perwf.txt`),
`07_docker.py` and `08_docker_an.py` (Dockerfiles and dependabot to `docker.txt`). Raw: `sample.json`,
`curated_status.json`, `trees/`, `workflows/`, `docker/`, `dependabot/`, `lint_findings.json`,
`repo_viol.json`. All re-runnable; fetching is resumable (cached by file).

A previous agent had produced `01_sample.py`, `curated.txt` and `curated_status.json` and was stopped
before the sample was written. I reused them and fixed two defects: `gh api search/repositories -f ...`
silently becomes a POST (404), so the script now passes `--method GET`; and the curated pass was made
skippable once `sample.json` exists. The previous curated list is a superset of the task's list
(250 names; it added git, curl, openssl, ripgrep, cargo-nextest, home-assistant, airflow, spark, kafka,
bevy, polars, llama.cpp, setuptools, pip, webpack, babel and others).

Sampling procedure:

- Curated: each `owner/name` was resolved through `repos/{o}/{r}`; a redirect (rename) is
  recorded. 249 resolved (244 exact, 5 renamed), 1 not found. All 249 are marked `tool = true`
  (the label is "curated developer tool or infrastructure project"; it includes some libraries and
  frameworks such as react, django and serde that the task listed in the curated set).
- Per language: `search/repositories?q=language:L stars:>500&sort=stars`, first N results not already in
  the sample (so the language counts are "next 50 beyond the curated ones", which biases the language
  buckets slightly away from the very biggest projects). N = 50 for Rust, Python, Go, Java, Kotlin, C,
  C++, C#, Ruby, Swift, Zig, Haskell, OCaml, Elixir, Scala; N = 35 for TypeScript and JavaScript (the earlier agent's choice, since
  many of their giants are already in the curated set; the brief asked for about 50 each, so these two
  buckets are 15 short of it but the curated set holds 40 JS/TS tools).
  820 repositories. These are `tool = false` ("libs/apps").
- Total: 249 + 820 = **1069** repositories. Minimum stars 420 (public-apis/public-apis; star counts drifted
  between query and read), maximum 485528.
  37 are archived. 97 have no CI of any kind (mostly curated-list/tutorial/documentation repositories
  that rank high by stars: awesome lists, system-design-primer, HelloGitHub; and mirrors whose real
  CI is elsewhere: golang/go (Gerrit/LUCI), ziglang/zig (moved off GitHub), gcc-mirror/gcc,
  istio/istio (Prow), sqlite/sqlite (Fossil)).

Primary language of the curated tools: Go 67, Rust 54, Python 43, TypeScript 27, JavaScript 13,
C++ 11, C 11, Ruby 5, others.

Per-language GHA adoption (repos with workflows / repos sampled): Rust 102/104, TypeScript 62/62,
Go 112/117, Ruby 51/55, C++ 54/61, Python 85/93, Java 46/55, JavaScript 40/48, C 47/61, Haskell 41/52,
Zig 40/51, Scala 35/51, C# 43/51, Kotlin 44/50, Swift 38/50, OCaml 36/50, Elixir 46/50.

### 1.2 Fetch per repository

The brief planned about 3 calls per repo. Actual: 1 call per repo (`git/trees/{branch}?recursive=1`,
which lists every path including `.github/workflows/*`, `.github/dependabot.yml`, charts and
Terraform directories) and, for the 17 truncated trees, 1 root-tree call plus up to 7 `contents`
listings. File bodies came from raw.githubusercontent.com (uncounted). `gh api rate_limit` reported 5000 of 5000 remaining at
every check including after the run, which is implausible for ~1400 calls, so I could not verify metering;
by plan the usage was about 1400 core calls of the 5000 budget.

### 1.3 Curated checklist: not found or renamed

| asked | result |
|---|---|
| vercel/turbo | renamed to vercel/turborepo |
| containers/podman | now podman-container-tools/podman |
| rustwasm/wasm-pack | now wasm-bindgen/wasm-pack |
| facebook/react | now react/react |
| prisma/prisma | now prisma/orm |
| forgejo/forgejo | NOT FOUND on GitHub (Forgejo develops on Codeberg); not in the sample |

The other 244 of 250 resolved as asked. Of the task's own curated names, "pypy mirror" resolved to
pypy/pypy, "nginx mirror" to nginx/nginx, "postgres mirror" to postgres/postgres, "sqlite mirror" to
sqlite/sqlite (a mirror: no CI, Fossil), "codeql cli" to github/codeql-cli-binaries (binaries repo,
little CI), "tekton pipeline" to tektoncd/pipeline, "vscode" to microsoft/vscode.

Tools with no CI detectable on the GitHub copy: golang/go, ziglang/zig, gcc-mirror/gcc, istio/istio,
sqlite/sqlite. The practical consequence for any frob CI rule: a project's CI may legitimately
live off GitHub (Gerrit, Prow, Buildbot, Fossil, Forgejo), so "no workflow" is Unknown, not a finding.

## 2. Prevalence tables

Columns: all / tools (curated, n=249) / libs and apps (language buckets, n=820). Denominator is stated
per table: "all repos" (1069 / 249 / 820) or "GHA repos" (930 / 240 / 690).

### 2.1 CI systems (denominator: all repos)

| item | all | tools | libs/apps |
|---|---|---|---|
| any CI detected | 90.9% (972/1069) | 98.0% (244/249) | 88.8% (728/820) |
| GitHub Actions | 87.0% (930/1069) | 96.4% (240/249) | 84.1% (690/820) |
| GHA plus another CI | 11.6% (124) | 15.7% (39) | 10.4% (85) |
| non-GHA CI only | 3.9% (42) | 1.6% (4) | 4.6% (38) |
| Travis | 4.9% (52) | 0.4% (1) | 6.2% (51) |
| AppVeyor | 4.2% (45) | 6.4% (16) | 3.5% (29) |
| CircleCI | 3.1% (33) | 4.0% (10) | 2.8% (23) |
| Azure Pipelines | 2.3% (25) | 4.8% (12) | 1.6% (13) |
| Buildkite | 0.9% (10) | 1.2% (3) | 0.9% (7) |
| GitLab CI | 0.8% (9) | 1.6% (4) | 0.6% (5) |
| Jenkinsfile | 0.7% (8) | 1.2% (3) | 0.6% (5) |
| Cirrus | 0.3% (3) | 0.4% (1) | 0.2% (2) |
| Drone | 0.2% (2) | 0.0% | 0.2% (2) |

Travis and AppVeyor files are largely stale leftovers (Travis is 6.2% of libs but 0.4% of tools,
the tools having migrated); AppVeyor survives for Windows builds in 6.4% of tools.

Workflow volume: median 6 workflow files per GHA repository; 85.3% have >= 2, 55.1% >= 5, 34.7% >= 10
(tools: 95.8% / 79.2% / 58.8%). 9894 workflow files, 23425 jobs in total (20428 ordinary jobs, 2997
jobs that call a reusable workflow).

### 2.2 Repository files (denominator: all repos)

| item | all | tools | libs/apps |
|---|---|---|---|
| Dockerfile anywhere (or Containerfile) | 44.2% (473) | 57.0% | 40.4% |
| Dockerfile at root | 19.8% (212) | 24.5% | 18.4% |
| docker-compose / compose.yaml | 19.0% (203) | 18.9% | 19.0% |
| Makefile (root) | 24.8% (265) | 32.9% | 22.3% |
| justfile | 2.4% (26) | 4.0% | 2.0% |
| Taskfile | 0.7% (8) | 1.2% | 0.6% |
| flake.nix | 9.8% (105) | 8.8% | 10.1% |
| shell.nix or default.nix | 3.6% (39) | 4.8% | 3.3% |
| .pre-commit-config.yaml | 8.2% (88) | 18.9% | 5.0% |
| renovate config | 9.5% (102) | 22.9% | 5.5% |
| .github/dependabot.yml | 36.7% (392) | 56.6% | 30.6% |
| renovate or dependabot | 44.7% (478) | 76.7% | 35.0% |
| CODEOWNERS | 23.6% (252) | 41.0% | 18.3% |
| SECURITY.md | 36.0% (385) | 55.8% | 30.0% |
| .github/release.yml | 2.8% (30) | 3.6% | 2.6% |
| release-please config | 1.9% (20) | 3.2% | 1.5% |
| goreleaser config | 4.0% (43) | 10.8% | 2.0% |
| cargo-dist (dist-workspace.toml) | 0.5% (5) | 2.0% | 0.0% |
| pyproject.toml (root) | 9.3% (99) | 21.7% | 5.5% |
| deny.toml | 3.6% (39) | 9.2% | 2.0% |
| .editorconfig | 27.7% (296) | 39.4% | 24.1% |
| rust-toolchain(.toml) | 4.9% (52) | 12.0% | 2.7% |
| .nvmrc / .tool-versions / mise.toml / .python-version / .go-version | 12.3% (131) | 19.7% | 10.0% |
| .devcontainer | 13.4% (143) | 23.7% | 10.2% |
| CITATION.cff | 3.2% (34) | 6.4% | 2.2% |
| CHANGELOG / CHANGES / HISTORY / NEWS | 40.4% (432) | 47.4% | 38.3% |
| towncrier / changesets / newsfragments | 1.8% (19) | 4.4% | 1.0% |
| Helm chart (Chart.yaml anywhere) | 3.9% (42) | 8.4% | 2.6% |
| Terraform (.tf anywhere) | 3.7% (40) | 10.4% | 1.7% |
| Terragrunt | 0.3% (3) | 0.8% | 0.1% |
| k8s-looking dirs (k8s, kubernetes, manifests, deploy, ... with YAML) | 5.4% (58) | 11.6% | 3.5% |
| kustomization.yaml | 2.0% (21) | 7.2% | 0.4% |
| Ansible (playbooks/, roles/, ansible.cfg) | 1.4% (15) | 3.2% | 0.9% |
| Pulumi.yaml, cdk.json | 0.0% (0) | 0.0% | 0.0% |
| codecov.yml | 9.7% (104) | 23.3% | 5.6% |
| lockfile (Cargo.lock, package-lock, pnpm, yarn, uv, poetry, go.sum, Gemfile.lock, bun) | 36.9% (394) | 67.9% | 27.4% |
| rustfmt.toml | 8.2% (88) | 18.9% | 5.0% |
| clippy.toml | 5.2% (56) | 14.1% | 2.6% |
| .github/zizmor.yml | 3.1% (33) | 10.0% | 1.0% |
| issue templates | 67.1% (717) | 85.9% | 61.3% |
| PR template | 45.7% (489) | 65.9% | 39.6% |
| CONTRIBUTING | 69.4% (742) | 88.4% | 63.7% |
| .github/codeql/ config | 1.9% (20) | 2.8% | 1.6% |

Caveats: Pulumi and CDK probes look only at `Pulumi.yaml` and `cdk.json` by basename anywhere; 0 hits
means no project in this sample ships Pulumi/CDK projects (the Pulumi and aws-cdk repositories
themselves ship them under other layouts). Lockfile prevalence is depressed by the library
convention (libraries do not commit lockfiles in Rust/Python/Ruby) and by monorepos with non-root lockfiles.
Terraform hits for tools are mostly provider/CLI repositories whose test fixtures, examples or
acceptance tests contain `.tf` (terraform, opentofu, consul, vault, nomad, cockroach, trivy, checkov,
semgrep, flux2 ...); true "infrastructure as code deployed by the project" is rarer.

### 2.3 Triggers and structure (denominator: GHA repos)

| item | all | tools | libs/apps |
|---|---|---|---|
| push | 95.1% (884/930) | 97.9% | 94.1% |
| pull_request | 93.1% (866) | 97.9% | 91.4% |
| push and pull_request | 90.5% (842) | 96.2% | 88.6% |
| workflow_dispatch | 71.6% (666) | 84.2% | 67.2% |
| schedule | 56.5% (525) | 81.2% | 47.8% |
| pull_request_target | 29.1% (271) | 45.0% | 23.6% |
| workflow_call (reusable defined) | 24.9% (232) | 41.2% | 19.3% |
| release | 19.5% (181) | 23.3% | 18.1% |
| issues | 20.0% (186) | 28.3% | 17.1% |
| issue_comment | 18.5% (172) | 31.2% | 14.1% |
| workflow_run | 15.3% (142) | 25.4% | 11.7% |
| merge_group (merge queue) | 11.7% (109) | 23.3% | 7.7% |
| pull_request_review | 5.1% (47) | 7.1% | 4.3% |
| calls a reusable workflow | 29.1% (271) | 49.2% | 22.2% |
| matrix used | 77.3% (719) | 91.7% | 72.3% |
| matrix over OS | 47.2% (439) | 62.9% | 41.7% |
| matrix over language/toolchain version | 24.5% (228) | 35.0% | 20.9% |
| runner family ubuntu | 94.8% (882) | 100.0% | 93.0% |
| runner family windows | 25.8% (240) | 29.6% | 24.5% |
| runner family macos | 25.2% (234) | 25.4% | 25.1% |
| all three OS families | 15.8% (147) | 18.3% | 14.9% |
| self-hosted runner label | 5.2% (48) | 7.1% | 4.5% |
| arm runner or arm target | 11.9% (111) | 19.6% | 9.3% |
| `environment:` used (deployment protection hook) | 25.5% (237) | 36.7% | 21.6% |

Note on pull_request_target: 29.1% looks alarming and is mostly labelers, stale-bots, PR-title lint and
comment bots, which never check out PR code. The dangerous subset is in 2.5.

### 2.4 Practices detected in workflow text (denominator: GHA repos)

Detected by regular expressions over non-comment workflow text per repository (any workflow). The
"test" regex includes the word `check` and `\btest\b` and is therefore an upper bound.

| item | all | tools | libs/apps |
|---|---|---|---|
| test step | 89.8% (835) | 99.2% | 86.5% |
| lint step | 57.1% (531) | 81.7% | 48.6% |
| format check | 55.8% (519) | 75.0% | 49.1% |
| typecheck | 23.2% (216) | 39.2% | 17.7% |
| coverage tooling | 25.8% (240) | 42.9% | 19.9% |
| coverage upload (codecov, coveralls, codacy, sonar) | 15.7% (146) | 27.9% | 11.4% |
| docs build | 24.4% (227) | 40.8% | 18.7% |
| pages / docs deploy | 15.7% (146) | 15.8% | 15.7% |
| benchmark | 17.3% (161) | 27.9% | 13.6% |
| fuzz | 6.8% (63) | 14.2% | 4.2% |
| sanitizers / valgrind / miri | 13.8% (128) | 21.7% | 11.0% |
| MSRV | 4.9% (46) | 11.7% | 2.6% |
| cross-compilation / multi-target | 34.9% (325) | 53.8% | 28.4% |
| release automation (any) | 41.6% (387) | 51.2% | 38.3% |
| GitHub release asset upload | 34.5% (321) | 37.9% | 33.3% |
| publish to crates.io | 3.7% (34) | 11.2% | 1.0% |
| publish to PyPI | 7.6% (71) | 15.4% | 4.9% |
| publish to npm | 9.2% (86) | 13.3% | 7.8% |
| publish to Maven/Sonatype | 3.9% (36) | 1.7% | 4.6% |
| publish to RubyGems | 0.6% (6) | 0.4% | 0.7% |
| publish to NuGet | 0.8% (7) | 0.0% | 1.0% |
| docker build/push/login | 24.9% (232) | 30.4% | 23.0% |
| ghcr.io referenced | 24.7% (230) | 34.6% | 21.3% |
| any package-registry publish workflow (crates, PyPI, npm, gem, nuget) | 17.0% (158) | 30.8% | 12.2% |
| any publish workflow incl. docker | 32.0% (298) | 45.0% | 27.5% |
| provenance / attestation | 12.3% (114) | 21.2% | 9.1% |
| sigstore / cosign | 5.9% (55) | 14.6% | 2.9% |
| SBOM | 6.3% (59) | 10.4% | 4.9% |
| CodeQL | 20.8% (193) | 37.5% | 14.9% |
| OpenSSF scorecard | 7.2% (67) | 17.9% | 3.5% |
| zizmor in CI | 10.5% (98) | 28.3% | 4.3% |
| actionlint in CI | 4.9% (46) | 9.2% | 3.5% |
| dependency-review-action | 4.0% (37) | 7.1% | 2.9% |
| dependency audit (deny, audit, pip-audit, osv, govulncheck, trivy, snyk) | 12.7% (118) | 24.6% | 8.6% |
| secret scanning (gitleaks, trufflehog) | 1.6% (15) | 2.9% | 1.2% |
| container scanning | 3.0% (28) | 5.0% | 2.3% |
| hadolint | 1.4% (13) | 2.1% | 1.2% |
| terraform fmt/validate/tflint/checkov/tfsec | 1.0% (9) | 2.1% | 0.6% |
| k8s / helm lint (kubeconform, kube-linter, helm lint, conftest) | 1.5% (14) | 1.2% | 1.6% |
| ansible-lint | 0.1% (1) | 0.4% | 0.0% |
| nix in CI (install-nix-action, cachix, nix build) | 6.7% (62) | 4.2% | 7.5% |
| stale bot | 18.2% (169) | 25.4% | 15.7% |
| labeler | 11.9% (111) | 19.6% | 9.3% |
| automerge / dependabot metadata | 4.9% (46) | 7.9% | 3.9% |
| commit / PR-title lint | 5.3% (49) | 7.9% | 4.3% |
| spellcheck (typos, codespell) | 8.9% (83) | 15.0% | 6.8% |
| license check | 4.7% (44) | 14.2% | 1.4% |
| link check | 3.5% (33) | 7.1% | 2.3% |
| any caching (actions/cache, rust-cache, setup-* cache) | 60.3% (561) | 68.3% | 57.5% |

Caveat on CodeQL: GitHub's "default setup" enables CodeQL without any workflow file, so 20.8% is
a floor; the same holds for Dependabot security updates and secret scanning.

### 2.5 Hardening (denominator: GHA repos unless stated)

| item | all | tools | libs/apps |
|---|---|---|---|
| any top-level `permissions` | 66.9% (622) | 88.8% | 59.3% |
| every workflow has top-level `permissions` | 21.6% (201) | 37.5% | 16.1% |
| any read-only top-level `permissions` (read-all, {}, or no write scope) | 55.6% (517) | 81.7% | 46.5% |
| any job-level `permissions` | 63.8% (593) | 89.2% | 54.9% |
| any permissions block anywhere | 77.0% (716) | 96.2% | 70.3% |
| top-level write permission somewhere | 45.5% (423) | 53.8% | 42.6% |
| job-level write permission somewhere | 62.3% (579) | 86.2% | 53.9% |
| `id-token: write` somewhere (OIDC-capable) | 39.5% (367) | 68.3% | 29.4% |
| `concurrency` declared (any workflow or job) | 54.9% (511) | 73.3% | 48.6% |
| `cancel-in-progress: true` (any) | 48.4% (450) | 67.9% | 41.6% |
| `timeout-minutes` on >= 1 job | 37.1% (345) | 51.7% | 32.0% |
| `timeout-minutes` on every job | 2.6% (24) | 1.2% | 3.0% |
| pull_request_target used | 29.1% (271) | 45.0% | 23.6% |
| pull_request_target plus checkout of the PR head | 2.8% (26) | 5.8% | 1.7% |
| `run:` with a known-dangerous interpolation (see below) | 9.0% (84) | 10.0% | 8.7% |
| `run:` with any `${{ github.event.* }}` | 30.1% (280) | 40.4% | 26.5% |
| `run:` with any event/inputs/step-output interpolation | 47.5% (442) | 59.6% | 43.3% |

Two different "known-dangerous" lists were used and should not be confused. The repository-level
line above (84 repositories) uses a wide list including `github.event.inputs.*`, `client_payload`,
`workflow_run.head_branch`; the narrow list used for per-workflow rule CI007 below (issue/PR/comment
title and body, review body, head_commit.message, head_ref, PR head ref/label, discussion text,
workflow_run.head_branch) hits 18 workflows in 18 repositories (1.9%). `workflow_dispatch` inputs
are controlled by users with write access, so they are lower risk than PR titles.

Per-workflow view (9889 workflows with at least one job; `perwf.txt`):

| item | count | share |
|---|---|---|
| workflows with no top-level `permissions` | 3660 | 37.0% |
| workflows with no `permissions` anywhere (top-level absent and not every job has one) | 2676 | 27.1% |
| workflows with top-level write | 1568 | 15.9% |
| workflows with read-only top-level | 4661 | 47.1% |
| workflows with at least one unpinned external reference (not 40-hex SHA) | 4412 | 44.6% |
| push or PR workflows (5214) with no concurrency | 2906 | 55.7% of 5214 |
| ordinary jobs (20428) without timeout-minutes | 15371 | 75.2% |
| workflows with a checkout (7605) lacking persist-credentials: false | 5358 | 70.5% of 7605 |
| pull_request_target workflows | 590 | 6.0% of all |
| of those, with PR-head checkout | 59 | 10.0% of 590 |
| of those, with no top-level permissions or with write | 343 | 58.1% of 590 |
| workflows with narrow-list event interpolation in run | 18 | 0.2% |
| workflows with any github.event interpolation in run | 580 | 5.9% |
| publish workflows (registry publish commands) | 217 | 2.2% |
| of those, triggerable from a PR or a non-tag push | 69 | 31.8% |
| of those, secret-based and no id-token | 43 | 19.8% |
| of those, with no `environment` | 106 | 48.8% |

Repository-level violation of each structural rule (share of 930 GHA repos with >= 1 violating
workflow): unpinned ref 76.5% (711), no permissions declaration 66.2% (616), no concurrency on a
push/PR workflow 86.8% (807), a job without timeout 96.6% (898), checkout without
persist-credentials false 91.1% (847), pull_request_target head checkout 2.8% (26), narrow dangerous
interpolation 1.9% (18), prt with default or write token 21.0% (195).

### 2.6 Action pinning (denominator: 928 repos using >= 1 external action)

| item | share |
|---|---|
| every external ref SHA-pinned | 23.4% (217/928) |
| >= 1 SHA-pinned ref | 49.7% (461) |
| >= 50% of refs SHA-pinned | 35.8% (332) |
| no SHA pins at all (tags/branches only) | 50.3% (467) |
| >= 1 branch ref (@main, @master, ...) | 19.6% (182) |
| >= 1 ref with no `@` at all | 2.6% (24) |
| tools: every ref SHA-pinned | 99/239 = 41.4% |
| libs/apps: every ref SHA-pinned | 118/689 = 17.1% |
| tools with >= 50% SHA | 156/239 = 65.3% |

Over all external `uses:` references: SHA 32443 (58.8%), tag 21245 (38.5%), branch 1120 (2.0%),
no ref 326 (0.6%), docker:// 49. The split between "most references are SHA" and "few repositories
are all-SHA" says pinning is adopted by a minority of repositories who then apply it almost
everywhere (typically Dependabot or Renovate with a pin preset or `pinact`), while the majority
use tags uniformly.

Star-tier trend (share of GHA repos; tiers by stars: top 250 (>54963 stars), 251-500, 501-750, rest):

| metric | top250 | 251-500 | 501-750 | 751-1069 |
|---|---|---|---|---|
| uses GHA | 90% | 90% | 88% | 82% |
| renovate or dependabot | 48% | 52% | 44% | 37% |
| any permissions | 85% | 85% | 76% | 64% |
| all-SHA | 30% | 24% | 22% | 17% |
| concurrency | 63% | 66% | 50% | 43% |
| timeout | 48% | 45% | 33% | 25% |
| CodeQL | 24% | 24% | 21% | 15% |
| scorecard | 9% | 6% | 8% | 6% |
| zizmor | 14% | 11% | 11% | 7% |
| provenance | 18% | 12% | 8% | 10% |
| SECURITY.md (all repos) | 51% | 48% | 31% | 18% |
| CODEOWNERS (all repos) | 31% | 25% | 21% | 19% |

Hardening practices correlate monotonically with stars. The popular projects are not secure by
construction; they are roughly twice as likely as the tail to do each thing, and even in the top 250
only 30% SHA-pin everything.

### 2.7 Publishing (denominator: 298 repositories with a detected publish workflow, incl. Docker)

| item | share |
|---|---|
| `id-token: write` in a publish workflow | 57.7% (172) |
| a long-lived secret referenced in a publish workflow | 58.7% (175) |
| OIDC and no secret | 27.2% (81) |
| secret and no OIDC | 28.2% (84) |
| both | 30.5% (91) |
| neither (publishes with GITHUB_TOKEN only, e.g. GHCR, releases) | 14.1% (42) |
| publish workflow triggerable by pull_request | 30.9% (92) |
| `environment:` gate | 45.6% (136) |

Registry-specific (workflow level, restricted to registry publish commands):

| registry | repos with publish workflow | using the registry's token-less path |
|---|---|---|
| PyPI | 68 | 49 (72.1%) use OIDC trusted publishing (id-token write and no PYPI token or `password:`) |
| crates.io | 34 | 23 (67.6%) use `rust-lang/crates-io-auth-action` (trusted publishing) |
| npm | 71 | 28 (39.4%) combine `--provenance` or provenance env with id-token |
| Docker Hub | n/a | 46 workflows reference DOCKERHUB_TOKEN, 40 DOCKERHUB_USERNAME, 19 DOCKER_PASSWORD: Docker Hub has no OIDC path, so long-lived secrets are the norm |

Most common long-lived secret names in publish workflows: DOCKERHUB_TOKEN (46), DOCKERHUB_USERNAME
(40), DOCKER_PASSWORD (19), NPM_TOKEN (19), DOCKER_USERNAME (15), PYPI_API_TOKEN (9),
CARGO_REGISTRY_TOKEN (6), AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (5 each), OPENAI_API_KEY (5).

zizmor `use-trusted-publishing` fired on 44 repos (4.7%): the places where a registry supports OIDC
but the workflow still uses a token. For PyPI and crates.io the move to trusted publishing is already
the majority practice among those who publish; this is the clearest "dominant and rising" pattern.

### 2.8 Top 50 actions (repos using, share of 930 GHA repos; total uses)

| action | repos | uses |
|---|---|---|
| actions/checkout | 918 (98.7%) | 16814 |
| actions/upload-artifact | 593 (63.8%) | 5441 |
| actions/download-artifact | 419 (45.1%) | 3104 |
| actions/cache | 393 (42.3%) | 2631 |
| actions/setup-node | 320 (34.4%) | 2259 |
| actions/github-script | 265 (28.5%) | 2896 |
| actions/setup-python | 219 (23.5%) | 1210 |
| docker/login-action | 206 (22.2%) | 707 |
| github/codeql-action | 193 (20.8%) | 563 |
| docker/setup-buildx-action | 191 (20.5%) | 567 |
| actions/stale | 168 (18.1%) | 220 |
| docker/build-push-action | 162 (17.4%) | 559 |
| actions/setup-java | 144 (15.5%) | 554 |
| actions/setup-go | 143 (15.4%) | 1111 |
| softprops/action-gh-release | 129 (13.9%) | 275 |
| docker/setup-qemu-action | 108 (11.6%) | 194 |
| codecov/codecov-action | 101 (10.9%) | 180 |
| peter-evans/create-pull-request | 100 (10.8%) | 243 |
| actions/create-github-app-token | 93 (10.0%) | 423 |
| docker/metadata-action | 92 (9.9%) | 186 |
| dtolnay/rust-toolchain | 86 (9.2%) | 652 |
| pnpm/action-setup | 81 (8.7%) | 549 |
| ruby/setup-ruby | 77 (8.3%) | 258 |
| actions/deploy-pages | 72 (7.7%) | 72 |
| Swatinem/rust-cache | 71 (7.6%) | 495 |
| actions/upload-pages-artifact | 71 (7.6%) | 71 |
| dorny/paths-filter | 70 (7.5%) | 160 |
| actions/labeler | 67 (7.2%) | 74 |
| astral-sh/setup-uv | 64 (6.9%) | 483 |
| ossf/scorecard-action | 62 (6.7%) | 62 |
| taiki-e/install-action | 58 (6.2%) | 260 |
| pypa/gh-action-pypi-publish | 50 (5.4%) | 80 |
| golangci/golangci-lint-action | 50 (5.4%) | 69 |
| zizmorcore/zizmor-action | 48 (5.2%) | 49 |
| cachix/install-nix-action | 48 (5.2%) | 199 |
| gradle/actions | 48 (5.2%) | 141 |
| actions/setup-dotnet | 47 (5.1%) | 131 |
| actions/configure-pages | 41 (4.4%) | 41 |
| mlugg/setup-zig | 41 (4.4%) | 152 |
| dessant/lock-threads | 39 (4.2%) | 40 |
| oven-sh/setup-bun | 38 (4.1%) | 179 |
| actions/dependency-review-action | 37 (4.0%) | 37 |
| sigstore/cosign-installer | 37 (4.0%) | 65 |
| actions/attest | 36 (3.9%) | 73 |
| actions/attest-build-provenance | 36 (3.9%) | 91 |
| goreleaser/goreleaser-action | 35 (3.8%) | 51 |
| erlef/setup-beam | 35 (3.8%) | 138 |
| crate-ci/typos | 34 (3.7%) | 40 |
| aws-actions/configure-aws-credentials | 33 (3.5%) | 152 |
| msys2/setup-msys2 | 33 (3.5%) | 64 |

Publishers by number of repositories: actions 924, docker 245, github 210, peter-evans 144,
softprops 129, codecov 101, pnpm 86, dtolnay 86, ruby 77, swatinem 76, dorny 75, astral-sh 68, ossf 62,
taiki-e 58, gradle 54, pypa 51, golangci 50, zizmorcore 49, cachix 49, azure 47. 835 of 930
repositories (89.8%) use at least one action from an owner other than actions/github/docker, and the
median repository has 32% of its `uses:` from outside actions/github. "Third-party from unverified
publishers": verified-creator status is not available offline (it is Marketplace metadata, not
repository content), so this study reports third-party-ness (owner not actions/github/docker) as the
proxy, and does NOT claim a verified/unverified split.

### 2.9 By language (GHA repos; share of repositories in each language bucket)

| lang | n | any perm | concurrency | timeout | all-SHA | matrix OS | lint | cov upload | CodeQL | dependabot or renovate | cache | windows | Dockerfile |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Rust | 102 | 91% | 79% | 51% | 32% | 76% | 94% | 19% | 15% | 66% | 81% | 34% | 59% |
| Python | 85 | 85% | 68% | 47% | 31% | 56% | 67% | 20% | 20% | 55% | 53% | 21% | 51% |
| TypeScript | 62 | 95% | 85% | 71% | 42% | 53% | 76% | 19% | 35% | 73% | 81% | 37% | 65% |
| JavaScript | 40 | 88% | 50% | 35% | 42% | 50% | 68% | 22% | 28% | 52% | 65% | 12% | 18% |
| Go | 112 | 95% | 57% | 38% | 32% | 54% | 79% | 28% | 46% | 75% | 70% | 29% | 78% |
| Java | 46 | 80% | 48% | 28% | 20% | 28% | 41% | 24% | 24% | 43% | 61% | 9% | 48% |
| Kotlin | 44 | 57% | 36% | 27% | 14% | 20% | 27% | 0% | 7% | 34% | 50% | 9% | 9% |
| C | 47 | 79% | 62% | 38% | 17% | 47% | 40% | 15% | 32% | 38% | 53% | 45% | 47% |
| C++ | 54 | 76% | 65% | 39% | 15% | 48% | 46% | 11% | 22% | 44% | 50% | 56% | 48% |
| C# | 43 | 79% | 30% | 28% | 7% | 30% | 16% | 7% | 21% | 58% | 40% | 70% | 23% |
| Ruby | 51 | 80% | 43% | 35% | 25% | 27% | 67% | 16% | 25% | 67% | 43% | 8% | 57% |
| Swift | 38 | 45% | 37% | 21% | 8% | 24% | 39% | 11% | 8% | 13% | 32% | 8% | 11% |
| Zig | 40 | 60% | 45% | 28% | 10% | 65% | 25% | 5% | 0% | 12% | 28% | 12% | 25% |
| Haskell | 41 | 44% | 34% | 20% | 7% | 54% | 46% | 2% | 0% | 34% | 78% | 17% | 49% |
| OCaml | 36 | 44% | 36% | 17% | 6% | 58% | 22% | 6% | 0% | 31% | 47% | 14% | 56% |
| Elixir | 46 | 67% | 33% | 15% | 30% | 26% | 70% | 20% | 13% | 39% | 74% | 11% | 43% |
| Scala | 35 | 63% | 51% | 37% | 14% | 23% | 31% | 9% | 6% | 46% | 83% | 11% | 37% |

("Dockerfile" is the share with any Dockerfile anywhere in the tree.)

Where language changes the picture: Rust, TypeScript and Go are the most hardened (permissions 91%,
95%, 95%; concurrency 79%, 85%, 57%; lint 94%, 76%, 79%); Rust has by far the highest multi-OS matrix
(76%) and lint (94%, clippy and fmt are cultural defaults) and caching (81%, Swatinem/rust-cache);
C# and C++ lean on Windows (70%, 56%) and cache (C++ 56%); Swift, Kotlin, Haskell, OCaml and Zig have
the least permissions hygiene (44% to 60%) and nearly no SHA pinning (6% to 14%); Zig has the highest
multi-OS matrix after Rust (65%) and the lowest Dependabot/Renovate (12%). Go leads in CodeQL (46%) and
Dockerfile presence (78%); the reasons were not investigated.

## 3. Lint and policy-tool results over the corpus

### 3.1 Tools used

- zizmor 1.30.1 via `uvx zizmor --offline --format json-v1 --no-exit-codes`, default ("regular")
  persona, one invocation per repository directory (so the `auditor` and `pedantic` personas, which add
  audits such as concurrency and timeout style checks, were NOT run). 895 of 930 directories were
  audited; 35 failed with "no audit was performed" (config/YAML-anchor errors in zizmor's strict
  loader). Offline mode: online audits (impostor-commit, known-vulnerable-actions, ref-confusion,
  stale-action-refs) were disabled.
- actionlint v1.7.12 built from source with Go (`go install github.com/rhysd/actionlint/cmd/actionlint@latest`
  into the scratchpad `bin/`). Neither shellcheck nor pyflakes was on PATH, so actionlint's embedded `run:` script checks
  were not active and `shellcheck`-kind findings are absent.

### 3.2 zizmor findings by id (930 repository directories linted; 64507 findings total)

876 repositories (94.2% of 930) have at least one finding; 827 (88.9%) at least one high-severity finding.

| id | findings | repos (of 930) | severity mix |
|---|---|---|---|
| unpinned-uses | 22136 | 679 (73.0%) | all high |
| artipacked | 11283 | 798 (85.8%) | 6921 medium, 4361 low |
| template-injection | 11168 | 444 (47.7%) | 3512 high, 563 medium, 1818 low, 5275 informational |
| self-repository | 7879 | 267 (28.7%) | low |
| excessive-permissions | 6974 | 677 (72.8%) | 625 high, 6285 medium |
| secrets-inherit | 1107 | 94 (10.1%) | medium |
| cache-poisoning | 1051 | 248 (26.7%) | high |
| dangerous-triggers | 693 | 262 (28.2%) | high |
| adhoc-packages | 429 | 150 (16.1%) | low |
| superfluous-actions | 367 | 176 (18.9%) | informational |
| unpinned-images | 319 | 84 (9.0%) | high |
| misfeature | 310 | 46 (4.9%) | low |
| archived-uses | 191 | 64 (6.9%) | medium |
| obfuscation | 183 | 21 (2.3%) | low |
| github-app | 181 | 53 (5.7%) | high |
| use-trusted-publishing | 74 | 44 (4.7%) | informational |
| github-env | 51 | 23 (2.5%) | high |
| overprovisioned-secrets | 40 | 9 (1.0%) | medium |
| unpinned-tools | 25 | 5 (0.5%) | medium |
| bot-conditions | 19 | 14 (1.5%) | high |
| unsound-condition | 13 | 10 (1.1%) | high |
| unsound-ternary | 11 | 8 (0.9%) | low |
| unsound-contains | 3 | 2 (0.2%) | high and informational |

23 distinct ids occurred. The top five account for 90% of findings. Read this table with the
zizmor policy in mind: `unpinned-uses` fires on tag pins (it demands a hash), `artipacked` on any
checkout without `persist-credentials: false`, `template-injection` includes informational
low-confidence cases. These are policy-grade findings, not confirmed exploits.

### 3.3 actionlint findings by kind (930 directories; 5946 findings; 489 repositories (52.6%) with >= 1)

| kind | findings | repos |
|---|---|---|
| runner-label | 3267 | 181 |
| action | 1227 | 213 |
| expression | 612 | 157 |
| syntax-check | 423 | 65 |
| events | 149 | 37 |
| workflow-call | 96 | 13 |
| if-cond | 70 | 42 |
| deprecated-commands | 40 | 20 |
| glob | 27 | 5 |
| permissions | 22 | 9 |
| job-needs | 5 | 3 |
| shell-name | 5 | 2 |
| matrix | 3 | 3 |

`runner-label` is dominated by custom or third-party runner labels actionlint does not know without a
config (blacksmith-*, tuist-linux, amd-medium, arm-tiny, ubuntu-arm64-small) and by labels newer
than this actionlint build (ubuntu-26.04: 278): this is false-positive noise from not supplying
`self-hosted-runner.labels`, a lesson for binding (the tool stage must pass the repo's labels or
suppress that kind). Excluding runner-label, 409 repositories (44.0%) still have a finding. The most
real signal: 185 repositories use an action old enough that its Node runtime is no longer supported
("the runner of actions/checkout@v3 is too old", 229 occurrences for checkout@v3 alone) and 127
occurrences of the `queue` concurrency key which this actionlint build does not yet know (also a
staleness problem: syntax-check findings will be false positives against newer GitHub schema).
Lesson: both tools are version-sensitive against a moving platform; a binding must pin and report
the tool version and treat its schema lag as an Unresolved source, not a finding.

## 4. What the dominant practices protect against

Mapping practice to threat or failure. "Evidence" is the prevalence from this survey; the threat
descriptions are standard CI security knowledge and some named incidents are cited from memory, not
verified in this session (flagged "background").

| practice | prevalence | threat / failure it addresses |
|---|---|---|
| CI on push and pull_request | 90.5% | regressions merge unnoticed; broken main |
| test, lint, format, typecheck steps | 90% / 57% / 56% / 23% | functional regressions; style drift; type errors; review noise |
| matrix over OS and versions | 77% matrix, 47% OS, 25% versions | platform-specific breakage; support-window promises (MSRV, Python versions) |
| `workflow_dispatch` | 71.6% | re-run and operate pipelines without a commit (ops convenience, release rehearsal) |
| `schedule` | 56.5% (tools 81.2%) | bit-rot (dependency/toolchain changes with no commits), nightly builds, stale-bot housekeeping |
| `concurrency` with cancel-in-progress | 54.9% / 48.4% | wasted runner minutes and queue starvation; stale results racing newer commits; for deploy jobs, overlapping deployments |
| `timeout-minutes` | 37.1% (any), 2.6% (all) | hung jobs burning minutes (default 360 min); availability of shared runners |
| caching | 60.3% | slow and flaky builds (and, mis-configured, cache poisoning: zizmor cache-poisoning 26.7%) |
| top-level `permissions` read-only | 55.6% any | a compromised step or action can write to repo, packages, releases; least privilege on GITHUB_TOKEN |
| SHA-pinning | 23.4% all, 58.8% of refs | mutable tag supply chain: a retargeted tag runs attacker code with your secrets (background: tj-actions/changed-files March 2025 and similar tag-rewrite incidents) |
| Dependabot or Renovate | 44.7% (tools 76.7%) | stale dependencies and unpatched CVEs; makes pinning maintainable; 89.7% of Dependabot configs here include the github-actions ecosystem and 329 update blocks carry a `cooldown` (delay against freshly published malicious releases) |
| CODEOWNERS and required review (not visible) | 23.6% CODEOWNERS | unreviewed change to sensitive paths (workflows, release config) |
| avoid `pull_request_target` head checkout | 97.2% of repos avoid it | "pwn request": untrusted PR code running with write token and secrets |
| no event text in `run:` | ~98% avoid the narrow list | script injection through PR titles, branch names, commit messages |
| OIDC trusted publishing | PyPI 72%, crates.io 68%, npm provenance 39% of publishers | stolen long-lived registry tokens; token leakage in logs; gives attestations tied to the workflow identity |
| `environment:` with protection rules | 25.5% (publish: 45.6%) | unreviewed publish/deploy; secrets scoped to approved deployments (rules are server-side, not visible) |
| provenance, sigstore, SBOM | 12.3% / 5.9% / 6.3% | artifact tampering between build and consumer; "what is in this artifact" for vulnerability response |
| CodeQL, dependency-review, audit tools, scorecard | 20.8% / 4.0% / 12.7% / 7.2% | known vulnerable code and dependencies entering main; posture visibility |
| zizmor, actionlint | 10.5% / 4.9% | workflow bugs and workflow-level vulnerabilities themselves (the CI config as an attack surface) |
| fuzz, sanitizers/miri, benchmarks, MSRV | 6.8% / 13.8% / 17.3% / 4.9% | memory-safety bugs, performance regressions, accidental toolchain-floor bumps |
| release automation, changelog, changesets | 41.6%, 40.4% changelog | inconsistent releases, missing release notes, version/tag drift |
| Dockerfile with USER, digest pin, no curl|sh | 25.3% / 8.8% / 90% avoid | container root escape; mutable base image; unverified script execution at build |
| lockfiles | 36.9% (tools 67.9%) | non-reproducible dependency resolution; dependency confusion window |
| devcontainer, version pin files, flake.nix, rust-toolchain | 13%, 12%, 10%, 5% | "works on my machine"; toolchain drift between dev and CI |
| pre-commit | 8.2% (tools 18.9%) | shifts format/lint failures left of CI; secret/trailing-whitespace hooks |

Failure classes worth naming: (1) supply-chain code execution inside CI (pinning, permissions,
injection, pull_request_target); (2) credential theft from CI (long-lived secrets, persisted
checkout credentials: artipacked 85.8%); (3) cost and availability (concurrency, timeouts); (4)
quality regressions (tests, lint, matrix); (5) release integrity (OIDC, provenance, environment
gates); (6) drift (schedule, Dependabot, toolchain pins).

## 5. Dominant patterns (> 70%) and rare-but-recommended practices (< 30%)

### 5.1 Dominant (over 70% of GHA repos, or of all repos where stated)

| pattern | share |
|---|---|
| GitHub Actions as CI (all repos) | 87.0% |
| `actions/checkout` | 98.7% |
| `push` and `pull_request` triggers | 95.1% / 93.1% |
| Ubuntu runners | 94.8% |
| A test step (upper bound) | ~90% |
| >= 2 workflow files | 85.3% |
| Matrix builds | 77.3% |
| Some `permissions:` block anywhere | 77.0% (tools 96.2%) |
| `workflow_dispatch` | 71.6% |
| Any write permission somewhere | 72.7% (needed for releases, labelers, comments) |
| Tools only: schedule 81%, lint 82%, any permissions 96%, concurrency 73%, Renovate/Dependabot 77%, >= 5 workflows 79%, matrix 92% | tools |

The dominant pattern is "CI exists, tests run on push and PR on Ubuntu in a matrix, with permissions
mentioned somewhere". It is a convergence on a shape, not on a quality bar.

### 5.2 Recommended but rare (under 30%): the enforcement opportunity

| practice | share | enforcement angle |
|---|---|---|
| Every external ref SHA-pinned | 23.4% (tools 41.4%) | CI001, mechanical |
| Top-level `permissions` in every workflow | 21.6% | CI002, mechanical |
| `timeout-minutes` on every job | 2.6% | CI005, mechanical, huge gap |
| `persist-credentials: false` on every checkout | ~9% of repos (91% violate) | CI010, mechanical |
| Typecheck in CI | 23.2% | policy, language-dependent |
| Coverage upload | 15.7% | policy, optional |
| Fuzzing | 6.8% | policy, language-dependent |
| MSRV job (Rust) | 4.9% overall; Rust-only share should be computed per language (not done) | join: `rust-version` in Cargo.toml vs CI matrix (CI012) |
| Provenance or attestation | 12.3% | publish-job rule CI009 extension |
| sigstore / cosign | 5.9% | out of scope to require; bind |
| SBOM | 6.3% | out of scope to require |
| OpenSSF scorecard | 7.2% | bind (scorecard is the aggregate) |
| zizmor in CI | 10.5% | frob binds it itself (section 9) |
| actionlint in CI | 4.9% | frob binds it itself |
| npm provenance with OIDC | 39% of npm publishers | CI009 |
| Dockerfile non-root USER | 25.3% of files | DK001 |
| Dockerfile base by digest | 8.8% | DK002 (policy) |
| Dockerfile HEALTHCHECK | 7.1% | optional |
| CODEOWNERS | 23.6% | file-presence rule |
| deny.toml (Rust) | 3.6% overall | Rust-specific policy; ties to frob vet |
| hadolint in CI | 1.4% | DK bind |
| Terraform/k8s/Helm/Ansible lint in CI | 1.0% / 1.5% / 1.5% / 0.1% | bind |
| secret scanning in CI | 1.6% | bind |
| pre-commit config | 8.2% | not needed if frob is the gate |

Noteworthy: there is a gap between what practice-literature recommends and what even the top 250
projects do, so a linter that demands everything will fail on nearly every repository on day one.
Findings must therefore be tiered (default severity per rule, opt-in strict profile), and the
numbers above (violation rate per rule) are the tiering input.

## 6. Deployment languages seen

Counts over 1069 repositories (file presence; lower bounds for 17 truncated trees).

| language / artifact | repos | notes | existing linters |
|---|---|---|---|
| Dockerfile / Containerfile | 473 (44.2%); 764 files examined in 409 repos | the only deployment language that is mainstream | hadolint (Haskell binary, JSON/SARIF output; embeds shellcheck for RUN), dockle (image), trivy config, checkov, docker build --check (BuildKit linter) |
| docker-compose / compose.yaml | 203 (19.0%) | dev environments, test fixtures | docker compose config, checkov, kics |
| Helm chart | 42 (3.9%; tools 8.4%) | in infra projects | helm lint, kubeconform on `helm template`, kube-linter, chart-testing (ct), checkov |
| Kubernetes manifests (dir heuristics) | 58 (5.4%); kustomize 21 (2.0%) | | kubeconform, kubeval (dead), kube-linter, kube-score, kyverno, conftest/OPA, datree (dead) |
| Terraform / OpenTofu (.tf) | 40 (3.7%; tools 10.4%) | mostly fixtures in IaC tools | terraform validate/fmt, tflint, tfsec (now trivy), checkov, terrascan, Terragrunt |
| Terragrunt | 3 (0.3%) | | terragrunt hclfmt/validate |
| Ansible | 15 (1.4%) | | ansible-lint, yamllint |
| Nix (flake.nix 105 = 9.8%; shell.nix or default.nix 39 = 3.6%) | ~13% have some Nix | dev shells and builds, notable in Haskell/Rust/OCaml | statix, deadnix, nixfmt, nil/nixd (LSP), `nix flake check` |
| Pulumi, AWS CDK | 0 | | (language-native linters: they are ordinary TypeScript/Python programs) |
| GitHub Actions workflow YAML | 930 (87.0%) | the dominant CI/CD language | actionlint, zizmor, pinact, ghalint, poutine, octoscan, yamllint |
| Other CI YAML (GitLab, CircleCI, Azure, Buildkite, Travis, AppVeyor, Cirrus, Drone, Jenkinsfile) | 166 repos with a non-GHA CI file (124 also use GHA, 42 only) | long tail | glab ci lint, circleci config validate, azure schema, bk pipeline validate; schemas via SchemaStore |
| Makefile, justfile, Taskfile | 265 / 26 / 8 | build orchestration, not deployment | checkmake, `just --fmt`, `task --list` |
| devcontainer.json | 143 (13.4%) | | JSON schema |
| Renovate / Dependabot config | 102 / 392 | dependency policy as config | renovate-config-validator, Dependabot schema (SchemaStore) |

Inventory of CI-scoped tools in the corpus: actionlint 4.9% of GHA repos, zizmor 10.5%, hadolint 1.4%,
terraform lint 1.0%, k8s/helm lint 1.5%, ansible-lint 0.1%. Nobody lints deployment languages in CI at
scale; the GHA linters are the only ones with measurable adoption, and they are concentrated in the
tools bucket (zizmor 28.3%).

### 6.1 Dockerfile structural survey (764 files in 409 repos)

| check | share of Dockerfiles |
|---|---|
| multi-stage | 43.2% (330) |
| has an external FROM | 86.9% (664) |
| every external FROM pinned by digest | 8.8% (67 of 664 files with external FROM = 10.1%) |
| any FROM `:latest` or untagged | 16.1% (123) |
| FROM parameterized by ARG | 10.9% (83) |
| a non-root `USER` is set | 25.3% (193); 71 of 409 repositories have it in every Dockerfile |
| HEALTHCHECK | 7.1% (54) |
| `ADD` of a remote URL | 2.5% (19) |
| `curl|sh` or `wget|sh` in RUN | 9.9% (76) |
| `apt-get install` present | 41.5% (317); of those 62.1% use `--no-install-recommends` (197/317) and 69.1% clean `/var/lib/apt/lists` |
| `sudo` in RUN | 8.4% (64) |
| `COPY . .` style context copy | 25.3% (193) |
| secret-looking ENV or ARG (password, token, secret, api_key assigned) | 2.2% (17) |
| BuildKit `--mount` cache or secret | 14.0% (107) |
| WORKDIR | 64.1% (490) |

Dependabot (389 configs parsed): ecosystems github-actions 349 (89.7%), npm 93, gomod 69, cargo 51,
docker 49, pip 41, bundler 21, mix 16, nuget 15, uv 12, gradle 12, maven 10, devcontainers 9,
gitsubmodule 9, swift 5. Schedule intervals: weekly 567 entries, daily 225, monthly 145, quarterly
14. 329 update blocks have a `cooldown`, 481 use `groups`.

## 7. The languages in the sense of universal-model.md

Per the vocabulary of docs/design/universal-model.md (units and roles, binders and scope graph,
apply edges with Must/May/Unknown status, embedded expression island as `region` with its own
language tag, effects as attributes or capabilities). Fidelity targets per section 3.3 of that
document. These are short sketches; none of the four needs a new primitive.

### 7.1 GitHub Actions workflow YAML

- Units: `workflow` (unit, identity = file path), `job` (unit, id key), `step` (anon or named by
  `id`/`name`), `trigger` (attr on workflow), `permissions` (attr at workflow or job scope),
  `env` (bind group at workflow, job and step scope), `matrix` (bind with a cartesian group).
- Binders and scope: lexical nesting workflow > job > step for `env` and `permissions`; `needs:`
  gives a topological `group(order=topological)` over jobs; step `id` binds a name usable in
  later `steps.<id>.outputs`; job `outputs` bind to `needs.<job>.outputs`; `matrix.<key>` binds
  inside the job; `inputs`/`secrets` bind at workflow_call. All of these are resolvable
  statically (Must) except dynamic matrices (`fromJSON(...)`), which are May/Unknown.
- Apply edges: `uses: owner/repo@ref` is `apply(kind=action)` to an external unit in another
  repository (resolution needs the fetched action.yml, so the edge is Must to a named external
  symref but the callee body is Unknown offline); `uses: ./.github/actions/x` and `uses:
  ./.github/workflows/x.yml` are Must to local units; `run:` is `apply(kind=shell)` into an embedded
  shell island; `needs:` is a dependency edge; `workflow_call` is the caller/callee edge.
- Embedded languages: `${{ expression }}` (the Actions expression language: contexts github, env,
  secrets, needs, matrix, steps, inputs, vars; functions contains, format, fromJSON, hashFiles,
  success, failure) is a `region` with language tag `gha-expr`; `run:` bodies are `region` with the
  shell (bash/pwsh/python by `shell:`) and, critically, expression interpolation happens BEFORE the
  shell sees the script, so the injection rule is a join between two embedded languages (`phase`
  site). `github-script` bodies are JavaScript islands.
- Effects: none in the IR; as attributes, token scopes (`permissions`), secret reads
  (`secrets.X`), network publish steps, `id-token: write` (OIDC mint), `environment` gate,
  artifact upload/download. Effects are carried, not checked, which matches section 2.4 of the
  model: CI rules read attributes (permissions, `uses` ref, trigger set), they do not need
  evaluation.
- Fidelity reachable: F3 (units, scope graph with Must edges for contexts, `apply` to local
  workflows), F4 for attributes and comments (zizmor ignore comments). Unknown by nature: external
  action bodies, dynamic matrix, reusable workflow secrets inheritance, runner image contents.

### 7.2 Dockerfile

- Units: `stage` (unit, name from `FROM ... AS name`, else index), `instruction` (anon, ordered by
  `group(order=sequence)`), `arg`/`env` (bind), `label` (attr).
- Binders and scope: `ARG` before the first FROM is global to FROM lines only; `ARG` in a stage is stage
  scoped; `ENV` persists into later instructions of the stage and into the image; `COPY --from=name`
  and `FROM name` are `ref` to a stage (Must) or to an external image (an opaque external symref
  `registry/repo:tag@digest`). Variable interpolation `${VAR:-default}` is a `phase`-like site with
  bounded expansion.
- Apply edges: `FROM image` (external unit edge; the identity is the tag-or-digest, so a digest makes
  the edge content-addressed, a tag makes it May), `COPY --from` (stage dependency), `RUN` (shell
  island).
- Embedded: `RUN` and `CMD`/`ENTRYPOINT` shell form are shell `region`s (exec form is a JSON array,
  no shell); heredocs are regions. hadolint's integration with shellcheck is exactly the island
  boundary.
- Effects: network (curl, apt, pip at build), filesystem layers, user switch (`USER`), exposed ports,
  secret mounts (`--mount=type=secret`), build-time vs run-time (`ARG` vs `ENV`).
- Fidelity: F3 is achievable with a small custom parser (the format is line-oriented; tree-sitter
  grammars exist); every rule in section 6.1 is decidable from instruction tokens.

### 7.3 Terraform / HCL

- Units: `resource`, `data`, `module`, `variable`, `output`, `locals` entry, `provider`, `terraform` block
  (required_providers/backend), `moved`/`import` blocks. Identity: address (`aws_s3_bucket.logs`),
  module-qualified.
- Binders and scope: module-level namespace per directory (a module is the set of `.tf` files in one
  directory, so the unit of scope is the directory, not the file); `var.x`, `local.x`,
  `resource_type.name`, `module.m.output`, `data.t.n` are references resolved Must within the
  module; `for_each`/`count` introduce `each.*`/`count.index` binders; dynamic blocks are binders.
- Apply edges: reference graph is the dependency DAG (implicit edges) plus `depends_on` (explicit);
  `module` call to a source (local path Must; registry or git source is an external unit,
  version-constrained: May); provider configuration edges.
- Embedded: HCL expression language (functions, conditionals, splat, templates `${}`) is a `region`
  with its own tag; `jsonencode` bodies (IAM policy documents) are JSON islands that matter for
  security rules.
- Effects: every `resource` is an effect declaration on the outside world (create/update/destroy), with
  `lifecycle` attributes (`prevent_destroy`, `create_before_destroy`); state backend and provider
  credentials are out-of-repository effects. Which effect actually occurs depends on state and `plan`
  and is Unknown offline.
- Fidelity: F3 for static references; lint rules (tflint-style provider-aware rules) need provider schemas
  (capability gated, external data) and so belong to a tool binding rather than frob rules.

### 7.4 Helm charts (Go-template over YAML)

- Units: `chart` (Chart.yaml), `values` (values.yaml schema and defaults), `template` files,
  `named template` (`define`), subchart dependency.
- Binders and scope: Go template scopes (`with`, `range` rebind `.`; `$` root; `define`/`include`
  names are a global per-chart namespace), `.Values.path`, `.Release`, `.Chart` contexts; `values`
  layering (subchart overrides) is an evaluation-time relation.
- Apply edges: `include "name"` and `template` are calls to named templates (Must by literal name; May when
  computed); rendered YAML manifests are the generated artifact; `dependencies` are chart edges.
- Embedded: the Go template language (with sprig functions) is the OUTER language and YAML the inner
  one, which is why raw YAML parsers fail on unrendered templates: the adapter must treat template
  actions as `phase` sites with the rendered output as `expansion`. Only after `helm template` can
  Kubernetes manifest rules apply (the second language, k8s resource schemas, is again a `region`
  with its own tag and `apiVersion/kind` as the dispatch key).
- Effects: the chart describes a desired cluster state; hooks (`helm.sh/hook`) are effect-ordering
  attributes; `lookup` reads live cluster state (Unknown by nature).
- Fidelity: F2 for the template layer (units, defines, includes, `.Values` references checked
  against values.yaml), F3 only with `helm template` expansion run through a tool stage.

Summary: GHA YAML and Dockerfile are structurally simple enough for frob's own adapters; Terraform
needs provider schemas for most useful rules; Helm needs expansion by an external binary. This is the
same line the findings in section 9 draw between own and bind.

## 8. What the repository cannot show

Everything below is a protection many of these projects very likely have and the survey cannot see.
Prevalences in this document should therefore be read as "visible in the repository", never as the
project's actual posture.

- Branch protection and rulesets: required status checks, required reviews, CODEOWNERS enforcement,
  linear history, signed commits, force-push and deletion bans, merge queue requirement (the
  `merge_group` trigger shows queue use only at 11.7%).
- Required checks and which workflow names they name (a workflow can exist and not be required).
- Repository, organization and environment secrets and variables; environment protection rules (required
  reviewers, wait timers, deployment branch policies); which secrets exist at all.
- The organization/repository default `GITHUB_TOKEN` permission setting (read-only is the default for
  new repositories since 2023; so a missing `permissions:` block does not imply a write token, and CI002
  has a different severity depending on that hidden setting) and the "allowed actions" policy
  (restricting to verified or listed actions, SHA-pinning enforcement setting now available).
- GitHub features that need no files: CodeQL default setup, Dependabot alerts and security updates,
  secret scanning and push protection, private vulnerability reporting, code scanning alerts.
- Runners: what the labels map to, ephemeral vs persistent self-hosted runners, network egress policy.
- Tag protection and release immutability; npm/PyPI/crates.io-side trusted publisher configuration (the
  workflow side is visible, the registry side is not: a workflow may use `id-token` and still be
  unregistered, or use a token and also be registered); account 2FA.
- Org-level shared Renovate presets (`extends: ["github>org/.github"]`) and reusable workflows defined in
  other repositories (calls are visible, bodies are not: 29.1% of repositories call a reusable workflow).
- Anything on other CI systems for the 97 repositories with no visible CI (Gerrit, Prow, Fossil).
- Whether `workflow_dispatch` workflows are restricted, and who can run them.

Consequence for frob: CI rules over the repository can be "necessary-condition" checks (a missing
`permissions` block is a finding unless a documented org default is declared in frob config) but
never proofs of safety. A frob rule that reports "your repository is secure" would violate the
honesty boundary of universal-model.md section 4.5; the answer type for settings-dependent rules is
`Unknown` with a reason naming the invisible setting, and the optional GitHub API binding (frob-gh)
can turn some of them into `Exact` (branch protection and the default token permission are readable
through the REST API with admin scope).

## 9. Recommendation for frob

### 9.1 Should frob lint CI/CD and deployment languages

Yes for GitHub Actions workflow YAML; yes (thinly) for Dockerfile; for Terraform, Helm, Kubernetes and
Ansible, bind existing tools and do not write rules. Reasons from the data:

1. CI is the largest executable surface of nearly every project (87% GHA; median 6 workflow files; 23425 jobs
   in this sample) and is almost always the least reviewed code in the repository: 94.2% of repositories
   have at least one zizmor finding, 88.9% at least one high-severity one. It is exactly the
   "structure plus policy" territory frob rules exist for.
2. frob's own repository will have workflows and Dockerfiles; milestone 1 self-hosting means they
   are linted by frob.
3. The gap between practice and recommendation is large and measurable (section 5.2), so rules have
   real signal at tiered severities.
4. Deployment languages other than Dockerfile are rare in this sample (Helm 3.9%, Terraform 3.7%,
   Ansible 1.4%, Pulumi/CDK 0%), and each has a mature specialist tool; frob adds nothing by reimplementing
   them and would perpetually trail provider schemas.

### 9.2 Own versus bind versus out of scope

The deciding question per check is whether frob has a join the tool lacks, or just a pattern the tool
already encodes.

Bind through a tool stage (frob invokes, parses structured output into diagnostics with the tool's
rule id and version, honors its ignore mechanism; frob supplies cache, location mapping, severity
policy and `Unresolved` when the tool is absent):

| tool | output to bind | reason |
|---|---|---|
| zizmor | `--format json-v1` (observed in this survey; also SARIF) | 23 distinct audits with moving threat knowledge (template-injection, cache-poisoning, impostor commits online); parity would be a treadmill. Binding offline mode gives all structural audits; online audits (known-vulnerable-actions, impostor-commit, ref-confusion) need a token and should be opt-in |
| actionlint | `-format '{{json .}}'` (observed) | schema and expression type checking, shellcheck and pyflakes integration, matrix and `needs` consistency. Must pass the repo's custom runner labels (3267 runner-label findings in this survey were label noise) |
| hadolint | `-f json` or sarif | Dockerfile and embedded shellcheck; not run in this survey |
| tflint, checkov or trivy config | json/sarif | provider-aware Terraform rules |
| helm lint, kubeconform, kube-linter | json | manifests after expansion |
| ansible-lint | `-f json` or sarif | |
| statix, deadnix | json | Nix |
| scorecard | json (online) | aggregate posture, needs API; optional |

Own as frob rules over the universal IR (small, decidable, cross-file or policy-bearing, and part of
how frob explains itself to the owner):

- The "presence and policy" rules neither tool covers well in the regular persona: CI002 (permissions
  declared), CI004 (concurrency on PR workflows), CI005 (job timeout), CI008 (publish only from tags) and
  CI009 (publish by OIDC). zizmor audits some of these only in non-default personas; I did not run
  those personas, so overlap with them is unmeasured. If overlap turns out to be total, drop the owned
  rule and keep the bind: the dedupe principle wins.
- The join rules (CI012): consistency of CI with the rest of the repository, which no GHA-only tool can
  see because it needs other adapters' IR: toolchain version in `rust-toolchain.toml` vs the version
  in `dtolnay/rust-toolchain`/matrix; `rust-version` (MSRV) in Cargo.toml vs a matrix entry; the
  commands CI runs (`cargo test`, `uv run pytest`) vs the verbs `frob check`/`frob test` declare;
  `frob:ticket` and doc-drift obligations (a workflow edit requires the CI doc be acked, which is a
  frob-native obligation); `dependabot.yml` ecosystems vs lockfiles and manifests actually present;
  `CODEOWNERS` covering `.github/workflows/`; Dockerfile base tag vs the toolchain pin; pinned SHA
  vs a comment version tag (the `# v4.1.2` convention) consistency.
- CI001 (pinned refs) and CI006/CI007 (the injection family) overlap zizmor entirely (unpinned-uses,
  dangerous-triggers, template-injection). Recommendation: do NOT own them as separate frob rules at
  first; bind zizmor and map its ids to frob rule ids (`CI001` = zizmor `unpinned-uses`, ...), so the
  numbering is stable and policy lives in frob config (pin allowlist for first-party `actions/*`,
  severity per id, suppression via frob's ack). If the owner wants zero-dependency self-hosting, an
  owned implementation of CI001 only is the cheapest (one attribute check on `apply(kind=action)`
  edges); keep the id and swap implementations behind it.
- DK001..DK004 (Dockerfile) as owned rules if a Dockerfile adapter is cheap to write (line-oriented);
  otherwise bind hadolint. hadolint covers DL3002 (last user root), DL3006/DL3007 (tag), DL3008 and
  friends (apt pinning), so the owned set should be restricted to what hadolint lacks or what needs a
  join (base-image tag vs toolchain pin).

Out of scope (do not build; may Unknown with a reason): anything depending on provider schemas,
live cluster state, registry-side trusted-publisher registration, branch protection (section 8), cost
or runner-minute optimization, caching strategy correctness, and the choice of CI vendor (non-GHA CI
files get only presence detection plus bind to the vendor's own validator where one exists).

### 9.3 Concrete rule candidates

Predicates are over the universal IR of the workflow YAML (units: workflow, job, step; attrs:
triggers, permissions, concurrency, timeout, uses ref, with, run text). "Violation rate" is the
measured rate from sections 2 and 3; "FP risk" is the expected share of findings a maintainer would
consider wrong.

| id | name | threat | decidable predicate | violation rate (measured) | FP risk | default severity | own or bind |
|---|---|---|---|---|---|---|---|
| CI001 | pinned-ref | mutable-tag supply chain execution | exists `apply(kind=action)` with external ref where ref is not 40-hex SHA and owner not in `ci.pin_allow` (default: none; common config: `actions`, `github`) | 76.5% repos, 44.6% workflows (zizmor unpinned-uses 73.0%) | low for third-party; high for first-party `actions/*` if no allowlist (these are most references) | warn; error for third-party in publish workflows | bind zizmor; optional owned fallback |
| CI002 | permissions-declared | implicit token scope depends on hidden org default | workflow has no top-level `permissions` and not every job has `permissions` | 66.2% repos, 27.1% workflows | low if the org default is declared in frob config, else medium (hidden setting) | warn | own |
| CI003 | no-top-level-write | broad write token available to all jobs and steps including third-party | top-level `permissions` contains any `write` scope or `write-all` | 45.5% repos, 15.9% workflows | medium: single-job workflows legitimately need it at top level | warn | own (or zizmor excessive-permissions) |
| CI004 | concurrency-on-pr | wasted minutes, stale results, overlapping deploys | workflow triggered by push or pull_request has no `concurrency` at workflow or any job level | 86.8% repos, 55.7% of push/PR workflows | medium: some workflows must queue (releases, deploys want `cancel-in-progress: false`, so require declaration not cancel) | note | own |
| CI005 | job-timeout | hung job burns up to 360 min | non-reusable-call job without `timeout-minutes` | 96.6% repos, 75.2% of jobs | low | note | own |
| CI006 | no-prt-head-checkout | pwn request: PR code with write token and secrets | trigger set contains `pull_request_target` or `workflow_run` and a `checkout` step whose `ref`/`repository` expression mentions `github.event.pull_request.head`, `head_ref`, `refs/pull`, `head.sha`, `head.repo` or `workflow_run.head_*` | 2.8% repos (26), 59 workflows | low (match is explicit); false negatives via indirection through env or step outputs | error | bind zizmor (dangerous-triggers) or own |
| CI007 | no-event-interpolation-in-run | script injection via PR title, body, branch, commit message | a `run:` text contains an expression whose context path is in the user-controlled set (issue/PR/comment/review title and body, `head_commit.message`, `head_ref`, PR `head.ref` and `head.label`, discussion text, `workflow_run.head_branch`) | 1.9% repos on the narrow set (18); 30.1% on any `github.event.*` | narrow set low; broad set high (many are numbers, shas, repo names) | error narrow, note broad | bind zizmor (template-injection) |
| CI008 | publish-only-from-tag | publish triggered by untrusted event or ordinary push | a workflow with a registry publish step has trigger in {pull_request, pull_request_target, push without `tags` filter} | 31.8% of publish workflows (69/217) | medium: branch pushes that publish nightlies or snapshots | warn | own |
| CI009 | publish-via-oidc | long-lived registry token leak or theft | publish job for a registry that supports trusted publishing (PyPI, crates.io, npm provenance, RubyGems) references a secret with name matching `(TOKEN|API_KEY|PASSWORD)` and has no `id-token: write` | 19.8% of publish workflows (43/217); zizmor use-trusted-publishing 4.7% repos | medium: registry-side registration may not exist yet (invisible), first-time publish requires a token | note, error in strict profile | own |
| CI010 | checkout-no-persist | token written to `.git/config` and exfiltrated through artifacts | `actions/checkout` step lacks `with.persist-credentials: false` in a workflow that later uses `upload-artifact` or runs third-party code | 91.1% repos, 70.5% of workflows with checkout (zizmor artipacked 85.8%) | high if applied to every checkout (noisy: git push steps legitimately need credentials); restrict to workflows with upload-artifact | note | bind zizmor |
| CI011 | prt-least-token | prt runs base-repo code with default write token | `pull_request_target` workflow lacks explicit read-only `permissions` | 58.1% of prt workflows (343/590) | low | warn | own |
| CI012 | ci-repo-consistency | CI drifts from repository truth (wrong toolchain, MSRV not tested, tool not run) | joins: toolchain pin file vs workflow toolchain input; `rust-version` vs matrix; `dependabot.yml` ecosystems vs manifests; CODEOWNERS covering `.github/**`; frob verbs vs workflow commands | not measured (needs joins); MSRV is tested in only 4.9% of repos | medium initially, low once keyed on explicit files | warn | own (the unique value) |
| CI013 | no-secrets-inherit | over-broad secret passing to reusable workflows | job with `uses:` and `secrets: inherit` where callee is external | 10.1% repos (zizmor secrets-inherit) | medium | note | bind zizmor |
| CI014 | gha-syntax-and-schema | workflow cannot run or is silently ignored | any actionlint finding other than `runner-label` unknown-label unless labels config is missing | 44.0% repos non-runner-label | high until tool version is current and labels supplied (schema lag, see 3.3) | warn | bind actionlint |
| CI015 | action-currency | archived or Node-EOL actions | external action from a repository flagged archived, or known-old major version (checkout@v2/v3) | zizmor archived-uses 6.9% repos; actionlint old-runner 185 repos (19.9%) | low; needs a maintained table | note | bind (actionlint, zizmor online) |
| DK001 | docker-non-root | container runs as root | final stage has no `USER` other than root/0 | 74.7% of Dockerfiles (193 of 764 set USER) | high: build-only images, test fixtures; restrict to files whose image is published | note | own or hadolint DL3002 |
| DK002 | docker-base-pinned | mutable base image tag | external `FROM` without `@sha256:` digest | 89.9% of files with an external FROM (only 10.1% are digest pinned) | high: digest pinning needs automation (Renovate `docker` manager or Dependabot `docker`: 49 repos); make it opt-in | off by default | own (policy) |
| DK003 | docker-no-latest | non-reproducible base | external `FROM` with no tag or `:latest` | 16.1% of files | low | warn | own or hadolint DL3006/DL3007 |
| DK004 | docker-no-pipe-to-shell | unverified script execution at build | `RUN` text matches `(curl|wget)[^|;]*|\s*(ba)?sh` | 9.9% of files | medium: installers (rustup, nvm, uv) are commonly piped; allowlist by URL host | note | own or hadolint |

Tiering from the numbers: start CI006, CI007 (narrow), CI011 at `error` (low base rate, high impact, low
false positives); CI001, CI002, CI003, CI008, CI009, CI013 at `warn`; CI004, CI005, CI010 at `note`,
promoting on a per-repository opt-in strict profile ("tools profile": the top-250 numbers show 30% to 48%
already comply, so strict for infrastructure projects is realistic). The honest default is that a typical
repository has dozens of CI001 and CI010 findings; the rule engine's baseline/ratchet feature (new
violations fail, old ones tracked as tickets via `frob:todo`) matters more than the rule set.

### 9.4 Mechanics

- A `workflow` adapter (YAML parse with positions; tree-sitter-yaml exists; `serde_yaml`-family
  parsers lose comments, which matters because zizmor-style ignore comments and the `# vX.Y.Z` pin
  comment are semantically load-bearing: use a CST-preserving parser) mapping to the IR sketched in 7.1.
  Fidelity F3 with the `gha-expr` and `shell` islands as regions. Interpolation detection (CI007) needs only
  a regex-level expression scanner, not an expression evaluator.
- A tool stage that runs `zizmor --format json-v1` and `actionlint -format json`, maps each finding
  to a diagnostic with `locator = file + route` (zizmor already provides symbolic YAML routes in
  addition to row/column, which maps directly onto frob's pointer locations from universal-model.md
  section 2.5), caches by content hash of the workflow set plus tool version, and maps the tool's id
  to a frob id, preserving the tool id as `source_rule`. This is the "binding output" route and costs
  one adapter of about a hundred lines per tool.
- The rate-limit and offline lesson: online zizmor audits need a GitHub token and network; keep them
  off in `frob check` and available in a separate `frob audit --online`.
- Version sensitivity (section 3.3): record the tool version in the diagnostic and treat a schema-lag
  finding class as Unresolved rather than failing the build.

### 9.5 Honest caveats about the evidence

- Stars are not usage; heavily used low-star infrastructure (internal tools, small libraries with
  huge download counts) is under-sampled, and the language buckets exclude whatever the curated set
  already covered.
- Detection is heuristic. The prevalence of lint, format, typecheck, test and release automation are
  regex matches on workflow text, so they include steps that name the word but do not enforce (e.g.
  `continue-on-error`, matrix `experimental` entries) and miss logic hidden in composite actions,
  Makefiles, `just` recipes, `tox`/`nox` sessions and `./ci/*.sh` scripts (Makefile 24.8%, justfile 2.4%),
  so those percentages are floors for "has such a check somewhere" and ceilings for "enforces it".
- Only default branches were read. Long-lived release branches often carry different workflows.
- Per-repository percentages weight a six-workflow library the same as the 120-workflow tools; the
  per-workflow table in 2.5 corrects that for the structural rules.
- `tool` vs `library` is crude: the curated set contains libraries (react, django, serde, tokio, pandas) and
  some language-bucket repositories are tools; the tool/lib gap is therefore an under-estimate of the true
  gap and more a "curated infrastructure vs ranked-by-stars" gap.
- zizmor and actionlint ran on the YAML as downloaded, with no config; many projects have
  `.github/zizmor.yml` (3.1% of repositories, 10.0% of tools) or inline ignores, so real post-triage
  findings are fewer than the 64507 raw findings; the percentages above are "would fire out of the box".
- No hadolint, checkov, tflint, kube-linter or ansible-lint run: Dockerfile numbers come from my own
  structural checks (section 6.1), not from hadolint rules.

## 10. Reproduction

All commands run from the scratchpad directory above.

1. `python3 01_sample.py` (curated via `repos/` API plus language searches; creates `sample.json`;
   about 250 core calls and 36 search calls).
2. `python3 02_fetch.py` (1069 recursive-tree calls plus listings for 17 truncated trees; raw bodies
   from raw.githubusercontent.com).
3. `python3 03_lint.py` (needs `uvx zizmor` and `bin/actionlint`; writes `lint_findings.json`).
4. `python3 04_analyze.py`, `python3 05_stats.py > stats.txt`, `python3 06_perwf.py > perwf.txt`,
   `python3 07_docker.py`, `python3 08_docker_an.py > docker.txt`.
