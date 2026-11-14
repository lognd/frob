//! CSS Color 4 parsing and `deltaE_OK`. The vectors in `VECTORS` come from an independent reference
//! implementation (numpy: primaries derived matrices, Bradford adaptation computed from the
//! white points, Ottosson's published `OKLab` matrices) running the CSS Color 4 gamut mapping.

// frob:ticket 01M48NF9E0WTVHPA4XQ3200J6N
#![allow(clippy::unreadable_literal)] // WHY: full-precision reference floats copied verbatim.

use crunk_values::{Color, ColorError};

/// Tolerance for the parse vectors (the gamut search stops at a 1e-4 chroma step).
const TOL: f64 = 2e-4;

/// `(css text, [r, g, b])` expected sRGB after gamut mapping.
const VECTORS: &[(&str, [f64; 3])] = &[
    ("oklch(0.628 0.2577 29.23)", [1.0, 0.0, 0.000261036483]),
    ("oklch(0.5 0.1 200)", [0.0, 0.453038864069, 0.476873917597]),
    (
        "oklch(0.7 0.15 145)",
        [0.35581302864, 0.7146830929, 0.378470645074],
    ),
    (
        "oklch(0.9 0.05 90)",
        [0.920723820415, 0.867684490794, 0.725484257621],
    ),
    ("oklch(0.4 0.3 300)", [0.378033397184, 0.0, 0.688053183766]),
    ("oklch(0.8 0.4 150)", [0.0, 0.906491146459, 0.351987732332]),
    (
        "oklch(0.2 0.02 10)",
        [0.118305578038, 0.071689025507, 0.078044444381],
    ),
    ("oklch(100% 0 0)", [0.999999969434, 1.0, 1.0]),
    ("oklch(0 0 0)", [0.0, 0.0, 0.0]),
    (
        "oklch(62.8% 0.2577 29.23deg / 50%)",
        [1.0, 0.0, 0.000261036483],
    ),
    (
        "oklab(0.5 0 0)",
        [0.388572846195, 0.38857286269, 0.388572907337],
    ),
    (
        "oklab(0.6 0.1 -0.1)",
        [0.62547111104, 0.388668857359, 0.727472799063],
    ),
    (
        "oklab(0.75 -0.12 0.08)",
        [0.420008143478, 0.776511742642, 0.458733468727],
    ),
    ("oklab(0.3 0.05 0.2)", [0.268843510594, 0.149069329888, 0.0]),
    (
        "lab(50 0 0)",
        [0.466326609284, 0.466326609284, 0.466326609284],
    ),
    (
        "lab(29.2345 39.3825 20.0664)",
        [0.49063371575, 0.138670787936, 0.15900566966],
    ),
    (
        "lab(70 -40 50)",
        [0.445764788546, 0.742607288619, 0.281360989192],
    ),
    (
        "lab(90 10 -5)",
        [0.950813219305, 0.863164663158, 0.926664619057],
    ),
    ("lab(60 80 70)", [1.0, 0.257580484623, 0.161597844748]),
    (
        "lch(50 50 40)",
        [0.72718025338, 0.350677575846, 0.26103384848],
    ),
    (
        "lch(80 30 200)",
        [0.478446540847, 0.838952142498, 0.848476863365],
    ),
    (
        "lch(40 60 300)",
        [0.403712877612, 0.305484975134, 0.708460585206],
    ),
    (
        "color(display-p3 0.2 0.6 0.4)",
        [0.0, 0.610174338036, 0.381434508256],
    ),
    (
        "color(display-p3 1 0 0)",
        [1.0, 0.044569534675, 0.045931665756],
    ),
    (
        "color(display-p3 0.9 0.8 0.1)",
        [0.918156952152, 0.795885715654, 0.0],
    ),
    ("color(srgb 0.2 0.4 0.6)", [0.2, 0.4, 0.6]),
    (
        "color(srgb-linear 0.2 0.4 0.6)",
        [0.484529204482, 0.665185084631, 0.797737733031],
    ),
    (
        "color(xyz-d65 0.3 0.4 0.5)",
        [0.3624135294, 0.722291319069, 0.710842225593],
    ),
    (
        "color(xyz-d50 0.3 0.4 0.5)",
        [0.242578020656, 0.728454899893, 0.816796373842],
    ),
    ("hwb(0 0% 0%)", [1.0, 0.0, 0.0]),
    ("hwb(120 20% 10%)", [0.2, 0.9, 0.2]),
    ("hwb(240 50% 30%)", [0.5, 0.5, 0.7]),
    ("hwb(200 60% 60%)", [0.5, 0.5, 0.5]),
];

fn c(text: &str) -> Color {
    Color::parse(text).unwrap_or_else(|e| panic!("{text}: {e}"))
}

#[test]
fn css_color_4_functions_parse_to_the_reference_values() {
    for (text, want) in VECTORS {
        let got = c(text);
        let ok = (got.r - want[0]).abs() < TOL
            && (got.g - want[1]).abs() < TOL
            && (got.b - want[2]).abs() < TOL;
        assert!(ok, "{text}: got {got:?}, want {want:?}");
    }
}

#[test]
fn spec_anchors_hold() {
    assert_eq!(c("oklch(0 0 0)").to_hex(), "#000000");
    assert_eq!(c("oklch(100% 0 0)").to_hex(), "#ffffff");
    assert_eq!(c("oklab(0.5 0 0)").to_hex(), "#636363");
    assert_eq!(c("lab(50% 0 0)").to_hex(), "#777777");
    assert_eq!(c("color(srgb 1 0 0)").to_hex(), "#ff0000");
    assert_eq!(c("hwb(0 0% 0%)").to_hex(), "#ff0000");
    assert_eq!(c("oklch(0.628 0.2577 29.23)").to_hex(), "#ff0000");
}

#[test]
fn forms_none_percent_angle_units_and_alpha() {
    assert_eq!(c("oklch(none none none)"), c("oklch(0 0 0)"));
    assert_eq!(
        c("OKLCH(62.8% 64.425% 29.23deg)"),
        c("oklch(0.628 0.2577 29.23)")
    );
    let turn = c("oklch(0.7 0.1 0.25turn)");
    let deg = c("oklch(0.7 0.1 90)");
    assert!((turn.r - deg.r).abs() < 1e-9 && (turn.g - deg.g).abs() < 1e-9);
    let rad = c("oklch(0.7 0.1 1.5707963267948966rad)");
    assert!((rad.b - deg.b).abs() < 1e-9);
    assert!((c("lab(50% 0 0 / 25%)").a - 0.25).abs() < 1e-12);
    assert!((c("oklab(0.5 0 0 / 0.5)").a - 0.5).abs() < 1e-12);
}

#[test]
fn out_of_gamut_colors_map_into_srgb() {
    for text in [
        "oklch(0.8 0.4 150)",
        "color(display-p3 0 1 0)",
        "lab(60 100 90)",
    ] {
        let got = c(text);
        for ch in [got.r, got.g, got.b] {
            assert!((0.0..=1.0).contains(&ch), "{text}: {got:?}");
        }
    }
    // Chroma is reduced, hue and lightness are kept: the mapped color is near its target.
    let mapped = c("oklch(0.8 0.4 150)").to_oklab();
    assert!((mapped[0] - 0.8).abs() < 0.03, "{mapped:?}");
}

#[test]
fn malformed_and_unsupported_forms_are_typed_errors() {
    for bad in [
        "oklch(0.5 0.1)",
        "oklch(0.5 0.1 20 30)",
        "oklch(0.5, 0.1, 20)",
        "oklch(from red l c h)",
        "oklab(a b c)",
        "lch(50 20 40grad2)",
        "color(unknown-space 1 1 1)",
        "color(srgb 1 1)",
        "hwb(0 10 20)",
        "lab(50 0 0",
    ] {
        assert!(
            matches!(
                Color::parse(bad),
                Err(ColorError::BadColorFunction(_) | ColorError::Unrecognized(_))
            ),
            "{bad}: {:?}",
            Color::parse(bad)
        );
    }
}

#[test]
fn delta_e_ok_is_the_euclidean_oklab_distance() {
    let (black, white) = (c("#000"), c("#fff"));
    assert!((black.delta_e_ok(white) - 1.0).abs() < 1e-6);
    assert!(black.delta_e_ok(black).abs() < 1e-12);
    let (a, b) = (c("#336699"), c("#993366"));
    assert!((a.delta_e_ok(b) - b.delta_e_ok(a)).abs() < 1e-15);
}

#[test]
fn delta_e_ok_ranks_a_known_redmean_misordering_correctly() {
    let target = Color::new(8.0 / 255.0, 252.0 / 255.0, 164.0 / 255.0, 1.0);
    let a = Color::new(40.0 / 255.0, 172.0 / 255.0, 169.0 / 255.0, 1.0);
    let b = Color::new(169.0 / 255.0, 229.0 / 255.0, 12.0 / 255.0, 1.0);
    // Redmean prefers `a`; the perceptual metric prefers `b`.
    assert!(target.distance(a) < target.distance(b));
    assert!(target.delta_e_ok(b) < target.delta_e_ok(a));
}

#[test]
fn contrast_is_still_wcag_2_luminance() {
    let (black, white) = (c("#000"), c("#fff"));
    assert!((black.contrast_ratio(white) - 21.0).abs() < 1e-9);
    // A colour written in Lab contrasts like its hex form (within byte rounding).
    let by_hex = c("#777777");
    let by_lab = c("lab(50% 0 0)");
    assert!((by_hex.contrast_ratio(white) - by_lab.contrast_ratio(white)).abs() < 0.01);
    assert!((c("#767676").contrast_ratio(white) - 4.542_224_859_788_96).abs() < 1e-6);
}
