//! The CSS number grammar shared by the color and length parsers.

/// Byte length of the leading `[-+]?(\d+\.\d+|\d+\.|\.\d+|\d+)` in `text`, if any.
pub(crate) fn number_prefix(text: &str) -> Option<usize> {
    let bytes = text.as_bytes();
    let mut idx = usize::from(matches!(bytes.first(), Some(b'+' | b'-')));
    let int_start = idx;
    while bytes.get(idx).is_some_and(u8::is_ascii_digit) {
        idx += 1;
    }
    let int_digits = idx - int_start;
    let mut frac_digits = 0;
    if bytes.get(idx) == Some(&b'.') {
        idx += 1;
        let frac_start = idx;
        while bytes.get(idx).is_some_and(u8::is_ascii_digit) {
            idx += 1;
        }
        frac_digits = idx - frac_start;
    }
    (int_digits + frac_digits > 0).then_some(idx)
}

/// Parses `text` as exactly one CSS number (the whole string), or `None`.
pub(crate) fn parse_number(text: &str) -> Option<f64> {
    if number_prefix(text)? != text.len() {
        return None;
    }
    text.parse().ok()
}

/// Splits `text` into a number and the remaining suffix, or `None` if it has no number prefix.
pub(crate) fn split_number(text: &str) -> Option<(f64, &str)> {
    let end = number_prefix(text)?;
    let value = text[..end].parse().ok()?;
    Some((value, &text[end..]))
}
