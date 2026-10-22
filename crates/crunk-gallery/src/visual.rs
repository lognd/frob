//! VIS001: perceptual diff of a rendered build against its design scene.
//!
//! This is the pure half of the T2 visual check: it compares two RGBA8 buffers, applies the
//! thresholds, and builds the diff image buffer. Producing the buffers (a browser render of the
//! scene and of the build) and encoding the diff as a PNG are the renderer's job, not this
//! module's, so nothing here touches a browser or the file system.
//!
//! # Edge cases
//!
//! - An image with a zero width or height is refused ([`VisualError::Empty`]), as is a buffer
//!   whose length is not `width * height * 4` ([`VisualError::BadBuffer`]).
//! - Two images of different sizes are never compared pixel by pixel: [`compare`] returns
//!   [`VisualError::SizeMismatch`] and [`check_visual`] fires VIS001 for it, because a build that
//!   renders at another size has drifted from its design.
//! - Alpha is composited over white before comparing, so a fully transparent pixel equals a white
//!   one and the hidden colour under it does not count.
//! - A threshold of `0.0` is the strict setting: any difference at all counts. Thresholds that are
//!   NaN, infinite or outside `0.0..=1.0` are refused ([`VisualError::BadThreshold`]).
//! - Identical images always produce a ratio of exactly `0.0` and never fire.

// frob:ticket 01M4CXRXWTA9DG9DTV5R149H7C

use crunk_spec::{DesignSpec, Severity};
use serde::Serialize;

use crate::cells::Cell;
use crate::rules::Finding;

/// The rule id for a build that differs from its design beyond threshold.
pub const VIS001: &str = "VIS001";

/// Largest possible YIQ-weighted squared distance (black against white), used to normalise.
const MAX_DELTA: f64 = 35215.0;

/// Why a comparison could not be made, or a threshold or buffer is unusable.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum VisualError {
    /// The image has no pixels.
    #[error("image is empty ({width}x{height})")]
    Empty {
        /// Declared width.
        width: u32,
        /// Declared height.
        height: u32,
    },
    /// The buffer length is not `width * height * 4`.
    #[error("buffer holds {actual} bytes, but {width}x{height} RGBA needs {expected}")]
    BadBuffer {
        /// Declared width.
        width: u32,
        /// Declared height.
        height: u32,
        /// Bytes required.
        expected: usize,
        /// Bytes supplied.
        actual: usize,
    },
    /// The two images differ in size.
    #[error("design is {design_width}x{design_height} but build is {build_width}x{build_height}")]
    SizeMismatch {
        /// Design width.
        design_width: u32,
        /// Design height.
        design_height: u32,
        /// Build width.
        build_width: u32,
        /// Build height.
        build_height: u32,
    },
    /// A threshold is NaN, infinite or outside `0.0..=1.0`.
    #[error("{name} threshold {value} is not a finite number in 0.0..=1.0")]
    BadThreshold {
        /// Which threshold.
        name: &'static str,
        /// The offending value.
        value: f64,
    },
}

/// An RGBA8 image: row-major, four bytes per pixel, non-zero in both dimensions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Image {
    width: u32,
    height: u32,
    pixels: Vec<u8>,
}

impl Image {
    /// Wrap `pixels` (RGBA8, row-major) as a `width` by `height` image, validating the length.
    ///
    /// # Errors
    ///
    /// [`VisualError::Empty`] for a zero dimension, [`VisualError::BadBuffer`] for a wrong length.
    pub fn new(width: u32, height: u32, pixels: Vec<u8>) -> Result<Self, VisualError> {
        if width == 0 || height == 0 {
            return Err(VisualError::Empty { width, height });
        }
        let expected =
            usize::try_from(u128::from(width) * u128::from(height) * 4).unwrap_or(usize::MAX);
        if pixels.len() != expected {
            return Err(VisualError::BadBuffer {
                width,
                height,
                expected,
                actual: pixels.len(),
            });
        }
        Ok(Self {
            width,
            height,
            pixels,
        })
    }

    /// Width in pixels.
    pub fn width(&self) -> u32 {
        self.width
    }

    /// Height in pixels.
    pub fn height(&self) -> u32 {
        self.height
    }

    /// The RGBA8 bytes, row-major.
    pub fn pixels(&self) -> &[u8] {
        &self.pixels
    }
}

/// The two thresholds that decide whether a build has drifted from its design.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct Thresholds {
    /// Perceptual distance (0.0 identical, 1.0 black against white) above which a pixel differs.
    pub per_pixel: f64,
    /// Share of differing pixels (0.0 to 1.0) above which the image as a whole fails.
    pub max_ratio: f64,
}

impl Thresholds {
    /// Validated thresholds; each must be finite and within `0.0..=1.0`.
    ///
    /// # Errors
    ///
    /// [`VisualError::BadThreshold`] naming the first value that is NaN, infinite or out of range.
    pub fn new(per_pixel: f64, max_ratio: f64) -> Result<Self, VisualError> {
        for (name, value) in [("per-pixel", per_pixel), ("max-ratio", max_ratio)] {
            if !(0.0..=1.0).contains(&value) {
                return Err(VisualError::BadThreshold { name, value });
            }
        }
        Ok(Self {
            per_pixel,
            max_ratio,
        })
    }
}

impl Default for Thresholds {
    /// A tolerant default: 10 percent perceptual distance per pixel, 1 percent of pixels overall.
    fn default() -> Self {
        Self {
            per_pixel: 0.1,
            max_ratio: 0.01,
        }
    }
}

/// The outcome of comparing a build with its design.
#[derive(Debug, Clone, PartialEq)]
pub struct VisualDiff {
    /// Pixels compared.
    pub total: u64,
    /// Pixels whose perceptual distance exceeded the per-pixel threshold.
    pub differing: u64,
    /// `differing / total`.
    pub ratio: f64,
    /// The diff image: differing pixels in opaque red over a faded copy of the design.
    pub diff: Image,
}

impl VisualDiff {
    /// True when the differing share is strictly above `thresholds.max_ratio`.
    pub fn exceeds(&self, thresholds: &Thresholds) -> bool {
        self.ratio > thresholds.max_ratio
    }
}

/// RGB over white by alpha, as 0..=255 floats.
fn over_white(px: &[u8]) -> [f64; 3] {
    let a = f64::from(px[3]) / 255.0;
    let mix = |c: u8| 255.0 + (f64::from(c) - 255.0) * a;
    [mix(px[0]), mix(px[1]), mix(px[2])]
}

/// A channel faded to a quarter of its contrast against white, for the diff image backdrop.
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    reason = "the value is clamped to 0..=255 first"
)]
fn fade(c: f64) -> u8 {
    (255.0 - (255.0 - c) * 0.25).round().clamp(0.0, 255.0) as u8
}

/// Perceptual distance between two RGBA pixels, in 0.0..=1.0 (YIQ weighted, alpha over white).
fn distance(a: &[u8], b: &[u8]) -> f64 {
    let (a, b) = (over_white(a), over_white(b));
    let yiq = |[r, g, b]: [f64; 3]| {
        (
            0.298_95 * r + 0.587_03 * g + 0.114_02 * b,
            0.595_77 * r - 0.274_57 * g - 0.321_20 * b,
            0.211_47 * r - 0.522_15 * g + 0.310_68 * b,
        )
    };
    let (ya, ia, qa) = yiq(a);
    let (yb, ib, qb) = yiq(b);
    let (dy, di, dq) = (ya - yb, ia - ib, qa - qb);
    ((0.5053 * dy * dy + 0.299 * di * di + 0.1957 * dq * dq) / MAX_DELTA).clamp(0.0, 1.0)
}

/// Compare `build` against `design`; pixels differ when their distance exceeds `thresholds.per_pixel`.
///
/// A zero per-pixel threshold counts any non-zero distance. The images must be the same size.
///
/// # Errors
///
/// [`VisualError::SizeMismatch`] when the dimensions differ.
pub fn compare(
    design: &Image,
    build: &Image,
    thresholds: &Thresholds,
) -> Result<VisualDiff, VisualError> {
    if (design.width, design.height) != (build.width, build.height) {
        return Err(VisualError::SizeMismatch {
            design_width: design.width,
            design_height: design.height,
            build_width: build.width,
            build_height: build.height,
        });
    }
    let mut out = Vec::with_capacity(design.pixels.len());
    let mut differing = 0_u64;
    let (design_px, _) = design.pixels.as_chunks::<4>();
    let (build_px, _) = build.pixels.as_chunks::<4>();
    for (d, b) in design_px.iter().zip(build_px) {
        if distance(d, b) > thresholds.per_pixel {
            differing += 1;
            out.extend_from_slice(&[255, 0, 0, 255]);
        } else {
            let [r, g, bl] = over_white(d);
            out.extend_from_slice(&[fade(r), fade(g), fade(bl), 255]);
        }
    }
    let total = u64::from(design.width) * u64::from(design.height);
    #[allow(
        clippy::cast_precision_loss,
        reason = "pixel counts are far below 2^52"
    )]
    let ratio = differing as f64 / total as f64;
    tracing::debug!(total, differing, ratio, "visual comparison done");
    Ok(VisualDiff {
        total,
        differing,
        ratio,
        diff: Image {
            width: design.width,
            height: design.height,
            pixels: out,
        },
    })
}

/// VIS001 for one cell: fires when `build` differs from `design` beyond `thresholds`.
///
/// `diff_path` is where the caller will write the diff image; the message names it. A size
/// mismatch fires as well (there is no diff to draw, so the message says so). Returns `None` when
/// the build matches within threshold or the spec turns VIS001 off.
pub fn check_visual(
    spec: &DesignSpec,
    cell: &Cell,
    design: &Image,
    build: &Image,
    thresholds: &Thresholds,
    diff_path: &str,
) -> Option<Finding> {
    let severity = spec.severity(VIS001);
    if severity == Severity::Off {
        return None;
    }
    let label = format!("{}/{} on {}", cell.screen, cell.state, cell.platform);
    let message = match compare(design, build, thresholds) {
        Ok(diff) if diff.exceeds(thresholds) => format!(
            "{label} differs from its design: {} of {} pixels ({:.2} percent) exceed the {:.2} percent budget; see the diff image at {diff_path}",
            diff.differing,
            diff.total,
            diff.ratio * 100.0,
            thresholds.max_ratio * 100.0,
        ),
        Ok(_) => return None,
        Err(e @ VisualError::SizeMismatch { .. }) => {
            format!("{label} cannot match its design: {e}; no diff image was drawn")
        }
        Err(e) => format!("{label} could not be compared with its design: {e}"),
    };
    tracing::info!(rule = VIS001, cell = %label, "visual regression");
    Some(Finding {
        rule: VIS001,
        severity,
        message,
        screen: Some(cell.screen.clone()),
        state: Some(cell.state.clone()),
        platform: Some(cell.platform.clone()),
    })
}
