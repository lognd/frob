//! FLASH001: the WCAG 2.3.1 flashing-frames check over frame sequences.

use crunk_gallery::cells::Cell;
use crunk_gallery::flashing::{FlashConfig, FlashError, Frame, Verdict, check_flashing};
use crunk_gallery::visual::Image;
use crunk_spec::{DesignSpec, parse_spec};
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

/// A 10x10 image with the first `n` pixels `px` and the rest `rest`.
fn split(n: usize, px: [u8; 4], rest: [u8; 4]) -> Image {
    let pixels = (0..100)
        .flat_map(|i| if i < n { px } else { rest })
        .collect();
    Image::new(10, 10, pixels).expect("image")
}

fn solid(px: [u8; 4]) -> Image {
    split(100, px, px)
}

/// `count` frames `step` ms apart, alternating `a` and `b`.
fn alternate(count: u64, step: u64, a: &Image, b: &Image) -> Vec<Frame> {
    (0..count)
        .map(|i| Frame {
            t_ms: i * step,
            image: if i % 2 == 0 { a.clone() } else { b.clone() },
        })
        .collect()
}

fn check(frames: &[Frame]) -> Result<Verdict, FlashError> {
    check_flashing(&spec(), &cell(), frames, &FlashConfig::default())
}

const BLACK: [u8; 4] = [0, 0, 0, 255];
const WHITE: [u8; 4] = [255, 255, 255, 255];

// frob:tests check_flashing
#[test]
fn four_flashes_in_a_second_fire_and_name_the_frames() {
    let frames = alternate(9, 100, &solid(WHITE), &solid(BLACK));
    let Ok(Verdict::Fail(f)) = check(&frames) else {
        panic!("expected a failing verdict");
    };
    assert_eq!(f.rule, "FLASH001");
    assert!(f.message.contains("frames 0 to 7"), "{}", f.message);
    assert!(f.message.contains("4 general flashes"), "{}", f.message);
}

// frob:tests check_flashing
#[test]
fn three_flashes_pass() {
    let frames = alternate(7, 100, &solid(WHITE), &solid(BLACK));
    assert_eq!(check(&frames), Ok(Verdict::Pass));
}

// frob:tests check_flashing
#[test]
fn flashes_spread_over_more_than_a_second_pass() {
    let frames = alternate(9, 300, &solid(WHITE), &solid(BLACK));
    assert_eq!(check(&frames), Ok(Verdict::Pass));
}

// frob:tests check_flashing
#[test]
fn red_flashes_fire_even_when_luminance_barely_moves() {
    let frames = alternate(
        9,
        100,
        &solid([255, 0, 0, 255]),
        &solid([128, 128, 128, 255]),
    );
    let Ok(Verdict::Fail(f)) = check(&frames) else {
        panic!("expected a failing verdict");
    };
    assert!(f.message.contains("red"), "{}", f.message);
}

// frob:tests check_flashing
#[test]
fn a_bright_dark_frame_is_not_a_flash() {
    let frames = alternate(
        9,
        100,
        &solid([255, 255, 255, 255]),
        &solid([240, 240, 240, 255]),
    );
    assert_eq!(check(&frames), Ok(Verdict::Pass));
}

// frob:tests check_flashing
#[test]
fn flashes_under_a_quarter_of_the_field_are_ignored() {
    let small = split(20, BLACK, WHITE);
    let frames = alternate(9, 100, &small, &solid(WHITE));
    assert_eq!(check(&frames), Ok(Verdict::Pass));
}

// frob:tests check_flashing
#[test]
fn a_quarter_of_the_field_counts() {
    let part = split(25, BLACK, WHITE);
    let frames = alternate(9, 100, &part, &solid(WHITE));
    assert!(matches!(check(&frames), Ok(Verdict::Fail(_))));
}

// frob:tests check_flashing
#[test]
fn fewer_than_two_frames_are_unresolved() {
    assert!(matches!(check(&[]), Ok(Verdict::Unresolved(_))));
    let one = alternate(1, 100, &solid(WHITE), &solid(BLACK));
    assert!(matches!(check(&one), Ok(Verdict::Unresolved(_))));
}

// frob:tests check_flashing
#[test]
fn non_monotonic_timestamps_are_a_typed_error() {
    let mut frames = alternate(4, 100, &solid(WHITE), &solid(BLACK));
    frames[2].t_ms = 50;
    assert_eq!(
        check(&frames),
        Err(FlashError::NonMonotonic {
            index: 2,
            t_ms: 50,
            prev_ms: 100
        })
    );
}

// frob:tests check_flashing
#[test]
fn mixed_frame_sizes_are_a_typed_error() {
    let mut frames = alternate(3, 100, &solid(WHITE), &solid(BLACK));
    frames[1].image = Image::new(1, 1, BLACK.to_vec()).expect("image");
    assert!(matches!(
        check(&frames),
        Err(FlashError::SizeMismatch { index: 1, .. })
    ));
}
