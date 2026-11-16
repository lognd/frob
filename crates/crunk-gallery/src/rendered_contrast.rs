//! Rendered contrast: WCAG text/background contrast measured over a rendered PNG.
//!
//! The pure half of the T2 CONTRAST check: it takes the decoded [`Image`], the text boxes from the
//! boxes capture and the declared page surface, samples the pixels under each text box and reports
//! the worst-case pair. Nothing here touches a browser or the file system.
//!
//! # Edge cases
//!
//! - No image at all is [`RenderedContrast::Unresolved`], never a pass: the check did not run.
//! - A box narrower or shorter than one pixel (or wholly off the image) is skipped with a note.
//! - Pixels with alpha are composited over the declared surface, so a fully transparent area
//!   reads as the page background.
//! - A uniform background reports exactly the ratio of the declared foreground against it.
//! - Large text is held to 3:1, other text to 4.5:1.

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F

use serde::Serialize;
use tracing::{debug, info};

use crate::visual::Image;

/// Minimum ratio for normal-size text (WCAG AA).
pub const NORMAL_THRESHOLD: f64 = 4.5;

/// Minimum ratio for large text (WCAG AA).
pub const LARGE_THRESHOLD: f64 = 3.0;

/// Most samples taken along one axis of a box; larger boxes are sampled on a coarser grid.
const MAX_SAMPLES_PER_AXIS: u32 = 16;

/// An sRGB colour without alpha.
pub type Rgb = [u8; 3];

/// A text box to check, in page pixels, with its declared colour and size class.
#[derive(Debug, Clone, PartialEq)]
pub struct TextBox {
    /// The `data-id` of the text node.
    pub id: String,
    /// Left edge in image pixels.
    pub x: f64,
    /// Top edge in image pixels.
    pub y: f64,
    /// Width in pixels.
    pub width: f64,
    /// Height in pixels.
    pub height: f64,
    /// The declared text colour.
    pub foreground: Rgb,
    /// True for large text (3:1 threshold).
    pub large: bool,
}

/// A rectangle of image pixels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct PixelRegion {
    /// Left pixel column.
    pub x: u32,
    /// Top pixel row.
    pub y: u32,
    /// Width in pixels.
    pub width: u32,
    /// Height in pixels.
    pub height: u32,
}

/// The worst-case result for one text box.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct BoxContrast {
    /// The `data-id` of the text node.
    pub id: String,
    /// The lowest contrast ratio found.
    pub ratio: f64,
    /// The ratio this text must reach.
    pub threshold: f64,
    /// Whether `ratio` reaches `threshold`.
    pub passes: bool,
    /// The pixel region where the worst pair was found.
    pub region: PixelRegion,
    /// The background colour (composited over the surface) at that region.
    pub background: Rgb,
}

/// The measured outcome for every checkable box, plus a note per skipped one.
#[derive(Debug, Clone, PartialEq, Default, Serialize)]
pub struct ContrastReport {
    /// One entry per box that was sampled.
    pub results: Vec<BoxContrast>,
    /// One note per skipped box.
    pub notes: Vec<String>,
}

/// Whether the check ran.
#[derive(Debug, Clone, PartialEq)]
pub enum RenderedContrast {
    /// The check could not run (for example the PNG is missing).
    Unresolved {
        /// Why it did not run.
        reason: String,
    },
    /// The check ran.
    Checked(ContrastReport),
}

/// Linearise one 8-bit sRGB channel.
fn linear(channel: f64) -> f64 {
    let c = channel / 255.0;
    if c <= 0.039_28 {
        c / 12.92
    } else {
        ((c + 0.055) / 1.055).powf(2.4)
    }
}

/// WCAG relative luminance of an sRGB colour.
fn luminance(rgb: Rgb) -> f64 {
    0.2126 * linear(f64::from(rgb[0]))
        + 0.7152 * linear(f64::from(rgb[1]))
        + 0.0722 * linear(f64::from(rgb[2]))
}

/// The WCAG contrast ratio (1.0 to 21.0) between two colours.
pub fn contrast_ratio(a: Rgb, b: Rgb) -> f64 {
    let (la, lb) = (luminance(a), luminance(b));
    let (hi, lo) = if la >= lb { (la, lb) } else { (lb, la) };
    (hi + 0.05) / (lo + 0.05)
}

/// Composite an RGBA pixel over the opaque `surface`.
fn composite(px: &[u8], surface: Rgb) -> Rgb {
    let alpha = u32::from(px[3]);
    let mut out = [0u8; 3];
    for (i, slot) in out.iter_mut().enumerate() {
        let mixed = u32::from(px[i]) * alpha + u32::from(surface[i]) * (255 - alpha);
        // Rounded division by 255; the result is at most 255.
        *slot = u8::try_from((mixed + 127) / 255).unwrap_or(u8::MAX);
    }
    out
}

/// Clip a float box to whole image pixels; `None` when it covers less than one pixel.
fn clip(b: &TextBox, image: &Image) -> Option<PixelRegion> {
    if !(b.width >= 1.0 && b.height >= 1.0) {
        return None;
    }
    let max_x = f64::from(image.width());
    let max_y = f64::from(image.height());
    let x0 = b.x.floor().max(0.0);
    let y0 = b.y.floor().max(0.0);
    let x1 = (b.x + b.width).ceil().min(max_x);
    let y1 = (b.y + b.height).ceil().min(max_y);
    if x1 <= x0 || y1 <= y0 {
        return None;
    }
    // Values are within the image bounds, so the truncating casts are exact.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    Some(PixelRegion {
        x: x0 as u32,
        y: y0 as u32,
        width: (x1 - x0) as u32,
        height: (y1 - y0) as u32,
    })
}

/// Sample the pixels under one box and return its worst-case pair.
fn worst_pair(b: &TextBox, region: PixelRegion, image: &Image, surface: Rgb) -> BoxContrast {
    let step_x = region.width.div_ceil(MAX_SAMPLES_PER_AXIS).max(1);
    let step_y = region.height.div_ceil(MAX_SAMPLES_PER_AXIS).max(1);
    let stride = image.width() as usize * 4;
    let mut worst: Option<(f64, PixelRegion, Rgb)> = None;
    let mut y = region.y;
    while y < region.y + region.height {
        let mut x = region.x;
        while x < region.x + region.width {
            let at = y as usize * stride + x as usize * 4;
            let bg = composite(&image.pixels()[at..at + 4], surface);
            let ratio = contrast_ratio(b.foreground, bg);
            if worst.as_ref().is_none_or(|w| ratio < w.0) {
                let cell = PixelRegion {
                    x,
                    y,
                    width: step_x.min(region.x + region.width - x),
                    height: step_y.min(region.y + region.height - y),
                };
                worst = Some((ratio, cell, bg));
            }
            x += step_x;
        }
        y += step_y;
    }
    // The region is non-empty, so at least one sample was taken; the fallback is never used.
    let (ratio, cell, background) = worst.unwrap_or((21.0, region, surface));
    let threshold = if b.large {
        LARGE_THRESHOLD
    } else {
        NORMAL_THRESHOLD
    };
    debug!(id = %b.id, ratio, threshold, "sampled text box");
    BoxContrast {
        id: b.id.clone(),
        ratio,
        threshold,
        passes: ratio >= threshold,
        region: cell,
        background,
    }
}

/// Measure the worst-case contrast of every text box over the rendered `image`.
///
/// `image` is `None` when the PNG is missing, which yields [`RenderedContrast::Unresolved`].
pub fn check_rendered_contrast(
    image: Option<&Image>,
    surface: Rgb,
    boxes: &[TextBox],
) -> RenderedContrast {
    let Some(image) = image else {
        info!("rendered contrast unresolved: no PNG");
        return RenderedContrast::Unresolved {
            reason: "rendered PNG is missing".to_owned(),
        };
    };
    let mut report = ContrastReport::default();
    for b in boxes {
        if let Some(region) = clip(b, image) {
            report.results.push(worst_pair(b, region, image, surface));
        } else {
            info!(id = %b.id, "skipping text box under one pixel");
            report.notes.push(format!(
                "{}: text box is smaller than 1 px or off the image; skipped",
                b.id
            ));
        }
    }
    RenderedContrast::Checked(report)
}
