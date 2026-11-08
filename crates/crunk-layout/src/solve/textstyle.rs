//! Inherited text style of a node, from its inline font declarations.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use crate::style::{ElementRef, Len, StyleError, TokenMap, parse_len, resolve_vars};
use crate::text::{TextStyle, bundled_fonts};

use super::SolveError;

/// The default text style at the root: Lato 16px, line-height 1.2, wrapping.
pub(crate) fn root_text_style() -> TextStyle {
    TextStyle::new("Lato", 16.0)
}

/// `parent` overridden by the font declarations in `decls`.
pub(crate) fn text_style_for(
    el: ElementRef<'_>,
    decls: &[(String, String)],
    tokens: &TokenMap,
    parent: &TextStyle,
) -> Result<TextStyle, SolveError> {
    let mut style = parent.clone();
    for (prop, raw) in decls {
        let prop = prop.trim().to_ascii_lowercase();
        if !is_text_property(&prop) {
            continue;
        }
        let value = resolve_vars(tokens, raw)
            .map_err(|e| bad(el, &prop, raw, &format!("{e:?}")))?
            .trim()
            .to_ascii_lowercase();
        apply(&mut style, el, &prop, &value)?;
    }
    Ok(style)
}

fn is_text_property(prop: &str) -> bool {
    matches!(
        prop,
        "font-family" | "font-size" | "letter-spacing" | "line-height" | "white-space"
    )
}

fn apply(s: &mut TextStyle, el: ElementRef<'_>, prop: &str, value: &str) -> Result<(), SolveError> {
    match prop {
        "font-family" => family(s, value)?,
        "font-size" => s.size_px = size(el, prop, value, s.size_px)?,
        "letter-spacing" => s.letter_spacing_px = spacing(el, prop, value)?,
        "line-height" => s.line_height = line_height(el, prop, value, s.size_px)?,
        _ => s.nowrap = matches!(value, "nowrap" | "pre"),
    }
    Ok(())
}

fn bad(el: ElementRef<'_>, prop: &str, value: &str, reason: &str) -> SolveError {
    SolveError::Style(vec![StyleError::BadValue {
        element: el.data_id.to_owned(),
        line: el.line,
        property: prop.to_owned(),
        value: value.to_owned(),
        reason: reason.to_owned(),
    }])
}

/// First listed family that is bundled; generics keep the inherited font; anything else errors.
fn family(s: &mut TextStyle, value: &str) -> Result<(), SolveError> {
    let names: Vec<String> = value
        .split(',')
        .map(|n| n.trim().trim_matches(['\'', '"']).trim().to_owned())
        .collect();
    let bundled = bundled_fonts();
    for n in &names {
        if let Some(b) = bundled.iter().find(|b| b.eq_ignore_ascii_case(n)) {
            (*b).clone_into(&mut s.font);
            return Ok(());
        }
    }
    if names.iter().any(|n| is_generic(n)) {
        return Ok(());
    }
    let font = names.first().cloned().unwrap_or_default();
    Err(crate::text::TextError::FontNotBundled {
        font,
        bundled: bundled.join(", "),
    }
    .into())
}

fn is_generic(name: &str) -> bool {
    matches!(
        name,
        "serif" | "sans-serif" | "monospace" | "cursive" | "fantasy" | "system-ui" | "inherit"
    )
}

fn size(el: ElementRef<'_>, prop: &str, value: &str, parent_px: f32) -> Result<f32, SolveError> {
    match parse_len(value) {
        Ok(Len::Px(v)) if v >= 0.0 => Ok(v),
        Ok(Len::Pct(v)) if v >= 0.0 => Ok(parent_px * v),
        Ok(_) => Err(bad(el, prop, value, "must be a non-negative length")),
        Err(reason) => Err(bad(el, prop, value, &reason)),
    }
}

fn spacing(el: ElementRef<'_>, prop: &str, value: &str) -> Result<f32, SolveError> {
    if value == "normal" {
        return Ok(0.0);
    }
    match parse_len(value) {
        Ok(Len::Px(v)) => Ok(v),
        Ok(_) => Err(bad(el, prop, value, "must be a length")),
        Err(reason) => Err(bad(el, prop, value, &reason)),
    }
}

/// Line height as a multiple of the font size.
fn line_height(
    el: ElementRef<'_>,
    prop: &str,
    value: &str,
    size_px: f32,
) -> Result<f32, SolveError> {
    if value == "normal" {
        return Ok(1.2);
    }
    if let Ok(n) = value.parse::<f32>() {
        return if n.is_finite() && n >= 0.0 {
            Ok(n)
        } else {
            Err(bad(el, prop, value, "must be a non-negative number"))
        };
    }
    match parse_len(value) {
        Ok(Len::Px(v)) if size_px > 0.0 && v >= 0.0 => Ok(v / size_px),
        Ok(Len::Pct(v)) if v >= 0.0 => Ok(v),
        Ok(_) => Err(bad(el, prop, value, "must be a non-negative length")),
        Err(reason) => Err(bad(el, prop, value, &reason)),
    }
}
