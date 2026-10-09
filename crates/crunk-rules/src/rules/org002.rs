//! ORG002: a class selector that violates `[org] class_case` (port of `crunk/rules/_org.py`
//! `org002`). A BEM class is judged part by part (block, element, modifier); the `__` and `--`
//! separators are not case content.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::org::{case_name, case_ok};
use crate::sheets::{examined_sheets, line_offset, site_path};

/// A class name that is not written in the configured casing.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG002",
    slug = "class-case",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Org002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let class_case = spec.org.class_case;
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for selector in &sheet.class_selectors {
                if case_ok(&selector.name, class_case) {
                    continue;
                }
                tracing::debug!(%path, line = selector.line, name = %selector.name, "ORG002: class case");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, selector.line),
                    format!(
                        "class '{}' violates {} case",
                        selector.name,
                        case_name(class_case)
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Org002 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
