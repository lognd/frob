//! CRAFT008: semantic colour roles complete (research section 4.7). A palette with only a `body`
//! role judges text contrast and nothing about state: CONTRAST001 measures the pairs that exist, so
//! deleting the danger, warning or success pair passes it vacuously. Each of the three state roles
//! missing from `[palette.roles]` fires once at `crunk.toml`. A role is matched by name, ignoring
//! ASCII case, and a conventional alias counts for its role (`error` and `destructive` for danger,
//! `caution` for warning, `positive` for success). Advisory; turn it off under `[lint]` for a design
//! with no state colours.

// frob:ticket 01M5HM3W18AJZET52BZBEJFYD4

use crunk_spec::DesignSpec;
use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};

/// The state roles a palette must declare, each with the names that stand in for it.
const SEMANTIC_ROLES: &[(&str, &[&str])] = &[
    ("danger", &["danger", "error", "destructive"]),
    ("warning", &["warning", "caution"]),
    ("success", &["success", "positive"]),
];

/// Whether `[palette.roles]` declares `names` (any of them, ASCII case ignored).
fn declared(spec: &DesignSpec, names: &[&str]) -> bool {
    spec.roles
        .keys()
        .any(|key| names.iter().any(|name| key.eq_ignore_ascii_case(name)))
}

/// A danger, warning or success role that `[palette.roles]` does not declare.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT008",
    slug = "semantic-roles-complete",
    severity = Advisory,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft008;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft008 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else {
            return;
        };
        for (role, names) in SEMANTIC_ROLES {
            if declared(spec, names) {
                continue;
            }
            tracing::debug!(role, "CRAFT008: semantic role missing");
            out.fire_in(
                "crunk.toml",
                0,
                format!(
                    "no `{role}` role: `[palette.roles]` declares none, so CONTRAST001 never \
                     measures a {role} foreground against its background; declare `{role}` \
                     as a [foreground, background] pair"
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
