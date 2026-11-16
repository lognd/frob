//! Rendered contrast over images and gradients.

use crunk_gallery::rendered_contrast::{
    RenderedContrast, TextBox, check_rendered_contrast, contrast_ratio,
};
use crunk_gallery::visual::Image;

const WHITE: [u8; 3] = [255, 255, 255];
const EPS: f64 = 1e-9;

fn solid(w: u32, h: u32, px: [u8; 4]) -> Image {
    Image::new(w, h, px.repeat((w * h) as usize)).expect("image")
}

fn text(fg: [u8; 3], large: bool) -> TextBox {
    TextBox {
        id: "t".to_owned(),
        x: 2.0,
        y: 2.0,
        width: 16.0,
        height: 8.0,
        foreground: fg,
        large,
    }
}

fn only(r: RenderedContrast) -> Vec<crunk_gallery::rendered_contrast::BoxContrast> {
    match r {
        RenderedContrast::Checked(c) => c.results,
        RenderedContrast::Unresolved { reason } => panic!("unresolved: {reason}"),
    }
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn gradient_reports_the_worst_pair_with_its_region() {
    // Horizontal gradient from white to mid grey under grey text.
    let (w, h) = (20u32, 10u32);
    let mut px = Vec::new();
    for _ in 0..h {
        for x in 0..w {
            let v = u8::try_from(255 - x * 6).expect("byte");
            px.extend_from_slice(&[v, v, v, 255]);
        }
    }
    let img = Image::new(w, h, px).expect("image");
    let res = only(check_rendered_contrast(
        Some(&img),
        WHITE,
        &[text([119, 119, 119], false)],
    ));
    assert_eq!(res.len(), 1);
    assert!(
        res[0].region.x >= 12,
        "worst is at the dark end: {:?}",
        res[0].region
    );
    assert!(res[0].ratio < contrast_ratio([119, 119, 119], WHITE));
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn transparent_area_falls_back_to_the_surface() {
    let img = solid(20, 10, [0, 0, 0, 0]);
    let res = only(check_rendered_contrast(
        Some(&img),
        WHITE,
        &[text([0, 0, 0], false)],
    ));
    assert_eq!(res[0].background, WHITE);
    assert!((res[0].ratio - 21.0).abs() < EPS);
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn box_under_one_pixel_is_skipped_with_a_note() {
    let img = solid(20, 10, [255, 255, 255, 255]);
    let mut b = text([0, 0, 0], false);
    b.width = 0.5;
    match check_rendered_contrast(Some(&img), WHITE, &[b]) {
        RenderedContrast::Checked(c) => {
            assert!(c.results.is_empty());
            assert_eq!(c.notes.len(), 1);
        }
        RenderedContrast::Unresolved { .. } => panic!("should run"),
    }
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn semi_transparent_pixels_composite_over_the_surface() {
    let img = solid(20, 10, [0, 0, 0, 128]);
    let res = only(check_rendered_contrast(
        Some(&img),
        WHITE,
        &[text([0, 0, 0], false)],
    ));
    assert_eq!(res[0].background, [127, 127, 127]);
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn uniform_background_reports_exactly_the_declared_ratio() {
    let bg = [200, 200, 200];
    let fg = [30, 60, 90];
    let img = solid(20, 10, [200, 200, 200, 255]);
    let res = only(check_rendered_contrast(
        Some(&img),
        WHITE,
        &[text(fg, false)],
    ));
    assert!((res[0].ratio - contrast_ratio(fg, bg)).abs() < EPS);
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn large_text_uses_the_three_to_one_threshold() {
    // Grey 130 on white is about 3.7:1: fails normal, passes large.
    let img = solid(20, 10, [255, 255, 255, 255]);
    let fg = [130, 130, 130];
    let normal = only(check_rendered_contrast(
        Some(&img),
        WHITE,
        &[text(fg, false)],
    ));
    let large = only(check_rendered_contrast(
        Some(&img),
        WHITE,
        &[text(fg, true)],
    ));
    assert!(!normal[0].passes);
    assert!(large[0].passes);
}

// frob:ticket 01M5XCXVJBTE8064EAX8E4PP6F
// frob:tests crates/crunk-gallery/src/rendered_contrast.rs::check_rendered_contrast
#[test]
fn missing_png_is_unresolved() {
    let r = check_rendered_contrast(None, WHITE, &[text([0, 0, 0], false)]);
    assert!(matches!(r, RenderedContrast::Unresolved { .. }));
}
