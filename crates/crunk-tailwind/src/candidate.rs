//! The utility candidate parser: one class string into its structural fields.
//!
//! Grammar (v3 and v4 spellings both accepted):
//! `variant*  [!]  [-]  utility [-value | -[arbitrary] | -(--css-var)]  [/alpha]  [!]` where a
//! variant is any `:`-terminated prefix outside brackets and parentheses, and the whole token may
//! instead be an arbitrary property `[prop:value]`. Value meaning is never judged here; the
//! project's own Tailwind does that (a later ticket). The only utility knowledge is the
//! [`COMPOUND_ROOTS`] list, needed to split `min-w-4` into `min-w` and `4` without a registry.

use thiserror::Error;

/// Utility roots containing a hyphen, so `min-w-4` splits as `min-w` + `4` rather than `min` + `w-4`.
pub const COMPOUND_ROOTS: &[&str] = &[
    "min-w",
    "min-h",
    "max-w",
    "max-h",
    "gap-x",
    "gap-y",
    "space-x",
    "space-y",
    "inset-x",
    "inset-y",
    "border-x",
    "border-y",
    "border-t",
    "border-r",
    "border-b",
    "border-l",
    "border-s",
    "border-e",
    "rounded-t",
    "rounded-r",
    "rounded-b",
    "rounded-l",
    "rounded-s",
    "rounded-e",
    "rounded-tl",
    "rounded-tr",
    "rounded-br",
    "rounded-bl",
    "grid-cols",
    "grid-rows",
    "col-span",
    "row-span",
    "col-start",
    "col-end",
    "row-start",
    "row-end",
    "translate-x",
    "translate-y",
    "scale-x",
    "scale-y",
    "skew-x",
    "skew-y",
    "divide-x",
    "divide-y",
    "scroll-m",
    "scroll-p",
    "line-clamp",
    "font-size",
    "underline-offset",
    "outline-offset",
    "ring-offset",
    "inset-ring",
    "backdrop-blur",
    "backdrop-brightness",
    "drop-shadow",
    "text-shadow",
    "mask-image",
    "size-x",
];

/// Why a token is not a well-formed candidate.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum CandidateError {
    /// The token was empty.
    #[error("empty candidate")]
    Empty,
    /// A `[` or `(` is never closed, or a closer has no opener.
    #[error("unbalanced brackets in `{0}`")]
    Unbalanced(String),
    /// A `:` with nothing before it.
    #[error("empty variant in `{0}`")]
    EmptyVariant(String),
    /// Nothing is left once variants, `!` and `-` are removed.
    #[error("no utility in `{0}`")]
    NoUtility(String),
    /// A `-[]`, `-()` or `[]` with empty content, or `/` with no alpha.
    #[error("empty arbitrary value or alpha in `{0}`")]
    EmptyValue(String),
    /// An arbitrary property `[x]` without a `property:value` shape.
    #[error("arbitrary property needs `property:value` in `{0}`")]
    BadProperty(String),
}

/// One variant prefix, e.g. `md`, `hover`, `[&>p]`, `group-hover`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Variant {
    /// The variant text without the trailing `:`.
    pub text: String,
    /// Whether it is an arbitrary variant (`[...]`).
    pub arbitrary: bool,
}

/// The value part of a candidate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UtilityValue {
    /// A theme key such as `4`, `red-500`, `lg`, `1/2` is split before this (see alpha).
    Named(String),
    /// `[13px]` or `[length:var(--x)]`: the optional type hint and the content.
    Arbitrary {
        /// The `type:` hint before the first `:`, if any.
        hint: Option<String>,
        /// The bracket content (underscores left as written).
        content: String,
    },
    /// v4 `(--name)` or `(length:--name)` shorthand for `var(--name)`.
    CssVar {
        /// The `type:` hint, if any.
        hint: Option<String>,
        /// The custom property name including the leading `--`.
        name: String,
    },
    /// The whole candidate was an arbitrary property `[property:value]`.
    Property {
        /// The CSS property.
        property: String,
        /// The CSS value.
        value: String,
    },
}

/// The `/alpha` modifier.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Alpha {
    /// `/50`, `/half`: a theme or numeric alpha.
    Named(String),
    /// `/[0.37]`.
    Arbitrary(String),
}

/// A parsed utility candidate; `raw` reassembles every field.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Candidate {
    /// The token exactly as written.
    pub raw: String,
    /// Variants in source order, outermost first.
    pub variants: Vec<Variant>,
    /// Whether `!` (leading, v3, or trailing, v4) forces importance.
    pub important: bool,
    /// Whether the utility is negated with a leading `-`.
    pub negative: bool,
    /// The utility root (`mt`, `min-w`, `bg`); empty for an arbitrary property.
    pub utility: String,
    /// The value, absent for bare utilities such as `flex`.
    pub value: Option<UtilityValue>,
    /// The alpha modifier, if any.
    pub alpha: Option<Alpha>,
}

/// Split `s` on `sep` at bracket depth zero; `None` when brackets do not balance.
fn split_top_level(s: &str, sep: char) -> Option<Vec<&str>> {
    let (mut depth, mut start) = (0usize, 0usize);
    let mut parts = Vec::new();
    for (i, ch) in s.char_indices() {
        match ch {
            '[' | '(' => depth += 1,
            ']' | ')' => depth = depth.checked_sub(1)?,
            c if c == sep && depth == 0 => {
                parts.push(&s[start..i]);
                start = i + ch.len_utf8();
            }
            _ => {}
        }
    }
    (depth == 0).then(|| {
        parts.push(&s[start..]);
        parts
    })
}

/// Split an optional `type:` hint off bracket or paren content.
fn split_hint(content: &str) -> (Option<String>, String) {
    match content.split_once(':') {
        Some((hint, rest))
            if !hint.is_empty()
                && !rest.is_empty()
                && hint.chars().all(|c| c.is_ascii_lowercase() || c == '-') =>
        {
            (Some(hint.to_owned()), rest.to_owned())
        }
        _ => (None, content.to_owned()),
    }
}

/// The value after the utility root of a named candidate: split by the longest compound root.
fn split_named(main: &str) -> (String, Option<UtilityValue>) {
    let compound = COMPOUND_ROOTS
        .iter()
        .filter(|r| {
            main.strip_prefix(**r)
                .is_some_and(|rest| rest.is_empty() || rest.starts_with('-'))
        })
        .max_by_key(|r| r.len());
    let root_len = match compound {
        Some(r) => r.len(),
        None => main.find('-').unwrap_or(main.len()),
    };
    let root = &main[..root_len];
    let value = main[root_len..]
        .strip_prefix('-')
        .map(|v| UtilityValue::Named(v.to_owned()));
    (root.to_owned(), value)
}

/// Parse the `main` part (no variants, importance or alpha) into `(utility, value)`.
fn parse_main(main: &str, raw: &str) -> Result<(String, Option<UtilityValue>), CandidateError> {
    let err_value = || CandidateError::EmptyValue(raw.to_owned());
    if let Some(inner) = main.strip_prefix('[') {
        let body = inner
            .strip_suffix(']')
            .ok_or_else(|| CandidateError::BadProperty(raw.to_owned()))?;
        let (property, value) = body
            .split_once(':')
            .filter(|(p, v)| !p.is_empty() && !v.is_empty())
            .ok_or_else(|| CandidateError::BadProperty(raw.to_owned()))?;
        return Ok((
            String::new(),
            Some(UtilityValue::Property {
                property: property.to_owned(),
                value: value.to_owned(),
            }),
        ));
    }
    for (open, close) in [('[', ']'), ('(', ')')] {
        let Some(body) = main.strip_suffix(close) else {
            continue;
        };
        let Some(at) = body.find(&format!("-{open}")) else {
            continue;
        };
        let (root, content) = (&body[..at], &body[at + 2..]);
        if root.is_empty() {
            return Err(CandidateError::NoUtility(raw.to_owned()));
        }
        if content.is_empty() {
            return Err(err_value());
        }
        let (hint, content) = split_hint(content);
        let value = if open == '[' {
            UtilityValue::Arbitrary { hint, content }
        } else {
            UtilityValue::CssVar {
                hint,
                name: content,
            }
        };
        return Ok((root.to_owned(), Some(value)));
    }
    let (root, value) = split_named(main);
    if root.is_empty() || (value.is_none() && main.ends_with('-')) {
        return Err(CandidateError::NoUtility(raw.to_owned()));
    }
    if matches!(&value, Some(UtilityValue::Named(v)) if v.is_empty()) {
        return Err(err_value());
    }
    Ok((root, value))
}

/// Parse one class token into a [`Candidate`], or say why it is not one.
///
/// # Errors
///
/// [`CandidateError`] for an empty token, unbalanced brackets, an empty variant, a missing
/// utility, an empty arbitrary value or alpha, or a malformed arbitrary property.
pub fn parse_candidate(raw: &str) -> Result<Candidate, CandidateError> {
    if raw.is_empty() {
        return Err(CandidateError::Empty);
    }
    let mut parts =
        split_top_level(raw, ':').ok_or_else(|| CandidateError::Unbalanced(raw.to_owned()))?;
    let base = parts.pop().unwrap_or_default();
    if parts.iter().any(|p| p.is_empty()) {
        return Err(CandidateError::EmptyVariant(raw.to_owned()));
    }
    let variants = parts
        .iter()
        .map(|p| Variant {
            text: (*p).to_owned(),
            arbitrary: p.starts_with('['),
        })
        .collect();

    let (leading, base) = base.strip_prefix('!').map_or((false, base), |b| (true, b));
    let (trailing, base) = base.strip_suffix('!').map_or((false, base), |b| (true, b));

    let mut slashes =
        split_top_level(base, '/').ok_or_else(|| CandidateError::Unbalanced(raw.to_owned()))?;
    let alpha_text = if slashes.len() > 1 {
        slashes.pop()
    } else {
        None
    };
    let main_joined = slashes.join("/");
    let alpha = match alpha_text {
        None => None,
        Some("") => return Err(CandidateError::EmptyValue(raw.to_owned())),
        Some(a) => Some(
            match a.strip_prefix('[').and_then(|a| a.strip_suffix(']')) {
                Some("") => return Err(CandidateError::EmptyValue(raw.to_owned())),
                Some(inner) => Alpha::Arbitrary(inner.to_owned()),
                None => Alpha::Named(a.to_owned()),
            },
        ),
    };

    let (negative, main) = match main_joined.strip_prefix('-') {
        Some(rest) if !rest.is_empty() => (true, rest.to_owned()),
        _ => (false, main_joined),
    };
    if main.is_empty() {
        return Err(CandidateError::NoUtility(raw.to_owned()));
    }
    let (utility, value) = parse_main(&main, raw)?;
    tracing::trace!(raw, %utility, "parsed candidate");
    Ok(Candidate {
        raw: raw.to_owned(),
        variants,
        important: leading || trailing,
        negative,
        utility,
        value,
        alpha,
    })
}
