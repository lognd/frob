//! Port of the Python `tests/unit/test_values.py` plus reference-vector parity tests.

mod vectors;

use crunk_values::{Color, ColorError, Length, LengthError, LengthKind, NAMED_COLORS, named_color};

const EPS: f64 = 1e-9;

fn c(text: &str) -> Color {
    Color::parse(text).unwrap()
}

fn close(a: f64, b: f64) -> bool {
    (a - b).abs() <= EPS
}

#[test]
fn color_parse_matches_python_vectors() {
    for (text, want) in vectors::PARSE {
        match (Color::parse(text), want) {
            (Ok(got), Some([r, g, b, a])) => {
                let ok =
                    close(got.r, *r) && close(got.g, *g) && close(got.b, *b) && close(got.a, *a);
                assert!(ok, "{text:?}: got {got:?}, want {want:?}");
            }
            (Err(_), None) => {}
            (got, want) => panic!("{text:?}: got {got:?}, want {want:?}"),
        }
    }
}

#[test]
fn color_parse_hex_forms() {
    assert_eq!(c("#f00"), Color::new(1.0, 0.0, 0.0, 1.0));
    assert_eq!(c("#ff0000ff"), Color::new(1.0, 0.0, 0.0, 1.0));
    assert!(close(c("#00000080").a, 128.0 / 255.0));
}

#[test]
fn color_parse_typed_errors() {
    assert_eq!(Color::parse("  "), Err(ColorError::Empty));
    assert_eq!(
        Color::parse("#12345"),
        Err(ColorError::BadHexLength { len: 5 })
    );
    assert_eq!(Color::parse("rgb(1, 2)"), Err(ColorError::BadRgb));
    assert_eq!(Color::parse("hsl(1, 2, 3)"), Err(ColorError::BadHsl));
    for junk in [
        "var(--brand)",
        "currentcolor",
        "linear-gradient(red, blue)",
        "#ggg",
    ] {
        assert!(
            matches!(Color::parse(junk), Err(ColorError::Unrecognized(_))),
            "{junk}"
        );
    }
}

#[test]
fn named_colors_table_is_sorted_and_complete() {
    assert!(NAMED_COLORS.len() >= 149);
    assert!(NAMED_COLORS.windows(2).all(|w| w[0].0 < w[1].0));
    assert_eq!(named_color("rebeccapurple"), Some([102, 51, 153, 255]));
    assert_eq!(named_color("transparent"), Some([0, 0, 0, 0]));
    assert_eq!(named_color("nope"), None);
    for (name, rgba) in NAMED_COLORS {
        assert_eq!(named_color(name), Some(*rgba));
    }
}

#[test]
fn contrast_and_distance_match_python_vectors() {
    for (a, b, dist, ratio) in vectors::PAIRS {
        let (ca, cb) = (c(a), c(b));
        assert!(close(ca.distance(cb), *dist), "distance {a} {b}");
        assert!(close(ca.contrast_ratio(cb), *ratio), "contrast {a} {b}");
    }
}

#[test]
fn contrast_basics() {
    assert!(close(c("#000").contrast_ratio(c("#fff")), 21.0));
    let gray = Color::new(0.5, 0.5, 0.5, 1.0);
    assert!(close(gray.contrast_ratio(gray), 1.0));
    assert!(close(c("red").distance(c("red")), 0.0));
    assert!(c("red").distance(c("#f20d0d")) < c("red").distance(c("blue")));
}

#[test]
fn hex_output_matches_python_vectors() {
    for ([r, g, b, a], to_hex, rgb_hex) in vectors::HEX {
        let col = Color::new(*r, *g, *b, *a);
        assert_eq!(col.to_hex(), *to_hex);
        assert_eq!(col.rgb_hex(), *rgb_hex);
    }
    assert!(Color::new(0.0, 0.0, 0.0, 1.0).is_opaque());
    assert!(!Color::new(0.0, 0.0, 0.0, 0.999_999).is_opaque());
}

#[test]
fn length_parse_matches_python_vectors() {
    for (text, root, want) in vectors::LENGTHS {
        match (Length::parse(text, *root), want) {
            (Ok(got), Some((px, kind))) => {
                assert_eq!(got.kind.as_str(), *kind, "{text:?}");
                match (got.px, px) {
                    (Some(g), Some(w)) => assert!(close(g, *w), "{text:?}"),
                    (None, None) => {}
                    other => panic!("{text:?}: px {other:?}"),
                }
                assert_eq!(got.raw, *text);
            }
            (Err(_), None) => {}
            (got, want) => panic!("{text:?}: got {got:?}, want {want:?}"),
        }
    }
}

#[test]
fn length_kinds_and_typed_errors() {
    let rem = Length::parse("2rem", 20.0).unwrap();
    assert_eq!((rem.px, rem.kind), (Some(40.0), LengthKind::Rem));
    let em = Length::parse("2em", 16.0).unwrap();
    assert_eq!((em.px, em.kind), (None, LengthKind::Other));
    assert_eq!(Length::parse("", 16.0), Err(LengthError::Empty));
    assert!(matches!(
        Length::parse("5", 16.0),
        Err(LengthError::UnitlessNonzero(_))
    ));
    assert!(matches!(
        Length::parse("5foo", 16.0),
        Err(LengthError::UnknownUnit { unit, .. }) if unit == "foo"
    ));
    assert!(matches!(
        Length::parse("not-a-length", 16.0),
        Err(LengthError::Unrecognized(_))
    ));
}

#[test]
fn parse_never_panics_on_junk() {
    let alphabet: Vec<char> = "#%(),./- \t\n\u{ff}\u{0}0123456789abcdefrgbhslpxem+."
        .chars()
        .collect();
    let mut state: u64 = 20_260_902;
    for _ in 0..5000 {
        let mut s = String::new();
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1);
        for _ in 0..(state >> 59) as usize + (state >> 40) as usize % 24 {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1);
            s.push(alphabet[(state >> 33) as usize % alphabet.len()]);
        }
        let _ = Color::parse(&s);
        let _ = Length::parse(&s, 16.0);
    }
}
