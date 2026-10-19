# grimble vet: what is implemented

Design context: cli.md (`grimble vet`), boundaries.md 2.3.

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

Any error exits 1. `grimble check --base REF` appends the same findings as
envelope warnings, which is how `frob check --ticket` sees them until VET
is a registered rule family.

Not yet implemented: `--hook`, licence, yanked, maintenance and typosquat
checks (follow-up tickets).
