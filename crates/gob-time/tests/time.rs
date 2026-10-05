//! Behaviour of the one clock, one zone crate (docs/design/time.md, D93).

use std::path::{Path, PathBuf};

use gob_time::{Clock, Day, FixedClock, Shown, Stamp, SystemClock};

/// 2026-10-05T00:06:00Z: the minute ~AAZFNR5 went red, and 17:06 on the previous day at UTC-07:00.
fn boundary() -> Stamp {
    "2026-10-05T00:06:00Z".parse().expect("stamp")
}

// frob:tests crates/gob-time/src/stamp.rs::Stamp
#[test]
fn stamp_renders_utc_z_and_normalises_offsets() {
    assert_eq!(boundary().to_string(), "2026-10-05T00:06:00Z");
    let local: Stamp = "2026-10-04T17:06:00-07:00".parse().expect("stamp");
    assert_eq!(local, boundary());
    assert_eq!(local.to_string(), "2026-10-05T00:06:00Z");
    assert!("yesterday".parse::<Stamp>().is_err());
    let json = serde_json::to_string(&boundary()).expect("json");
    assert_eq!(json, "\"2026-10-05T00:06:00Z\"");
    assert_eq!(
        serde_json::from_str::<Stamp>(&json).expect("back"),
        boundary()
    );
}

// frob:tests crates/gob-time/src/stamp.rs::Stamp.to_system_time
#[test]
fn stamp_converts_to_system_time_on_both_sides_of_the_epoch() {
    let after = Stamp::from_unix(86_400).to_system_time();
    let before = Stamp::from_unix(-86_400).to_system_time();
    assert_eq!(
        after
            .duration_since(std::time::UNIX_EPOCH)
            .expect("after")
            .as_secs(),
        86_400
    );
    assert_eq!(
        std::time::UNIX_EPOCH
            .duration_since(before)
            .expect("before")
            .as_secs(),
        86_400
    );
}

// frob:tests crates/gob-time/src/day.rs::Day
#[test]
fn day_is_the_utc_day_whatever_offset_the_stamp_was_written_in() {
    assert_eq!(Day::of(boundary()).to_string(), "2026-10-05");
    let late: Stamp = "2026-10-04T23:59:59Z".parse().expect("stamp");
    assert_eq!(Day::of(late).to_string(), "2026-10-04");
    assert_eq!(Day::of(late.plus_seconds(1)).to_string(), "2026-10-05");
    let day: Day = "2026-10-05".parse().expect("day");
    assert_eq!(day.plus_days(-1).expect("shift").to_string(), "2026-10-04");
    assert!("2026-13-40".parse::<Day>().is_err());
}

// frob:tests crates/gob-time/src/clock.rs::FixedClock
#[test]
fn today_is_derived_from_the_same_snapshot_as_now() {
    let clock = FixedClock::new(boundary());
    assert_eq!(clock.now(), boundary());
    assert_eq!(clock.today(), Day::of(clock.now()));
    assert_eq!(clock.today().to_string(), "2026-10-05");
}

// frob:tests crates/gob-time/src/clock.rs::SystemClock.pin
#[test]
fn a_pinned_clock_gives_every_date_of_a_command_one_snapshot() {
    let pinned = SystemClock::pin();
    let (first_now, first_day) = (pinned.now(), pinned.today());
    std::thread::sleep(std::time::Duration::from_millis(1_100));
    assert_eq!(pinned.now(), first_now, "a pinned clock never advances");
    assert_eq!(pinned.today(), first_day);
    assert_eq!(first_day, Day::of(first_now));
}

// frob:tests crates/gob-time/src/shown.rs::Shown
#[test]
fn release_date_follows_the_utc_rule_not_the_local_zone() {
    // A release cut at 00:06 UTC while the local zone (UTC-07:00) is still on the previous day.
    let clock = FixedClock::new(boundary());
    assert_eq!(clock.today().to_string(), "2026-10-05");
    let shown = Shown::at_offset(clock.now(), -7 * 3600).to_string();
    assert_eq!(shown, "2026-10-04 17:06:00 -07:00");
    assert_ne!(&shown[..10], clock.today().to_string());
}

// frob:tests crates/gob-time/src/shown.rs::Shown.local
#[test]
fn local_display_renders_text_with_an_offset() {
    let text = Shown::local(boundary()).to_string();
    assert_eq!(text.len(), "2026-10-05 00:06:00 +00:00".len(), "{text}");
}

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_files(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

// frob:tests crates/gob-time/src/clock.rs::SystemClock
#[test]
fn clippy_confines_wall_clock_and_local_zone_reads_to_gob_time() {
    let root = workspace_root();
    let clippy = std::fs::read_to_string(root.join("clippy.toml")).expect("clippy.toml");
    let banned = [
        "std::time::SystemTime::now",
        "std::time::SystemTime::elapsed",
        "jiff::Timestamp::now",
        "jiff::Zoned::now",
        "jiff::tz::TimeZone::system",
        "jiff::tz::TimeZone::try_system",
    ];
    for path in banned {
        assert!(
            clippy.contains(&format!("path = \"{path}\"")),
            "clippy.toml must disallow {path}"
        );
    }
    assert!(
        !clippy.contains("path = \"std::time::Instant"),
        "Instant (elapsed time) stays allowed"
    );
    let manifest = std::fs::read_to_string(root.join("Cargo.toml")).expect("Cargo.toml");
    assert!(
        manifest.contains("disallowed_methods = \"deny\""),
        "the lint must be an error, not a warning"
    );
    // The lint cannot see a crate that is not compiled for this target: scan every source too.
    let needles = [
        "SystemTime::now(",
        "Timestamp::now(",
        "Zoned::now(",
        "TimeZone::system(",
        "TimeZone::try_system(",
    ];
    let mut files = Vec::new();
    rust_files(&root.join("crates"), &mut files);
    let own = Path::new(env!("CARGO_MANIFEST_DIR"));
    for file in files {
        if file.starts_with(own) {
            continue;
        }
        let text = std::fs::read_to_string(&file).expect("read");
        for needle in needles {
            assert!(
                !text.contains(needle),
                "{} reads the wall clock or local zone ({needle}); take a gob_time::Clock",
                file.display()
            );
        }
    }
    let wall = std::fs::read_to_string(own.join("src/wall.rs")).expect("wall.rs");
    assert_eq!(
        wall.matches("#![allow(").count(),
        1,
        "gob-time carries exactly one allow, with a reason"
    );
    assert!(wall.contains("reason ="));
}

// frob:tests crates/gob-time/src/stamp.rs::Stamp.precise
#[test]
fn frob_lock_ack_text_round_trips_byte_identically() {
    // acked_at values captured from the frob.lock of experimental before this migration.
    let fixture = include_str!("fixtures/lock_acked_at.txt");
    let mut seen = 0;
    for line in fixture.lines().filter(|l| !l.is_empty()) {
        let stamp: Stamp = line.parse().expect("ack stamp");
        assert_eq!(
            stamp.precise(),
            line,
            "ack text keeps its sub-second digits"
        );
        seen += 1;
    }
    assert!(seen >= 2, "fixture holds real acks");
}

// frob:tests crates/gob-time/src/stamp.rs::Stamp.seconds
#[test]
fn whole_second_text_drops_the_fraction_and_seconds_truncates() {
    let s: Stamp = "2026-10-03T23:11:28.931959538Z".parse().expect("stamp");
    assert_eq!(s.to_string(), "2026-10-03T23:11:28Z");
    assert_eq!(s.seconds().precise(), "2026-10-03T23:11:28Z");
    assert!(s > s.seconds());
}
