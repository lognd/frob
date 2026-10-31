//! Detection matrix and presenter output on buffers: `NO_COLOR`, piped, TTY, dumb, CI.

use std::io::Write;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use frob_present::{
    Capabilities, EnvSnapshot, Glyphs, Kind, Live, Outcome, Palette, Plain, Presenter,
    ProfileReport, Quiet, Role, StageId, StreamFacts, bar, build, fmt_elapsed, select, status_line,
};

#[derive(Clone, Default)]
struct Buf(Arc<Mutex<Vec<u8>>>);

impl Write for Buf {
    fn write(&mut self, b: &[u8]) -> std::io::Result<usize> {
        self.0.lock().unwrap().extend_from_slice(b);
        Ok(b.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

impl Buf {
    fn text(&self) -> String {
        String::from_utf8(self.0.lock().unwrap().clone()).unwrap()
    }
}

fn caps(env: &[(&str, &str)], out_tty: bool, err_tty: bool) -> Capabilities {
    Capabilities::detect(
        &EnvSnapshot::from_pairs(env.iter().copied()),
        StreamFacts {
            stdout_tty: out_tty,
            stderr_tty: err_tty,
            width: None,
        },
    )
}

fn run(p: &dyn Presenter) {
    let s = StageId::new("land.merge");
    p.stage_start(&s, Some(4)).unwrap();
    p.stage_progress(&s, 2).unwrap();
    p.line(Role::Warn, "careful").unwrap();
    p.stage_end(&s, Duration::from_millis(1500), Outcome::Ok)
        .unwrap();
    let mut r = ProfileReport::default();
    r.push(s, Duration::from_millis(1500), Outcome::Ok);
    p.finish(&r).unwrap();
}

#[test]
fn detect_tty_with_term_colors_and_is_interactive() {
    let c = caps(&[("TERM", "xterm-256color")], true, true);
    assert!(c.stdout.color && c.stderr.color && c.interactive);
}

#[test]
fn detect_no_color_disables_colour_but_keeps_interactive() {
    let c = caps(&[("TERM", "xterm"), ("NO_COLOR", "1")], true, true);
    assert!(!c.stdout.color && !c.stderr.color && c.interactive);
}

#[test]
fn detect_empty_no_color_is_ignored() {
    assert!(
        caps(&[("TERM", "xterm"), ("NO_COLOR", "")], true, true)
            .stdout
            .color
    );
}

#[test]
fn detect_piped_has_no_colour_and_no_redraw() {
    let c = caps(&[("TERM", "xterm")], false, false);
    assert!(!c.stdout.color && !c.stderr.color && !c.interactive);
}

#[test]
fn detect_streams_are_independent() {
    let c = caps(&[("TERM", "xterm")], false, true);
    assert!(!c.stdout.color && c.stderr.color && c.interactive);
    let c = caps(&[("TERM", "xterm")], true, false);
    assert!(c.stdout.color && !c.stderr.color && !c.interactive);
}

#[test]
fn detect_dumb_terminal_is_plain() {
    let c = caps(&[("TERM", "dumb")], true, true);
    assert!(!c.stdout.color && !c.stderr.color && !c.interactive);
}

#[test]
fn detect_force_colour_applies_when_piped_but_not_with_no_color() {
    let c = caps(&[("TERM", "xterm"), ("CLICOLOR_FORCE", "1")], false, false);
    assert!(c.stdout.color && c.stderr.color && !c.interactive);
    let c = caps(
        &[("TERM", "xterm"), ("FORCE_COLOR", "1"), ("NO_COLOR", "1")],
        false,
        false,
    );
    assert!(!c.stdout.color);
    let c = caps(&[("TERM", "xterm"), ("FORCE_COLOR", "0")], false, false);
    assert!(!c.stdout.color);
}

#[test]
fn detect_ci_colours_but_does_not_redraw() {
    let c = caps(&[("TERM", "xterm"), ("CI", "true")], true, true);
    assert!(c.ci && c.stderr.color && !c.interactive);
    assert!(!caps(&[("TERM", "xterm"), ("CI", "false")], true, true).ci);
}

#[test]
fn detect_width_prefers_measured_then_columns_then_80() {
    assert_eq!(caps(&[], true, true).width, 80);
    assert_eq!(caps(&[("COLUMNS", "120")], true, true).width, 120);
    let c = Capabilities::detect(
        &EnvSnapshot::from_pairs([("COLUMNS", "120")]),
        StreamFacts {
            stdout_tty: true,
            stderr_tty: true,
            width: Some(60),
        },
    );
    assert_eq!(c.width, 60);
}

#[test]
fn select_follows_capabilities() {
    let tty = caps(&[("TERM", "xterm")], true, true);
    assert_eq!(select(&tty, false), Kind::Live);
    assert_eq!(select(&tty, true), Kind::Quiet);
    let piped = caps(&[("TERM", "xterm")], true, false);
    assert_eq!(select(&piped, false), Kind::Plain);
    let ci = caps(&[("TERM", "xterm"), ("CI", "1")], true, true);
    assert_eq!(select(&ci, false), Kind::Plain);
}

#[test]
fn piped_output_has_no_escape_bytes() {
    let buf = Buf::default();
    let c = caps(&[("TERM", "xterm")], false, false);
    run(build(&c, false, buf.clone()).as_ref());
    let t = buf.text();
    assert!(t.contains("land.merge") && t.contains("careful") && t.contains("profile"));
    assert!(!t.contains('\x1b') && !t.contains('\r'), "{t:?}");
}

#[test]
fn no_color_tty_live_has_cursor_control_but_no_colour() {
    let buf = Buf::default();
    let c = caps(&[("TERM", "xterm"), ("NO_COLOR", "1")], true, true);
    run(build(&c, false, buf.clone()).as_ref());
    let t = buf.text();
    assert!(t.contains("\x1b[2K"));
    assert!(!t.contains("\x1b[3") && !t.contains("\x1b[1;"), "{t:?}");
}

#[test]
fn tty_live_is_coloured_and_redraws_in_place() {
    let buf = Buf::default();
    let c = caps(&[("TERM", "xterm")], true, true);
    run(build(&c, false, buf.clone()).as_ref());
    let t = buf.text();
    assert!(t.contains("\x1b[32m"), "{t:?}");
    assert!(t.contains("\r\x1b[2K"));
    assert!(t.contains("2/4"));
}

#[test]
fn dumb_terminal_gets_plain_lines() {
    let buf = Buf::default();
    let c = caps(&[("TERM", "dumb")], true, true);
    run(build(&c, false, buf.clone()).as_ref());
    let t = buf.text();
    assert!(!t.contains('\x1b') && !t.contains('\r'), "{t:?}");
}

#[test]
fn ci_degrades_to_one_line_per_start_and_end() {
    let buf = Buf::default();
    let c = caps(&[("TERM", "xterm"), ("CI", "1")], true, true);
    run(build(&c, false, buf.clone()).as_ref());
    let t = buf.text();
    assert!(!t.contains('\r'));
    assert_eq!(t.matches("land.merge").count(), 3, "{t}"); // start, end, profile row
}

#[test]
fn quiet_writes_nothing() {
    let buf = Buf::default();
    let c = caps(&[("TERM", "xterm")], true, true);
    run(build(&c, true, buf.clone()).as_ref());
    assert!(buf.text().is_empty());
    run(&Quiet);
}

#[test]
fn plain_snapshot_with_ascii_glyphs() {
    let buf = Buf::default();
    let p = Plain::new(buf.clone(), Palette::plain(), Glyphs::ascii());
    run(&p);
    assert_eq!(
        buf.text(),
        "> land.merge (4 steps)\ncareful\n+ land.merge ok 1.50s\nprofile\n  land.merge 1.50s 100%\n  total 1.50s\n"
    );
}

#[test]
fn live_resize_never_exceeds_width_and_collapses_when_narrow() {
    let g = Glyphs::ascii();
    for w in [20u16, 39, 40, 80, 200] {
        let l = status_line(&g, w, "check.rules", 5, Some(10), 0);
        assert!(l.chars().count() < usize::from(w), "{w}: {l}");
    }
    assert_eq!(status_line(&g, 30, "a.b", 3, Some(9), 0), "a.b 3/9");
    assert!(status_line(&g, 80, "a.b", 3, Some(9), 0).contains('['));
}

#[test]
fn live_throbber_cycles_when_total_unknown() {
    let g = Glyphs::ascii();
    let a = status_line(&g, 80, "x", 0, None, 0);
    let b = status_line(&g, 80, "x", 0, None, 1);
    assert_ne!(a, b);
    let buf = Buf::default();
    let l = Live::new(buf.clone(), Palette::plain(), g, 80);
    l.stage_start(&StageId::new("x"), None).unwrap();
    l.tick().unwrap();
    assert!(buf.text().contains("| x") && buf.text().contains("/ x"));
}

#[test]
fn bar_fills_proportionally_and_clamps() {
    let g = Glyphs::ascii();
    assert_eq!(bar(&g, 10, 5, 10), "[#####-----]");
    assert_eq!(bar(&g, 4, 9, 4), "[####]");
    assert_eq!(bar(&g, 4, 0, 0), "[----]");
}

#[test]
fn elapsed_formats() {
    assert_eq!(fmt_elapsed(Duration::from_millis(42)), "42ms");
    assert_eq!(fmt_elapsed(Duration::from_millis(1234)), "1.23s");
}

#[test]
fn palette_plain_never_emits_escapes_and_colored_does() {
    assert_eq!(Palette::plain().paint(Role::Error, "x"), "x");
    assert!(Palette::colored().paint(Role::Error, "x").contains('\x1b'));
}

#[test]
fn profile_flags_slowest_stage() {
    let mut r = ProfileReport::default();
    r.push(StageId::new("a"), Duration::from_secs(1), Outcome::Ok);
    r.push(StageId::new("b"), Duration::from_secs(9), Outcome::Ok);
    assert_eq!(r.slowest_above(0.5).unwrap().stage.as_str(), "b");
    assert!(r.slowest_above(0.95).is_none());
}
