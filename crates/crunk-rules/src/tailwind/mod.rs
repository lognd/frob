//! What TW001-TW005 share (port of `crunk/rules/_tailwind.py`): the Tailwind facts a rule reads
//! from its host, the utility-name grammar (arbitrary `family-[value]` form, alpha modifier, family
//! stem) and the scale a length family is judged by.
//!
//! The facts are a side input outside the files, like GEN001's: the theme the project's Tailwind
//! resolves and the CSS it compiles each utility to. A rule never guesses from a class name's text
//! what Tailwind would emit; a utility Tailwind could not answer for is reported Unresolved.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::collections::HashMap;

use crunk_spec::DesignSpec;
use crunk_spec::naming::{font_size_token, radius_token, size_token, space_token};
use crunk_tailwind::runtime::{ClassDeclaration, ClassResult, ClassStatus};
use crunk_tokens::TokenSet;
use indexmap::IndexMap;

/// Utility prefixes with a length scale (box sizes included; `max-w` stays out, exempt by design
/// like SIZE001's max-width).
pub const LENGTH_PREFIXES: &[&str] = &[
    "p", "m", "gap", "inset", "rounded", "text", "w", "h", "min-w", "min-h", "max-h",
];

/// The z-index prefixes; `-z` is the negative utility, never a variant.
pub const ZINDEX_PREFIXES: &[&str] = &["z", "-z"];

/// Compound family prefixes that contain a hyphen themselves, longest-match first.
const COMPOUND_PREFIXES: &[&str] = &["min-w", "min-h", "max-h", "max-w"];

/// What Tailwind said about one utility.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClassState<'a> {
    /// Tailwind was not run for it; the reason.
    Unresolved(&'a str),
    /// Tailwind ran and emitted nothing: not a Tailwind class, so there is no CSS to judge.
    Invalid,
    /// The declarations Tailwind compiled it to.
    Valid(&'a [ClassDeclaration]),
}

/// The Tailwind side input of a check run: the effective theme and the compiled utilities.
#[derive(Debug, Clone, Default)]
pub struct TailwindFacts {
    /// The effective `{key: value}` theme: the project's Tailwind theme overlaid with the mapping
    /// the spec itself generates, so the spec's own tokens count as defined.
    pub theme: IndexMap<String, String>,
    classes: HashMap<String, ClassResult>,
    unresolved: Option<String>,
}

impl TailwindFacts {
    /// The facts from the ingested project `theme`, the spec's generated mapping, the compiled
    /// `results` and, when Tailwind could not answer at all, the `unresolved` reason.
    pub fn new(
        spec: &DesignSpec,
        mut theme: IndexMap<String, String>,
        results: Vec<ClassResult>,
        unresolved: Option<String>,
    ) -> Self {
        match TokenSet::from_spec(spec) {
            Ok(tokens) => theme.extend(
                tokens.theme_mapping(spec.tailwind.namespace_keys, spec.tailwind.alpha_channels),
            ),
            Err(err) => {
                tracing::warn!(%err, "tailwind facts: the spec's own theme mapping is unavailable");
            }
        }
        tracing::debug!(
            theme = theme.len(),
            classes = results.len(),
            unresolved = unresolved.is_some(),
            "tailwind facts built"
        );
        Self {
            theme,
            classes: results
                .into_iter()
                .map(|r| (r.candidate.clone(), r))
                .collect(),
            unresolved,
        }
    }

    /// What Tailwind said about the utility `name`.
    pub fn class(&self, name: &str) -> ClassState<'_> {
        match self.classes.get(name) {
            Some(result) => match result.status {
                ClassStatus::Valid => ClassState::Valid(&result.declarations),
                ClassStatus::Invalid => ClassState::Invalid,
                ClassStatus::Unresolved => ClassState::Unresolved(self.reason()),
            },
            None => ClassState::Unresolved(self.reason()),
        }
    }

    fn reason(&self) -> &str {
        self.unresolved
            .as_deref()
            .unwrap_or("Tailwind was not asked about this utility")
    }
}

/// The message of an Unresolved utility finding.
pub fn unresolved_message(name: &str, why: &str) -> String {
    format!(
        "utility '{name}' is unresolved-by-tailwind ({why}); skipped rather than guessed from its name"
    )
}

/// The family prefix of an arbitrary-value utility (`p` of `p-[13px]`, `-z` of `-z-[5]`), if `name`
/// is one: an optional `-`, dash-joined lowercase words, then `-[value]`.
pub fn arbitrary_prefix(name: &str) -> Option<&str> {
    let inner_end = name.strip_suffix(']')?;
    let at = inner_end.find("-[")?;
    let (prefix, value) = (&name[..at], &inner_end[at + 2..]);
    let body = prefix.strip_prefix('-').unwrap_or(prefix);
    let words_ok = !value.is_empty()
        && body.split('-').enumerate().all(|(i, word)| {
            let mut chars = word.chars();
            let first_ok = chars
                .next()
                .is_some_and(|c| c.is_ascii_lowercase() || (i > 0 && c.is_ascii_digit()));
            first_ok && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        });
    words_ok.then_some(prefix)
}

/// `name` without a trailing `/<digits>` alpha modifier.
pub fn strip_alpha(name: &str) -> &str {
    alpha_parts(name).map_or(name, |(stem, _)| stem)
}

/// `(stem, digits)` of an alpha-modified utility (`bg-x/50`), if `name` is one.
pub fn alpha_parts(name: &str) -> Option<(&str, &str)> {
    let (stem, digits) = name.rsplit_once('/')?;
    (!digits.is_empty() && digits.chars().all(|c| c.is_ascii_digit())).then_some((stem, digits))
}

/// Split `<category>-<rest>` at the first hyphen when the category is `[a-z][a-z0-9]*`.
pub fn category_split(stem: &str) -> Option<(&str, &str)> {
    let (category, rest) = stem.split_once('-')?;
    let mut chars = category.chars();
    let ok = chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit());
    (ok && !rest.is_empty()).then_some((category, rest))
}

/// Split a non-arbitrary utility into `(family prefix, key)`, a leading `-` belonging to the prefix
/// (`-z-10`) and a compound prefix (`min-h`) kept whole; `None` when there is no hyphen at all.
pub fn split_family_stem(name: &str) -> Option<(String, &str)> {
    let negative = name.starts_with('-');
    let body = name.strip_prefix('-').unwrap_or(name);
    let sign = if negative { "-" } else { "" };
    for compound in COMPOUND_PREFIXES {
        if let Some(key) = body
            .strip_prefix(compound)
            .and_then(|r| r.strip_prefix('-'))
        {
            return Some((format!("{sign}{compound}"), key));
        }
    }
    let (prefix, key) = body.split_once('-')?;
    Some((format!("{sign}{prefix}"), key))
}

/// The scale a length-utility `prefix` is judged by and the token name of `step` on it.
pub fn scale_and_token(spec: &DesignSpec, prefix: &str, step: f64) -> (Vec<f64>, String) {
    match prefix {
        "rounded" => (spec.scales.radii.clone(), radius_token(&spec.tokens, step)),
        "text" => (
            spec.scales.font_sizes.clone(),
            font_size_token(&spec.tokens, step),
        ),
        "w" | "h" | "min-w" | "min-h" | "max-h" => {
            if spec.scales.sizes.is_empty() {
                (spec.scales.spacing.clone(), space_token(&spec.tokens, step))
            } else {
                (spec.scales.sizes.clone(), size_token(&spec.tokens, step))
            }
        }
        _ => (spec.scales.spacing.clone(), space_token(&spec.tokens, step)),
    }
}

/// Why the TW rules cannot run on `host`: no spec or styles, or no Tailwind facts collected.
pub fn missing_facts<H: crate::host::CrunkHost + ?Sized>(host: &H) -> Option<String> {
    if let Some(why) = crate::host::missing_inputs(host) {
        return Some(why);
    }
    host.tailwind()
        .is_none()
        .then(|| "no Tailwind facts were collected".to_owned())
}
