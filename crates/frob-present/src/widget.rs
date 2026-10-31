//! Pure rendering of the progress bar, throbber and elapsed text (no I/O).

use std::time::Duration;

use crate::palette::Glyphs;

/// Below this many columns the bar collapses to `stage n/m`.
const NARROW: u16 = 40;

/// Format a duration as `123ms` under a second, else `1.23s`.
pub fn fmt_elapsed(d: Duration) -> String {
    if d < Duration::from_secs(1) {
        format!("{}ms", d.as_millis())
    } else {
        format!("{:.2}s", d.as_secs_f64())
    }
}

/// Render a bar of `cells` cells filled for `done` of `total`, e.g. `[###---]`.
pub fn bar(glyphs: &Glyphs, cells: usize, done: u64, total: u64) -> String {
    let filled = if total == 0 {
        0
    } else {
        let scaled = u128::from(done.min(total)) * cells as u128 * 2 / u128::from(total);
        usize::try_from(scaled.div_ceil(2)).map_or(cells, |f| f.min(cells))
    };
    let mut out = String::with_capacity(cells + 2);
    out.push('[');
    out.extend(std::iter::repeat_n(glyphs.fill, filled));
    out.extend(std::iter::repeat_n(glyphs.empty, cells - filled));
    out.push(']');
    out
}

/// Render the live status line for a stage, never wider than `width - 1` columns.
///
/// A known `total` gives a bar; otherwise the throbber frame `tick` is shown. Under 40 columns
/// it collapses to `stage n/m` (or `stage` alone with no total).
pub fn status_line(
    glyphs: &Glyphs,
    width: u16,
    stage: &str,
    done: u64,
    total: Option<u64>,
    tick: usize,
) -> String {
    let max = usize::from(width.saturating_sub(1));
    let line = match total {
        _ if width < NARROW => match total {
            Some(t) => format!("{stage} {done}/{t}"),
            None => stage.to_owned(),
        },
        Some(t) => {
            let counts = format!(" {done}/{t}");
            let fixed = stage.chars().count() + counts.chars().count() + 4;
            let cells = max.saturating_sub(fixed).min(30);
            format!("{stage} {}{counts}", bar(glyphs, cells, done, t))
        }
        None => {
            let frame = glyphs.spinner[tick % glyphs.spinner.len()];
            format!("{frame} {stage}")
        }
    };
    line.chars().take(max).collect()
}
