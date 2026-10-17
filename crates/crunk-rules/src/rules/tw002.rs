//! TW002: a `tw_theme` entry that maps to a `var(--x)` the token export does not define.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::tailwind::theme_view;

/// A Tailwind theme entry mapped to a `var(--x)` that is not an exported token.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW002",
    slug = "tailwind-theme-unknown-token",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tw002;

/// The custom property of a value spelled exactly `var(--name)`.
pub fn bare_var(value: &str) -> Option<&str> {
    let name = value.trim().strip_prefix("var(")?.strip_suffix(')')?;
    let body = name.strip_prefix("--")?;
    (!body.is_empty()
        && body
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-'))
    .then_some(name)
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(theme)) = (host.spec(), host.tailwind_theme()) else {
            return;
        };
        let view = theme_view(host, spec);
        let Some(names) = &view.token_names else {
            tracing::warn!("TW002: token set did not build; skipped");
            return;
        };
        let path = site_path(spec, &theme.path);
        let mut keys: Vec<&String> = view.map.keys().collect();
        keys.sort();
        for key in keys {
            let value = &view.map[key];
            let Some(var) = bare_var(value) else { continue };
            if names.contains(var) {
                continue;
            }
            tracing::debug!(%path, key, var, "TW002: theme entry maps to an unexported token");
            out.fire_in(
                &path,
                0,
                format!(
                    "tailwind theme entry '{key}' maps to var({var}) which is not an exported token"
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host).or_else(|| {
            host.tailwind_theme()
                .is_none()
                .then(|| "no [tailwind] theme ingested".to_owned())
        })
    }
}
