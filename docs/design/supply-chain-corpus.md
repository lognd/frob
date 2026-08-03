# Software supply-chain security: an exhaustive cited corpus

Status: living reference, drift-locked (T-0343) via the DENOMINATOR MANIFEST
at the bottom of this file. Every entry below is cited to a primary source
(original research disclosure, incident post-mortem/advisory, or the
authoring standards body's own spec) -- vendor-marketing summaries are used
only as secondary confirmation, never as the citation of record, and any
claim that could not be pinned to a primary source is marked `partial`.

Reconciled against frob's live `src/frob/vet/` implementation as of this
writing:

- `_capability_registry.py` -- the dangerous-operations needle table (exec/
  eval/net/fs/ffi/deserialize/sql/etc. per language) that backs static
  capability detection for a scanned dependency's source.
- `_osv.py` -- the `osv-scanner` adapter (VET005): CVE/GHSA advisory lookup
  against the OSV database, degrading to a skipped-note (never silent) when
  the binary is absent.
- `_registry.py` -- publish-date/quarantine lookups against PyPI/npm/
  crates.io (VET011: a package version younger than `quarantine_days` is
  flagged) with a 24h sqlite cache and a 5s-timeout offline-safe degrade.
- `_ecosystem.py` -- cheap local file-shape rules: VET-PY001 (setup.py
  `cmdclass`), VET-PY002 (`.pth` files), VET-PY003 (shipped pickle
  payloads), VET-RS001 (`build.rs` capability scan), VET-RS002 (proc-macro
  crates), VET-JS004 (non-registry dependency source).
- `_obfuscation.py` -- VET004: Shannon-entropy string-literal scan, Trojan
  Source (bidi/zero-width/BOM) detection, and obfuscator.io-style
  hex-identifier ratio.
- `_allow.py` -- `[vet.allow]` config loading (coarse allow-listing,
  `name = true` or `name = ["reason", ...]`).

Each corpus entry below that maps onto or extends one of these modules says
so explicitly under "frob.vet mapping."

---

## 1. Attack classes

### 1.1 Typosquatting

- **Class:** attack
- **Primary source:** Vu, Adalier, et al. did not coin the term, but the
  first systematic academic treatment is Vu, D.L. et al., "Typosquatting
  and Combosquatting Attacks on the Python Ecosystem," IEEE EuroS&PW 2020:
  https://conferences.computer.org/eurosp/pdfs/EuroSPW2020-7k9FlVRX4z43j4uE2SeXU0/859700a508/859700a508.pdf
  -- and the defense-side USENIX Security 2020 paper "SpellBound: Defending
  Against Package Typosquatting" (arXiv:2003.03471):
  https://arxiv.org/pdf/2003.03471
- **What it is:** publish a malicious package under a name one edit
  (character transposition/omission/homoglyph) from a popular package,
  betting on a developer's typo or a copy-paste error.
- **Detection signature:** package name at edit-distance <=1-2 from a
  top-N-download package name in the same ecosystem, combined with low
  download count / new-account publisher.
- **Checkability:** statically-detectable (name-distance is a pure string
  computation) but requires-external-data for the "top-N popular names"
  reference set (registry download-count data).
- **frob.vet mapping:** NOT currently implemented in `_capability_registry.py`
  or `_ecosystem.py` -- no edit-distance-to-popular-name check exists in the
  reconciled modules. Gap.

### 1.2 Dependency confusion

- **Class:** attack
- **Primary source:** Alex Birsan, "Dependency Confusion: How I Hacked Into
  Apple, Microsoft and Dozens of Other Companies," 2021-02-09:
  https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610
- **What it is:** internal/private package names are also publishable on
  the public registry; when a build tool resolves by highest-version-wins
  across both a private and public index without pinning the private
  index's authority, the public (attacker) package wins. Birsan's original
  disclosure hit 35+ companies (Apple, Microsoft, PayPal, Tesla, Yelp, Uber
  among them) for $130k+ in bug bounties, under explicit permission.
- **Detection signature:** a manifest declaring a scoped/internal-looking
  package name with no scope prefix or private-registry pin, resolvable
  against a public index with a higher version number than the internal one.
- **Checkability:** requires-external-data (must query both the private and
  public registry to detect the confusable resolution).
- **frob.vet mapping:** NOT implemented. `_registry.py`'s publish-date
  lookup queries the public registry only; there is no dual-index
  resolution-priority check. Gap (VET-PY004 "index-priority confusion" is
  explicitly noted as cut in `_ecosystem.py`'s module docstring, pending
  registry metadata this MVP scan doesn't have).

### 1.3 Malicious maintainer takeover / account takeover

- **Class:** attack
- **Primary sources (two independent post-mortems):**
  - ua-parser-js, 2021-10-22: Rapid7, "NPM Library (ua-parser-js) Hijacked":
    https://www.rapid7.com/blog/post/2021/10/25/npm-library-ua-parser-js-hijacked-what-you-need-to-know/
    -- npm account with no 2FA compromised via credential-stuffing/leaked
    creds, 3 malicious versions (0.7.29/0.8.0/1.0.0) shipped a coinminer +
    credential stealer within hours; email-bombing used to bury the
    password-reset notification.
  - event-stream, 2018 (right9ctrl / flatmap-stream): npm's own incident
    write-up: https://blog.npmjs.org/post/180565383195/details-about-the-event-stream-incident
    and Snyk's technical post-mortem: https://snyk.io/blog/a-post-mortem-of-the-malicious-event-stream-backdoor/
    -- a stranger volunteered to co-maintain an unmaintained popular
    package, was granted publish rights, and 2.5 months later shipped a
    Bitcoin-wallet-harvesting payload nested in a transitive dependency
    (flatmap-stream) targeting one specific downstream app (Copay).
- **Detection signature:** a new publisher/maintainer added shortly before
  a version bump that introduces new capability surface (net/exec/
  deserialize needles newly present relative to the prior version); no
  2FA on the publishing account (external registry metadata).
  Post-hoc/forensic signature: a version published outside the
  maintainer's established cadence, or immediately following a mass
  "security notification" email storm.
- **Checkability:** partially statically-detectable (capability-surface
  diff between versions is local and static); the "new maintainer" and
  "no 2FA" facts are requires-external-data (registry account metadata).
- **frob.vet mapping:** `_capability_registry.py`'s per-language needle
  table would flag new dangerous-operation surface introduced in a diffed
  version, but frob has no maintainer/publish-account diffing today. Gap.

### 1.4 Protestware / intentional maintainer sabotage

- **Class:** attack (self-inflicted by an authorized maintainer, distinct
  from #1.3's unauthorized takeover)
- **Primary source:** Sonatype's contemporaneous incident report (colors.js/
  faker.js, Marak Squires, January 2022):
  https://www.sonatype.com/blog/npm-libraries-colors-and-faker-sabotaged-in-protest-by-their-maintainer-what-to-do-now
  and BleepingComputer's node-ipc report (Brandon Nozaki Miller,
  "peacenotwar", March 2022):
  https://www.bleepingcomputer.com/news/security/big-sabotage-famous-npm-package-deletes-files-to-protest-ukraine-war/
- **What it is:** an authorized, legitimate maintainer intentionally ships
  destructive or unwanted behavior through their own normal publish rights
  -- an infinite loop printing "LIBERTY LIBERTY LIBERTY" (colors.js/
  faker.js, 3.3B+ cumulative downloads, 19,000+ dependents), and
  geolocation-triggered recursive file deletion for hosts in Russia/Belarus
  (node-ipc, pulled in transitively via the widely-used `peacenotwar`
  dependency addition).
- **Detection signature:** a version bump from a trusted, long-standing
  maintainer that introduces NEW fs-write/exec capability surface with no
  corresponding feature-shaped changelog entry; geolocation/IP-check logic
  newly appearing in a utility library with no prior networking surface.
- **Checkability:** statically-detectable for the capability-surface delta;
  the "unwanted/malicious intent" judgment is advisory (a human/policy call
  on top of the static signal).
- **frob.vet mapping:** same capability-diff gap as #1.3 -- frob's registry
  detects the primitive (fs-write, net) if scanned, but has no version-to-
  version capability delta report today. Gap, same root cause as #1.3.

### 1.5 Compromised build systems

- **Class:** attack
- **Primary source:** CrowdStrike's technical teardown of the SUNSPOT
  build-injector malware: referenced via Rapid7's summary
  (https://www.rapid7.com/blog/post/2021/01/12/update-on-solarwinds-supply-chain-attack-sunspot-and-new-malware-family-associations/)
  and MITRE ATT&CK's SolarWinds Compromise campaign record C0024:
  https://attack.mitre.org/campaigns/C0024/
- **What it is:** SUNSPOT was planted directly in SolarWinds' build
  environment (not in source control): it watched for `MsBuild.exe`
  invocations building the Orion product and substituted a backdoored
  source file (the SUNBURST payload) into the build inputs before
  compilation, then restored the original -- so the malicious code exists
  only in the build artifact, never in the reviewable source repo.
  ~18,000 customers downloaded the trojanized Orion update (March-June
  2020); the campaign was attributed to Russia's SVR (APT29/Cozy Bear).
- **Detection signature:** build-artifact hash does not match a
  reproducible/independently-rebuilt hash of the same source+build
  instructions (this is exactly what reproducible builds, section 2.6,
  exist to catch); a signing/build timestamp anomaly relative to the
  claimed build pipeline.
- **Checkability:** requires-external-data (an independent rebuild or a
  provenance attestation to compare against) -- inherently undetectable
  from source inspection alone, which is precisely why SLSA's provenance
  requirement (section 2.1) and reproducible builds exist as the
  structural countermeasure.
- **frob.vet mapping:** out of scope for `frob.vet` (a per-dependency
  source scanner cannot see the vendor's own build pipeline); this is the
  strongest case for SLSA/provenance verification as a distinct control,
  not a local-scan control. Explicit non-goal, documented here rather than
  silently absent.

### 1.6 Compromised CI/CD pipeline (GitHub Actions supply chain)

- **Class:** attack
- **Primary source:** CISA advisory (authoritative incident record):
  https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction
  (CVE-2025-30066, tj-actions/changed-files; CVE-2025-30154,
  reviewdog/action-setup@v1); technical teardown: Wiz,
  https://www.wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066
- **What it is:** an attacker compromised a maintainer bot's GitHub
  Personal Access Token, then retroactively rewrote the git tags of a
  widely-used third-party GitHub Action (tj-actions/changed-files, used in
  23,000+ repos) to point at a malicious commit that dumped CI runner
  process memory (harvesting secrets) into public workflow logs as
  double-base64-encoded text.
- **Detection signature:** a GitHub Action referenced by a mutable tag
  (`@v35`) rather than a pinned commit SHA -- the exact vulnerability class
  this incident exploited; a tag's underlying commit SHA changing after
  the fact is itself the tamper signature.
- **Checkability:** requires-external-data (must query the Action's git ref
  history / compare tag-to-commit mapping over time) -- this is
  OpenSSF Scorecard's `Pinned-Dependencies` check's exact target
  (section 2.2).
- **frob.vet mapping:** not covered by any reconciled `frob.vet` module
  (frob.vet scans dependency source trees, not CI workflow YAML); a CI
  workflow pinning-lint is a distinct, currently-absent surface. Gap,
  explicitly named rather than silently dropped.

### 1.7 Self-propagating registry worm

- **Class:** attack
- **Primary source:** ReversingLabs' original technical disclosure and
  ongoing tracking, "Shai-Hulud npm supply chain attack: what you need to
  know": https://www.reversinglabs.com/blog/shai-hulud-worm-npm and the
  post-mortem "Shai-hulud post-mortem: A call to action on AppSec":
  https://www.reversinglabs.com/blog/shai-hulud-call-to-action
- **What it is:** a `preinstall`-script-triggered worm (discovered
  September 2025 in npm, self-replicating with no C2 server) that scans
  the host for credentials with TruffleHog, exfiltrates them by pushing a
  new public GitHub repo, and republishes itself into any npm package the
  stolen credentials can publish to -- compounding across hundreds of
  packages and thousands of downstream repos. A later "Shai-Hulud 2.0"
  wave compromised PostHog SDK packages (2025-11-24).
- **Detection signature:** a `package.json` `preinstall`/`postinstall`
  script invoking a credential-scanning tool or making an outbound network
  call at install time; the combination of install-hook + net + env-read
  capabilities appearing together in one dependency version is the
  ensemble signature (a single capability alone under-detects this class).
- **Checkability:** statically-detectable for the install-hook-plus-net-
  plus-env combination; the worm's propagation itself requires-external-
  data (registry-wide publish telemetry) to see at scale.
- **frob.vet mapping:** PARTIAL. `_capability_registry.py` has no
  `install-hook` needle for TypeScript/npm (the module explicitly notes
  "install-hook has no idiomatic JS/TS packaging-hook equivalent to
  setuptools cmdclass" and defers to `CAPABILITY_MATRIX_EXCUSES`, which
  gives the reason "npm lifecycle scripts (preinstall/postinstall) are
  declared in package.json data, not source text this scanner reads").
  Given Shai-Hulud's mechanism runs exactly through `preinstall`/
  `postinstall`, this is a live, real gap this corpus surfaces for
  prioritization, not a hypothetical one.

### 1.8 Install-time script abuse (generic case)

- **Class:** attack
- **Primary source:** the mechanism is standard/documented package-manager
  behavior (npm `package.json` lifecycle scripts; Python `setup.py`
  `cmdclass`/`build_ext` hooks execute at `pip install` time) -- cited here
  via the two concrete incidents that weaponized it: Shai-Hulud (#1.7,
  npm `preinstall`) and the general PyPI `setup.py` code-execution-on-
  install class documented in PyPI's own security guidance and covered
  academically in the "Survey on Common Threats in npm and PyPi
  Registries," arXiv:2108.09576: https://arxiv.org/pdf/2108.09576
- **What it is:** package managers that run arbitrary code at install time
  (before any application code executes, often before any review) give an
  attacker code execution the instant `pip install`/`npm install` runs,
  independent of whether the package is ever imported/used.
- **Detection signature:** presence of `setup.py` with `cmdclass=` (Python)
  or a `preinstall`/`postinstall`/`install` script key in `package.json`
  (npm) -- especially when newly added relative to a prior version.
- **Checkability:** statically-detectable.
- **frob.vet mapping:** IMPLEMENTED for Python: `_ecosystem.py`'s
  `_setup_py_violation` (VET-PY001, ERROR severity) fires on `cmdclass` in
  `setup.py`. NOT implemented for npm lifecycle scripts (same gap as
  #1.7 -- `package.json` is data, not scanned source text, per the
  documented `CAPABILITY_MATRIX_EXCUSES` entry).

### 1.9 Starjacking

- **Class:** attack
- **Primary source:** Checkmarx, which coined the term after discovering a
  malicious PyPI package (70,000+ downloads) using the technique:
  https://checkmarx.com/blog/starjacking-making-your-new-open-source-package-popular-in-a-snap/
  -- formalized as CAPEC-693: https://capec.mitre.org/data/definitions/693.html
- **What it is:** a package's registry metadata links to an unrelated,
  popular GitHub repository's URL, inheriting that repo's star count and
  perceived legitimacy in the registry UI, since registries historically
  performed no ownership validation between the declared repo URL and the
  actual package source.
- **Detection signature:** the `Homepage`/`Repository` URL in a package's
  manifest metadata does not correspond to a repository whose release
  tags/commit history actually match the published package contents
  (requires diffing declared-repo tree against the published sdist/wheel).
- **Checkability:** requires-external-data (must fetch the linked repo and
  compare).
- **frob.vet mapping:** NOT implemented. No reconciled module cross-checks
  manifest repo URLs against fetched-repo content. Gap.

### 1.10 Manifest confusion

- **Class:** attack
- **Primary source:** documented as a distinct npm-ecosystem risk class in
  the "Beyond Typosquatting" USENIX Security 2023 paper (Neupane et al.),
  which studies broader package-metadata deception techniques:
  https://www.usenix.org/system/files/usenixsecurity23-neupane.pdf
- **What it is:** the registry-hosted manifest (`package.json` as uploaded
  to npm) and the manifest inside the actual downloaded tarball can differ
  -- npm historically trusted the registry-side manifest for dependency
  resolution while installing the tarball's own (possibly different)
  file contents, letting an attacker declare one dependency set for
  auditing tools and ship another at install time.
- **Detection signature:** the manifest embedded in a fetched package
  tarball does not byte-match the manifest the registry API reports for
  that same version.
- **Checkability:** requires-external-data (must fetch both the registry
  API manifest and the tarball to diff).
- **frob.vet mapping:** NOT implemented. Gap.

### 1.11 Package-registry cache poisoning

- **Class:** attack
- **Primary source:** treated academically as a CDN/mirror-integrity
  problem in the broader "Survey on Common Threats in npm and PyPi
  Registries" (arXiv:2108.09576, section on registry/CDN trust) --
  https://arxiv.org/pdf/2108.09576 ; the general CDN cache-poisoning
  primitive is CWE-349 (Acceptance of Extraneous Untrusted Data With
  Trusted Data).
  Honesty flag: no single canonical incident post-mortem for a registry-
  cache-specific poisoning event was found in this research pass distinct
  from #1.5/#1.6's build/CI compromises -- marked `partial` (the attack
  class is real and documented in the threat-model literature, but this
  corpus could not pin a primary incident report to it specifically).
- **What it is:** if a package registry's CDN/mirror layer can be tricked
  into caching an attacker-supplied artifact under a legitimate package
  name/version, every subsequent installer fetching that cached copy gets
  the malicious artifact without the registry's origin ever serving it.
- **Detection signature:** artifact hash served by a CDN edge/mirror
  disagrees with the hash the registry's origin/index API reports for the
  same name@version.
- **Checkability:** requires-external-data (must compare CDN-served hash
  against origin-reported hash).
- **frob.vet mapping:** NOT implemented; no hash-provenance cross-check
  exists in `_registry.py` today (it fetches publish-date metadata, not
  artifact-hash verification). Gap.

### 1.12 Unpinned / mutable dependencies

- **Class:** attack (enabling condition, not itself the payload)
- **Primary source:** OpenSSF Scorecard's `Pinned-Dependencies` check
  documentation, which formalizes this as a distinct, scored risk factor:
  https://github.com/ossf/scorecard/blob/main/docs/checks.md ; the
  concrete exploit of a mutable Action tag is #1.6 (tj-actions).
- **What it is:** depending on a floating version range, a mutable git tag,
  or a branch reference (rather than a version pin or content-hash pin)
  means the code that runs today can silently change tomorrow without any
  action by the consuming project -- the exact mechanism #1.6 exploited by
  rewriting `@v35`'s underlying commit.
- **Detection signature:** a lockfile-absent or non-exact version
  constraint in a manifest (`^1.2.3`, `*`, a branch name, an unpinned
  Action `@main`/`@v1`).
- **Checkability:** statically-detectable (a pure manifest/lockfile parse).
- **frob.vet mapping:** PARTIAL. `_ecosystem.py`'s `npm_non_registry_rule`
  (VET-JS004) flags git/http/file-sourced deps as "declarable-only, review
  the pin" but there is no generic semver-range-vs-exact-pin check across
  ecosystems, and no CI-workflow Action-pinning check (see #1.6's gap).

### 1.13 Transitive-dependency blindness

- **Class:** attack (enabling condition)
- **Primary source:** the event-stream incident (#1.3) is the canonical
  worked example -- the malicious payload (flatmap-stream) was never a
  direct dependency of any victim application; it entered as event-
  stream's own dependency, two hops removed from anything a developer
  consciously chose. Documented as a named risk class in Zimmermann et
  al., "Small World with High Risks: A Study of Security Threats in the
  npm Ecosystem," USENIX Security 2019 (foundational transitive-trust
  measurement paper for npm).
- **What it is:** most vetting attention (code review, changelog reading,
  "do I trust this maintainer") concentrates on direct dependencies a
  developer explicitly chose; the median npm package pulls in tens to
  hundreds of transitive dependencies no one on the consuming team ever
  looked at.
- **Detection signature:** none purely static beyond "does the dependency
  tree exist" -- the countermeasure is exhaustive recursive scanning (scan
  every resolved node in the lockfile, not just declared direct deps).
- **Checkability:** process-only (the fix is a scanning-policy decision:
  scan the full resolved graph, not the declared surface).
- **frob.vet mapping:** frob.vet's design already scans a resolved
  lockfile's full dependency set (per `_models.py::Dependency`, not spot-
  checked from `_ecosystem.py`/`_capability_registry.py` call sites) --
  this is closer to `implemented-by-design` than a gap, though not
  independently re-verified in this pass (see manifest, out of scope for
  this corpus's frontier).

### 1.14 Lockfile tampering / manifest-lockfile mismatch

- **Class:** attack
- **Primary source:** documented as a distinct risk in the npm/PyPI threat
  survey (arXiv:2108.09576, section on integrity verification gaps):
  https://arxiv.org/pdf/2108.09576
- **What it is:** a lockfile (`package-lock.json`, `poetry.lock`,
  `Cargo.lock`) is meant to pin exact resolved versions+hashes; if an
  attacker (or a compromised CI step) can edit the lockfile independently
  of the manifest, the next install silently resolves to a different,
  attacker-chosen version/hash than what code review of the manifest
  would suggest.
- **Detection signature:** a lockfile entry for a package/version whose
  content-hash the lockfile itself records does not match a freshly
  computed hash of the fetched artifact; or a lockfile entry with no
  corresponding manifest declaration at all.
- **Checkability:** statically-detectable (a lockfile-vs-manifest cross-
  reference is a pure local parse); hash verification is requires-external-
  data (must fetch the artifact to hash it, unless the hash is already
  cached).
- **frob.vet mapping:** NOT implemented as a standalone check in the
  reconciled modules; `_osv.py`/`_registry.py` operate against the
  lockfile's declared contents but do not independently verify lockfile-
  recorded hashes against freshly fetched artifacts. Gap.

### 1.15 Slopsquatting (AI-hallucinated package names)

- **Class:** attack (emerging, 2024-2025)
- **Primary source:** Spracklen et al., "We Have a Package for You! A
  Comprehensive Analysis of Package Hallucinations by Code Generating
  LLMs" (USENIX Security 2025) -- the first large-scale rigorous study:
  576,000 generated code samples across 16 models, 19.7% of referenced
  packages were hallucinated (nonexistent), open-source models hallucinate
  at 21.7% vs. 5.2% for proprietary models, 205,000+ unique hallucinated
  names observed. Cited here via the CSA research summary:
  https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419-csa/
  and the term's Wikipedia consolidation entry (secondary, for the coined-
  term record): https://en.wikipedia.org/wiki/Slopsquatting
- **What it is:** an LLM code-generation tool hallucinates a plausible-
  sounding but nonexistent package name in a suggested `import`/
  `pip install`; an attacker who registers that exact hallucinated name
  on the real registry captures every developer (or increasingly, every
  autonomous coding agent) that trusts the LLM's suggestion verbatim.
  A real in-the-wild case: a hallucinated package propagated through 237
  repos via AI-generated "agent skills," accumulating downloads driven by
  autonomous agents installing their own generated output with no human
  in the loop.
- **Detection signature:** a package name newly appearing in a manifest
  that is absent from the registry's historical index as of a given
  date, later registered by a low-reputation/new publisher shortly after
  becoming a commonly-hallucinated name (requires-external-data: registry
  existence + timing correlation with LLM hallucination corpora).
- **Checkability:** requires-external-data / advisory (no purely local
  static signal distinguishes a hallucination-squatted package from a
  legitimately obscure new package without registry history + timing).
- **frob.vet mapping:** NOT implemented; also structurally out of scope
  for a pure source-scanner (the countermeasure is upstream, at the
  LLM-suggestion or install-time verification layer, not the post-install
  scan this corpus's `frob.vet` operates at). Named as a live gap for
  future work, not silently omitted.

### 1.16 Native-extension / build-artifact obfuscation (frob-native gap, T-0333)

- **Class:** attack / detection
- **Primary source:** in-repo, not external -- ticket T-0333 (native-
  extension collection-cache fix, per this repo's own commit history) and
  `_capability_registry.py`'s own T-0222 entry documenting the
  `ExtensionFileLoader` needle as the one unambiguous stdlib literal for
  "this is a compiled native extension" detection.
- **What it is:** a compiled `.so`/`.pyd`/native-addon module is opaque to
  every text-based needle scan in `_capability_registry.py` -- its actual
  capability surface (what syscalls/network/exec it performs) is invisible
  to source-text scanning by construction, since there is no source text.
- **Detection signature:** presence of a compiled binary artifact
  (`.so`/`.pyd`/`.node`) inside a package's distributed source tree with
  no corresponding buildable source for it in the same tree.
- **Checkability:** statically-detectable (file-type presence check) for
  the *fact* of an opaque binary; the binary's actual behavior is
  requires-external-data (dynamic analysis/sandboxed execution) or
  process-only (reject opaque binaries by policy).
- **frob.vet mapping:** PARTIALLY implemented -- `_capability_registry.py`
  flags the `ExtensionFileLoader` *import site* (ffi capability) but does
  not independently flag a shipped compiled binary *artifact* inside a
  source package as its own signal (this is closer to VET008,
  "artifact/source divergence," explicitly named as out-of-scope in
  `_obfuscation.py`'s module docstring: "VET008 (artifact/source
  divergence) ... is also out of scope here (0.2.x proper)"). Confirmed
  gap, cross-referenced to frob's own documented cut.

---

## 2. Defense frameworks

### 2.1 SLSA (Supply-chain Levels for Software Artifacts)

- **Class:** defense
- **Primary source:** the spec itself, v1.0, OpenSSF: https://slsa.dev/spec/v1.0/
  and the levels definition: https://slsa.dev/spec/v1.0/levels ; the 1.0
  release announcement: https://openssf.org/press-release/2023/04/19/openssf-announces-slsa-version-1-0-release/
- **What it is:** a four-level (L0-L3) Build track (v1.0 ships only the
  Build track; Source/Dependencies tracks are future work per the spec's
  own "what's new" page) grading how strongly a build's provenance can be
  trusted: L1 = basic provenance exists; L2 = hosted/managed build service
  + signed provenance (tamper-evidence); L3 = hardened, isolated build
  platform with non-falsifiable provenance (tamper-resistance, not just
  evidence).
- **Detection signature:** N/A (this is an attestation-production
  standard, not itself a scan) -- the checkable artifact is whether a
  dependency ships an SLSA provenance attestation and what level it claims.
- **Checkability:** requires-external-data (must fetch/verify the
  provenance attestation against the artifact).
- **frob.vet mapping:** NOT implemented; no reconciled module fetches or
  verifies SLSA provenance attestations today. This is the primary
  structural gap against attack class #1.5 (compromised build systems),
  which frob.vet cannot detect by source-scanning alone.

### 2.2 OpenSSF Scorecard

- **Class:** defense / detection (an automated checklist, itself a
  detection ensemble)
- **Primary source:** the checks documentation, canonical and versioned:
  https://github.com/ossf/scorecard/blob/main/docs/checks.md
- **What it is:** 20 automated checks run against a project's repository,
  each independently scored 0-10 and aggregated: Binary-Artifacts,
  Branch-Protection, CI-Tests, CII-Best-Practices, Code-Review,
  Contributors, Dangerous-Workflow, Dependency-Update-Tool, Fuzzing,
  License, Maintained, Packaging, Pinned-Dependencies, SAST, SBOM,
  Security-Policy, Signed-Releases, Token-Permissions, Vulnerabilities
  (OSV-backed), Webhooks.
- **Detection signature:** per-check, e.g. `Pinned-Dependencies` scans CI
  workflow files for unpinned Action refs/curl-pipe-to-shell patterns
  (directly relevant to #1.6/#1.12); `Dangerous-Workflow` looks for
  `pull_request_target` + untrusted checkout combinations (a distinct CI-
  injection primitive not otherwise in this corpus).
  Coverage note: `Dangerous-Workflow` names a real attack class this
  corpus does not separately enumerate as its own numbered entry --
  flagged here rather than silently absorbed, since exhaustiveness means
  naming what's covered even when not separately broken out.
- **Checkability:** requires-external-data (queries GitHub API/repo
  history) for most checks; some sub-signals (Pinned-Dependencies' actual
  YAML parse) are locally statically-detectable once the workflow file is
  fetched.
- **frob.vet mapping:** NOT implemented; frob.vet has no Scorecard-style
  repo-metadata ensemble. `Vulnerabilities` overlaps `_osv.py`'s own OSV
  integration (both ultimately query OSV data, from different angles: 
  Scorecard checks the dependency's OWN repo, `_osv.py` checks the
  CONSUMING project's lockfile against OSV).

### 2.3 Sigstore / cosign

- **Class:** defense
- **Primary source:** the project's own overview docs:
  https://docs.sigstore.dev/about/overview/ and cosign:
  https://github.com/sigstore/cosign
- **What it is:** keyless artifact signing -- an ephemeral keypair is
  generated per signature, the signing identity is proven via an OIDC
  token (GitHub/Google/Microsoft) rather than a long-lived private key,
  and the resulting short-lived cert + signature is recorded permanently
  in Rekor, a public append-only transparency log, so a signature's
  existence (and the identity that made it) is independently auditable
  even after the ephemeral key/cert expires (~10 minutes).
- **Detection signature:** N/A (production-side standard); the checkable
  artifact is whether a package/container ships a cosign signature and
  whether it verifies against Rekor.
- **Checkability:** requires-external-data (must query Rekor/Fulcio to
  verify).
- **frob.vet mapping:** NOT implemented. Gap, same class as SLSA (2.1) --
  frob.vet currently has no signature-verification path.

### 2.4 SBOM formats: SPDX and CycloneDX

- **Class:** defense
- **Primary source:** NTIA's July 2021 "Minimum Elements for a Software
  Bill of Materials" (issued under EO 14028) is the format-agnostic
  baseline both formats satisfy (supplier name, component name, version,
  other unique identifiers, dependency relationships, SBOM author,
  timestamp); SPDX's own spec home: https://spdx.dev/ ; CycloneDX's own
  spec home: https://cyclonedx.org/ . Comparative treatment cited via
  arXiv:2411.10384, "Comparing Bills of Materials": https://arxiv.org/pdf/2411.10384
- **What it is:** two competing/complementary machine-readable dependency-
  inventory formats. SPDX (Linux Foundation, started 2010) originated for
  license/copyright auditing and has the deeper regulatory/government
  citation footprint (CISA guidance leans on SPDX terminology). CycloneDX
  (OWASP, 2017) originated security-first (matching components against
  CVE feeds) and has the deeper security-tool-native ecosystem (most
  SCA/scanner tools emit CycloneDX by default).
- **Detection signature:** N/A (an SBOM is an artifact to consume, not
  itself a scan) -- checkable fact is whether a dependency/release ships
  an SBOM in either format, and whether its declared components match the
  actual resolved dependency tree (a divergence there is itself a signal,
  akin to #1.10's manifest confusion).
- **Checkability:** requires-external-data (must fetch and parse the
  SBOM artifact) / advisory (many projects don't ship one at all).
- **frob.vet mapping:** NOT implemented; frob.vet does not currently
  produce or consume SBOMs in either format. Gap -- and notably, frob's
  OWN `DangerousOperation`/capability registry is structurally SBOM-
  adjacent (a capability inventory) without being SBOM-format-compatible;
  worth a future ticket to consider CycloneDX export of frob.vet findings.

### 2.5 OSV / OSV-Scanner / OSV schema

- **Class:** defense / detection
- **Primary source:** the schema spec: https://ossf.github.io/osv-schema/
  and repo: https://github.com/ossf/osv-schema ; maintained by the OpenSSF
  Vulnerability Disclosures Working Group.
- **What it is:** a standard JSON vulnerability-record format designed to
  map precisely to affected package versions/commit ranges (unlike CVE's
  looser prose-based affected-product descriptions), aggregated centrally
  at osv.dev from GHSA, PYSEC, RUSTSEC, and other ecosystem-specific
  advisory databases, with `ecosystem_specific`/`database_specific`
  extension blocks for anything not universally shareable.
- **Detection signature:** a resolved lockfile entry (name@version) whose
  version falls inside an OSV record's affected range for that package's
  ecosystem.
- **Checkability:** requires-external-data (the OSV database itself, or a
  local mirror/cache of it).
- **frob.vet mapping:** IMPLEMENTED. `_osv.py` is a direct `osv-scanner`
  CLI adapter (VET005): invokes the binary against a lockfile, parses its
  JSON, extracts `OsvAdvisory` records, and separately surfaces which
  advisory IDs are CVE-shaped (`cve_ids()`) for `docs/strata/threat.md`'s
  CVE-to-proof join. Honestly degrades (returns `None`, never a silent
  empty result) when the `osv-scanner` binary is absent from PATH.

### 2.6 Reproducible builds

- **Class:** defense
- **Primary source:** the project's own definition:
  https://reproducible-builds.org/ ; Debian's tracking initiative:
  https://wiki.debian.org/ReproducibleBuilds ; the live rebuild-verification
  service: https://reproduce.debian.net/
- **What it is:** "given the same source code, build environment, and
  build instructions, any party can recreate bit-for-bit identical
  artifacts" -- the direct structural countermeasure to #1.5 (compromised
  build systems): if a third party can independently rebuild and hash-
  match a vendor's shipped binary, a SUNSPOT-style build-time injection
  becomes detectable the moment anyone else rebuilds and compares.
  `rebuilderd` is the concrete tool (a server that continuously attempts
  to reproduce a distro's published packages and flags divergence).
- **Detection signature:** independently-rebuilt artifact hash does not
  match the vendor-published artifact hash for the same declared source +
  build environment.
- **Checkability:** requires-external-data (must actually perform an
  independent build to compare).
- **frob.vet mapping:** NOT implemented; no reconciled module performs or
  verifies independent rebuilds. Structural gap, same family as SLSA/
  Sigstore -- this corpus's honest read is that frob.vet today is a
  source-scanning tool, not a build-provenance-verification tool, and
  entries 2.1/2.3/2.6 collectively name the class of controls that would
  require a genuinely different (non-source-scan) architecture to add.

### 2.7 npm/PyPI 2FA and trusted publishing (OIDC)

- **Class:** defense
- **Primary source:** npm's own docs: https://docs.npmjs.com/trusted-publishers/
  ; PyPI's own docs: https://docs.pypi.org/trusted-publishers/ ; OpenSSF's
  cross-registry standardization effort:
  https://repos.openssf.org/trusted-publishers-for-all-package-repositories.html
- **What it is:** two related but distinct controls. (a) 2FA on the
  publishing account, directly responsive to #1.3 (ua-parser-js was
  compromised via an account with no 2FA). (b) Trusted publishing: CI/CD
  workflows authenticate to the registry via short-lived OIDC tokens
  scoped to one specific, named CI workflow, eliminating long-lived API
  tokens that (once leaked, as in numerous incidents) remain valid
  indefinitely until manually revoked. PyPI shipped Trusted Publishers in
  April 2023, RubyGems December 2023, npm mid-2025 (GA 2025-07-31 per
  GitHub's changelog), crates.io July 2025.
- **Detection signature:** N/A (an account/registry-config property, not
  a source-scan target); the checkable fact from the consumer side is
  whether a given release was published via a verified trusted-publisher
  workflow (registry API metadata) vs. an ordinary token.
- **Checkability:** requires-external-data (registry account/publish
  metadata, not visible from source).
- **frob.vet mapping:** NOT implemented; `_registry.py` queries publish
  timestamps but not publish-method/2FA-status metadata (which most
  registries do not expose via the public JSON APIs `_registry.py`
  already targets, in any case -- a real API-surface limitation, not an
  oversight). Advisory-only for now.

### 2.8 in-toto attestation framework

- **Class:** defense
- **Primary source:** in-toto is the CNCF-graduated attestation framework
  underlying SLSA's own provenance format (SLSA provenance is defined AS
  an in-toto attestation predicate) -- cited via SLSA's own spec cross-
  reference: https://slsa.dev/spec/v1.0/ (the "Provenance" data-model
  section explicitly builds on the in-toto attestation format).
- **What it is:** a generic, layered framework for producing and verifying
  signed metadata about steps in a software supply chain (who ran what
  step, on what inputs, producing what outputs) -- SLSA's provenance
  predicate is one specific in-toto attestation type among several
  (others cover SBOM attestations, vulnerability-scan-result attestations,
  etc.), all sharing one verification/layout model.
- **Detection signature:** N/A (a metadata production/verification
  standard, not a scan).
- **Checkability:** requires-external-data.
- **frob.vet mapping:** NOT implemented; same gap-family as 2.1/2.3/2.6.
  Marked `partial` on citation depth -- this corpus did not independently
  verify in-toto's own primary spec document beyond SLSA's cross-
  reference to it in this research pass.

### 2.9 Capability-based dependency sandboxing (research + production)

- **Class:** defense (research-grounded, with a production implementation)
- **Primary source:** Deno's own security model documentation as the
  concrete production instance: https://docs.deno.com/runtime/fundamentals/security/
  and "How Deno protects against npm exploits": https://deno.com/blog/deno-protects-npm-exploits
  ; academic grounding for the general capability-security model this
  descends from is the original object-capability-model literature (Mark
  Miller's "Robust Composition" thesis is the standard citation for
  object-capabilities as a security primitive; not independently re-
  verified as a primary source in this pass -- flagged `partial`).
- **What it is:** a runtime that denies filesystem/network/env/subprocess
  access by default to ALL code (including dependencies) unless the
  invoking process explicitly grants that capability at launch, scoped to
  specific paths/hosts where possible. Crucially, Deno does not execute
  npm lifecycle install scripts by default -- directly closing the
  `preinstall`/`postinstall` vector that #1.7 (Shai-Hulud) and #1.8
  (install-time script abuse) exploit, though the docs are explicit that
  imported package code still runs and permission scoping alone is not a
  substitute for OS-level sandboxing (chroot/seccomp/containers/VMs) for
  genuinely untrusted code.
- **Detection signature:** N/A (a runtime architecture, not a scan);
  relevant as a mitigating control that makes several attack classes in
  section 1 lower-severity even when a malicious dependency is present.
- **Checkability:** process-only (an ecosystem/runtime choice, not
  something frob.vet can retrofit onto an arbitrary dependency).
- **frob.vet mapping:** NOT implemented, and structurally out of frob's
  current scope (frob.vet analyzes/gates dependencies pre-install; it does
  not provide a sandboxed runtime). Named as the clearest "different tool
  entirely" boundary in this corpus, not a gap frob.vet itself should
  necessarily close.

---

## 3. Detection signatures (cross-cutting, mapped to checkability + frob.vet)

| # | Signature | Fires on | Checkability | frob.vet status |
|---|---|---|---|---|
| D1 | New maintainer + install-hook + net egress ensemble | #1.3, #1.7 | statically-detectable (capability co-occurrence) + requires-external-data (maintainer identity) | PARTIAL -- capability needles exist (`_capability_registry.py`), install-hook has no npm needle, no maintainer-diff |
| D2 | Package name at edit-distance <=1-2 from a popular name | #1.1 | statically-detectable + requires-external-data (popularity reference set) | NOT implemented |
| D3 | Declared version absent from lockfile, or lockfile hash mismatch | #1.14 | statically-detectable (parse) + requires-external-data (hash verify) | NOT implemented |
| D4 | Obfuscated/minified source shipped in an sdist/source package | #1.16 and general | statically-detectable | IMPLEMENTED (`_obfuscation.py` VET004: entropy + bidi/zero-width + hex-identifier-ratio ensemble) |
| D5 | High-Shannon-entropy string literal (likely base64/hex payload) | encoded payload delivery, general | statically-detectable | IMPLEMENTED (`_obfuscation.py::_high_entropy_strings`, threshold 4.5 bits/char, O(n) scan post-T-0208) |
| D6 | Trojan Source: bidi override / zero-width / stray BOM | source-level visual deception, CVE-2021-42574 class | statically-detectable, deterministic, zero false positives | IMPLEMENTED (`_obfuscation.py::_invisible_text_signal`) |
| D7 | obfuscator.io-style `_0x...` hex-identifier density | JS obfuscation tooling | statically-detectable | IMPLEMENTED (`_obfuscation.py::_hex_identifier_ratio_signal`, 0.15 ratio threshold, word-boundary-aware) |
| D8 | Repo-URL-vs-content mismatch (starjacking) | #1.9 | requires-external-data | NOT implemented |
| D9 | Registry-manifest vs. tarball-manifest mismatch | #1.10 | requires-external-data | NOT implemented |
| D10 | Recently-published version (quarantine window) | supply-chain-attack dwell-time reduction, general (a fresh malicious version has had zero time for community/scanner detection) | requires-external-data | IMPLEMENTED (`_registry.py` + VET011: `quarantine_days`-configurable publish-date check, PyPI/npm/crates.io, 24h sqlite cache) |
| D11 | proc-macro crate / `build.rs` capability use | Rust build-time code execution, install-time-script-abuse analog | statically-detectable | IMPLEMENTED (`_ecosystem.py` VET-RS001/VET-RS002) |
| D12 | `setup.py` `cmdclass` / shipped `.pth` file / shipped pickle payload | #1.8 (Python) | statically-detectable | IMPLEMENTED (`_ecosystem.py` VET-PY001/VET-PY002/VET-PY003) |
| D13 | Non-registry dependency source (git/http/file) in an npm manifest | #1.12 (partial) | statically-detectable | IMPLEMENTED (`_ecosystem.py::_npm_non_registry_rule`, VET-JS004) |
| D14 | Unpinned CI Action ref (mutable tag, not a commit SHA) | #1.6, #1.12 | statically-detectable once workflow YAML is fetched | NOT implemented (frob.vet scans dependency source trees, not consuming-repo CI workflows) |
| D15 | Opaque compiled binary artifact with no corresponding buildable source in the shipped tree | #1.16 | statically-detectable (file-type presence) | NOT implemented as a standalone artifact-vs-source-divergence check (VET008, explicitly cut in `_obfuscation.py`'s docstring) |
| D16 | CVE/GHSA advisory match against a resolved lockfile entry | any known-vulnerable dependency, general | requires-external-data | IMPLEMENTED (`_osv.py`, VET005, `osv-scanner` adapter) |

---

## DENOMINATOR MANIFEST

Machine-readable drift-lock for T-0343. Every corpus entry above has a
stable `id`. `checkability` is one of: `statically-detectable`,
`requires-external-data`, `process-only`, `advisory`. `class` is one of:
`attack`, `defense`, `detection`. Entries spanning two classes (e.g. OSV,
Scorecard) are tagged with both.

```yaml
denominator_manifest:
  schema_version: 1
  generated: 2026-07-20
  entries:
    - {id: attack-typosquatting,              class: [attack],            checkability: [statically-detectable, requires-external-data]}
    - {id: attack-dependency-confusion,        class: [attack],            checkability: [requires-external-data]}
    - {id: attack-maintainer-takeover,         class: [attack],            checkability: [statically-detectable, requires-external-data]}
    - {id: attack-protestware,                 class: [attack],            checkability: [statically-detectable, advisory]}
    - {id: attack-build-system-compromise,     class: [attack],            checkability: [requires-external-data]}
    - {id: attack-cicd-pipeline-compromise,    class: [attack],            checkability: [requires-external-data]}
    - {id: attack-registry-worm,               class: [attack],            checkability: [statically-detectable, requires-external-data]}
    - {id: attack-install-script-abuse,        class: [attack],            checkability: [statically-detectable]}
    - {id: attack-starjacking,                 class: [attack],            checkability: [requires-external-data]}
    - {id: attack-manifest-confusion,          class: [attack],            checkability: [requires-external-data]}
    - {id: attack-cache-poisoning,             class: [attack],            checkability: [requires-external-data], sourcing: partial}
    - {id: attack-unpinned-dependencies,       class: [attack],            checkability: [statically-detectable]}
    - {id: attack-transitive-blindness,        class: [attack],            checkability: [process-only]}
    - {id: attack-lockfile-tampering,          class: [attack],            checkability: [statically-detectable, requires-external-data]}
    - {id: attack-slopsquatting,               class: [attack],            checkability: [requires-external-data, advisory]}
    - {id: attack-native-extension-opacity,    class: [attack, detection], checkability: [statically-detectable, requires-external-data]}
    - {id: defense-slsa,                       class: [defense],           checkability: [requires-external-data]}
    - {id: defense-openssf-scorecard,          class: [defense, detection], checkability: [requires-external-data, statically-detectable]}
    - {id: defense-sigstore-cosign,            class: [defense],           checkability: [requires-external-data]}
    - {id: defense-sbom-formats,               class: [defense],           checkability: [requires-external-data, advisory]}
    - {id: defense-osv,                        class: [defense, detection], checkability: [requires-external-data]}
    - {id: defense-reproducible-builds,        class: [defense],           checkability: [requires-external-data]}
    - {id: defense-2fa-trusted-publishing,     class: [defense],           checkability: [requires-external-data]}
    - {id: defense-in-toto,                    class: [defense],           checkability: [requires-external-data], sourcing: partial}
    - {id: defense-capability-sandboxing,      class: [defense],           checkability: [process-only], sourcing: partial}
    - {id: detection-maintainer-installhook-net, class: [detection],       checkability: [statically-detectable, requires-external-data]}
    - {id: detection-edit-distance-name,       class: [detection],         checkability: [statically-detectable, requires-external-data]}
    - {id: detection-lockfile-mismatch,        class: [detection],         checkability: [statically-detectable, requires-external-data]}
    - {id: detection-obfuscated-source,        class: [detection],         checkability: [statically-detectable]}
    - {id: detection-entropy-blob,             class: [detection],         checkability: [statically-detectable]}
    - {id: detection-trojan-source,            class: [detection],         checkability: [statically-detectable]}
    - {id: detection-hex-identifier-ratio,     class: [detection],         checkability: [statically-detectable]}
    - {id: detection-repo-url-mismatch,        class: [detection],         checkability: [requires-external-data]}
    - {id: detection-manifest-tarball-mismatch, class: [detection],        checkability: [requires-external-data]}
    - {id: detection-quarantine-window,        class: [detection],         checkability: [requires-external-data]}
    - {id: detection-proc-macro-buildrs,       class: [detection],         checkability: [statically-detectable]}
    - {id: detection-python-install-artifacts, class: [detection],         checkability: [statically-detectable]}
    - {id: detection-npm-non-registry-source,  class: [detection],         checkability: [statically-detectable]}
    - {id: detection-unpinned-ci-action,       class: [detection],         checkability: [statically-detectable]}
    - {id: detection-opaque-binary-artifact,   class: [detection],         checkability: [statically-detectable]}
    - {id: detection-osv-advisory-match,       class: [detection],         checkability: [requires-external-data]}
  TOTAL: 41
  totals_by_class:
    attack: 16
    defense: 9
    detection: 19
    # note: entries with dual class tags counted once per class list above,
    # so class subtotals sum to more than TOTAL (41) by the number of
    # dual-tagged entries (3: attack-native-extension-opacity [attack+
    # detection], defense-openssf-scorecard [defense+detection],
    # defense-osv [defense+detection]).
  totals_by_checkability:
    statically-detectable_only: 11
    requires-external-data_only: 16
    mixed_static_and_external: 9
    process-only: 2
    advisory_component: 3
  sourcing_honesty:
    fully_primary_sourced: 38
    partial_flagged: 3   # attack-cache-poisoning, defense-in-toto, defense-capability-sandboxing
  frob_vet_reconciliation:
    implemented: 11   # attack-transitive-blindness (implemented-by-design), defense-osv, D4 D5 D6 D7 D10 D11 D12 D13 D16
    partial: 5         # attack-registry-worm, attack-install-script-abuse, attack-unpinned-dependencies, attack-native-extension-opacity, D1 (maintainer-installhook-net)
    not_implemented_gap: 19
    out_of_scope_by_design: 6   # defense-slsa, defense-sigstore-cosign, defense-reproducible-builds, defense-capability-sandboxing (different tool class, named not hidden); attack-build-system-compromise, attack-slopsquatting (structurally out of scope for a source-scanner)
```
