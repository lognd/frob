//! BP002: a utility with a responsive variant in a `base_required` family and no unprefixed base
//! of that family in the same `className` string (port of `crunk/rules/_breakpoints.py` `bp002`).
//! The bare display entries (`flex`, `grid`, `block`, `hidden`) form one family, so `hidden md:flex`
//! passes. Off when no breakpoints are declared.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::collections::{BTreeMap, BTreeSet};

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::breakpoints::{has_responsive_variant, matched_family};
use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, line_offset, site_path};

/// A responsive utility whose mobile behaviour is undefined for want of an unprefixed base.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP002",
    slug = "responsive-without-base",
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
pub struct Bp002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let points = &spec.breakpoints.points;
        let required = &spec.breakpoints.base_required;
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            let mut by_line: BTreeMap<u32, Vec<&crunk_ingest::model::LocatedUtility>> =
                BTreeMap::new();
            for utility in &sheet.utilities {
                by_line.entry(utility.line).or_default().push(utility);
            }
            for (line, group) in by_line {
                let bases: BTreeSet<&str> = group
                    .iter()
                    .filter(|u| u.variants.is_empty())
                    .filter_map(|u| matched_family(&u.name, required))
                    .map(|(_, key)| key)
                    .collect();
                for utility in group {
                    if !has_responsive_variant(&utility.variants, points) {
                        continue;
                    }
                    let Some((family, key)) = matched_family(&utility.name, required) else {
                        continue;
                    };
                    if bases.contains(key) {
                        continue;
                    }
                    tracing::debug!(%path, line, utility = %utility.name, family, "BP002: no base");
                    out.fire_in(
                        &path,
                        line_offset(&sheet.source, line),
                        format!(
                            "utility '{}' has a responsive variant in family '{family}' with no unprefixed base in the same className -- mobile behavior undefined",
                            utility.name
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        crate::breakpoints::off_reason(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Bp002 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
