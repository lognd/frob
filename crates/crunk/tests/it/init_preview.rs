//! `crunk preview`: the terminal sheet and its `NO_COLOR` handling.

// frob:ticket 01M43ATD7ZGTNCY5036AYEJR7P

use assert_cmd::Command;

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    Command::cargo_bin("crunk")
        .expect("bin")
        .current_dir(dir.path())
        .arg("init")
        .assert()
        .success();
    dir
}

fn preview(dir: &std::path::Path, no_color: bool, args: &[&str]) -> String {
    let mut cmd = Command::cargo_bin("crunk").expect("bin");
    cmd.current_dir(dir).arg("preview").args(args);
    cmd.env_remove("NO_COLOR");
    if no_color {
        cmd.env("NO_COLOR", "1");
    }
    String::from_utf8(cmd.assert().success().get_output().stdout.clone()).expect("utf8")
}

// frob:tests crates/crunk/src/preview.rs::Preview
#[test]
fn no_color_env_prints_no_escape_codes_even_when_forced() {
    let dir = project();
    let out = preview(dir.path(), true, &["--color", "always", "--format", "text"]);
    assert!(
        !out.contains('\x1b'),
        "escape codes under NO_COLOR: {out:?}"
    );
    assert!(out.starts_with("palette\n"), "{out}");
}

// frob:tests crates/crunk/src/preview.rs::render
#[test]
fn forced_color_adds_truecolor_swatches() {
    let dir = project();
    let out = preview(
        dir.path(),
        false,
        &["--color", "always", "--format", "text"],
    );
    assert!(out.contains("\x1b[48;2;26;26;26m    \x1b[0m"), "{out:?}");
}

// frob:tests crates/crunk/src/preview.rs::render
#[test]
fn plain_sheet_matches_the_layout() {
    let dir = project();
    let out = preview(dir.path(), true, &["--format", "text"]);
    let want = "palette\n  ink                      #1a1a1a  \n";
    assert!(out.starts_with(want), "{out:?}");
    assert!(
        out.contains("\nspacing\n       0px  #\n       4px  ##\n"),
        "{out}"
    );
    assert!(out.contains("\nstacks\n  (empty)\n\nlayers\n"), "{out}");
}
