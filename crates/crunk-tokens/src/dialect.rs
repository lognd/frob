//! The design/tokens TOML dialect: terse authored tokens compiled to a [`TokenSet`].
//!
//! A table holding a `value` key is a token; any other table is a group. A token path
//! (`color.ink`) names the custom property `--color-ink`. Values are terse: `"#e6e8ef"` (color),
//! `"16px"` (dimension), `"150ms"` / `"0.2s"` (duration), `"{color.ink}"` (alias), an integer or
//! float (number), `[0.4, 0, 0.2, 1]` (cubic bezier), `["Inter", "sans-serif"]` (font family) and
//! a table (composite: typography, shadow, border, transition). A token table may also carry
//! `type`, `tier`, `description`, `deprecated`, `scopes` and `modes = { dark = "#fff" }`.
//!
//! ```
//! let set = crunk_tokens::dialect::parse("[color]\nink = \"#e6e8ef\"\n", "tokens.toml").unwrap();
//! assert!(set.get("--color-ink").is_some());
//! ```

// frob:ticket 01M4CXQXGBYXFCDTSQQVQKN1E9

use indexmap::IndexMap;
use serde::Deserialize;
use thiserror::Error;

use crate::model::{Scope, Tier, Token, TokenError, TokenKind, TokenSet, TokenValue, Unit};
use crunk_values::Color;

/// Why a dialect file did not compile to a [`TokenSet`].
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum DialectError {
    /// The text is not valid TOML.
    #[error("{origin}: {message}")]
    Syntax {
        /// The file the text came from.
        origin: String,
        /// The TOML parser's message.
        message: String,
    },
    /// A token path or value is malformed.
    #[error("{origin}: token `{path}`: {reason}")]
    Invalid {
        /// The file the text came from.
        origin: String,
        /// The dotted token path.
        path: String,
        /// What is wrong.
        reason: String,
    },
    /// An alias names no token, or its chain is cyclic, in some mode.
    #[error("{origin}: token `{path}` aliases `{target}`, which does not resolve{in_mode}")]
    BrokenAlias {
        /// The file the text came from.
        origin: String,
        /// The aliasing token, as a custom property name.
        path: String,
        /// The alias target, as a custom property name.
        target: String,
        /// ` in mode <name>` or empty for the default.
        in_mode: String,
    },
    /// Two tokens produce the same name.
    #[error(transparent)]
    Collision(#[from] TokenError),
}

/// A TOML value as the dialect reads it, keeping table order.
#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum Raw {
    Table(IndexMap<String, Raw>),
    Array(Vec<Raw>),
    Str(String),
    Int(i64),
    Float(f64),
}

struct Ctx<'a> {
    origin: &'a str,
    path: String,
}

impl Ctx<'_> {
    fn invalid(&self, reason: impl Into<String>) -> DialectError {
        DialectError::Invalid {
            origin: self.origin.to_owned(),
            path: self.path.clone(),
            reason: reason.into(),
        }
    }
}

/// The custom property name of a dotted token path (`color.ink` is `--color-ink`).
pub fn name_of_path(path: &str) -> String {
    format!("--{}", path.replace('.', "-"))
}

/// Compile dialect `text` (read from `origin`, for messages) to a [`TokenSet`].
///
/// # Errors
///
/// [`DialectError`] for bad TOML, a malformed token, a name collision or an alias that does not
/// resolve in the default or any mode.
pub fn parse(text: &str, origin: &str) -> Result<TokenSet, DialectError> {
    let raw: IndexMap<String, Raw> =
        toml_edit::de::from_str(text).map_err(|e| DialectError::Syntax {
            origin: origin.to_owned(),
            message: e.to_string(),
        })?;
    let mut tokens = Vec::new();
    walk(&raw, &mut Vec::new(), origin, &mut tokens)?;
    let set = TokenSet::from_tokens(tokens)?;
    check_aliases(&set, origin)?;
    tracing::debug!(origin, count = set.len(), "dialect compiled");
    Ok(set)
}

fn walk(
    table: &IndexMap<String, Raw>,
    prefix: &mut Vec<String>,
    origin: &str,
    out: &mut Vec<Token>,
) -> Result<(), DialectError> {
    for (key, node) in table {
        prefix.push(key.clone());
        let ctx = Ctx {
            origin,
            path: prefix.join("."),
        };
        if key.is_empty() || key.contains(['.', '{', '}']) || key.starts_with('$') {
            return Err(
                ctx.invalid("a name may not be empty, contain `.`, `{`, `}` or start with `$`")
            );
        }
        match node {
            Raw::Table(inner) if inner.contains_key("value") => out.push(token(inner, &ctx)?),
            Raw::Table(inner) => walk(inner, prefix, origin, out)?,
            _ => out.push(token_from_value(node, None, &ctx)?),
        }
        prefix.pop();
    }
    Ok(())
}

fn token(fields: &IndexMap<String, Raw>, ctx: &Ctx<'_>) -> Result<Token, DialectError> {
    for key in fields.keys() {
        if ![
            "value",
            "type",
            "tier",
            "description",
            "scopes",
            "modes",
            "deprecated",
        ]
        .contains(&key.as_str())
        {
            return Err(ctx.invalid(format!("unknown field `{key}`")));
        }
    }
    let declared = match fields.get("type") {
        Some(Raw::Str(t)) => Some(t.as_str()),
        Some(_) => return Err(ctx.invalid("`type` must be a string")),
        None => None,
    };
    let mut tok = token_from_value(&fields["value"], declared, ctx)?;
    match fields.get("description") {
        Some(Raw::Str(d)) => tok.description = Some(d.clone()),
        Some(_) => return Err(ctx.invalid("`description` must be a string")),
        None => {}
    }
    match fields.get("deprecated") {
        Some(Raw::Str(d)) => tok.deprecated = Some(d.clone()),
        Some(_) => return Err(ctx.invalid("`deprecated` must be a string")),
        None => {}
    }
    match fields.get("tier") {
        Some(Raw::Str(t)) => {
            tok.tier = match t.as_str() {
                "primitive" => Tier::Primitive,
                "semantic" => Tier::Semantic,
                "component" => Tier::Component,
                other => return Err(ctx.invalid(format!("unknown tier `{other}`"))),
            };
        }
        Some(_) => return Err(ctx.invalid("`tier` must be a string")),
        None => {}
    }
    if let Some(scopes) = fields.get("scopes") {
        let Raw::Array(items) = scopes else {
            return Err(ctx.invalid("`scopes` must be a list of strings"));
        };
        for item in items {
            let scope = match item {
                Raw::Str(s) => Scope::parse(s),
                _ => None,
            };
            tok.scopes
                .push(scope.ok_or_else(|| ctx.invalid("unknown scope in `scopes`"))?);
        }
    }
    if let Some(modes) = fields.get("modes") {
        let Raw::Table(modes) = modes else {
            return Err(ctx.invalid("`modes` must be a table of mode name to value"));
        };
        for (mode, raw) in modes {
            let value = value(raw, ctx)?;
            if declared.is_some() && value.dtcg_type().is_some_and(|t| Some(t) != declared) {
                return Err(ctx.invalid(format!(
                    "mode `{mode}` value is not a {}",
                    declared.unwrap_or("")
                )));
            }
            tok.modes.insert(mode.clone(), value);
        }
    }
    Ok(tok)
}

fn token_from_value(
    raw: &Raw,
    declared: Option<&str>,
    ctx: &Ctx<'_>,
) -> Result<Token, DialectError> {
    let value = value(raw, ctx)?;
    if let Some(found) = value.dtcg_type() {
        if declared.is_some_and(|d| d != found) {
            return Err(ctx.invalid(format!(
                "declared type `{}` but the value is a {found}",
                declared.unwrap_or("")
            )));
        }
    } else if matches!(value, TokenValue::Composite(_)) {
        return Err(
            ctx.invalid("a composite must match typography, shadow, border or transition members")
        );
    }
    let kind = match value {
        TokenValue::Color(_) => TokenKind::Color,
        _ => TokenKind::Custom,
    };
    Ok(Token {
        name: name_of_path(&ctx.path),
        kind,
        key: ctx.path.clone(),
        origin: format!("{} {}", ctx.origin, ctx.path),
        tier: if matches!(value, TokenValue::Alias(_)) {
            Tier::Semantic
        } else {
            Tier::Primitive
        },
        value,
        modes: IndexMap::new(),
        scopes: Vec::new(),
        description: None,
        deprecated: None,
    })
}

fn value(raw: &Raw, ctx: &Ctx<'_>) -> Result<TokenValue, DialectError> {
    match raw {
        Raw::Int(n) => Ok(TokenValue::Number(*n)),
        Raw::Float(f) => Ok(TokenValue::Float(*f)),
        Raw::Str(s) => string_value(s, ctx),
        Raw::Array(items) => array_value(items, ctx),
        Raw::Table(members) => {
            let mut out = IndexMap::new();
            for (k, v) in members {
                out.insert(k.clone(), member(v, ctx)?);
            }
            Ok(TokenValue::Composite(out))
        }
    }
}

/// A composite member: like a value, but a bare non-special string is literal text.
fn member(raw: &Raw, ctx: &Ctx<'_>) -> Result<TokenValue, DialectError> {
    match raw {
        Raw::Str(s) => Ok(string_value(s, ctx).unwrap_or_else(|_| TokenValue::Text(s.clone()))),
        other => value(other, ctx),
    }
}

fn number(text: &str) -> Option<f64> {
    text.parse::<f64>().ok().filter(|n| n.is_finite())
}

fn string_value(s: &str, ctx: &Ctx<'_>) -> Result<TokenValue, DialectError> {
    if let Some(path) = s.strip_prefix('{').and_then(|r| r.strip_suffix('}')) {
        return Ok(TokenValue::Alias(name_of_path(path)));
    }
    if s.starts_with('#') {
        return Color::parse(s)
            .map(TokenValue::Color)
            .map_err(|e| ctx.invalid(format!("bad color `{s}`: {e}")));
    }
    if let Some(n) = s.strip_suffix("px").and_then(number) {
        return Ok(TokenValue::Dimension {
            value: n,
            unit: Unit::Px,
        });
    }
    if let Some(n) = s.strip_suffix("ms").and_then(number) {
        return Ok(TokenValue::Duration(n));
    }
    if let Some(n) = s.strip_suffix('s').and_then(number) {
        return Ok(TokenValue::Duration(n * 1000.0));
    }
    Err(ctx.invalid(format!(
        "cannot read value `{s}` (expected a color, px, ms, s or alias)"
    )))
}

fn array_value(items: &[Raw], ctx: &Ctx<'_>) -> Result<TokenValue, DialectError> {
    let nums: Option<Vec<f64>> = items
        .iter()
        .map(|i| match i {
            #[allow(
                clippy::cast_precision_loss,
                reason = "authored bezier ordinates are tiny"
            )]
            Raw::Int(n) => Some(*n as f64),
            Raw::Float(f) => Some(*f),
            _ => None,
        })
        .collect();
    if let Some(n) = nums {
        return match n[..] {
            [a, b, c, d] => Ok(TokenValue::CubicBezier([a, b, c, d])),
            _ => Err(ctx.invalid("a number list is a cubic bezier and needs exactly 4 numbers")),
        };
    }
    let names: Option<Vec<String>> = items
        .iter()
        .map(|i| match i {
            Raw::Str(s) => Some(s.clone()),
            _ => None,
        })
        .collect();
    names
        .filter(|n| !n.is_empty())
        .map(TokenValue::FontFamily)
        .ok_or_else(|| ctx.invalid("a list is 4 bezier numbers or a non-empty font-family list"))
}

/// Every alias, in the default and each mode, must resolve to a concrete value.
fn check_aliases(set: &TokenSet, origin: &str) -> Result<(), DialectError> {
    let modes = set.mode_names();
    for token in set.iter() {
        let candidates = std::iter::once((None, &token.value))
            .chain(token.modes.iter().map(|(m, v)| (Some(m.as_str()), v)));
        for (mode, v) in candidates {
            let mut targets = Vec::new();
            match v {
                TokenValue::Alias(t) => targets.push(t),
                TokenValue::Composite(members) => {
                    targets.extend(members.values().filter_map(|m| {
                        if let TokenValue::Alias(t) = m {
                            Some(t)
                        } else {
                            None
                        }
                    }));
                }
                _ => {}
            }
            for target in targets {
                let mut scan: Vec<Option<&str>> = vec![mode];
                if mode.is_none() {
                    scan.extend(modes.iter().map(|m| Some(*m)));
                }
                for m in scan {
                    if set.resolve(target, m).is_none() {
                        return Err(DialectError::BrokenAlias {
                            origin: origin.to_owned(),
                            path: token.name.clone(),
                            target: target.clone(),
                            in_mode: m.map(|m| format!(" in mode {m}")).unwrap_or_default(),
                        });
                    }
                }
            }
        }
    }
    Ok(())
}
