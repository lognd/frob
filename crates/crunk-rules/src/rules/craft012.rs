//! CRAFT012: design intent covers the styling. Colours and lengths written as literals bypass the
//! tokens a design decided; declarations reading a token (a `var()` of a defined custom property,
//! or a Tailwind utility without an arbitrary value) are covered. When a project has at least
//! 10 styling values and under 90 percent of them are tokens, the rule fires once, at the sheet
//! with the most literals, with the percentages. Custom property definitions are not styling and
//! are left out. Advisory.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

use std::collections::BTreeSet;

use crunk_values::LengthKind;
use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{line_offset, site_path};
use crate::slop::judged_sheets;

/// The fewest styling values worth a coverage percentage.
const MIN_VALUES: usize = 10;

/// The token share, in percent, below which the rule fires.
const MIN_COVERAGE_PERCENT: usize = 90;

/// Styling mostly written as literals rather than tokens.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT012",
    slug = "intent-coverage",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft012;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft012 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let defined: BTreeSet<&str> = styles
            .sheets
            .iter()
            .flat_map(|s| s.custom_props.iter().map(|p| p.name.as_str()))
            .collect();
        let (mut tokens, mut literals) = (0_usize, 0_usize);
        let mut worst: Option<(usize, &crunk_ingest::Stylesheet, u32)> = None;
        for sheet in judged_sheets(styles) {
            let mut here = 0_usize;
            let mut first_line = 0_u32;
            for decl in sheet
                .declarations
                .iter()
                .filter(|d| !d.prop.starts_with("--"))
            {
                tokens += decl
                    .var_refs
                    .iter()
                    .filter(|r| defined.contains(r.name.as_str()))
                    .count();
                let found = decl.colors.len()
                    + decl
                        .lengths
                        .iter()
                        .filter(|l| {
                            matches!(l.length.kind, LengthKind::Px | LengthKind::Rem)
                                && l.length.px.is_some_and(|px| px != 0.0)
                        })
                        .count();
                if found > 0 && here == 0 {
                    first_line = decl.line;
                }
                here += found;
            }
            for utility in &sheet.utilities {
                if utility.name.contains('[') {
                    here += 1;
                    if first_line == 0 {
                        first_line = utility.line;
                    }
                } else {
                    tokens += 1;
                }
            }
            literals += here;
            if here > 0 && worst.is_none_or(|(n, _, _)| here > n) {
                worst = Some((here, sheet, first_line));
            }
        }
        let total = tokens + literals;
        if total < MIN_VALUES {
            tracing::debug!(total, "CRAFT012: too few styling values to judge");
            return;
        }
        let percent = tokens * 100 / total;
        let Some((count, sheet, line)) = worst.filter(|_| percent < MIN_COVERAGE_PERCENT) else {
            return;
        };
        tracing::debug!(percent, literals, tokens, "CRAFT012: low intent coverage");
        out.fire_in(
            &site_path(spec, &sheet.path),
            line_offset(&sheet.source, line),
            format!(
                "{percent} percent of styling values come from tokens ({tokens} of {total}; {literals} \
                 are literal colours or lengths, {count} of them here): reach for a token so the \
                 design's decisions cover the styling",
            ),
        );
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
