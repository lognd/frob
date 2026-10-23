//! Byte-range splices over an unchanged original text.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

/// Replace `len` bytes at `start` with `text`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Edit {
    /// First byte replaced.
    pub start: usize,
    /// Bytes replaced.
    pub len: usize,
    /// The new text.
    pub text: String,
}

/// Apply non-overlapping `edits` (overlaps keep the earliest) to `text`; the count applied and the result.
pub(crate) fn apply(text: &str, mut edits: Vec<Edit>) -> (usize, String) {
    edits.sort_by_key(|e| (e.start, e.len));
    let mut out = String::with_capacity(text.len());
    let mut at = 0;
    let mut applied = 0;
    for e in edits {
        if e.start < at || text[e.start..e.start + e.len] == e.text {
            continue;
        }
        out.push_str(&text[at..e.start]);
        out.push_str(&e.text);
        at = e.start + e.len;
        applied += 1;
    }
    out.push_str(&text[at..]);
    (applied, out)
}
