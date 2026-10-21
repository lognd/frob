//! Cell enumeration: every `(screen, state, platform)` the gallery must render and approve.
//!
//! A screen applies to the platforms its `applies_to` names (absent means every platform); a state
//! may narrow that with its own `applies_to`. `tag:<name>` entries expand to the platforms carrying
//! the tag. Order is screens as declared, then their states, then platforms in declaration order,
//! so the list is stable and diffable.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

use std::collections::BTreeSet;

use crunk_spec::DesignSpec;
use serde::Serialize;

/// One gallery cell: a state of a screen on a platform.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize)]
pub struct Cell {
    /// Screen id.
    pub screen: String,
    /// State id.
    pub state: String,
    /// Platform id.
    pub platform: String,
}

/// Which cells `cells` keeps; an unset field keeps everything.
#[derive(Debug, Clone, Default)]
pub struct CellFilter {
    /// Keep only this screen.
    pub screen: Option<String>,
    /// Keep only this state id.
    pub state: Option<String>,
    /// Keep only this platform.
    pub platform: Option<String>,
}

/// The platform ids `names` selects, in declaration order; `None` selects every platform.
fn resolve(spec: &DesignSpec, names: Option<&Vec<String>>) -> Vec<String> {
    let Some(names) = names else {
        return spec.platforms.keys().cloned().collect();
    };
    let mut wanted: BTreeSet<&str> = BTreeSet::new();
    for name in names {
        match name.strip_prefix("tag:") {
            Some(tag) => wanted.extend(
                spec.platforms
                    .values()
                    .filter(|p| p.tags.iter().any(|t| t == tag))
                    .map(|p| p.id.as_str()),
            ),
            None => {
                wanted.insert(name.as_str());
            }
        }
    }
    spec.platforms
        .keys()
        .filter(|id| wanted.contains(id.as_str()))
        .cloned()
        .collect()
}

/// Every cell of `spec`: screens, then states, then platforms, each in declaration order.
pub fn enumerate(spec: &DesignSpec) -> Vec<Cell> {
    let mut out = Vec::new();
    for screen in spec.screens.values() {
        for state in &screen.states {
            let names = state.applies_to.as_ref().or(screen.applies_to.as_ref());
            for platform in resolve(spec, names) {
                out.push(Cell {
                    screen: screen.id.clone(),
                    state: state.id.clone(),
                    platform,
                });
            }
        }
    }
    tracing::debug!(cells = out.len(), "gallery cells enumerated");
    out
}

/// The cells of `spec` that pass `filter`, in [`enumerate`] order.
pub fn cells(spec: &DesignSpec, filter: &CellFilter) -> Vec<Cell> {
    let keep = |want: &Option<String>, have: &str| want.as_deref().is_none_or(|w| w == have);
    enumerate(spec)
        .into_iter()
        .filter(|c| {
            keep(&filter.screen, &c.screen)
                && keep(&filter.state, &c.state)
                && keep(&filter.platform, &c.platform)
        })
        .collect()
}
