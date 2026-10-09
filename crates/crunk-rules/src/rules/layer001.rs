//! LAYER001: a `z-index` integer that is not one of the declared `[layers]` values (port of
//! `crunk/rules/_layers.py`). `auto` and non-integer values are exempt; a project that declares no
//! layers has no design law to judge against, so the rule is then inapplicable and reported.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};

/// A `z-index` integer outside the declared layer values.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYER001",
    slug = "z-index-off-layers",
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
pub struct Layer001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layer001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let mut declared: Vec<i64> = spec.layers.values().copied().collect();
        declared.sort_unstable();
        declared.dedup();
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for decl in sheet.declarations.iter().filter(|d| d.prop == "z-index") {
                let raw = decl.value.trim();
                if raw.eq_ignore_ascii_case("auto") {
                    continue;
                }
                let Ok(value) = raw.parse::<i64>() else {
                    tracing::debug!(%path, line = decl.line, raw, "LAYER001: unparseable z-index skipped");
                    continue;
                };
                if declared.contains(&value) {
                    continue;
                }
                tracing::debug!(%path, line = decl.line, value, "LAYER001: undeclared z-index");
                out.fire_in(
                    &path,
                    decl.span.0,
                    format!("z-index {value} is not among declared layers {declared:?}"),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if let Some(why) = missing_inputs(host) {
            return Some(why);
        }
        host.spec()
            .is_some_and(|spec| spec.layers.is_empty())
            .then(|| "no [layers] are declared".to_owned())
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layer001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
