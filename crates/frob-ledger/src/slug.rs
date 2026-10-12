//! The ticket slug function (navigation.md 2.1): a title as a file name stem.
// frob:ticket 01M3ZX82FBZHFCX6P69NRTFCH7

/// Longest slug, in characters, before it is cut on a word boundary.
pub const SLUG_MAX_LEN: usize = 60;

/// Map one non-ASCII letter to its ASCII spelling, or `None` when it has none.
fn transliterate(c: char) -> Option<&'static str> {
    Some(match c {
        'À'..='Å' | 'à'..='å' | 'Ā'..='ą' => "a",
        'Ç' | 'ç' | 'Ć'..='č' => "c",
        'Ď'..='đ' | 'Ð' | 'ð' => "d",
        'È'..='Ë' | 'è'..='ë' | 'Ē'..='ě' => "e",
        'Ĝ'..='ģ' => "g",
        'Ì'..='Ï' | 'ì'..='ï' | 'Ĩ'..='ı' => "i",
        'Ķ' | 'ķ' => "k",
        'Ĺ'..='ł' => "l",
        'Ñ' | 'ñ' | 'Ń'..='ň' => "n",
        'Ò'..='Ö' | 'Ø' | 'ò'..='ö' | 'ø' | 'Ō'..='ő' => "o",
        'Ŕ'..='ř' => "r",
        'Ś'..='š' => "s",
        'Ţ'..='ŧ' => "t",
        'Ù'..='Ü' | 'ù'..='ü' | 'Ũ'..='ų' => "u",
        'Ý' | 'ý' | 'ÿ' | 'Ŷ'..='Ÿ' => "y",
        'Ź'..='ž' => "z",
        'ß' => "ss",
        'Æ' | 'æ' => "ae",
        'Œ' | 'œ' => "oe",
        'Þ' | 'þ' => "th",
        _ => return None,
    })
}

/// The file-name slug of `title`; an empty result becomes `handle` without its `~`.
///
/// The title is transliterated to ASCII and lowercased, every run of other
/// characters becomes one `-`, the ends are trimmed, and the result is cut
/// at [`SLUG_MAX_LEN`] characters on a word boundary.
pub fn slugify(title: &str, handle: &str) -> String {
    let mut out = String::with_capacity(title.len());
    let mut pending_dash = false;
    let push = |out: &mut String, text: &str| {
        for c in text.chars() {
            out.push(c.to_ascii_lowercase());
        }
    };
    for c in title.chars() {
        let mapped = if c.is_ascii_alphanumeric() {
            None
        } else {
            transliterate(c)
        };
        if c.is_ascii_alphanumeric() || mapped.is_some() {
            if pending_dash && !out.is_empty() {
                out.push('-');
            }
            pending_dash = false;
            match mapped {
                Some(text) => push(&mut out, text),
                None => out.push(c.to_ascii_lowercase()),
            }
        } else {
            pending_dash = true;
        }
    }
    let slug = cut_on_word(&out, SLUG_MAX_LEN);
    if slug.is_empty() {
        handle.trim_start_matches('~').to_owned()
    } else {
        slug.to_owned()
    }
}

/// Cut an all-ASCII dashed `slug` to at most `max` characters at a dash.
fn cut_on_word(slug: &str, max: usize) -> &str {
    if slug.len() <= max {
        return slug;
    }
    // A dash right after the first `max` characters ends a whole word.
    let head = &slug[..max];
    if slug.as_bytes()[max] == b'-' {
        return head;
    }
    match head.rfind('-') {
        Some(at) => &head[..at],
        // One word longer than the limit: nothing to break on, cut hard.
        None => head,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M3ZX82FBZHFCX6P69NRTFCH7
    #[test]
    fn punctuation_title_slugs_to_dashed_words() {
        assert_eq!(
            slugify("Parser rewrite: faster, safer (v2)!", "~NRTFCH7"),
            "parser-rewrite-faster-safer-v2"
        );
    }

    // frob:ticket 01M3ZX82FBZHFCX6P69NRTFCH7
    #[test]
    fn symbol_only_title_yields_handle_without_tilde() {
        assert_eq!(slugify("!?*** ---", "~NRTFCH7"), "NRTFCH7");
        assert_eq!(slugify("", "NRTFCH7"), "NRTFCH7");
    }

    // frob:ticket 01M3ZX82FBZHFCX6P69NRTFCH7
    #[test]
    fn long_title_is_cut_on_a_word_boundary_within_sixty() {
        let title = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike";
        assert!(title.len() >= 76);
        let slug = slugify(title, "H");
        assert!(slug.len() <= SLUG_MAX_LEN);
        assert_eq!(
            slug,
            "alpha-bravo-charlie-delta-echo-foxtrot-golf-hotel-india"
        );
        // Words of exactly 90 characters total, with a break at the limit.
        let ninety = format!("{} {}", "a".repeat(59), "b".repeat(30));
        assert_eq!(slugify(&ninety, "H"), "a".repeat(59));
        let exact = format!("{} {}", "a".repeat(60), "b".repeat(29));
        assert_eq!(slugify(&exact, "H"), "a".repeat(60));
    }

    // frob:ticket 01M3ZX82FBZHFCX6P69NRTFCH7
    #[test]
    fn accents_are_transliterated_and_one_huge_word_is_cut_hard() {
        assert_eq!(
            slugify("Caf\u{e9} \u{dc}ber  na\u{ef}ve", "H"),
            "cafe-uber-naive"
        );
        assert_eq!(slugify(&"x".repeat(90), "H"), "x".repeat(60));
    }
}
