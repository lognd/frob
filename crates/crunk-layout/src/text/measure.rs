//! The parley-backed measurer and the taffy measure hook.

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C

use parley::{
    FontContext, FontFamily, Layout, LayoutContext, LineHeight, PositionedLayoutItem, StyleProperty,
};

use super::error::TextError;
use super::fonts::{self, FALLBACK_FONT};
use super::style::{AvailableWidth, MeasureNote, Measured, TextStyle};

/// Measures text over the bundled fonts; reuse one per solve for warm caches.
pub struct TextMeasurer {
    fc: FontContext,
    lc: LayoutContext<()>,
    blob_ids: Vec<(&'static str, u64)>,
}

impl Default for TextMeasurer {
    fn default() -> Self {
        Self::new()
    }
}

impl TextMeasurer {
    /// A measurer holding only the bundled fonts.
    pub fn new() -> Self {
        let (fc, blob_ids) = fonts::bundled_context();
        Self {
            fc,
            lc: LayoutContext::new(),
            blob_ids,
        }
    }

    /// Measures `text` under `style` and `avail`.
    ///
    /// # Errors
    /// [`TextError::FontNotBundled`] when the style's font is outside the bundle.
    pub fn measure(
        &mut self,
        text: &str,
        style: &TextStyle,
        avail: AvailableWidth,
    ) -> Result<Measured, TextError> {
        check_font(&style.font)?;
        if text.is_empty() {
            tracing::trace!("empty text measures zero");
            return Ok(Measured::empty());
        }
        let layout = self.shape(text, style, break_width(style, avail));
        let notes = self.notes(&layout, &style.font);
        let out = Measured {
            width: layout.width(),
            height: layout.height(),
            lines: u32::try_from(layout.len()).unwrap_or(u32::MAX),
            notes,
        };
        tracing::debug!(width = out.width, lines = out.lines, "measured text");
        Ok(out)
    }

    /// Shapes and breaks lines at `width` (`None` is unbounded).
    fn shape(&mut self, text: &str, style: &TextStyle, width: Option<f32>) -> Layout<()> {
        let stack = format!("'{}', '{}'", style.font, FALLBACK_FONT);
        let mut b = self.lc.ranged_builder(&mut self.fc, text, 1.0, true);
        b.push_default(StyleProperty::FontSize(style.size_px));
        b.push_default(StyleProperty::FontFamily(FontFamily::Source(stack.into())));
        b.push_default(StyleProperty::LetterSpacing(style.letter_spacing_px));
        b.push_default(StyleProperty::LineHeight(LineHeight::FontSizeRelative(
            style.line_height,
        )));
        let mut layout = b.build(text);
        layout.break_all_lines(width);
        layout
    }

    /// Notes for glyphs not drawn from the requested font.
    fn notes(&self, layout: &Layout<()>, font: &str) -> Vec<MeasureNote> {
        let primary = self.blob_ids.iter().find(|(n, _)| *n == font).map(|p| p.1);
        let missing = layout.lines().any(|line| {
            line.items().any(|item| match item {
                PositionedLayoutItem::GlyphRun(run) => {
                    run.run().font().data.id() != primary.unwrap_or(0)
                        || run.positioned_glyphs().any(|g| g.id == 0)
                }
                PositionedLayoutItem::InlineBox(_) => false,
            })
        });
        if missing {
            tracing::debug!(
                font,
                "missing_glyph: fell back to the bundled fallback font"
            );
            vec![MeasureNote::MissingGlyph]
        } else {
            Vec::new()
        }
    }
}

/// The line-break width for a style and constraint (`None` never wraps).
fn break_width(style: &TextStyle, avail: AvailableWidth) -> Option<f32> {
    match avail {
        AvailableWidth::MaxContent => None,
        _ if style.nowrap => None,
        AvailableWidth::MinContent => Some(0.0),
        AvailableWidth::Definite(w) => Some(w.max(0.0)),
    }
}

/// Rejects fonts outside the bundle.
fn check_font(font: &str) -> Result<(), TextError> {
    if fonts::is_bundled(font) {
        return Ok(());
    }
    let bundled = fonts::bundled_fonts().join(", ");
    tracing::warn!(font, "font not in the bundle");
    Err(TextError::FontNotBundled {
        font: font.to_string(),
        bundled,
    })
}

/// The taffy measure hook: known width wins, otherwise the available space decides.
///
/// # Errors
/// [`TextError::FontNotBundled`] when the style's font is outside the bundle.
pub fn measure_for_taffy(
    m: &mut TextMeasurer,
    text: &str,
    style: &TextStyle,
    known: taffy::Size<Option<f32>>,
    available: taffy::Size<taffy::AvailableSpace>,
) -> Result<taffy::Size<f32>, TextError> {
    let avail = known
        .width
        .map_or_else(|| available.width.into(), AvailableWidth::Definite);
    let r = m.measure(text, style, avail)?;
    Ok(taffy::Size {
        width: known.width.unwrap_or(r.width),
        height: known.height.unwrap_or(r.height),
    })
}
