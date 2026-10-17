//! Text helpers shared by the v3 and v4 readers: comment masking, lines, waiver comments.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

/// A `crunk:waive` comment found in a config or CSS entry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct LineWaiver {
    pub line: u32,
    pub rule: String,
    pub reason: Option<String>,
}

/// `src` with comments blanked to spaces (newlines kept, so offsets and lines are stable).
/// `line_comments` also blanks `//` comments (JS); strings are left intact.
pub(crate) fn mask_comments(src: &str, line_comments: bool) -> String {
    let b = src.as_bytes();
    let mut out = b.to_vec();
    let mut i = 0;
    while i < b.len() {
        match b[i] {
            q @ (b'"' | b'\'' | b'`') => {
                i += 1;
                while i < b.len() && b[i] != q {
                    i += if b[i] == b'\\' { 2 } else { 1 };
                }
                i += 1;
            }
            b'/' if b.get(i + 1) == Some(&b'*') => {
                let end = src[i + 2..].find("*/").map_or(b.len(), |p| i + 2 + p + 2);
                blank(&mut out, i, end.min(b.len()));
                i = end;
            }
            b'/' if line_comments && b.get(i + 1) == Some(&b'/') => {
                let end = src[i..].find('\n').map_or(b.len(), |p| i + p);
                blank(&mut out, i, end);
                i = end;
            }
            _ => i += 1,
        }
    }
    String::from_utf8(out).unwrap_or_else(|_| src.to_owned())
}

fn blank(out: &mut [u8], from: usize, to: usize) {
    let to = to.min(out.len());
    for byte in &mut out[from..to] {
        if *byte != b'\n' {
            *byte = b' ';
        }
    }
}

/// 1-based line of byte `offset`.
#[allow(clippy::naive_bytecount)] // single short scan; not worth a bytecount dependency
pub(crate) fn line_of(src: &str, offset: usize) -> u32 {
    let end = offset.min(src.len());
    1 + u32::try_from(
        src.as_bytes()[..end]
            .iter()
            .filter(|&&c| c == b'\n')
            .count(),
    )
    .unwrap_or(u32::MAX - 1)
}

/// Every `crunk:waive RULE [reason=...]` comment in `src`.
pub(crate) fn waivers(src: &str) -> Vec<LineWaiver> {
    let mut out = Vec::new();
    for (idx, text) in src.lines().enumerate() {
        let Some(at) = text.find("crunk:waive") else {
            continue;
        };
        let rest = text[at + "crunk:waive".len()..]
            .trim()
            .trim_end_matches("*/")
            .trim();
        let mut parts = rest.splitn(2, char::is_whitespace);
        let rule = parts.next().unwrap_or_default().to_owned();
        if rule.is_empty() {
            continue;
        }
        let reason = parts
            .next()
            .and_then(|r| r.trim().strip_prefix("reason="))
            .map(|r| r.trim().trim_matches('"').to_owned());
        out.push(LineWaiver {
            line: u32::try_from(idx + 1).unwrap_or(u32::MAX),
            rule,
            reason,
        });
    }
    out
}

/// The waiver for `rule` on `line` or the line above it.
pub(crate) fn waiver_for<'a>(
    all: &'a [LineWaiver],
    rule: &str,
    line: u32,
) -> Option<&'a LineWaiver> {
    all.iter()
        .find(|w| w.rule == rule && (w.line == line || w.line + 1 == line))
}
