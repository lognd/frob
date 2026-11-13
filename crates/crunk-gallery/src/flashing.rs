//! FLASH001: the T2 flashing-frames check (WCAG 2.3.1, three flashes or below threshold).
//!
//! Pure frame-sequence logic over [`Image`]: given timestamped frames it finds the luminance
//! (general) and saturated-red transitions between consecutive frames and fires when more than
//! three flashes land in any one second. Capturing the frames is the renderer's job, not this
//! module's.
//!
//! # Model
//!
//! - A pixel flashes between two frames when its relative luminance changes by at least
//!   [`FlashConfig::delta`] (10 percent of the maximum) and the darker of the two is below
//!   [`FlashConfig::dark_max`] (0.8). A red flash is a change of at least 20 in the WCAG red
//!   measure `(R - G - B) * 320` where either frame is saturated red.
//! - A frame pair is a transition only when the flashing pixels cover at least
//!   [`FlashConfig::area_fraction`] (25 percent) of the frame; smaller flashes are ignored. The
//!   frame is taken to be the 10-degree field.
//! - A flash is a pair of opposing transitions, so only transitions that alternate in direction
//!   count. More than `max_flashes` flashes (three) whose transitions fit within
//!   [`FlashConfig::window_ms`] fires the rule, naming the frame range.
//!
//! # Edge cases
//!
//! - Fewer than two frames cannot be judged: [`Verdict::Unresolved`].
//! - Timestamps must strictly increase ([`FlashError::NonMonotonic`]); frames must share one size
//!   ([`FlashError::SizeMismatch`]).
//! - A spec that turns FLASH001 off yields [`Verdict::Pass`].

// frob:ticket 01M5XCXVQXDWR7J92VZDBK0E3V

use std::sync::OnceLock;

use crunk_spec::{DesignSpec, Severity};

use crate::cells::Cell;
use crate::rules::Finding;
use crate::visual::Image;

/// The rule id for a frame sequence that flashes more than three times in a second.
pub const FLASH001: &str = "FLASH001";

/// Minimum change in the WCAG red measure (already scaled by 320) for a red flash.
const RED_DELTA: f64 = 20.0;

/// One captured frame and the time it was shown.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Frame {
    /// Milliseconds since the start of the capture.
    pub t_ms: u64,
    /// The frame pixels.
    pub image: Image,
}

/// Why a frame sequence could not be judged.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum FlashError {
    /// A timestamp is not after the one before it.
    #[error("frame {index} at {t_ms} ms is not after the previous frame at {prev_ms} ms")]
    NonMonotonic {
        /// Index of the offending frame.
        index: usize,
        /// Its timestamp.
        t_ms: u64,
        /// The previous frame's timestamp.
        prev_ms: u64,
    },
    /// A frame differs in size from the first.
    #[error(
        "frame {index} is {width}x{height} but the first frame is {first_width}x{first_height}"
    )]
    SizeMismatch {
        /// Index of the offending frame.
        index: usize,
        /// Its width.
        width: u32,
        /// Its height.
        height: u32,
        /// The first frame's width.
        first_width: u32,
        /// The first frame's height.
        first_height: u32,
    },
}

/// The thresholds of the check; [`Default`] is WCAG 2.3.1.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FlashConfig {
    /// Smallest luminance change (0.0 to 1.0 of the maximum) that counts.
    pub delta: f64,
    /// The darker frame must have relative luminance below this.
    pub dark_max: f64,
    /// Share of the field (0.0 to 1.0) that must flash for a transition to count.
    pub area_fraction: f64,
    /// The span, in milliseconds, within which flashes are counted.
    pub window_ms: u64,
    /// Flashes allowed in the window; more than this fires.
    pub max_flashes: usize,
}

impl Default for FlashConfig {
    /// WCAG 2.3.1: 10 percent change, dark frame under 0.8, 25 percent of the field, 3 per second.
    fn default() -> Self {
        Self {
            delta: 0.1,
            dark_max: 0.8,
            area_fraction: 0.25,
            window_ms: 1000,
            max_flashes: 3,
        }
    }
}

/// The result of checking one frame sequence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    /// No window has more flashes than allowed.
    Pass,
    /// The sequence cannot be judged; the string says why.
    Unresolved(String),
    /// Too many flashes; the finding names the frame range.
    Fail(Finding),
}

/// Which flash definition a transition scan uses.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Kind {
    General,
    Red,
}

impl Kind {
    fn name(self) -> &'static str {
        match self {
            Self::General => "general",
            Self::Red => "red",
        }
    }
}

/// A frame pair whose flashing pixels cover enough of the field.
#[derive(Debug, Clone, Copy)]
struct Transition {
    from: usize,
    to: usize,
    t_ms: u64,
    rising: bool,
}

/// A run of flashes found in one window.
struct Burst {
    kind: Kind,
    first: usize,
    last: usize,
    flashes: usize,
}

/// sRGB channel to linear light, via a 256-entry table.
fn linear(c: u8) -> f64 {
    static LUT: OnceLock<[f64; 256]> = OnceLock::new();
    let lut = LUT.get_or_init(|| {
        let mut t = [0.0; 256];
        for (i, slot) in t.iter_mut().enumerate() {
            #[allow(clippy::cast_precision_loss, reason = "i is at most 255")]
            let s = i as f64 / 255.0;
            *slot = if s <= 0.04045 {
                s / 12.92
            } else {
                ((s + 0.055) / 1.055).powf(2.4)
            };
        }
        t
    });
    lut[usize::from(c)]
}

/// RGB over white as 0..=255 bytes.
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    reason = "the value is clamped to 0..=255 first"
)]
fn rgb(px: &[u8]) -> [u8; 3] {
    let a = f64::from(px[3]) / 255.0;
    let mix = |c: u8| {
        (255.0 + (f64::from(c) - 255.0) * a)
            .round()
            .clamp(0.0, 255.0) as u8
    };
    [mix(px[0]), mix(px[1]), mix(px[2])]
}

/// WCAG relative luminance of an RGBA pixel composited over white.
fn luminance(px: &[u8]) -> f64 {
    let [r, g, b] = rgb(px);
    0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
}

/// The WCAG red measure `(R - G - B) * 320` on a 0..1 scale, floored at zero.
fn red_measure(c: [u8; 3]) -> f64 {
    let n = |v: u8| f64::from(v) / 255.0;
    ((n(c[0]) - n(c[1]) - n(c[2])) * 320.0).max(0.0)
}

/// True when red makes up at least 80 percent of the pixel.
fn saturated_red(c: [u8; 3]) -> bool {
    let sum: u32 = c.iter().map(|&v| u32::from(v)).sum();
    sum > 0 && f64::from(c[0]) / f64::from(sum) >= 0.8
}

/// The signed change of one pixel pair when it flashes under `kind`, else `None`.
fn pixel_change(kind: Kind, a: &[u8], b: &[u8], cfg: &FlashConfig) -> Option<f64> {
    match kind {
        Kind::General => {
            let (la, lb) = (luminance(a), luminance(b));
            let flashes = (lb - la).abs() >= cfg.delta && la.min(lb) < cfg.dark_max;
            flashes.then_some(lb - la)
        }
        Kind::Red => {
            let (ca, cb) = (rgb(a), rgb(b));
            let d = red_measure(cb) - red_measure(ca);
            (d.abs() >= RED_DELTA && (saturated_red(ca) || saturated_red(cb))).then_some(d)
        }
    }
}

/// The transition between two frames under `kind`, if enough of the field flashes.
fn transition(
    kind: Kind,
    a: &Frame,
    b: &Frame,
    index: usize,
    cfg: &FlashConfig,
) -> Option<Transition> {
    let (pa, _) = a.image.pixels().as_chunks::<4>();
    let (pb, _) = b.image.pixels().as_chunks::<4>();
    let (mut count, mut sum) = (0_u64, 0.0_f64);
    for (x, y) in pa.iter().zip(pb) {
        if let Some(d) = pixel_change(kind, x, y, cfg) {
            count += 1;
            sum += d;
        }
    }
    let total = u64::from(a.image.width()) * u64::from(a.image.height());
    #[allow(
        clippy::cast_precision_loss,
        reason = "pixel counts are far below 2^52"
    )]
    let share = count as f64 / total as f64;
    (count > 0 && share >= cfg.area_fraction).then_some(Transition {
        from: index - 1,
        to: index,
        t_ms: b.t_ms,
        rising: sum > 0.0,
    })
}

/// Keep only transitions that reverse the direction of the one before (one flash = an opposing pair).
fn alternating(all: Vec<Transition>) -> Vec<Transition> {
    let mut out: Vec<Transition> = Vec::new();
    for t in all {
        if out.last().is_none_or(|p| p.rising != t.rising) {
            out.push(t);
        }
    }
    out
}

/// The first window of `cfg.window_ms` holding more than `cfg.max_flashes` flashes, if any.
fn find_burst(kind: Kind, ts: &[Transition], cfg: &FlashConfig) -> Option<Burst> {
    let mut start = 0;
    for end in 0..ts.len() {
        while ts[end].t_ms - ts[start].t_ms >= cfg.window_ms {
            start += 1;
        }
        let transitions = end - start + 1;
        if transitions > cfg.max_flashes * 2 {
            return Some(Burst {
                kind,
                first: ts[start].from,
                last: ts[end].to,
                flashes: transitions.div_ceil(2),
            });
        }
    }
    None
}

/// Scan every consecutive pair for `kind` and report a burst, if any.
fn scan(kind: Kind, frames: &[Frame], cfg: &FlashConfig) -> Option<Burst> {
    let all = frames
        .windows(2)
        .enumerate()
        .filter_map(|(i, w)| transition(kind, &w[0], &w[1], i + 1, cfg))
        .collect();
    let ts = alternating(all);
    tracing::debug!(
        kind = kind.name(),
        transitions = ts.len(),
        "flash transitions found"
    );
    find_burst(kind, &ts, cfg)
}

/// Refuse out-of-order timestamps and mixed frame sizes.
fn validate(frames: &[Frame]) -> Result<(), FlashError> {
    let first = &frames[0].image;
    for (index, w) in frames.windows(2).enumerate() {
        if w[1].t_ms <= w[0].t_ms {
            return Err(FlashError::NonMonotonic {
                index: index + 1,
                t_ms: w[1].t_ms,
                prev_ms: w[0].t_ms,
            });
        }
        let img = &w[1].image;
        if (img.width(), img.height()) != (first.width(), first.height()) {
            return Err(FlashError::SizeMismatch {
                index: index + 1,
                width: img.width(),
                height: img.height(),
                first_width: first.width(),
                first_height: first.height(),
            });
        }
    }
    Ok(())
}

/// FLASH001 for one cell's frame sequence: fires on more than `cfg.max_flashes` flashes in a window.
///
/// General flashes are checked first, then red; the first burst found is reported. A spec that
/// turns FLASH001 off passes.
///
/// # Errors
///
/// [`FlashError`] for non-increasing timestamps or frames of differing size.
pub fn check_flashing(
    spec: &DesignSpec,
    cell: &Cell,
    frames: &[Frame],
    cfg: &FlashConfig,
) -> Result<Verdict, FlashError> {
    let severity = spec.severity(FLASH001);
    if severity == Severity::Off {
        return Ok(Verdict::Pass);
    }
    if let Some(unresolved) = too_few_frames(frames) {
        return Ok(unresolved);
    }
    validate(frames)?;
    Ok(first_burst(frames, cfg).map_or(Verdict::Pass, |b| {
        Verdict::Fail(finding(severity, cell, &b, cfg))
    }))
}

/// `Unresolved` when fewer than two frames were captured, since flashing needs a pair.
fn too_few_frames(frames: &[Frame]) -> Option<Verdict> {
    (frames.len() < 2).then(|| {
        tracing::info!(frames = frames.len(), "too few frames to judge flashing");
        Verdict::Unresolved(format!(
            "{} frame(s) captured; flashing needs at least 2",
            frames.len()
        ))
    })
}

/// The first burst found, general flashes before red.
fn first_burst(frames: &[Frame], cfg: &FlashConfig) -> Option<Burst> {
    [Kind::General, Kind::Red]
        .into_iter()
        .find_map(|k| scan(k, frames, cfg))
}

/// The FLASH001 finding for a burst.
fn finding(severity: Severity, cell: &Cell, burst: &Burst, cfg: &FlashConfig) -> Finding {
    let label = format!("{}/{} on {}", cell.screen, cell.state, cell.platform);
    tracing::info!(rule = FLASH001, cell = %label, "flashing frames");
    Finding {
        rule: FLASH001,
        severity,
        message: format!(
            "{label} has {} {} flashes within {} ms (frames {} to {}); WCAG 2.3.1 allows at most {}",
            burst.flashes,
            burst.kind.name(),
            cfg.window_ms,
            burst.first,
            burst.last,
            cfg.max_flashes,
        ),
        screen: Some(cell.screen.clone()),
        state: Some(cell.state.clone()),
        platform: Some(cell.platform.clone()),
    }
}
