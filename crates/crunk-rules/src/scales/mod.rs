//! The scale judgment shared by SPACE001, TYPE001, RADIUS001 and SIZE001 (port of
//! `crunk/rules/_scales.py`): is a px-comparable length on its scale, and if not, which steps
//! bracket it and which one is nearest.
//!
//! Only px and rem lengths carry a comparable px value; zero, percent, `auto`, `calc()` and other
//! units are exempt. The tolerance convention has exactly one home, [`off_scale`]: relative
//! (`|value - step| <= tolerance * step`), with step 0 borrowing `tolerance * smallest nonzero
//! step` as an absolute allowance.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use crunk_ingest::ProjectStyles;
use crunk_spec::DesignSpec;
use crunk_values::{Length, LengthKind};
use gob_rules::{Out, RuleDecl};

use crate::sheets::site_path;

/// The properties SPACE001 judges.
pub const SPACE_PROPS: &[&str] = &[
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "gap",
    "row-gap",
    "column-gap",
    "inset",
    "top",
    "right",
    "bottom",
    "left",
];

/// The properties RADIUS001 judges.
pub const RADIUS_PROPS: &[&str] = &[
    "border-radius",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
];

/// The property TYPE001 judges.
pub const FONT_SIZE_PROPS: &[&str] = &["font-size"];

/// The properties SIZE001 judges. `max-width` is exempt by design (r10/CR-22): box sizes are their
/// own vocabulary, and a maximum is a bound, not a size the design system hands out.
pub const SIZE_PROPS: &[&str] = &["width", "height", "min-width", "min-height", "max-height"];

/// One off-scale length: its neighbouring steps, the nearest step and whether a fix may snap to it.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct OffScale {
    /// The largest step at or below the value (the smallest step when none is).
    pub lower: f64,
    /// The smallest step at or above the value (the largest step when none is).
    pub upper: f64,
    /// The step closest to the value.
    pub nearest: f64,
    /// True when the value is within the tolerance of [`OffScale::nearest`].
    pub snappable: bool,
}

/// `None` when `length` is not px-comparable or lands exactly on `scale`; otherwise where it falls.
///
/// A negative length is judged by its magnitude (`margin: -13px` is as off as `13px`). The scale
/// must not be empty; callers skip a rule whose scale is undeclared.
#[allow(
    clippy::float_cmp,
    reason = "a length is on the scale only when it equals a step exactly, as in the Python rule"
)]
pub fn off_scale(length: &Length, scale: &[f64], tolerance: f64) -> Option<OffScale> {
    if !matches!(length.kind, LengthKind::Px | LengthKind::Rem) {
        return None;
    }
    let value = length.px?.abs();
    if scale.contains(&value) {
        return None;
    }
    let mut ordered = scale.to_vec();
    ordered.sort_by(f64::total_cmp);
    let (first, last) = (*ordered.first()?, *ordered.last()?);
    let (mut lower, mut upper) = (first, last);
    for &step in &ordered {
        if step <= value {
            lower = step;
        }
        if step >= value {
            upper = step;
            break;
        }
    }
    let nearest = scale.iter().copied().reduce(|best, step| {
        if (value - step).abs() < (value - best).abs() {
            step
        } else {
            best
        }
    })?;
    let allowance = if nearest == 0.0 {
        let smallest_nonzero = scale.iter().copied().filter(|s| *s > 0.0).reduce(f64::min);
        tolerance * smallest_nonzero.unwrap_or(0.0)
    } else {
        tolerance * nearest
    };
    Some(OffScale {
        lower,
        upper,
        nearest,
        snappable: (value - nearest).abs() <= allowance,
    })
}

/// What one scale rule judges: its properties, its scale and how a step is named as a token.
pub struct ScaleJudgment<'a> {
    /// The properties whose lengths are judged.
    pub props: &'static [&'static str],
    /// The allowed steps in px.
    pub scale: &'a [f64],
    /// The custom property name of a step (`--space-4`).
    pub token: &'a dyn Fn(f64) -> String,
}

/// Judge every px-comparable length of the declarations of `judgment.props` against the scale and
/// emit one located finding per off-scale length.
///
/// The message names the property, the length as written, the two bracketing steps and the nearest
/// one (the Python rule left the nearest to its fix payload; here the finding carries it, and says
/// when it is beyond `[lint] fix_tolerance` so no automatic replacement applies).
pub fn check<R: RuleDecl>(
    spec: &DesignSpec,
    styles: &ProjectStyles,
    judgment: &ScaleJudgment<'_>,
    out: &mut Out<'_, R>,
) {
    if judgment.scale.is_empty() {
        tracing::debug!(rule = R::DEF.id, "scale is undeclared; nothing to judge");
        return;
    }
    let tolerance = spec.lint.fix_tolerance;
    for sheet in &styles.sheets {
        let path = site_path(spec, &sheet.path);
        let declarations = sheet
            .declarations
            .iter()
            .filter(|d| judgment.props.contains(&d.prop.as_str()));
        for decl in declarations {
            for located in &decl.lengths {
                let Some(off) = off_scale(&located.length, judgment.scale, tolerance) else {
                    continue;
                };
                let name = judgment.token;
                let mut message = format!(
                    "{}: {} is off the scale; between var({}) and var({}); nearest is var({})",
                    decl.prop,
                    located.length.raw,
                    name(off.lower),
                    name(off.upper),
                    name(off.nearest),
                );
                if !off.snappable {
                    message.push_str(" (beyond fix_tolerance, so no automatic replacement)");
                }
                tracing::debug!(rule = R::DEF.id, %path, prop = %decl.prop, raw = %located.length.raw, "off-scale length");
                out.fire_in(&path, located.span.0, message);
            }
        }
    }
}
