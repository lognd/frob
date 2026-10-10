//! TW005: a non-arbitrary utility whose key is one of Tailwind's default scale keys (`p-4`,
//! `rounded-lg`, `z-10`) that the project theme does not override, bypassing the declared scale
//! (port of `crunk/rules/_tailwind.py` `tw005`, r13/A-063, r14/A-066). Spared when the key's
//! compiled value is already on the declared scale (`inset-0` is `0px`). Arbitrary utilities are
//! TW001's job; `text-` keys that are not numeric are not font sizes at all.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::DesignSpec;
use crunk_tailwind::defaults::{
    V3_BORDER_RADIUS_KEYS, V3_FONT_SIZE_KEYS, V3_SPACING_KEYS, V3_Z_INDEX_KEYS,
};
use crunk_tailwind::runtime::ClassDeclaration;
use crunk_values::Length;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, line_offset, site_path};
use crate::tailwind::{
    ClassState, ZINDEX_PREFIXES, arbitrary_prefix, missing_facts, scale_and_token,
    split_family_stem, strip_alpha, unresolved_message,
};

/// A default-scale Tailwind utility that bypasses the declared scale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW005",
    slug = "tailwind-default-scale",
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
pub struct Tw005;

/// The governed family of `prefix`: its scale's name and Tailwind's default key table.
fn family(prefix: &str) -> Option<(&'static str, &'static [&'static str])> {
    Some(match prefix {
        "z" | "-z" => ("zIndex", V3_Z_INDEX_KEYS),
        "p" | "m" | "gap" | "inset" | "w" | "h" | "min-w" | "min-h" | "max-h" => {
            ("spacing", V3_SPACING_KEYS)
        }
        "rounded" => ("borderRadius", V3_BORDER_RADIUS_KEYS),
        "text" => ("fontSize", V3_FONT_SIZE_KEYS),
        _ => return None,
    })
}

fn numeric_key(key: &str) -> bool {
    let mut parts = key.splitn(2, '.');
    let digits = |s: &str| !s.is_empty() && s.chars().all(|c| c.is_ascii_digit());
    digits(parts.next().unwrap_or_default()) && parts.next().is_none_or(digits)
}

#[allow(
    clippy::float_cmp,
    reason = "a value is on the scale only when it equals a step exactly, as in the Python rule"
)]
fn on_declared_scale(
    spec: &DesignSpec,
    prefix: &str,
    scale_name: &str,
    decls: &[ClassDeclaration],
) -> bool {
    match scale_name {
        "zIndex" => decls
            .iter()
            .find(|d| d.property == "z-index")
            .and_then(|d| d.value.parse::<i64>().ok())
            .is_some_and(|value| spec.layers.values().any(|z| *z == value)),
        "spacing" => {
            let (scale, _) = scale_and_token(spec, prefix, 0.0);
            decls
                .iter()
                .find_map(|d| {
                    Length::parse(&d.value, spec.project.root_font_size)
                        .ok()
                        .and_then(|l| l.px)
                })
                .is_some_and(|px| scale.contains(&px))
        }
        _ => false,
    }
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles), Some(facts)) = (host.spec(), host.styles(), host.tailwind())
        else {
            return;
        };
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for utility in &sheet.utilities {
                let stem = strip_alpha(&utility.name);
                if arbitrary_prefix(stem).is_some() {
                    continue;
                }
                let Some((prefix, key)) = split_family_stem(stem) else {
                    continue;
                };
                let Some((scale_name, defaults)) = family(&prefix) else {
                    continue;
                };
                if (ZINDEX_PREFIXES.contains(&prefix.as_str()) && spec.layers.is_empty())
                    || (prefix == "text" && !numeric_key(key))
                    || !defaults.contains(&key)
                    || facts.theme.contains_key(key)
                {
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
                if on_declared_scale(spec, &prefix, scale_name, decls) {
                    continue;
                }
                tracing::debug!(%path, line = utility.line, name = %utility.name, key, "TW005: default scale key");
                out.fire_in(
                    &path,
                    offset,
                    format!(
                        "utility '{}' resolves to Tailwind's default {scale_name} scale (key '{key}'), bypassing the declared {scale_name} scale",
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

impl<P: ?Sized + CrunkHost> Measured<P> for Tw005 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
