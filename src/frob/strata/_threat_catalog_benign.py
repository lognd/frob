"""strata `BenignCapability` excuse data: the built-in
`DEFAULT_BENIGN_CAPABILITIES` tuple excusing `may` capability kinds the
CWE/quality catalogs do not classify (T-1420 split from `_threat.py`,
verbatim relocation -- WHY: pure data, no runtime check, previously
sitting inside the same file as every catalog and all the checker logic
that reads it). See docs/strata/threat.md#phasing and
docs/guides/extending/benign-capabilities.md#benign-capabilities."""

from __future__ import annotations

from ._threat_models import BenignCapability

#: T-0150: `may` capability kinds `_selfconform.py`'s SYS100/SYS101 measure
#: via `frob.vet._capability`'s scanner vocabulary (net/fs-write-derived
#: "fs"/eval/env/ffi/install-hook) that name NO `CWE_CATALOG`/
#: `QUALITY_CATALOG` `capability_kind` at all (the catalog's kinds --
#: html_render/sql/exec/fetch_url/deserialize/client_storage -- are a
#: DIFFERENT, CWE-sink-shaped vocabulary, docs/strata/threat.md#the-
#: catalog-stdcwe). Declaring these on `design/frob.strata`'s nodes (so
#: SYS100/SYS101 can reconcile them) would otherwise fail THREAT002 on
#: every one of them ("matches no sink taxonomy entry") with NO way to
#: excuse it, since `BenignCapability` is a Python-side argument neither
#: `evaluate_exhaustiveness` (`_audit.py`) nor `audit_claim` (`_sysdoc.py`,
#: DOC003's model-side half) wired to a default until now. `exec` IS
#: listed below too, despite having a real `CWE_CATALOG` entry (CWE-78) --
#: `_evaluate_family` (`_audit.py`) passes the SAME `benign` tuple to BOTH
#: the security (`CWE_CATALOG`) and quality (`QUALITY_CATALOG`) family
#: loops, and `QUALITY_CATALOG` has no `exec`-mapped entry at all;
#: `check_capability_completeness`'s `known` set is catalog-derived, so
#: `exec` already being `known` for the security loop makes this entry a
#: no-op there (`excused` is consulted only for kinds NOT already known) --
#: it only takes effect for the quality loop, where it is a genuine gap in
#: `QUALITY_CATALOG`'s vocabulary, not a security exemption.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:waive AFFECT001 reason="T-1075 added env.read/env.write entries, same shape as \
# every other entry already in this tuple; docs/strata/threat.md is outside T-1075's \
# declared scope (src/frob/strata/_effects.py, src/frob/vet/_capability_modes.py, \
# extended to src/frob/strata/_selfconform.py, src/frob/strata/_threat.py, \
# src/frob/vet/_capability_registry.py, and their test files) -- matches T-1047's own \
# precedent for the identical situation on CAPABILITY_KINDS"
DEFAULT_BENIGN_CAPABILITIES: tuple[BenignCapability, ...] = (
    BenignCapability(
        kind="exec",
        reason=(
            "already classified as CWE-78 in CWE_CATALOG (the security "
            "family); this entry only affects the QUALITY_CATALOG loop, "
            "which has no exec-mapped weakness at all -- module docstring "
            "above explains why this is a no-op for the security loop"
        ),
        caught_by=(
            "CWE-78 in CWE_CATALOG (the security family); this entry "
            "only affects the QUALITY_CATALOG loop"
        ),
    ),
    BenignCapability(
        kind="net",
        reason=(
            "tier-2 net-effect capability (T-0079 _KIND_MAP); no CWE_CATALOG "
            "entry targets bare outbound network calls as a sink on their own "
            "(SSRF/fetch_url is the catalog's closest analog and is a distinct, "
            "already-classified kind)"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets bare outbound network "
            "calls as a sink on their own; not compensated elsewhere"
        ),
    ),
    # T-0771: `net` joined `frob.vet._capability_modes.WIRED_MODE_FAMILIES`
    # -- `_effects.py::_KIND_MAP` now normalizes an observed net effect to
    # the precise `net.connect`/`net.listen` spelling (T-0717's own
    # `fs.write`/`fs.read` precedent) instead of the coarse bare `net`
    # THREAT005's `check_effect_completeness` used to see, so the bare
    # `net` excuse above no longer matches a real observed effect's
    # `.kind` -- mandate point 2 ("BenignCapability entries... would be
    # needed... once a family is wired") applied for real, not deferred.
    # `net.listen` has no code exercising it in this repo's own `src/`
    # tree (frob is a CLI/library, not a server) but is excused
    # unconditionally anyway -- unreachable today is not the same claim as
    # "can never happen", and an excuse that only fires when hit is not
    # weaker for firing rarely.
    BenignCapability(
        kind="net.connect",
        reason=(
            "same reasoning as the bare 'net' excuse above, T-0771's "
            "precise spelling: no CWE_CATALOG entry targets an outbound "
            "network connection as a sink on its own"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets bare outbound network "
            "calls as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="net.listen",
        reason=(
            "same reasoning as the bare 'net' excuse above, T-0771's "
            "precise spelling: no CWE_CATALOG entry targets binding/"
            "accepting inbound network connections as a sink on its own"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets an inbound network bind/"
            "accept as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="fs",
        reason=(
            "tier-2 filesystem-write capability (T-0079 _KIND_MAP, from vet's "
            "fs-write); no CWE_CATALOG entry targets local filesystem writes "
            "as a sink on their own (CWE-22 path traversal is a distinct, "
            "flow-to-path-sink precondition, capability_kind=None)"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets local filesystem writes "
            "as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="fs-read",
        reason=(
            "T-0018 (graphite adoption): tier-2 filesystem-read capability, "
            "the read-only sibling of the fs-write-derived 'fs' kind above "
            "(frob.vet._capability_registry, split so a read-only node is "
            "not forced to declare a write-shaped capability it does not "
            "have); no CWE_CATALOG entry targets local filesystem reads as a "
            "sink on their own, same rationale as 'fs' above"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets local filesystem reads "
            "as a sink on their own (same gap as 'fs'); not compensated "
            "elsewhere"
        ),
    ),
    # T-0717 added the precise, mode-qualified `fs.write`/`fs.read` spellings
    # (`_effects.py::_KIND_MAP`, `frob.vet._capability_modes`) as the
    # preferred replacement for the deprecated bare `fs`/`fs-read` kinds
    # above -- same `net`/`net.connect`/`net.listen` precedent as T-0771's
    # entries earlier in this tuple. The old `fs`/`fs-read` entries are kept
    # (not replaced) since `LEGACY_CAPABILITY_ALIASES` still lets a consumer
    # declare the deprecated spelling; these two entries are what let
    # `design/frob.strata`'s own migrated nodes (may "fs.write"/"fs.read")
    # pass THREAT002 without a per-node waiver.
    BenignCapability(
        kind="fs.write",
        reason=(
            "T-0717 mode-qualified spelling of the tier-2 filesystem-write "
            "capability above ('fs'); no CWE_CATALOG entry targets local "
            "filesystem writes as a sink on their own (CWE-22 path "
            "traversal is a distinct, flow-to-path-sink precondition, "
            "capability_kind=None), same rationale as 'fs'"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets local filesystem writes "
            "as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="fs.read",
        reason=(
            "T-0717 mode-qualified spelling of the tier-2 filesystem-read "
            "capability above ('fs-read'); no CWE_CATALOG entry targets "
            "local filesystem reads as a sink on their own, same rationale "
            "as 'fs-read'"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets local filesystem reads "
            "as a sink on their own (same gap as 'fs-read'); not "
            "compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="process-control",
        reason=(
            "process-lifecycle/signal-handling registry entries (sys.exit/"
            "os._exit, signal.signal), reclassified out of the bare 'env' "
            "capability kind by T-1439 -- they were never an actual "
            "environment-variable read or write; no CWE_CATALOG entry "
            "targets process termination or signal-handler installation "
            "as a sink on their own"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets process termination or "
            "signal-handler installation as a sink on their own; not "
            "compensated elsewhere"
        ),
    ),
    # T-1439: bare `env` keeps ITS OWN excuse even after the process-
    # control reclassification above -- `env` is still a legal coarse
    # `may "env"` declaration spelling on real design nodes (cli, core,
    # gates, mutate, natives, testsuite, tickets_ledger, vet), discharged
    # via `expand_declared_kind` by either the env-read or env-write
    # observed kind (T-1075's `WIRED_MODE_FAMILIES` wiring). THREAT002
    # still needs a taxonomy answer for the coarse spelling itself.
    BenignCapability(
        kind="env",
        reason=(
            'coarse `may "env"` is a legal, backward-compatible '
            "declaration spelling discharged by either the env-read or "
            "env-write observed kind (T-1075); no CWE_CATALOG entry "
            "targets a bare, unqualified environment-variable capability "
            "as a sink on their own"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets a bare environment-"
            "variable capability as a sink on its own; not compensated "
            "elsewhere"
        ),
    ),
    # T-1075: `env` joined `frob.vet._capability_modes.WIRED_MODE_FAMILIES`
    # -- `_effects.py::_KIND_MAP` now normalizes an observed env-read/
    # env-write effect to the precise `env.read`/`env.write` spelling
    # (T-0771's needle split) instead of the coarse bare `env` THREAT005's
    # `check_effect_completeness` used to see for those two, so these two
    # excuses are ADDITIONAL to (not a replacement for) the bare `env`
    # excuse above, mirroring `net`'s T-0771 precedent exactly.
    BenignCapability(
        kind="env.read",
        reason=(
            "tier-2 environment-variable-read capability (T-0079/T-1075 "
            "_KIND_MAP, from vet's env-read); no CWE_CATALOG entry targets "
            "environment-variable reads as a sink on their own"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets environment-variable "
            "reads as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="env.write",
        reason=(
            "tier-2 environment-variable-write capability (T-0079/T-1075 "
            "_KIND_MAP, from vet's env-write); no CWE_CATALOG entry "
            "targets environment-variable writes as a sink on their own"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets environment-variable "
            "writes as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="ffi",
        reason=(
            "vet dependency-vetting signal (ctypes/extern C usage); no "
            "CWE_CATALOG entry targets FFI/native-extension boundaries as a "
            "sink in v0's catalog"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets FFI/native-extension "
            "boundaries as a sink in v0's catalog; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="install-hook",
        reason=(
            "vet dependency-vetting signal (setuptools packaging install "
            "hooks); no CWE_CATALOG entry targets packaging install hooks as "
            "a sink -- this is a dependency-supply-chain concern `frob vet` "
            "itself already flags, not a CWE-catalog weakness"
        ),
        caught_by=(
            "frob vet's dependency-supply-chain scan -- the mechanism that "
            "already flags packaging install hooks"
        ),
    ),
    # T-0158: `deserialize`/`fetch_url` ARE mapped in `CWE_CATALOG` (CWE-502/
    # CWE-918, the security family) but have NO `QUALITY_CATALOG` entry at
    # all -- same "distinct family, distinct vocabulary" shape the module
    # docstring already explains for `exec`/`net`/`fs` above. Without these
    # two entries the QUALITY_CATALOG loop alone would flag both kinds as
    # unmapped (THREAT002), even though the security loop already accounts
    # for them via a real CWE with a real discharge obligation.
    BenignCapability(
        kind="deserialize",
        reason=(
            "already classified as CWE-502 in CWE_CATALOG (the security "
            "family); QUALITY_CATALOG has no deserialization-mapped entry "
            "at all -- this entry only affects the QUALITY_CATALOG loop"
        ),
        caught_by=(
            "CWE-502 in CWE_CATALOG (the security family); this entry "
            "only affects the QUALITY_CATALOG loop"
        ),
    ),
    BenignCapability(
        kind="fetch_url",
        reason=(
            "already classified as CWE-918 in CWE_CATALOG (the security "
            "family); QUALITY_CATALOG has no SSRF/fetch-mapped entry at "
            "all -- this entry only affects the QUALITY_CATALOG loop"
        ),
        caught_by=(
            "CWE-918 in CWE_CATALOG (the security family); this entry "
            "only affects the QUALITY_CATALOG loop"
        ),
    ),
)
