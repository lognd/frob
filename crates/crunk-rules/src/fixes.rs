//! Tier A fix payloads shared by COLOR001, SPACE001, TYPE001, RADIUS001 and SIZE001: replace the
//! off-scale token with its design token, only when the nearest candidate is inside the spec's
//! tolerance (design: `docs/design/crunk/crunk.md` section 6).
//!
//! A fix is a single machine-applicable edit of the literal's own byte span. An opaque colour
//! becomes `var(--token)`; a translucent one becomes `color-mix(in srgb, var(--token) N%,
//! transparent)` so its alpha survives. A negative length gets no fix (`var()` cannot carry the
//! sign), and nothing outside the tolerance is ever rewritten.

// frob:ticket 01M54H34N0CPKAZ7TP91EYXGVV

use crunk_values::Color;
use gob_rules::{Applicability, EmittedEdit, EmittedFix};

/// The fix replacing the literal at `span` with `replacement`, applied without review.
pub fn replace_span(title: String, span: (usize, usize), replacement: String) -> EmittedFix {
    tracing::debug!(?span, %replacement, "attaching a Tier A replace fix");
    EmittedFix {
        title,
        applicability: Applicability::Machine,
        edits: vec![EmittedEdit {
            start: span.0,
            end: span.1,
            replacement,
        }],
    }
}

/// The CSS that stands for `color` re-expressed over the custom property `token`.
pub fn color_replacement(color: Color, token: &str) -> String {
    if color.is_opaque() {
        return format!("var({token})");
    }
    let percent = format!("{:.2}", color.a * 100.0);
    let percent = percent.trim_end_matches('0').trim_end_matches('.');
    format!("color-mix(in srgb, var({token}) {percent}%, transparent)")
}
