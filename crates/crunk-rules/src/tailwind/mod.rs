//! What TW001-005 share: the split of an arbitrary utility (`p-[13px]`), the scale a length
//! family is judged against, the `tw_theme` view (ingested theme overlaid with the token export),
//! the family/stem splitter for named utilities and the utility sites of a project.
//!
//! No Tailwind runtime runs here. The semantics follow the Python crunk: arbitrary values are
//! judged against the palette, the layers and the scales; named utilities are judged by whether
//! they fall through to Tailwind's default theme instead of the project's.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::collections::{BTreeSet, HashMap};

use crunk_ingest::ProjectStyles;
use crunk_spec::model::TokensConfig;
use crunk_spec::{DesignSpec, naming};
use crunk_tailwind::defaults::{
    V3_BORDER_RADIUS_KEYS, V3_FONT_SIZE_KEYS, V3_SPACING_KEYS, V3_Z_INDEX_KEYS,
};
use crunk_tokens::TokenSet;

use crate::host::CrunkHost;
use crate::org::line_offset;
use crate::sheets::site_path;

/// Utility prefixes whose arbitrary length is judged against a scale (`max-w` is exempt).
pub const LENGTH_PREFIXES: &[&str] = &[
    "p", "m", "gap", "inset", "rounded", "text", "w", "h", "min-w", "min-h", "max-h",
];

/// Compound family prefixes tried before the first-hyphen split.
const COMPOUND_PREFIXES: &[&str] = &["min-w", "min-h", "max-h", "max-w"];

/// Split an arbitrary utility `prefix-[inner]` into `(prefix, inner)`.
///
/// `None` unless the prefix is `-?[a-z][a-z0-9]*(-[a-z0-9]+)*` and the inner part is non-empty.
pub fn split_arbitrary(name: &str) -> Option<(&str, &str)> {
    let idx = name.find("-[")?;
    let inner = name[idx + 2..].strip_suffix(']')?;
    let prefix = &name[..idx];
    if inner.is_empty() || !valid_prefix(prefix) {
        return None;
    }
    Some((prefix, inner))
}

fn valid_prefix(prefix: &str) -> bool {
    let body = prefix.strip_prefix('-').unwrap_or(prefix);
    let mut segments = body.split('-');
    let Some(first) = segments.next() else {
        return false;
    };
    let mut chars = first.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        && segments.all(|s| {
            !s.is_empty()
                && s.chars()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        })
}

/// Split a trailing `/digits` alpha modifier: `(stem, Some(digits))`, or `(name, None)`.
pub fn split_alpha(name: &str) -> (&str, Option<&str>) {
    match name.rsplit_once('/') {
        Some((stem, alpha)) if !alpha.is_empty() && alpha.bytes().all(|b| b.is_ascii_digit()) => {
            (stem, Some(alpha))
        }
        _ => (name, None),
    }
}

/// Split `family-key` of a stem as `^([a-z][a-z0-9]*)-(.+)$` does (`word`, `rest`).
pub fn split_word_key(stem: &str) -> Option<(&str, &str)> {
    let (word, rest) = stem.split_once('-')?;
    let mut chars = word.chars();
    (chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        && !rest.is_empty())
    .then_some((word, rest))
}

/// Split a named utility stem into `(family, key)`: a leading `-` belongs to the family, the
/// compound prefixes win, otherwise the first hyphen splits. `None` without a hyphen.
pub fn split_family_stem(stem: &str) -> Option<(&str, &str)> {
    let lead = usize::from(stem.starts_with('-'));
    let body = &stem[lead..];
    for compound in COMPOUND_PREFIXES {
        if let Some(key) = body
            .strip_prefix(compound)
            .and_then(|r| r.strip_prefix('-'))
        {
            return Some((&stem[..lead + compound.len()], key));
        }
    }
    let (family, key) = body.split_once('-')?;
    Some((&stem[..lead + family.len()], key))
}

/// A Tailwind default scale a named utility can fall through to.
#[derive(Debug, Clone, Copy)]
pub struct DefaultScale {
    /// The Tailwind theme key (`spacing`, `zIndex`, ...).
    pub name: &'static str,
    /// The default keys of that scale.
    pub keys: &'static [&'static str],
}

/// The default scale a governed family reads, `None` for an ungoverned one (`max-w`, `bg`).
pub fn default_scale(family: &str) -> Option<DefaultScale> {
    let (name, keys) = match family {
        "z" | "-z" => ("zIndex", V3_Z_INDEX_KEYS),
        "p" | "m" | "gap" | "inset" | "w" | "h" | "min-w" | "min-h" | "max-h" => {
            ("spacing", V3_SPACING_KEYS)
        }
        "rounded" => ("borderRadius", V3_BORDER_RADIUS_KEYS),
        "text" => ("fontSize", V3_FONT_SIZE_KEYS),
        _ => return None,
    };
    Some(DefaultScale { name, keys })
}

/// True for `^\d+(\.\d+)?$`.
pub fn numeric_key(key: &str) -> bool {
    let digits = |s: &str| !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit());
    match key.split_once('.') {
        Some((a, b)) => digits(a) && digits(b),
        None => digits(key),
    }
}

/// The scale an arbitrary length prefix is judged against and how to spell a step as a token.
pub struct ScaleChoice<'a> {
    /// The declared px steps.
    pub steps: &'a [f64],
    /// Token-name function for a step.
    pub token: fn(&TokensConfig, f64) -> String,
}

/// Pick the scale for `prefix`: rounded -> radii, text -> font sizes, w/h family -> sizes (or
/// spacing when none are declared), everything else -> spacing.
pub fn scale_and_token<'a>(spec: &'a DesignSpec, prefix: &str) -> ScaleChoice<'a> {
    let scales = &spec.scales;
    match prefix {
        "rounded" => ScaleChoice {
            steps: &scales.radii,
            token: naming::radius_token,
        },
        "text" => ScaleChoice {
            steps: &scales.font_sizes,
            token: naming::font_size_token,
        },
        "w" | "h" | "min-w" | "min-h" | "max-h" if !scales.sizes.is_empty() => ScaleChoice {
            steps: &scales.sizes,
            token: naming::size_token,
        },
        _ => ScaleChoice {
            steps: &scales.spacing,
            token: naming::space_token,
        },
    }
}

/// Where an off-scale value sits on its scale.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct OffScale {
    /// The nearest step at or below the value.
    pub lower: f64,
    /// The nearest step at or above the value.
    pub upper: f64,
    /// The closest step.
    pub nearest: f64,
}

/// Judge `px` against `steps`: `None` when it is a step (or the scale is empty), else its neighbours.
pub fn off_scale(px: f64, steps: &[f64]) -> Option<OffScale> {
    let value = px.abs();
    if steps.is_empty() || steps.iter().any(|s| (s - value).abs() < 1e-6) {
        return None;
    }
    let mut ordered = steps.to_vec();
    ordered.sort_by(f64::total_cmp);
    let (mut lower, mut upper) = (ordered[0], ordered[ordered.len() - 1]);
    for &step in &ordered {
        if step <= value {
            lower = step;
        }
        if step >= value {
            upper = step;
            break;
        }
    }
    let nearest = ordered
        .iter()
        .copied()
        .min_by(|a, b| (value - a).abs().total_cmp(&(value - b).abs()))?;
    Some(OffScale {
        lower,
        upper,
        nearest,
    })
}

/// The `tw_theme` the rules judge utilities against, plus the exported token names.
#[derive(Debug, Default)]
pub struct ThemeView {
    /// Bare utility key to its mapped value.
    pub map: HashMap<String, String>,
    /// Names of every exported custom property; `None` when the token set did not build.
    pub token_names: Option<BTreeSet<String>>,
}

/// Build the theme view: the ingested theme's bare keys with the token export's mapping overlaid
/// (the spec wins), the overlay applying only when `[tailwind]` is configured.
pub fn theme_view<P: ?Sized + CrunkHost>(host: &P, spec: &DesignSpec) -> ThemeView {
    let mut view = ThemeView::default();
    if let Some(theme) = host.tailwind_theme() {
        for entry in theme.entries.iter().filter(|e| !e.namespace.is_empty()) {
            view.map.insert(entry.key.clone(), entry.value.clone());
        }
    }
    match TokenSet::from_spec(spec) {
        Ok(tokens) => {
            if tailwind_configured(spec) {
                let mapping = tokens
                    .theme_mapping(spec.tailwind.namespace_keys, spec.tailwind.alpha_channels);
                view.map.extend(mapping);
            }
            view.token_names = Some(tokens.names().into_iter().map(str::to_owned).collect());
        }
        Err(err) => {
            tracing::warn!(%err, "tailwind: token set did not build; theme view is partial");
        }
    }
    view
}

/// True when `[tailwind]` names a config or a CSS entry.
pub fn tailwind_configured(spec: &DesignSpec) -> bool {
    spec.tailwind_config_path().is_some() || !spec.tailwind.css_entry.is_empty()
}

/// One utility token of the project.
#[derive(Debug)]
pub struct Site<'a> {
    /// Project-relative path of the source holding the token.
    pub path: String,
    /// Byte offset of the start of the token's line.
    pub offset: usize,
    /// The 1-based line.
    pub line: u32,
    /// The variant prefixes as written, outermost first.
    pub variants: &'a [String],
    /// The utility name without variants.
    pub name: &'a str,
}

/// Every statically known utility token of every ingested source, the tokens sheet included.
pub fn sites<'a>(spec: &DesignSpec, styles: &'a ProjectStyles) -> Vec<Site<'a>> {
    let mut out = Vec::new();
    for sheet in &styles.sheets {
        let path = site_path(spec, &sheet.path);
        for utility in &sheet.utilities {
            out.push(Site {
                path: path.clone(),
                offset: line_offset(&sheet.source, utility.line),
                line: utility.line,
                variants: &utility.variants,
                name: &utility.name,
            });
        }
    }
    tracing::debug!(count = out.len(), "tailwind: utility sites collected");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::split_arbitrary
    #[test]
    fn arbitrary_utilities_split_into_prefix_and_inner() {
        assert_eq!(split_arbitrary("p-[13px]"), Some(("p", "13px")));
        assert_eq!(split_arbitrary("-z-[5]"), Some(("-z", "5")));
        assert_eq!(split_arbitrary("min-h-[111px]"), Some(("min-h", "111px")));
        for bad in [
            "p-4",
            "p-[]",
            "P-[1px]",
            "p-[1px",
            "--p-[1px]",
            "p--x-[1px]",
        ] {
            assert_eq!(split_arbitrary(bad), None, "{bad}");
        }
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::split_alpha
    #[test]
    fn alpha_modifiers_split_off() {
        assert_eq!(split_alpha("bg-brand/50"), ("bg-brand", Some("50")));
        assert_eq!(split_alpha("w-1/2x"), ("w-1/2x", None));
        assert_eq!(split_alpha("bg-brand"), ("bg-brand", None));
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::split_family_stem
    #[test]
    fn family_stems_prefer_compound_prefixes() {
        assert_eq!(split_family_stem("min-h-9"), Some(("min-h", "9")));
        assert_eq!(split_family_stem("-z-10"), Some(("-z", "10")));
        assert_eq!(split_family_stem("p-5"), Some(("p", "5")));
        assert_eq!(split_family_stem("flex"), None);
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::split_word_key
    #[test]
    fn word_key_split_needs_a_lowercase_word() {
        assert_eq!(split_word_key("bg-red-500"), Some(("bg", "red-500")));
        assert_eq!(split_word_key("-bg-red"), None);
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::off_scale
    #[test]
    fn off_scale_reports_neighbours_and_nearest() {
        let scale = [0.0, 4.0, 8.0, 12.0, 16.0];
        assert_eq!(off_scale(8.0, &scale), None);
        assert_eq!(
            off_scale(13.0, &scale),
            Some(OffScale {
                lower: 12.0,
                upper: 16.0,
                nearest: 12.0
            })
        );
        assert_eq!(off_scale(13.0, &[]), None);
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::default_scale
    #[test]
    fn only_governed_families_have_a_default_scale() {
        assert_eq!(default_scale("p").map(|s| s.name), Some("spacing"));
        assert_eq!(default_scale("-z").map(|s| s.name), Some("zIndex"));
        assert!(default_scale("max-w").is_none());
        assert!(numeric_key("1.5") && !numeric_key("lg"));
    }
}
