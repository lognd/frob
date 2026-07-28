# strata: coverage totality (T-0341 epic)

This file is the `docs/modules/strata.md` doc-edge home the T-0341 epic's
child tickets declare in their `scope` (`tickets.md` T-0341, T-0667, and
siblings). The detailed SYS100-102 self-conformance mechanism (grammar,
gap statements, waiver shape) lives in `docs/strata/selfconform.md` --
this file adds only what T-0667's own scope covers and does not duplicate
that page.

<a id="sys-cov-coverage-totality-sys103-t-0667"></a>
## SYS-COV coverage totality (SYS103, T-0667)

`frob sys audit`'s self-conformance family (`src/frob/strata/_selfconform.py`)
gains a fourth rule, SYS103, whose finding label is "SYS-COV" --
`docs/design/structural-linter-adversarial-hardening.md`'s "un-modeled
module" row and the T-0341 epic's acceptance criterion [0]: "every
deployable/public module -- and every module the binding-aware scanner
finds ANY capability in -- must bind to exactly one strata node;
unbound-but-capable code is a hard failure." Same posture as COV001 for
missing documentation: a capable module that escapes the `.strata` model
escapes every downstream obligation this repo can express, so leaving it
un-modeled cannot be a silent pass.

### Why SYS103, not just SYS102

SYS102 ("unmodeled code", `docs/strata/selfconform.md#the-three-rules`)
already flags every `FOREIGN` file inside `src/frob/` -- but it is
hardcoded to `_PACKAGE_ROOT` ("src/frob"), frob's own package layout
(T-0211). Every other repo `frob sys audit` runs against structurally
lacks `src/frob/`, so SYS102 is permanently, silently vacuous there --
exactly the evasion the T-0341 epic exists to close. SYS103 is the
repo-general form: it runs over the SAME `_capability_binding` superset
(`bind_code` + the T-0169 non-Python extension) on WHATEVER root is
audited, with no `src/frob/`-specific path assumption -- EXCEPT on frob's
own tree, where `_coverage_totality_scan_prefix` restricts it to
`_PACKAGE_ROOT`, same as SYS102 (see "Known gap" below for why).

### Rule

A `FOREIGN` file (no node's `code=` glob claims it) for which
`frob.vet._capability.scan_file_capabilities` (T-0328's import/binding-
aware resolver -- not a bare substring guess) observes at least one
capability fires SYS103 once, naming the file and the observed capability
kind(s) in its `detail`. A `FOREIGN` file with zero observed capabilities
(pure data, a re-export-only `__init__.py`) does not fire -- it carries no
dangerous effect escaping an obligation, so it is not the failure mode
SYS-COV exists to catch. A file bound to any real node never fires SYS103
regardless of what it does (SYS100/SYS101 already reconcile a BOUND
file's declared-vs-observed capabilities; SYS103's only question is
binding, not conformance).

### Waiving

SYS103 has no per-capability-kind sub-target (unlike SYS100/SYS101):
the finding is about the whole FILE having no owner, not one specific
kind of it. It is not in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, so
it takes the bare-rule waiver form: `waive "SYS103" reason "..." ticket
"T-...";` -- same shape as SYS102's.

### Known gap: registry cross-reference

`docs/design/registry/check-coverage.yaml`'s `CHK-GATE-SYS100`/
`CHK-GATE-SYS101`/`CHK-GATE-SYS102` entries record each sibling rule as "a
live, enforced gate rule". A matching `CHK-GATE-SYS103` entry (and the
corresponding `frob:enforces CHK-GATE-SYS103` directive on
`check_self_conformance`) was NOT added by T-0667: `docs/design/
registry/**` is outside this ticket's declared `scope`. Filed as a
follow-up so the registry cross-reference does not silently lag (see
T-0667's Done report for the filed ticket id).

### Known gap: `_PACKAGE_ROOT` restriction on frob's own tree

Running SYS103 unrestricted (whole `root`, no `_PACKAGE_ROOT` prefix
filter) against frob's OWN `design/frob.strata` surfaces 264 real,
currently-unmodeled findings under `tests/**`, `scripts/**`,
`frob-core/src/**`, and `strata-core/src/**` (measured 2026-07-28) --
`design/frob.strata` has only ever declared `code=`/`may` for
`src/frob/`. Wiring that unrestricted would have regressed the live
`SELFAUDIT001` gate (`src/frob/gates/__init__.py`, out of T-0667's
declared scope) from green to 264 errors on this repo's own `frob check
--only sys`. `_coverage_totality_scan_prefix` avoids that regression by
restricting SYS103 to `_PACKAGE_ROOT` specifically when auditing frob's
own tree (any OTHER repo still gets the full, unrestricted root scan --
see "Why SYS103, not just SYS102" above). Generalizing SYS103 past
`_PACKAGE_ROOT` for frob's own tree -- i.e. actually declaring `code=`/
`may` for `tests/**`/`scripts/**`/`frob-core/src/**`/`strata-core/src/**`
in `design/frob.strata`, or deciding some of those are legitimately out
of the model's scope with a reasoned waiver -- is real, disclosed
follow-up work (see T-0667's Done report for the filed ticket id), not
done by this ticket.
