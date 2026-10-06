//! Character reference decoding for HTML text and attribute values.

// frob:ticket 01M47QKT10CG0RSF784EEYTQ0J

/// The named references decoded (the ones that matter for attribute values and text queries).
const NAMED: [(&str, char); 7] = [
    ("amp", '&'),
    ("lt", '<'),
    ("gt", '>'),
    ("quot", '"'),
    ("apos", '\''),
    ("nbsp", '\u{a0}'),
    ("copy", '\u{a9}'),
];

/// `s` with numeric and the common named character references decoded; unknown references are kept as written.
pub(crate) fn decode(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(i) = rest.find('&') {
        out.push_str(&rest[..i]);
        rest = &rest[i..];
        if let Some((c, len)) = reference(rest) {
            out.push(c);
            rest = &rest[len..];
        } else {
            out.push('&');
            rest = &rest[1..];
        }
    }
    out.push_str(rest);
    out
}

/// The character and byte length of the reference at the start of `s` (which starts with `&`).
fn reference(s: &str) -> Option<(char, usize)> {
    let body_end = s[1..].find(';').filter(|&e| e <= 10)?;
    let body = &s[1..=body_end];
    let c = match body.strip_prefix('#') {
        Some(num) => {
            let code = match num.strip_prefix(['x', 'X']) {
                Some(hex) => u32::from_str_radix(hex, 16).ok()?,
                None => num.parse().ok()?,
            };
            char::from_u32(code)?
        }
        None => NAMED.iter().find(|(n, _)| *n == body)?.1,
    };
    Some((c, body_end + 2))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-symbols/src/html/entities.rs::decode
    #[test]
    fn references_decode_and_unknowns_stay() {
        assert_eq!(decode("a &amp; b &lt;c&gt; &#65;&#x42;"), "a & b <c> AB");
        assert_eq!(decode("&bogus; & x &"), "&bogus; & x &");
        assert_eq!(decode("plain"), "plain");
    }
}
