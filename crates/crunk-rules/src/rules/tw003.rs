//! TW003: a utility with an alpha modifier (`bg-brand/50`) whose theme colour entry has no
//! `<alpha-value>` placeholder, so the modifier is a silent no-op (port of
//! `crunk/rules/_tailwind.py` `tw003`, r9/A-035). Judges the theme's own mapping text, not a
//! compiled class. A utility whose key is not in the theme is skipped.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, line_offset, site_path};
use crate::tailwind::{alpha_parts, category_split, missing_facts};

/// The placeholder a theme mapping needs to honour an alpha modifier.
const ALPHA_VALUE_PLACEHOLDER: &str = "<alpha-value>";

/// An alpha-modified utility over a theme colour that cannot take alpha.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW003",
    slug = "alpha-modifier-without-placeholder",
    severity = Warn,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tw003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles), Some(facts)) = (host.spec(), host.styles(), host.tailwind())
        else {
            return;
        };
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for utility in &sheet.utilities {
                let Some((stem, _)) = alpha_parts(&utility.name) else {
                    continue;
                };
                let Some((_, key)) = category_split(stem) else {
                    continue;
                };
                let Some(mapping) = facts.theme.get(key) else {
                    continue;
                };
                if mapping.contains(ALPHA_VALUE_PLACEHOLDER) {
                    continue;
                }
                tracing::debug!(%path, line = utility.line, name = %utility.name, key, "TW003: alpha modifier is a no-op");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, utility.line),
                    format!(
                        "utility '{}' applies an alpha modifier but tw_theme entry '{key}' maps to '{mapping}', which has no {ALPHA_VALUE_PLACEHOLDER} placeholder -- the modifier is a silent no-op",
                        utility.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_facts(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Tw003 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
