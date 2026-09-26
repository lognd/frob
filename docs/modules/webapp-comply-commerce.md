# frob.webapp._comply_commerce -- COMPLY123-127 commerce dark patterns

One sentence: `comply_commerce_findings` lints a repo's subscription/
cancellation route table, email templates, and checkout form fields
against 16 CFR 425 (click-to-cancel), CAN-SPAM, and a PCI SAQ-A scope
proxy -- reusing `frob.webapp._comply_substrate` (T-5360) for its
manifest signals and adding its own route-table/email-template text
scans, which the substrate has no API for at all.

## Relationship to `frob.webapp._comply_substrate` (T-5360)

This module calls `detect_signals` for `ComplySignal.SUBSCRIPTIONS`/
`ComplySignal.EMAIL_COLLECTION` and never re-implements manifest
sniffing. The substrate's own `RequiredPage` union covers only privacy/
terms/accessibility pages -- it has no route-table depth-comparison API
and no email-template content API -- so this module's route-string and
email-template scans are new work, not a duplicate of anything the
substrate already owns.

Stripe webhook SIGNATURE verification is explicitly out of this leaf's
corpus (T-5144-3/WEBSEC config-headers owns that check); this module
never duplicates it.

## The five rule ids

- **COMPLY123** -- a subscribe/checkout route exists but no cancel-
  shaped route exists anywhere in the route table (16 CFR 425
  click-to-cancel: a Negative Option Rule cancellation mechanism must
  exist).
- **COMPLY124** -- both exist, but the shallowest cancel route is
  deeper (more `/`-segments) than the shallowest subscribe/checkout
  route -- a proxy for 16 CFR 425's equal-prominence/simplicity
  requirement.
- **COMPLY125** -- `ComplySignal.EMAIL_COLLECTION`/`SUBSCRIPTIONS`
  detected and an email-template-shaped file exists, but none has an
  unsubscribe-shaped link (CAN-SPAM 15 U.S.C. 7704(a)(3)/(5)).
- **COMPLY126** -- same gating, but no email template has a
  postal-address-shaped line (CAN-SPAM 15 U.S.C. 7704(a)(5)).
- **COMPLY127** -- `ComplySignal.SUBSCRIPTIONS` detected and a raw
  card-number/CVV form field is found with no Stripe/hosted-checkout
  element marker in the same file -- a PCI SAQ-A scope proxy (SAQ-A's
  premise is that raw cardholder data never touches the merchant's own
  form fields).

## Public API

### ComplyCommerceFinding

`@dataclass(frozen=True)`: `rule: str`, `file: str`, `line: int`,
`message: str` -- one COMPLY123-127 finding.

### comply_commerce_findings

`comply_commerce_findings(root: Path) -> tuple[ComplyCommerceFinding, ...]`

Short-circuits to `()` when `frob.webapp._detect.detect_frameworks(root)`
reports no web framework at all (T-5302's contract, same posture every
sibling WEBSEC/COMPLY family follows).

### websec_findings

`websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) -> tuple[Violation, ...]`

Reuses `frob.gates._taint_gate`'s `websec_findings(root, frameworks)`
hook-discovery convention (T-5308); T-5372's sibling leaf already widened
the gate's discovery prefix to also match `_comply_*` modules, so this
leaf needs no further `_taint_gate.py` edit. WARN-tier at first turn-on
(T-0688/T-0973 promotion posture, same as every sibling WEBSEC/COMPLY
family).

## Fixtures

`tests/fixtures/webapp/comply1xx/commerce/` -- one positive-control
directory per rule id (`no_cancel_route`, `deep_cancel_route`,
`missing_unsubscribe`, `missing_postal_address`, `raw_card_field`) plus
two negative controls (`compliant_routes` for COMPLY123/124,
`compliant_commerce` covering all five at once). Separate from T-5360's
own `tests/fixtures/webapp/comply1xx/` substrate fixtures and from
sibling leaves' `comply1xx/privacy/**` (T-5372), `comply1xx/gdpr/**`
(T-5373), `comply1xx/sector/**` (T-5370).
