"""LANGUAGES/CAPABILITY_KINDS: the single-source vocabulary the rest of
`frob.vet._capability_registry` compiles against (T-0158). Split out of
the former monolithic module (T-1420) so the vocabulary constants have a
home independent of the (much larger) dangerous-operation tables that
consume them."""

from __future__ import annotations

# frob:doc docs/modules/vet.md#public-api
#: every language the matrix reasons about. C and C++ share one bucket
#: (`c-cpp`) since the dangerous idioms -- `system`/`popen`/`exec*`/
#: `dlopen`/`strcpy`-family -- are identical C ABI surface in both.
LANGUAGES: tuple[str, ...] = ("python", "typescript", "rust", "c-cpp", "kotlin")

# frob:doc docs/modules/vet.md#public-api
#: SINGLE-SOURCE enumeration of every reserved capability kind (T-0158).
#: Union of: every `capability_kind` `frob.strata._threat.CWE_CATALOG`/
#: `CWE_TOP_25_CATALOG` names, every kind `DEFAULT_BENIGN_CAPABILITIES`
#: excuses, and every kind this registry's `_DangerousOperation` table
#: patterns. Any kind used anywhere else that is NOT in this tuple is a
#: drift bug -- `_validate_registry_kinds` (below) is the loud failure.
CAPABILITY_KINDS: tuple[str, ...] = (
    #: T-1073 naming-reconciliation decision: this stays `"exec"`, NOT
    #: renamed to `"proc"` to match `frob.vet._capability_modes.
    #: FAMILY_MODES`'s `"proc"` family -- the two are deliberately
    #: different vocabulary LAYERS (raw scanner kind here vs. mode-
    #: qualified `family.mode` id there), same split `fs-write`/`fs` and
    #: `net-connect`/`net` already carry below. `_capability_modes.
    #: PROC_FAMILY_SCANNER_KIND` is the one named bridge between this
    #: string and that family, for whichever ticket wires `proc`'s
    #: tier-2 join.
    "exec",
    "eval",
    "net",
    #: T-0771 (T-0717 follow-up): precise connect-vs-listen scanner-
    #: observed kinds, the `net` sibling of `fs-write`/`fs-read` below --
    #: same shape, same reason (a coarse `may "net"` declaration stays
    #: legal and backward-compatibly satisfied by either observed kind via
    #: `frob.vet._capability_modes.expand_declared_kind`, now that `net` is
    #: in `WIRED_MODE_FAMILIES`). A handful of legacy "net" entries with no
    #: clean connect/listen distinction (none remain in this registry as of
    #: T-0771 -- every `net`-kind `_DangerousOperation` was reclassified)
    #: would stay coarse "net" rather than force a guess.
    "net-connect",
    "net-listen",
    #: T-0771: `frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES` excuses
    #: THREAT005 against the tier-2 `_effects.py::_KIND_MAP`-NORMALIZED
    #: observed kind (`net.connect`/`net.listen`, mode-qualified, the same
    #: spelling `may` declarations resolve to) -- a DIFFERENT string from
    #: the raw vet-scanner kind just above (`net-connect`/`net-listen`,
    #: hyphenated). Both live here: `_validate_registry_kinds` treats
    #: "every kind used anywhere" as one flat vocabulary, so the
    #: mode-qualified spelling needs its own registration too (mirrors
    #: `frob.vet._capability_modes.CAPABILITY_MODE_KINDS`, generated
    #: separately from `FAMILY_MODES` for the SAME two strings -- kept
    #: as literals here rather than importing that tuple to avoid a
    #: registry -> capability_modes import for two constant strings).
    "net.connect",
    "net.listen",
    "fs-write",
    #: `frob.strata._effects._KIND_MAP` normalizes the scanner's `fs-write`
    #: spelling to `fs` for the tier-2 `may`-declaration vocabulary (net/
    #: fs-write/exec are the three delegated kinds); `DEFAULT_BENIGN_
    #: CAPABILITIES` excuses THAT normalized spelling, not the raw scanner
    #: token, so both live in this registry.
    "fs",
    #: T-0018 (graphite adoption): a node whose code ONLY reads local
    #: filesystem state (config loads, e.g. `Path.read_text()`/
    #: `json.loads()`) could never satisfy SYS101 declaring `may "fs"` --
    #: the scanner only ever emitted the write-derived "fs"/"fs-write"
    #: kinds, forcing a `waive "SYS101:fs"` for genuinely-real read-only
    #: access. `fs-read` is a NEW, separate observed kind (not an alias of
    #: "fs"); `frob.strata._selfconform`'s SYS101 join treats a bare `may
    #: "fs"` declaration as backward-compatibly satisfied by EITHER
    #: observed kind (a pre-existing "fs" declaration should not go stale
    #: just because the only real access turns out to be reads), while a
    #: node that declares `may "fs-read"` specifically gets the honest,
    #: narrower signal (docs/strata/selfconform.md#fs-read-fs-write).
    "fs-read",
    #: T-1252: `fs` joined `frob.vet._capability_modes.WIRED_MODE_
    #: FAMILIES` -- `frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES` now
    #: excuses THREAT005 against the tier-2 `_effects.py::_KIND_MAP`-
    #: NORMALIZED observed kind (`fs.read`/`fs.write`, mode-qualified, the
    #: same spelling `may` declarations resolve to) -- a DIFFERENT string
    #: from the raw vet-scanner kind just above (`fs-read`/`fs-write`,
    #: hyphenated), mirroring `net.connect`/`net.listen`'s and `env.read`/
    #: `env.write`'s own T-0771/T-1075 dual-registration.
    "fs.read",
    "fs.write",
    "env",
    #: T-0771: precise read-vs-write scanner-observed kinds for `env`, the
    #: same shape as `net-connect`/`net-listen` above.
    "env-read",
    "env-write",
    #: T-1075: `env` joined `frob.vet._capability_modes.WIRED_MODE_
    #: FAMILIES` -- `frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES` now
    #: excuses THREAT005 against the tier-2 `_effects.py::_KIND_MAP`-
    #: NORMALIZED observed kind (`env.read`/`env.write`, mode-qualified,
    #: the same spelling `may` declarations resolve to) -- a DIFFERENT
    #: string from the raw vet-scanner kind just above (`env-read`/
    #: `env-write`, hyphenated), mirroring `net.connect`/`net.listen`'s
    #: own T-0771 dual-registration just above.
    "env.read",
    "env.write",
    #: T-1439: process-lifecycle/signal-handling operations (`sys.exit`/
    #: `os._exit`, `signal.signal`) reclassified OUT of bare `env` -- they
    #: never read or wrote an environment variable, they shared the `env`
    #: string only by a pre-existing kind-naming mismatch (T-0771's own
    #: Done report flagged it, left unfixed at the time). Considered and
    #: rejected reusing `install-hook` for this: that kind is specifically
    #: packaging-lifecycle code (setuptools cmdclass, npm postinstall), a
    #: different semantic surface from a running process exiting or
    #: handling a signal.
    "process-control",
    "ffi",
    "install-hook",
    "html_render",
    "sql",
    "fetch_url",
    "deserialize",
    "client_storage",
    #: T-0244: a large HTML/JS-shaped STRING LITERAL embedded in another
    #: language's source (the malmberg pilot P3 shape -- a 5400-line
    #: dashboard's markup/script sitting inside a Python string) is
    #: structurally invisible to every per-language needle table above,
    #: which only ever scans a file's OWN source grammar. `frob.vet.
    #: _capability._embedded_code_regions` detects such a region (size +
    #: HTML/JS signal heuristic) and always emits this kind for the region
    #: it found, independent of whether the embedded needle re-scan below
    #: (typescript table over the region's own text) turns up anything
    #: specific -- fail-closed per docs/design/structural-linter-
    #: adversarial-hardening.md rule 3: the region is DECLARED, never
    #: silently passed, even when the best-effort re-scan is empty.
    "embedded_code",
)


# T-0524: frob:doc removed -- DANGEROUS_OPERATIONS (public, below) already
# carries both the same docs/modules/vet.md#public-api anchor and the
# extending-guide anchor (COV007: a private schema class does not need
# its own copy of the doc edge its public constant already carries).
