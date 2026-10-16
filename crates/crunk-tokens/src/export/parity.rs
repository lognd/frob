//! Cross-target parity: the same token must resolve to the same value in every generated
//! artifact (CSS, the flat JSON export, USS and the C# class).
//!
//! Each artifact is read back into a `token -> value` view of the default mode and the views are
//! compared pairwise on a scalar form (colours by channel, lengths, durations and numbers by
//! magnitude), so a hand-edited CSS value, a stale JSON export or an exporter that rounds
//! differently shows up as a [`Divergence`]. The CSS and JSON views read the file on disk when
//! the spec configures one; USS and C# have no configured path and are rendered from the spec.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use std::collections::BTreeMap;

use crunk_spec::DesignSpec;
use crunk_values::Color;

use super::Target;
use super::csharp::pascal;
use super::write::ExportError;
use crate::model::TokenSet;
use crate::naming::bare_name;

/// One token that two targets disagree on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Divergence {
    /// The custom property name (`--space-4`).
    pub token: String,
    /// The reference target (the first view that has the token).
    pub left: Target,
    /// The reference target's value, as written.
    pub left_value: String,
    /// The target that disagrees.
    pub right: Target,
    /// The disagreeing target's value, as written.
    pub right_value: String,
}

/// A value reduced to what can be compared across artifact syntaxes.
#[derive(Debug, Clone, Copy, PartialEq)]
enum Scalar {
    Color([f64; 4]),
    Num(f64),
}

impl Scalar {
    fn alike(self, other: Self) -> bool {
        match (self, other) {
            (Self::Color(a), Self::Color(b)) => a.iter().zip(b).all(|(x, y)| (x - y).abs() < 0.003),
            (Self::Num(a), Self::Num(b)) => (a - b).abs() <= 1e-4 * a.abs().max(1.0),
            _ => false,
        }
    }
}

fn number(text: &str) -> Option<f64> {
    text.parse::<f64>().ok().filter(|n| n.is_finite())
}

/// The scalar of a CSS-syntax value (`#2f6fed`, `16px`, `150ms`, `400`), `None` for the rest.
fn css_scalar(text: &str) -> Option<Scalar> {
    let t = text.trim();
    if t.starts_with('#') {
        let c = Color::parse(t).ok()?;
        return Some(Scalar::Color([c.r, c.g, c.b, c.a]));
    }
    let magnitude = t
        .strip_suffix("px")
        .or_else(|| t.strip_suffix("ms"))
        .unwrap_or(t);
    number(magnitude).map(Scalar::Num)
}

/// The scalar of a C# initializer (`8f`, `400`, `new CrunkColor(0.1f, 0.2f, 0.3f, 1f)`).
fn csharp_scalar(text: &str) -> Option<Scalar> {
    let t = text.trim();
    if let Some(args) = t
        .strip_prefix("new CrunkColor(")
        .and_then(|r| r.strip_suffix(')'))
    {
        let parts: Vec<f64> = args
            .split(',')
            .filter_map(|a| number(a.trim().trim_end_matches('f')))
            .collect();
        return <[f64; 4]>::try_from(parts).ok().map(Scalar::Color);
    }
    number(t.trim_end_matches('f')).map(Scalar::Num)
}

/// Custom properties declared in the first `{ ... }` block of a CSS or USS sheet.
fn root_view(text: &str) -> BTreeMap<String, String> {
    let mut view = BTreeMap::new();
    let mut inside = false;
    for line in text.lines() {
        let line = line.trim();
        if line.ends_with('{') {
            if inside {
                break;
            }
            inside = true;
        } else if line.starts_with('}') {
            if inside {
                break;
            }
        } else if inside
            && let Some((name, value)) = line.split_once(':')
            && name.trim().starts_with("--")
        {
            view.insert(
                name.trim().to_owned(),
                value.trim().trim_end_matches(';').trim().to_owned(),
            );
        }
    }
    view
}

/// The flat JSON export as `--name -> value`.
fn json_view(text: &str) -> BTreeMap<String, String> {
    let Ok(serde_json::Value::Object(map)) = serde_json::from_str(text) else {
        tracing::debug!("parity: the JSON export does not parse; no JSON view");
        return BTreeMap::new();
    };
    map.into_iter()
        .filter_map(|(k, v)| v.as_str().map(|s| (format!("--{k}"), s.to_owned())))
        .collect()
}

/// The default-mode `CrunkTokens` class of the C# file as `--name -> initializer`, mapping each
/// identifier back through the tokens of `set`.
fn csharp_view(text: &str, set: &TokenSet) -> BTreeMap<String, String> {
    let by_ident: BTreeMap<String, &str> = set
        .iter()
        .map(|t| (pascal(bare_name(&t.name)), t.name.as_str()))
        .collect();
    let mut view = BTreeMap::new();
    let mut in_class = false;
    for line in text.lines() {
        let line = line.trim();
        if line.starts_with("public static class CrunkTokens") && !in_class {
            in_class = true;
        } else if in_class && line == "}" {
            break;
        } else if in_class && line.starts_with("public ") {
            let Some((decl, init)) = line.trim_end_matches(';').split_once(" = ") else {
                continue;
            };
            let ident = decl.rsplit(' ').next().unwrap_or_default();
            if let Some(name) = by_ident.get(ident) {
                view.insert((*name).to_owned(), init.to_owned());
            }
        }
    }
    view
}

/// One artifact: its target, its `--name -> value` view and how to read a value.
type View = (Target, BTreeMap<String, String>, fn(&str) -> Option<Scalar>);

/// Compare the artifact `views` (target, token -> value, how to read a value) pairwise against the
/// first view that has each token.
fn compare_views(views: &[View]) -> Vec<Divergence> {
    let mut out = Vec::new();
    let names: std::collections::BTreeSet<&String> =
        views.iter().flat_map(|(_, v, _)| v.keys()).collect();
    for name in names {
        let mut reference: Option<(Target, &str, Scalar)> = None;
        for (target, view, read) in views {
            let Some(raw) = view.get(name) else { continue };
            let Some(scalar) = read(raw) else { continue };
            match reference {
                None => reference = Some((*target, raw, scalar)),
                Some((left, left_raw, left_scalar)) if !left_scalar.alike(scalar) => {
                    out.push(Divergence {
                        token: name.clone(),
                        left,
                        left_value: left_raw.to_owned(),
                        right: *target,
                        right_value: raw.clone(),
                    });
                }
                Some(_) => {}
            }
        }
    }
    out
}

/// Pure parity of the given artifact texts: `css` and `json` are the files as they are (or `None`
/// to leave that view out), USS and C# are the renders of `tokens`.
pub fn parity_of(
    spec: &DesignSpec,
    tokens: &TokenSet,
    css: Option<&str>,
    json: Option<&str>,
) -> Vec<Divergence> {
    let mut views: Vec<View> = Vec::new();
    if let Some(text) = css {
        views.push((Target::Css, root_view(text), css_scalar));
    }
    if let Some(text) = json {
        views.push((Target::Json, json_view(text), css_scalar));
    }
    views.push((
        Target::Uss,
        root_view(&Target::Uss.exporter().render(spec, tokens)),
        css_scalar,
    ));
    views.push((
        Target::Csharp,
        csharp_view(&Target::Csharp.exporter().render(spec, tokens), tokens),
        csharp_scalar,
    ));
    let found = compare_views(&views);
    tracing::debug!(divergences = found.len(), "export parity compared");
    found
}

fn read_optional(path: &std::path::Path) -> Result<Option<String>, ExportError> {
    match std::fs::read_to_string(path) {
        Ok(text) => Ok(Some(text)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(source) => Err(ExportError::Read {
            path: path.to_owned(),
            source,
        }),
    }
}

/// Parity of the generated files on disk (CSS and JSON, when they exist) with the USS and C# renders
/// of `spec`.
///
/// # Errors
///
/// [`ExportError`] when the spec produces a colliding token name or a file cannot be read.
pub fn check_parity(spec: &DesignSpec) -> Result<Vec<Divergence>, ExportError> {
    let tokens = TokenSet::from_spec(spec)?;
    let css = match Target::Css.exporter().path(spec) {
        Some(p) => read_optional(&p)?,
        None => None,
    };
    let json = match Target::Json.exporter().path(spec) {
        Some(p) => read_optional(&p)?,
        None => None,
    };
    Ok(parity_of(spec, &tokens, css.as_deref(), json.as_deref()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec() -> DesignSpec {
        crunk_spec::parse_spec(
            crunk_spec::presets::DEFAULT,
            std::path::Path::new("crunk.toml"),
            std::path::Path::new("/proj"),
        )
        .expect("default preset parses")
    }

    #[test]
    fn rendered_targets_agree() {
        let spec = spec();
        let tokens = TokenSet::from_spec(&spec).expect("tokens");
        let css = Target::Css.exporter().render(&spec, &tokens);
        let json = Target::Json.exporter().render(&spec, &tokens);
        assert_eq!(parity_of(&spec, &tokens, Some(&css), Some(&json)), vec![]);
    }

    #[test]
    fn a_hand_edited_css_value_diverges_from_uss_and_csharp() {
        let spec = spec();
        let tokens = TokenSet::from_spec(&spec).expect("tokens");
        let css = Target::Css
            .exporter()
            .render(&spec, &tokens)
            .replace("--space-16: 16px;", "--space-16: 17px;");
        let found = parity_of(&spec, &tokens, Some(&css), None);
        assert!(
            found.iter().any(|d| d.token == "--space-16"
                && d.left == Target::Css
                && d.right == Target::Uss),
            "{found:?}"
        );
    }

    #[test]
    fn scalars_ignore_units_and_float_suffixes() {
        assert!(
            css_scalar("16px")
                .unwrap()
                .alike(csharp_scalar("16f").unwrap())
        );
        assert!(
            !css_scalar("16px")
                .unwrap()
                .alike(csharp_scalar("17f").unwrap())
        );
        assert_eq!(csharp_scalar("new CrunkColor(1f, 0f, 0f)"), None);
    }
}
