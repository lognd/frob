//! TOKENS001: a generated token file that no longer matches what `crunk tokens` writes.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_tokens::export::{Drift, compare};
use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::sheets::site_path;

/// A generated token file (css, json or tailwind mapping) that is missing or differs from the exporter's output.
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
            let on_disk = host.read_generated(&file.path);
            let status = match compare(file, on_disk.as_deref()) {
                Drift::Clean => continue,
                Drift::Missing => "missing",
                Drift::Drifted => "drifted",
            };
            let path = site_path(spec, &file.path);
            tracing::debug!(%path, status, target = file.target.name(), "TOKENS001: generated file is stale");
            out.fire_in(
                &path,
                0,
                format!("tokens file {status}; run `crunk tokens` to regenerate"),
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
