# grimble vet: what is implemented

Status: current
Owner: grimble
Decisions: none
Audience: contributor

Related grimble specs: [grmb-spec](grmb-spec.md), [GRL](../shared/grl-spec.md), [capabilities v3](grimble-capabilities-v3.md), [rule families](rule-families.md).

Design context: shared/cli-contract.md (`grimble vet`), shared/charter.md 4.2.3.

Inputs: `Cargo.lock`, the allowlist `.grimble/vet.toml` (`allow = ["serde",
"tokio@1.40.0"]`) and an offline RustSec snapshot directory (the
advisory-db layout; `--advisory-db`, default `.grimble/advisory-db`; absent
means advisories are not checked, with a warning in the log). With
`--base REF` only packages new relative to the lockfile at REF are vetted.

| Rule | Severity | Meaning |
|---|---|---|
| VET001 | error | new direct dependency not on the allowlist |
| VET002 | error | locked version has an advisory; the finding carries the id and the fixed version requirements |
| VET003 | info | new transitive dependency not on the allowlist |
| VET004 | warning | two versions of one crate are locked |

Any error exits 1. VET is a registered rule family of `grimble-check`
(`crates/grimble-vet/src/rules`), so `frob check` and `frob check --ticket`
report it natively as the `repo:vet` group, pointing at `Cargo.lock`. The
pipeline knows only error and unresolved severities, so the three
informational severities above collapse to error there; `grimble vet` keeps
them. In the pipeline VET002 and VET004 run over the head lockfile alone
(VET002 needs a snapshot in `.grimble/advisory-db`), while VET001 and VET003
need a base ref and are reported as not applicable until the product
passes one to its collect step. An unparsable lockfile or allowlist is an
unresolved finding, never a silent pass.

Not yet implemented: `--hook`, licence, yanked, maintenance and typosquat
checks (follow-up tickets).
