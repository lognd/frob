//! ORG003: a component class that does not carry the component name as a prefix (port of `crunk/rules/_org.py` `org003`).
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Out, RepoRule, rule};

use crunk_ingest::Bucket;

use crate::host::{CrunkHost, missing_inputs};
use crate::org::{has_component_prefix, is_ignored, line_offset};
use crate::sheets::site_path;

/// A class in a `components` sheet that lacks the sheet's component name as a prefix.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG003",
    slug = "component-prefix",
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
pub struct Org003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if !spec.org.component_prefix {
            return;
        }
        for sheet in styles
            .sheets
            .iter()
            .filter(|s| s.bucket == Some(Bucket::Components) && !is_ignored(spec, s))
        {
            let Some(component) = sheet.component.as_deref() else {
                continue;
            };
            let path = site_path(spec, &sheet.path);
            for class in &sheet.class_selectors {
                if !has_component_prefix(&class.name, component) {
                    tracing::debug!(%path, class = %class.name, component, "ORG003: class lacks the component prefix");
                    out.fire_in(
                        &path,
                        line_offset(&sheet.source, class.line),
                        format!(
                            "class `{}` does not carry the component prefix `{component}`",
                            class.name
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
