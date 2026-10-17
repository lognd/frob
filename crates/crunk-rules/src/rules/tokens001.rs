//! TOKENS001: a generated token file that no longer matches what `crunk tokens` writes.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::sheets::site_path;
use crate::tokens_drift::drift;

/// A generated file (the tokens sheet) whose bytes differ from the exporter's output for the current spec.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKENS001",
    slug = "generated-tokens-stale",
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
pub struct Tokens001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tokens001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(files)) = (host.spec(), host.generated_files()) else {
            return;
        };
        for file in files {
            let Some(why) = drift(file) else { continue };
            let path = site_path(spec, &file.path);
            tracing::debug!(%path, %why, "TOKENS001: generated file is stale");
            out.fire_in(
                &path,
                0,
                format!("generated file {why}; run `crunk tokens` to regenerate it"),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if host.spec().is_none() {
            return Some("no valid crunk.toml".to_owned());
        }
        host.generated_files()
            .is_none()
            .then(|| "no expected token output was supplied".to_owned())
    }
}
