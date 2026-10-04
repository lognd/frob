//! The one text escaper: control, bidi and invisible characters become visible `\u{..}` escapes (security.md D82, 2.10).
//!
//! Text mode renders strings that other people wrote (messages, paths, tracker text). Left raw, an ESC sequence
//! can repaint the terminal and a bidi override can reorder source ("Trojan Source"). JSON never goes through
//! here: it keeps the exact string.

use std::borrow::Cow;
use std::fmt::Write as _;

/// True for characters that render as nothing or reorder neighbours: bidi controls, zero-width and format characters.
fn is_invisible(c: char) -> bool {
    matches!(u32::from(c),
        0x00AD          // soft hyphen
        | 0x034F        // combining grapheme joiner
        | 0x061C        // arabic letter mark
        | 0x115F | 0x1160 | 0x3164 | 0xFFA0 // hangul fillers
        | 0x180E        // mongolian vowel separator
        | 0x200B..=0x200F // zero-width space/joiners, LRM, RLM
        | 0x2028..=0x202E // line/paragraph separators, bidi embeddings and overrides
        | 0x2060..=0x206F // word joiner, invisible operators, bidi isolates, deprecated formats
        | 0xFEFF        // BOM / zero-width no-break space
        | 0xFFF9..=0xFFFC // interlinear annotation, object replacement
        | 0xE0000..=0xE007F // tag characters
    )
}

/// True when `c` must not reach a terminal raw: any C0 or C1 control (newline excepted by callers), DEL, or an invisible.
pub fn is_dangerous(c: char) -> bool {
    c.is_control() || is_invisible(c)
}

fn push_escape(out: &mut String, c: char) {
    let _ = write!(out, "\\u{{{:x}}}", u32::from(c));
}

/// Escape every control, bidi and invisible character of `text` except `\n`, which is kept so multi-line text stays readable.
///
/// Borrows when nothing needs escaping. Tab is escaped too: it is a control character and can fake alignment.
pub fn escape_text(text: &str) -> Cow<'_, str> {
    if !text.chars().any(|c| c != '\n' && is_dangerous(c)) {
        return Cow::Borrowed(text);
    }
    let mut out = String::with_capacity(text.len() + 16);
    for c in text.chars() {
        if c != '\n' && is_dangerous(c) {
            push_escape(&mut out, c);
        } else {
            out.push(c);
        }
    }
    tracing::debug!("dangerous characters escaped in rendered text");
    Cow::Owned(out)
}

/// Escape `text` for one line of output: newline becomes `\n`; controls and every non-ASCII character become `\u{..}`.
pub fn escape_line(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '\n' => out.push_str("\\n"),
            c if c.is_ascii() && !c.is_ascii_control() => out.push(c),
            c => push_escape(&mut out, c),
        }
    }
    out
}

/// Escape every non-ASCII character of `text` as `\u{..}`, keeping ASCII (newlines, tabs and ESC included) as is.
///
/// For ledger files, which must be ASCII; it is not a terminal-safety escape, use [`escape_text`] for that.
pub fn escape_non_ascii(text: &str) -> String {
    if text.is_ascii() {
        return text.to_owned();
    }
    let mut out = String::with_capacity(text.len() + 16);
    for c in text.chars() {
        if c.is_ascii() {
            out.push(c);
        } else {
            push_escape(&mut out, c);
        }
    }
    tracing::debug!("non-ASCII captured text escaped");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    fn raw_dangerous(s: &str) -> bool {
        s.chars().any(|c| c != '\n' && is_dangerous(c))
    }

    #[test]
    fn ansi_injection_is_escaped() {
        assert_eq!(
            escape_text("a\u{1b}[31mred\u{1b}[0m"),
            "a\\u{1b}[31mred\\u{1b}[0m"
        );
        assert_eq!(escape_text("\u{1b}]0;title\u{7}"), "\\u{1b}]0;title\\u{7}");
        assert_eq!(escape_text("\u{9b}31m\u{85}"), "\\u{9b}31m\\u{85}");
    }

    #[test]
    fn trojan_source_bidi_is_escaped() {
        for c in [
            '\u{202a}', '\u{202b}', '\u{202c}', '\u{202d}', '\u{202e}', '\u{2066}', '\u{2067}',
            '\u{2068}', '\u{2069}', '\u{200e}', '\u{200f}', '\u{061c}',
        ] {
            let src = format!("if x {c}{{ /* admin {c}*/");
            let out = escape_text(&src);
            assert!(!out.contains(c), "{c:?} survived");
            assert!(out.contains(&format!("\\u{{{:x}}}", u32::from(c))));
        }
    }

    #[test]
    fn zero_width_and_invisibles_are_escaped() {
        for c in [
            '\u{200b}',
            '\u{200c}',
            '\u{200d}',
            '\u{2060}',
            '\u{feff}',
            '\u{ad}',
            '\u{3164}',
            '\u{e0041}',
            '\u{2028}',
        ] {
            assert!(
                !escape_text(&format!("a{c}b")).contains(c),
                "{c:?} survived"
            );
        }
    }

    #[test]
    fn c0_c1_del_escaped_newline_kept() {
        let all: String = (0u32..=0x9f).filter_map(char::from_u32).collect();
        let out = escape_text(&all);
        assert!(!raw_dangerous(&out));
        assert!(out.contains('\n'));
        assert!(
            out.contains("\\u{7f}")
                && out.contains("\\u{0}")
                && out.contains("\\u{9f}")
                && out.contains("\\u{9}")
        );
    }

    #[test]
    fn clean_text_is_borrowed_and_unicode_letters_survive() {
        assert!(matches!(
            escape_text("caf\u{e9} \u{4e2d}\nok"),
            Cow::Borrowed(_)
        ));
    }

    #[test]
    fn escape_non_ascii_keeps_layout_and_hides_the_rest() {
        assert_eq!(escape_non_ascii("a\n\tb"), "a\n\tb");
        assert_eq!(escape_non_ascii("\u{2500}x\u{e9}\n"), "\\u{2500}x\\u{e9}\n");
    }

    #[test]
    fn escape_line_hides_controls_and_non_ascii() {
        assert_eq!(escape_line("a\nb\u{1b}[31m"), "a\\nb\\u{1b}[31m");
        assert_eq!(escape_line("x\u{202e}y\u{e9}"), "x\\u{202e}y\\u{e9}");
        assert!(escape_line("\u{202e}\u{7}\u{85}").is_ascii());
    }

    proptest! {
        // frob:tests escape_text
        #[test]
        fn escaped_text_never_holds_a_raw_dangerous_char(s in any::<String>()) {
            let out = escape_text(&s);
            prop_assert!(!raw_dangerous(&out));
        }

        #[test]
        fn escaped_text_is_idempotent_free_of_controls_for_mixed_input(
            s in proptest::collection::vec(prop_oneof![
                0u32..0xa0, 0x200bu32..0x2070, Just(0xfeffu32), 0xe0000u32..0xe0080, 0x20u32..0x7f
            ], 0..64)
        ) {
            let s: String = s.into_iter().filter_map(char::from_u32).collect();
            let out = escape_text(&s);
            prop_assert!(!raw_dangerous(&out));
            prop_assert!(!out.contains(char::from(0x1b_u8)));
        }

        #[test]
        fn escaped_line_is_ascii_without_controls(s in any::<String>()) {
            let out = escape_line(&s);
            prop_assert!(out.is_ascii() && !out.chars().any(|c| c.is_ascii_control()));
        }
    }
}
