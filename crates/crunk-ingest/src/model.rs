//! The ingested style model: located, typed facts with no judgment (the Python `ingest.models`).
//!
//! Every span is a half-open pair of byte offsets into the owning [`Stylesheet::source`], so
//! `&source[start..end]` is the exact original text at that span.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

use std::path::PathBuf;

use crunk_values::{Color, Length, LengthKind};
use serde::{Deserialize, Serialize};

/// Which `[org] buckets` group (or the tokens file or an entry sheet) a stylesheet belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Bucket {
    /// The generated tokens file.
    Tokens,
    /// A `base` bucket sheet.
    Base,
    /// A `components` bucket sheet.
    Components,
    /// A `layouts` bucket sheet.
    Layouts,
    /// A `utilities` bucket sheet.
    Utilities,
    /// An `[org] entry` sheet, exempt from bucket placement.
    Entry,
    /// A JSX source (set by the JSX ingest, not by the CSS walk).
    Jsx,
}

impl Bucket {
    /// The lowercase bucket name, as it appears in `[org] buckets`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Tokens => "tokens",
            Self::Base => "base",
            Self::Components => "components",
            Self::Layouts => "layouts",
            Self::Utilities => "utilities",
            Self::Entry => "entry",
            Self::Jsx => "jsx",
        }
    }

    /// The bucket named `name`, if it is one of the seven.
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "tokens" => Self::Tokens,
            "base" => Self::Base,
            "components" => Self::Components,
            "layouts" => Self::Layouts,
            "utilities" => Self::Utilities,
            "entry" => Self::Entry,
            "jsx" => Self::Jsx,
            _ => return None,
        })
    }
}

/// One `crunk:waive` comment directive: rule, optional reason, source line.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Waiver {
    /// The waived rule id.
    pub rule: String,
    /// Why the waiver exists, when given.
    pub reason: Option<String>,
    /// 1-based line of the directive.
    pub line: u32,
}

/// One class name used in a selector prelude, and the line it appears on.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassSelector {
    /// The class name without the dot.
    pub name: String,
    /// 1-based line of the dot.
    pub line: u32,
}

/// One `--x:` custom property definition site (not a `var()` use).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CustomProp {
    /// The lowercased property name including `--`.
    pub name: String,
    /// 1-based line of the definition.
    pub line: u32,
}

/// A byte span `(start, end)` into the owning source.
pub type Span = (usize, usize);

/// A [`Color`] parsed from a value token, with the token's own span.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LocatedColor {
    /// The parsed color.
    #[serde(with = "color_serde")]
    pub color: Color,
    /// The token span.
    pub span: Span,
}

/// A [`Length`] parsed from a value token, with the token's own span.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LocatedLength {
    /// The parsed length.
    #[serde(with = "length_serde")]
    pub length: Length,
    /// The token span.
    pub span: Span,
}

/// One `var(--name)` reference in a value, with the reference's own span.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LocatedVarRef {
    /// The custom property name including `--`.
    pub name: String,
    /// The span of the whole `var(...)` token.
    pub span: Span,
}

/// One `@media` prelude the walk recursed into: raw text plus parsed min/max-width px values.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LocatedMediaQuery {
    /// The prelude text, trimmed.
    pub prelude: String,
    /// The first literal `min-width` in px, `None` when the prelude carries none.
    pub min_px: Option<f64>,
    /// The first literal `max-width` in px, `None` when the prelude carries none.
    pub max_px: Option<f64>,
    /// 1-based line of the `@media`.
    pub line: u32,
}

/// One `prop: value;` with its byte span and every parsed value fact.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Declaration {
    /// The lowercased property name.
    pub prop: String,
    /// The value text as written, without `!important`; empty when the value is empty.
    pub value: String,
    /// 1-based line of the declaration.
    pub line: u32,
    /// The value span, `(0, 0)` when the value is empty.
    pub span: Span,
    /// Waivers attached to this declaration.
    pub waivers: Vec<Waiver>,
    /// Colors found in the value.
    pub colors: Vec<LocatedColor>,
    /// Lengths found in the value.
    pub lengths: Vec<LocatedLength>,
    /// `var()` references found in the value.
    pub var_refs: Vec<LocatedVarRef>,
}

/// A file that failed to read or parse; the walk survives and records this.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParseDiagnostic {
    /// The offending file (or the missing root), as walked.
    pub path: PathBuf,
    /// What went wrong.
    pub message: String,
}

/// One parsed `.css` file: its declarations, selectors, and custom props.
#[derive(Debug, Clone, PartialEq)]
pub struct Stylesheet {
    /// The file path as walked.
    pub path: PathBuf,
    /// The bucket, `None` for a stray.
    pub bucket: Option<Bucket>,
    /// The component name for a `components` sheet (the file stem).
    pub component: Option<String>,
    /// The file text.
    pub source: String,
    /// Every declaration, custom property definitions included, in source order.
    pub declarations: Vec<Declaration>,
    /// Every class selector.
    pub class_selectors: Vec<ClassSelector>,
    /// Every `--x:` definition site.
    pub custom_props: Vec<CustomProp>,
    /// Waivers that attached to no declaration.
    pub orphan_waivers: Vec<Waiver>,
    /// Every `@media` prelude.
    pub media_queries: Vec<LocatedMediaQuery>,
}

/// The full ingest result for a project: every stylesheet, stray, diagnostic.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ProjectStyles {
    /// Every parsed sheet in walk order.
    pub sheets: Vec<Stylesheet>,
    /// Sheets that sit in no bucket.
    pub strays: Vec<PathBuf>,
    /// Files that failed to read or parse, and root-level problems.
    pub diagnostics: Vec<ParseDiagnostic>,
    /// `.css` files outside `css_root` that no `[org] ignore` glob covers.
    pub ungoverned: Vec<PathBuf>,
}

mod color_serde {
    use crunk_values::Color;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub(super) fn serialize<S: Serializer>(color: &Color, s: S) -> Result<S::Ok, S::Error> {
        [color.r, color.g, color.b, color.a].serialize(s)
    }

    pub(super) fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Color, D::Error> {
        let [red, green, blue, alpha] = <[f64; 4]>::deserialize(d)?;
        Ok(Color {
            r: red,
            g: green,
            b: blue,
            a: alpha,
        })
    }
}

mod length_serde {
    use super::{Length, LengthKind};
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub(super) fn serialize<S: Serializer>(l: &Length, s: S) -> Result<S::Ok, S::Error> {
        (&l.raw, l.px, l.kind.as_str()).serialize(s)
    }

    pub(super) fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Length, D::Error> {
        let (raw, px, kind) = <(String, Option<f64>, String)>::deserialize(d)?;
        let kind = match kind.as_str() {
            "px" => LengthKind::Px,
            "rem" => LengthKind::Rem,
            "zero" => LengthKind::Zero,
            "percent" => LengthKind::Percent,
            "auto" => LengthKind::Auto,
            "calc" => LengthKind::Calc,
            "other" => LengthKind::Other,
            other => {
                return Err(serde::de::Error::custom(format!(
                    "unknown length kind `{other}`"
                )));
            }
        };
        Ok(Length { raw, px, kind })
    }
}
