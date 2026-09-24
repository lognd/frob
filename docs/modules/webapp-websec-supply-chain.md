# frob.webapp._websec_supply_chain -- WEBSEC318-325 CI/supply-chain hardening

One sentence: `frob.webapp._websec_supply_chain.websec_supply_chain_findings`
extends `frob.gates._taint_gate.taint_gate`'s WEBSEC scan with an EIGHTH
framework-scoped family covering GitHub Actions workflow hardening,
Dockerfile hardening, and dependency manifest/lockfile hygiene, folded
into `taint_gate`'s own scan via T-5308's pkgutil-discovery hook rather
than a second gate registration -- the same reasoning T-5307's
`docs/modules/webapp-websec-injection.md` already documents for
WEBSEC101-106.

This is a downstream leaf of the T-5140 web-app epic's seven-sibling
substrate wave (`docs/modules/webapp.md`'s own scope: framework
detection only, not any individual rule family).

## Framework gating

`websec_supply_chain_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

| rule | shape | file kind | detection |
| --- | --- | --- | --- |
| WEBSEC318 | a workflow step echoes/prints a `${{ secrets.* }}` expansion directly, no `::add-mask::` guard first | GitHub Actions workflow YAML | text-regex |
| WEBSEC319 | `pull_request_target` trigger combined with a fork-PR-head `actions/checkout` AND a `secrets.` reference in the same workflow | GitHub Actions workflow YAML | `yaml.safe_load` parse (trigger + fork-head checkout) + text-regex (secrets use) |
| WEBSEC320 | no `USER` instruction anywhere before the final `ENTRYPOINT`/`CMD` | Dockerfile | text-regex |
| WEBSEC321 | a `FROM` line pinned to `:latest` (or no tag at all) | Dockerfile | text-regex |
| WEBSEC322 | a dependency manifest tracked with no matching lockfile | manifest/lockfile pair | tracked-file-set presence check |
| WEBSEC323 | a lockfile present, but at least one manifest-declared dependency name is not found anywhere in the lockfile text | manifest/lockfile pair | best-effort text-containment diff |
| WEBSEC324 | a manifest dependency name within Levenshtein distance 1-2 of a bundled popular-package name for that ecosystem, but not an exact match | manifest | Levenshtein edit distance against `_POPULAR_PACKAGES` |
| WEBSEC325 | a GitHub Actions workflow granting `permissions: write-all` at the workflow level | GitHub Actions workflow YAML | text-regex |

WEBSEC322/323/324 currently recognize five manifest/lockfile pairs:
`package.json`/(`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`),
`pyproject.toml`/(`uv.lock`, `poetry.lock`), `Gemfile`/`Gemfile.lock`,
`go.mod`/`go.sum`, `Cargo.toml`/`Cargo.lock`. WEBSEC324's popular-package
list is bundled and deliberately NOT exhaustive (top-10 per ecosystem as
of this leaf, `npm` and `pypi` only) -- a real typosquat check would
query a live package-registry popularity feed; this is a best-effort
local heuristic, the same disclosed-gap posture every text-regex WEBSEC
family in this epic carries.

### Deliberately out of scope: SHA-pinned `uses:` refs

A GitHub Actions `uses: owner/action@ref` pinned to a mutable tag/branch
rather than a full 40-hex commit SHA is a real CI supply-chain hardening
gap, and appears in this ticket's own corpus, but it is NOT implemented
in this module. `frob.vet._supplychain._unpinned_ci_action_violations`
(rule `VET009`) already ships exactly that check today, and T-3923 is
the open ticket to extend it further. This leaf cross-references rather
than duplicates that check.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/T-5307's `websec_sink_findings`/T-5308's
`websec_headers_log_findings` already follow for a brand-new structural
rule.

## Public API

- `WebsecSupplyChainFinding` (`src/frob/webapp/_websec_supply_chain.py`)
  -- one finding: `rule`, `file`, `line`, `message`.
- `websec_supply_chain_findings(root: Path) ->
  tuple[WebsecSupplyChainFinding, ...]` -- every WEBSEC318-325 finding
  under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- the `taint_gate` module-
  discovery hook (T-5308): `frob.gates._taint_gate.taint_gate`
  auto-discovers every `frob.webapp._websec_*` module exposing a
  module-level `websec_findings(root, frameworks)` callable and folds
  its returned `Violation`s into the same tuple it returns, so this
  leaf never needs its own hand-edit to `_taint_gate.py`/
  `gates/__init__.py`. `frameworks` is the caller's own
  already-computed `detect_frameworks(root)` result (this hook never
  re-detects); an empty set short-circuits to `()`, same contract as
  `websec_supply_chain_findings` itself.

## Tests and fixtures

`tests/unit/test_websec_supply_chain.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec3xx/supply/webesc3{18..25}_{positive,negative}/`,
each carrying a minimal Flask (`requirements.txt` with `flask`) or
Next.js (`package.json` naming `next`) framework marker so
`detect_frameworks` fires, plus exactly the workflow/Dockerfile/manifest
shape under test. Also includes an end-to-end positive control
(`test_taint_gate_discovers_websec_supply_chain_hook`) proving
`frob.gates._taint_gate.taint_gate` discovers and calls this module's
hook with no `_taint_gate.py` edit.

frob:ticket T-5331
