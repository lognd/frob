//! LAYER001: a `z-index` integer that is not one of the declared `[layers]` (port of `crunk/rules/_layers.py` `layer001`).
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::layers::{declared_values, z_index_literal};
use crate::sheets::site_path;

/// A `z-index` literal that no `[layers]` entry declares.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYER001",
    slug = "z-index-not-a-layer",
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
pub struct Layer001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layer001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let layers = declared_values(spec);
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for decl in sheet.declarations.iter().filter(|d| d.prop == "z-index") {
                let Some(z) = z_index_literal(&decl.value) else {
                    continue;
                };
                if !layers.contains(&z) {
                    tracing::debug!(%path, z, "LAYER001: z-index is not a declared layer");
                    out.fire_in(
                        &path,
                        decl.span.0,
                        format!("z-index {z} is not a declared layer (declared: {layers:?})"),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host).or_else(|| {
            host.spec()
                .is_some_and(|s| s.layers.is_empty())
                .then(|| "no [layers] declared".to_owned())
        })
    }
}
