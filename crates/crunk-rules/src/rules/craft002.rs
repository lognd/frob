//! CRAFT002: a component declares the states a user can reach. COMP and STATE rules judge the
//! states a component lists against its kind; CRAFT002 asks for the full interaction set on every
//! component: hover, active, disabled, focus (`focus` or `focus-visible`), loading, error and
//! empty. Each component missing any fires once at its `states` table (or the file start) naming
//! what is missing. A component with every state is quiet, and a project with no component files
//! is not judged. Advisory; turn it off under `[lint]` for a design of static components.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_component_inputs};

/// The states every component declares, each with the ids that stand in for it.
const STATES: &[(&str, &[&str])] = &[
    ("hover", &["hover"]),
    ("active", &["active", "pressed"]),
    ("disabled", &["disabled"]),
    ("focus", &["focus", "focus-visible"]),
    ("loading", &["loading"]),
    ("error", &["error", "invalid"]),
    ("empty", &["empty"]),
];

/// A component missing one of the full interaction states.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT002",
    slug = "component-states-complete",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.components() else {
            return;
        };
        for file in &facts.files {
            let missing: Vec<&str> = STATES
                .iter()
                .filter(|(_, ids)| !file.state_ids().any(|id| ids.contains(&id)))
                .map(|(name, _)| *name)
                .collect();
            if missing.is_empty() {
                continue;
            }
            tracing::debug!(path = %file.path, ?missing, "CRAFT002: states missing");
            out.fire_in(
                &file.path,
                file.offset_of("states"),
                format!(
                    "component `{}` declares no {} state: declare every state a user can reach \
                     under `[[states]]`",
                    file.component.name,
                    missing.join(", ")
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_component_inputs(host)
    }
}
