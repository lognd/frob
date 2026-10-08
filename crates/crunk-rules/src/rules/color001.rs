//! COLOR001: a colour literal that is not a palette colour (port of `crunk/rules/_color.py`
//! `color001`; design: `crunk.md` section 6, D115).
//!
//! The literals come from [`crunk_ingest`]: the colours of every declaration and custom property
//! of the CSS sheets and of the JSX style props and `className` sites, each with its own byte span.
//! The palette maths is `crunk-values` through [`crate::color::Palette`]. The rule runs once per
//! declared mode ([`crate::mode`]); the spec declares one palette today.
//!
//! Divergences from the Python rule: the finding is located at the colour token, not at the
//! declaration line; the fix payload is not attached here (the autofix ticket owns it), so
//! `fix = Manual`, and the message says when the nearest entry is beyond `color_tolerance`; an
//! unparseable literal (`inherit`, `transparent`, a `calc()`) is not a colour and is skipped by
//! ingest; waivers are the pipeline's exceptions, not an in-rule lookup.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM
// frob:ticket 01M48R0538K77RY0W3W6AN9XJY

use crunk_spec::naming::color_token;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::color::{Palette, off_palette_message};
use crate::host::{CrunkHost, missing_inputs};
use crate::mode::modes;
use crate::sheets::{examined_sheets, is_tokens_sheet, site_path};

/// A colour literal that is not a palette colour (and not a translucent variant of an opaque one).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COLOR001",
    slug = "color-off-palette",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 2,
    since = "0.532.0",
)]
pub struct Color001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Color001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        for mode in modes(spec) {
            let palette = Palette::new(mode.palette(spec));
            for sheet in styles.sheets.iter().filter(|s| !is_tokens_sheet(s)) {
                let path = site_path(spec, &sheet.path);
                for located in sheet.declarations.iter().flat_map(|d| &d.colors) {
                    if palette.conforms(located.color) {
                        continue;
                    }
                    let Some((name, distance)) = palette.nearest(located.color) else {
                        tracing::debug!(%path, "COLOR001: the palette is empty, nothing to suggest");
                        continue;
                    };
                    let token = color_token(&spec.tokens, name);
                    let near = distance <= spec.lint.color_tolerance;
                    tracing::debug!(%path, mode = mode.name, %token, distance, "COLOR001: off-palette literal");
                    out.fire_in(
                        &path,
                        located.span.0,
                        format!(
                            "{}{}",
                            off_palette_message(located.color, &token, distance, near),
                            mode.suffix()
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Color001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
