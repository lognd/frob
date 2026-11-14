//! VIS001: the perceptual design-versus-build comparison over RGBA buffers.

use crunk_gallery::cells::Cell;
use crunk_gallery::visual::{Image, Thresholds, VisualError, check_visual, compare};
use crunk_spec::{DesignSpec, Severity, parse_spec};
use std::path::Path;

fn spec() -> DesignSpec {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../crunk-spec/tests/fixtures/valid")
        .join("minimal_no_lint.toml");
    let text = std::fs::read_to_string(&path).expect("fixture");
    parse_spec(&text, &path, path.parent().expect("dir")).expect("fixture parses")
}

fn cell() -> Cell {
    Cell {
        screen: "landing".to_owned(),
        state: "default".to_owned(),
        platform: "chromium-desktop".to_owned(),
    }
}

fn solid(w: u32, h: u32, px: [u8; 4]) -> Image {
    let pixels = px.repeat((w * h) as usize);
    Image::new(w, h, pixels).expect("image")
}

/// A 10x10 image with the first `n` pixels set to `px`, the rest white.
fn with_first(n: usize, px: [u8; 4]) -> Image {
    let mut pixels = [255, 255, 255, 255].repeat(100);
    for i in 0..n {
        pixels[i * 4..i * 4 + 4].copy_from_slice(&px);
    }
    Image::new(10, 10, pixels).expect("image")
}

// frob:tests check_visual
#[test]
fn build_beyond_threshold_fires_vis001_with_the_diff_path() {
    let spec = spec();
    let design = solid(10, 10, [255, 255, 255, 255]);
    let build = with_first(10, [0, 0, 0, 255]);
    let t = Thresholds::new(0.1, 0.05).expect("thresholds");
    let f = check_visual(&spec, &cell(), &design, &build, &t, "out.diff.png").expect("fires");
    assert_eq!(f.rule, "VIS001");
    assert_eq!(f.severity, Severity::Error);
    assert!(f.message.contains("out.diff.png"), "{}", f.message);
    assert!(f.message.contains("10 of 100"), "{}", f.message);
    assert_eq!(f.screen.as_deref(), Some("landing"));
}

// frob:tests check_visual
#[test]
fn build_within_threshold_and_identical_images_stay_clean() {
    let spec = spec();
    let design = solid(10, 10, [255, 255, 255, 255]);
    let t = Thresholds::new(0.1, 0.05).expect("thresholds");
    let small = with_first(5, [0, 0, 0, 255]);
    assert!(check_visual(&spec, &cell(), &design, &small, &t, "d.png").is_none());
    let same = compare(&design, &design, &Thresholds::new(0.0, 0.0).expect("t")).expect("same");
    assert_eq!(same.differing, 0);
    assert!(same.ratio.abs() < f64::EPSILON);
}

// frob:tests compare
#[test]
fn zero_threshold_is_strict_and_slight_noise_below_per_pixel_is_ignored() {
    let design = solid(2, 2, [200, 200, 200, 255]);
    let off_by_one = solid(2, 2, [201, 200, 200, 255]);
    let strict = Thresholds::new(0.0, 0.0).expect("t");
    assert_eq!(
        compare(&design, &off_by_one, &strict).expect("c").differing,
        4
    );
    let loose = Thresholds::new(0.1, 0.0).expect("t");
    assert_eq!(
        compare(&design, &off_by_one, &loose).expect("c").differing,
        0
    );
}

// frob:tests compare
#[test]
fn transparent_pixels_compare_as_white_and_the_diff_marks_changes_red() {
    let t = Thresholds::new(0.0, 0.0).expect("t");
    let clear = solid(1, 1, [0, 0, 0, 0]);
    let white = solid(1, 1, [255, 255, 255, 255]);
    assert_eq!(compare(&clear, &white, &t).expect("c").differing, 0);
    let black = solid(1, 1, [0, 0, 0, 255]);
    let d = compare(&white, &black, &t).expect("c");
    assert_eq!(d.diff.pixels(), &[255, 0, 0, 255]);
    assert!((d.ratio - 1.0).abs() < f64::EPSILON);
}

// frob:tests compare
#[test]
fn size_mismatch_is_an_error_and_fires_without_a_diff_image() {
    let a = solid(2, 2, [0; 4]);
    let b = solid(3, 2, [0; 4]);
    let t = Thresholds::default();
    assert!(matches!(
        compare(&a, &b, &t),
        Err(VisualError::SizeMismatch { .. })
    ));
    let f = check_visual(&spec(), &cell(), &a, &b, &t, "d.png").expect("fires");
    assert!(
        f.message.contains("2x2") && f.message.contains("3x2"),
        "{}",
        f.message
    );
}

// frob:tests new
#[test]
fn empty_images_bad_buffers_and_nan_thresholds_are_refused() {
    assert!(matches!(
        Image::new(0, 4, vec![]),
        Err(VisualError::Empty { .. })
    ));
    assert!(matches!(
        Image::new(u32::MAX, u32::MAX, vec![0; 4]),
        Err(VisualError::BadBuffer { .. })
    ));
    assert!(matches!(
        Image::new(1, 1, vec![0; 3]),
        Err(VisualError::BadBuffer { .. })
    ));
    for bad in [f64::NAN, f64::INFINITY, -0.1, 1.5] {
        assert!(matches!(
            Thresholds::new(bad, 0.0),
            Err(VisualError::BadThreshold { .. })
        ));
        assert!(matches!(
            Thresholds::new(0.0, bad),
            Err(VisualError::BadThreshold { .. })
        ));
    }
}

// frob:tests Image.width
// frob:tests Image.height
// frob:tests Image.pixels
#[test]
fn image_accessors_report_what_was_supplied() {
    let img = solid(3, 2, [1, 2, 3, 4]);
    assert_eq!((img.width(), img.height()), (3, 2));
    assert_eq!(img.pixels().len(), 24);
}
