//! TW004: a utility whose colour part is one of Tailwind's default colour names (`bg-black/10`,
//! `text-red-500`) that the project theme does not define, confirmed against the colour Tailwind
//! compiles it to (port of `crunk/rules/_tailwind.py` `tw004`, r13/A-063). Only a class whose
//! compiled colour is that default's own rgb is a bypass of the project theme; a compiled
//! `var()` has no literal colour to refute the name and the name test alone decides.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::naming::color_token;
use crunk_tailwind::defaults::{V3_COLOR_HEXES, V3_COLOR_NAMES};
use crunk_values::Color;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::color::Palette;
use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, line_offset, site_path};
use crate::tailwind::{ClassState, category_split, missing_facts, strip_alpha, unresolved_message};

/// A utility that resolves to Tailwind's default colour instead of the project theme.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW004",
    slug = "tailwind-default-color",
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
pub struct Tw004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles), Some(facts)) = (host.spec(), host.styles(), host.tailwind())
        else {
            return;
        };
        let palette = Palette::new(spec.palette.iter().map(|(n, c)| (n.as_str(), *c)).collect());
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for utility in &sheet.utilities {
                let Some((_, colorpart)) = category_split(strip_alpha(&utility.name)) else {
                    continue;
                };
                if !V3_COLOR_NAMES.contains(&colorpart) || facts.theme.contains_key(colorpart) {
                    continue;
                }
                let offset = line_offset(&sheet.source, utility.line);
                let decls = match facts.class(&utility.name) {
                    ClassState::Unresolved(why) => {
                        out.unresolved_in(&path, offset, unresolved_message(&utility.name, why));
                        continue;
                    }
                    ClassState::Invalid => continue,
                    ClassState::Valid(decls) => decls,
                };
                let Some(hex) = V3_COLOR_HEXES
                    .iter()
                    .find_map(|(name, hex)| (*name == colorpart).then_some(*hex))
                else {
                    continue;
                };
                let Ok(expected) = Color::parse(hex) else {
                    continue;
                };
                let resolved: Vec<Color> = decls
                    .iter()
                    .filter_map(|d| Color::parse(&d.value).ok())
                    .collect();
                let expected_rgb = expected.rgb_hex();
                if !resolved.is_empty() && !resolved.iter().any(|c| c.rgb_hex() == expected_rgb) {
                    continue;
                }
                let Some((nearest, distance)) = palette.nearest(expected) else {
                    continue;
                };
                let token = color_token(&spec.tokens, nearest);
                tracing::debug!(%path, line = utility.line, name = %utility.name, colorpart, "TW004: default colour");
                out.fire_in(
                    &path,
                    offset,
                    format!(
                        "utility '{}' resolves to Tailwind's default color '{colorpart}' ({hex}), not the project theme; nearest is {token} (distance {distance:.2})",
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

impl<P: ?Sized + CrunkHost> Measured<P> for Tw004 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
