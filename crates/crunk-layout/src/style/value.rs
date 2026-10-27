//! Value-text helpers: top-level splitting and CSS length parsing.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

/// Pixels per `rem` (the browser default root font size).
pub(crate) const REM_PX: f32 = 16.0;

/// A parsed CSS length-percentage-or-auto, before conversion to a taffy type.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Len {
    /// `auto`.
    Auto,
    /// Pixels.
    Px(f32),
    /// A fraction (`50%` is `0.5`).
    Pct(f32),
}

impl Len {
    /// Whether the value is below zero.
    pub(crate) fn is_negative(self) -> bool {
        matches!(self, Len::Px(v) | Len::Pct(v) if v < 0.0)
    }
}

/// Split on whitespace outside parentheses.
pub(crate) fn split_top(s: &str) -> Vec<&str> {
    split_on(s, char::is_whitespace)
}

/// Split on commas outside parentheses, trimming each part.
pub(crate) fn split_commas(s: &str) -> Vec<&str> {
    split_on(s, |c| c == ',')
}

fn split_on(s: &str, is_sep: impl Fn(char) -> bool) -> Vec<&str> {
    let mut out = Vec::new();
    let mut depth = 0usize;
    let mut start: Option<usize> = None;
    for (i, c) in s.char_indices() {
        if depth == 0 && is_sep(c) {
            if let Some(st) = start.take() {
                out.push(s[st..i].trim());
            }
            continue;
        }
        if start.is_none() {
            start = Some(i);
        }
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            _ => {}
        }
    }
    if let Some(st) = start {
        out.push(s[st..].trim());
    }
    out
}

/// A finite float from `s`.
pub(crate) fn parse_num(s: &str) -> Option<f32> {
    s.parse::<f32>().ok().filter(|v| v.is_finite())
}

/// Parse `auto`, `0`, `<n>px`, `<n>rem` or `<n>%`.
pub(crate) fn parse_len(tok: &str) -> Result<Len, String> {
    if tok == "auto" {
        return Ok(Len::Auto);
    }
    if let Some(n) = tok.strip_suffix("px") {
        return parse_num(n)
            .map(Len::Px)
            .ok_or_else(|| format!("`{tok}` is not a finite length"));
    }
    if let Some(n) = tok.strip_suffix("rem") {
        return parse_num(n)
            .map(|v| Len::Px(v * REM_PX))
            .ok_or_else(|| format!("`{tok}` is not a finite length"));
    }
    if let Some(n) = tok.strip_suffix('%') {
        return parse_num(n)
            .map(|v| Len::Pct(v / 100.0))
            .ok_or_else(|| format!("`{tok}` is not a finite percentage"));
    }
    match parse_num(tok) {
        Some(0.0) => Ok(Len::Px(0.0)),
        Some(_) => Err(format!("`{tok}` needs a unit (px, rem or %)")),
        None => Err(format!("`{tok}` is not a supported length")),
    }
}

/// Expand a 1-4 value box shorthand into `[top, right, bottom, left]`.
pub(crate) fn expand_box<T: Copy>(vals: &[T]) -> Option<[T; 4]> {
    match *vals {
        [a] => Some([a, a, a, a]),
        [v, h] => Some([v, h, v, h]),
        [t, h, b] => Some([t, h, b, h]),
        [t, r, b, l] => Some([t, r, b, l]),
        _ => None,
    }
}
