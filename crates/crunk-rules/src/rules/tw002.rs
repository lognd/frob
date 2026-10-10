//! TW002: a Tailwind theme entry whose value is `var(--x)` with `--x` defined nowhere (port of
//! `crunk/rules/_tailwind.py` `tw002`; COLOR002's analog for the Tailwind config). The theme has no
//! per-entry location, so every finding is attributed to `[tailwind] config` at its start.
//! `--x` is defined by the spec's token export or any ingested sheet; when a definition source was
//! not indexed an undefined name is Unresolved, never a finding.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::color::defs::{defined_names, unindexed_sources};
use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, site_path};
use crate::tailwind::missing_facts;

/// A Tailwind theme entry that maps to a custom property nothing defines.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW002",
    slug = "theme-entry-undefined-token",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tw002;

/// The custom property name of a whole-value `var(--name)`, if `value` is exactly one.
fn var_name(value: &str) -> Option<&str> {
    let inner = value.strip_prefix("var(")?.strip_suffix(')')?;
    let ok = inner.starts_with("--")
        && inner.len() > 2
        && inner
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_');
    ok.then_some(inner)
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles), Some(facts)) = (host.spec(), host.styles(), host.tailwind())
        else {
            return;
        };
        let Some(config) = spec.tailwind_config_path() else {
            return;
        };
        let path = site_path(spec, &config);
        let defined = match defined_names(spec, styles) {
            Ok(defined) => defined,
            Err(err) => {
                tracing::warn!(%err, "TW002: the token export set cannot be built");
                out.unresolved(format!("the token export set cannot be built: {err}"));
                return;
            }
        };
        let unindexed = unindexed_sources(spec, styles);
        for (key, value) in &facts.theme {
            let Some(name) = var_name(value) else {
                continue;
            };
            if defined.contains(name) {
                continue;
            }
            if unindexed.is_empty() {
                tracing::debug!(%path, key, name, "TW002: theme entry maps to an undefined token");
                out.fire_in(
                    &path,
                    0,
                    format!(
                        "tailwind theme entry '{key}' maps to var({name}) which is not an exported token"
                    ),
                );
            } else {
                out.unresolved_in(
                    &path,
                    0,
                    format!(
                        "tailwind theme entry '{key}' maps to var({name}), which nothing indexed defines, but the definition set is incomplete ({})",
                        unindexed.join("; ")
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if let Some(why) = missing_facts(host) {
            return Some(why);
        }
        host.spec()
            .is_some_and(|spec| spec.tailwind.config.is_empty())
            .then(|| "no [tailwind] config is declared".to_owned())
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Tw002 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
