//! Bundled-font text measurement (~6XH9D6C): determinism and the edge cases of the measure hook.

use crunk_layout::text::{AvailableWidth, MeasureNote, TextError, TextMeasurer, TextStyle};

const SENTENCE: &str = "The quick brown fox jumps over the lazy dog";

fn style() -> TextStyle {
    TextStyle::new("Lato", 16.0)
}

fn measure(text: &str, s: &TextStyle, a: AvailableWidth) -> crunk_layout::text::Measured {
    TextMeasurer::new()
        .measure(text, s, a)
        .expect("bundled font")
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_is_identical_across_100_runs() {
    let mut m = TextMeasurer::new();
    let first = m
        .measure(SENTENCE, &style(), AvailableWidth::Definite(120.0))
        .unwrap();
    for _ in 0..100 {
        let again = m
            .measure(SENTENCE, &style(), AvailableWidth::Definite(120.0))
            .unwrap();
        assert_eq!(again, first);
    }
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_empty_string_is_zero_width_and_lines() {
    let r = measure("", &style(), AvailableWidth::MaxContent);
    assert_eq!((r.width, r.lines), (0.0, 0));
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_long_word_overflows_on_one_line() {
    let r = measure(
        "Supercalifragilistic",
        &style(),
        AvailableWidth::Definite(20.0),
    );
    assert_eq!(r.lines, 1);
    assert!(r.width > 20.0);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_newlines_force_breaks() {
    let r = measure("a\nb\nc", &style(), AvailableWidth::MaxContent);
    assert_eq!(r.lines, 3);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_nowrap_never_wraps() {
    let mut s = style();
    s.nowrap = true;
    let r = measure(SENTENCE, &s, AvailableWidth::Definite(40.0));
    assert_eq!(r.lines, 1);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_wraps_at_a_definite_width() {
    let r = measure(SENTENCE, &style(), AvailableWidth::Definite(120.0));
    assert!(r.lines > 1 && r.width <= 120.0);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_missing_glyph_records_a_note() {
    let r = measure(
        "a \u{4e2d} b",
        &TextStyle::new("Lato", 16.0),
        AvailableWidth::MaxContent,
    );
    assert!(r.notes.contains(&MeasureNote::MissingGlyph));
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_plain_ascii_has_no_notes() {
    let r = measure(SENTENCE, &style(), AvailableWidth::MaxContent);
    assert!(r.notes.is_empty());
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_rtl_and_mixed_direction_do_not_panic() {
    let r = measure(
        "abc \u{5e9}\u{5dc}\u{5d5}\u{5dd} def",
        &style(),
        AvailableWidth::MaxContent,
    );
    assert!(r.width > 0.0);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_zero_width_equals_min_content() {
    let zero = measure(SENTENCE, &style(), AvailableWidth::Definite(0.0));
    let min = measure(SENTENCE, &style(), AvailableWidth::MinContent);
    assert_eq!(zero, min);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_min_content_is_the_longest_word_and_max_content_the_line() {
    let min = measure(SENTENCE, &style(), AvailableWidth::MinContent);
    let max = measure(SENTENCE, &style(), AvailableWidth::MaxContent);
    assert!(min.width < max.width && max.lines == 1 && min.lines == 9);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_letter_spacing_widens() {
    let mut s = style();
    let base = measure("abcdef", &s, AvailableWidth::MaxContent).width;
    s.letter_spacing_px = 2.0;
    let wide = measure("abcdef", &s, AvailableWidth::MaxContent).width;
    assert!((wide - base - 12.0).abs() < 0.01);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_line_height_scales_height() {
    let mut s = style();
    s.line_height = 2.0;
    let r = measure("abc", &s, AvailableWidth::MaxContent);
    assert!((r.height - 32.0).abs() < 0.01);
}

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C
#[test]
fn text_measure_unbundled_font_is_a_typed_error_naming_it() {
    let err = TextMeasurer::new()
        .measure(
            "x",
            &TextStyle::new("Comic Sans", 16.0),
            AvailableWidth::MaxContent,
        )
        .unwrap_err();
    assert!(matches!(&err, TextError::FontNotBundled { font, .. } if font == "Comic Sans"));
}
