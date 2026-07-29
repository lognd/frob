"""OPAQUE001: fail-closed obligation for runtime-resolved capability
indirection (docs/modules/gates.md#rule-catalog, T-0665).

`docs/design/capability-evasion-taxonomy.md` defines two disjoint universes
per language: statically-resolvable name bindings (the ordinary per-language
resolver `frob.vet._capability`'s `scan_file_capabilities` already walks,
T-0328/T-0377/T-0378/T-0379/T-0662/T-0663/T-0664) and "runtime-opaque"
constructs the spec itself says are resolved at runtime, not by any static
analysis. T-0339's
own doctrine is that the analysis MUST fail closed on the latter -- it must
never silently claim "no capability" through a construct it cannot see
through. This gate is that fail-closed boundary: `frob.vet.
_capability._opaque_indirection_findings` finds every coordinator-signed
"evasion-indicative dynamic lookup" site (category 1 of the T-0665 sign-off
-- `eval`/`exec`, a non-literal `getattr`/`setattr`/`__import__`/
`importlib.import_module` name, a non-literal `dlsym` symbol, a non-literal
JS/TS dynamic `import()` specifier, reflection APIs, and `libloading`
dynamic symbol lookup), and this gate turns every finding into a
`Violation` unless a `frob:waive OPAQUE001 reason="..."` (T-0174) is
present -- never a silent pass.

Two sibling categories the T-0665 sign-off explicitly carved OUT of this
gate, not silently dropped:

- BOUNDED POLYMORPHISM (ordinary virtual dispatch/`dyn Trait`/interface
  calls whose implementation set is statically enumerable in-repo): not a
  finding at all -- the may-analysis is sound over the statically-visible
  override/impl set, so no capability is laundered. Where the impl set is
  OPEN (plugins arriving via dynamic loading), the dangerous construct is
  the dynamic LOAD itself, which this gate's `libloading`/`dlsym`/reflection
  rows already catch at their own site.
- SOURCE-INVISIBLE constructs (linker weak-symbol interposition,
  LD_PRELOAD-class, runtime vtable patching): excused via
  `frob.vet._capability_registry.OPAQUE_SOURCE_INVISIBLE`'s REG011-
  compliant "none -- <explanation>" dispositions, cross-registered in
  `docs/design/registry/check-coverage.yaml` so the REG gates keep them
  accountable forever rather than silently forgotten -- this gate makes no
  attempt to detect them (it cannot; that is the whole point of the
  disposition), and never claims to.

T-0665's own first-turn-on measurement against this repo's live codebase
found frob's own use of dynamic `getattr` at more than the T-0688/T-0973
25-site WARN-first threshold -- 93 sites. T-1038 fixed or waived 90 of
them (every site outside `src/frob/gates/**`, which was out of its
declared scope, owned by a concurrent sibling ticket this wave); the
3 remaining `src/frob/gates/**` sites and the actual promotion to
`Severity.ERROR` are tracked by a follow-up ticket (see tickets.md) --
the T-0973/T-0976 promote-at-zero precedent means promoting happens in
the SAME land that zeroes the REPO-WIDE unwaived count, never before.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._tracked_files import tracked_files as _shared_tracked_files
from frob.lang import supported_extensions
from frob.logging import get_logger
from frob.vet._capability import _opaque_indirection_findings

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0665
# frob:tests tests/test_vet.py::TestOpaqueIndirectionGate.test_opaque_gate_emits_warn_severity_violation  # noqa: E501
# frob:tests tests/test_vet.py::TestOpaqueIndirectionGate.test_opaque_gate_no_findings_on_empty_tracked_set  # noqa: E501
# frob:tests tests/test_vet.py::TestOpaqueIndirectionGate.test_waived_finding_is_suppressed_and_reason_recorded  # noqa: E501
# frob:enforces CHK-GATE-OPAQUE001
# T-1087: two `docs/design/registry/supply-chain.yaml` entries whose
# structural finding source is `frob.vet._capability_registry.
# RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS` (native-extension import,
# proc-macro/build.rs) but whose enforcing VIOLATION-emitting rule is
# this gate's own OPAQUE001 -- the `frob:enforces` edge belongs at the
# rule's emission site, not the out-of-this-ticket's-scope detection
# module.
# frob:enforces SC-ATTACK-NATIVE-EXTENSION-OPACITY
# frob:enforces SC-DETECTION-PROC-MACRO-BUILDRS
# frob:waive AFFECT001 reason="T-1038: this docstring edit is the disposition-count \
# update itself (93 -> 90-fixed-or-waived/3-deferred) already fully told by the \
# docstring text; docs/modules/gates.md#public-api's own OPAQUE001 entry describes the \
# rule's mechanism, not its live promotion status, so nothing there needs to change"
def opaque_gate(root: Path) -> tuple[Violation, ...]:
    """OPAQUE001: every git-tracked, language-recognized source file
    scanned for `RUNTIME_OPAQUE_CONSTRUCTS` sites (T-0665). WARN-tier
    (`Severity.WARN`, not `Severity.ERROR`) still, at T-1038's own close:
    that ticket fixed or waived every non-`src/frob/gates/**` site (90 of
    93), but 3 sites inside `src/frob/gates/**` were out of its declared
    scope (owned by a concurrent sibling ticket) and remain live/unwaived
    -- promoting to ERROR before those resolve would red the build on a
    site this ticket could not touch. A follow-up ticket (see tickets.md)
    tracks disposing the last 3 and completing the promotion; do not
    flip this to ERROR without it landing (or those 3 being resolved)."""
    root = Path(root)
    exts = set(supported_extensions())
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _shared_tracked_files(root, caller="opaque_gate"):
        if Path(rel_path).suffix not in exts:
            continue
        abs_path = root / rel_path
        try:
            findings = _opaque_indirection_findings(abs_path)
        except OSError as exc:
            _log.debug("opaque_gate: skipping unreadable %s: %s", rel_path, exc)
            continue
        scanned += 1
        for finding in findings:
            violations.append(
                Violation(
                    rule="OPAQUE001",
                    # T-1185: promoted WARN -> ERROR now that every named
                    # gates/** site (T-1038's original 90/93 plus this
                    # ticket's last 3) is fixed-or-waived repo-wide, same
                    # promote-at-zero posture as SEC110 (T-0973)/PII010/
                    # PII012 (T-0971).
                    severity=Severity.ERROR,
                    file=rel_path,
                    line=finding.line,
                    message=(
                        f"OPAQUE001: {rel_path}:{finding.line} "
                        f"{finding.construct_name} is a runtime-resolved "
                        f"capability indirection ({finding.taxonomy_row}) -- "
                        f"{finding.rationale}; the fail-closed obligation "
                        f"fires because no static resolver can see through "
                        f"it. Fix by resolving the target statically, or "
                        f'`frob:waive OPAQUE001 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )

    _log.info(
        "opaque_gate: scanned %d tracked file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = ["opaque_gate"]
