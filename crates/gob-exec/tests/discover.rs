//! Sibling discovery (D87): beside the running executable first, then `PATH`; Windows rules on any host.
// frob:ticket 01M421F7Q66MW38R7J1JS1VMBC

use std::collections::BTreeSet;
use std::ffi::OsStr;
use std::path::{Path, PathBuf};

use gob_exec::{Origin, Platform, executable_names, find_sibling, plan};

/// An `is_file` probe over a fixed set of existing files.
fn existing(files: &[&PathBuf]) -> impl Fn(&Path) -> bool + use<> {
    let set: BTreeSet<PathBuf> = files.iter().map(|p| (*p).clone()).collect();
    move |p| set.contains(p)
}

// frob:tests crates/gob-exec/src/discover.rs::executable_names
#[test]
fn windows_names_take_exe_ignoring_case_and_unix_names_are_bare() {
    let names = |p, n: &str| executable_names(p, OsStr::new(n));
    assert_eq!(names(Platform::Unix, "grimble"), vec!["grimble"]);
    assert_eq!(names(Platform::Windows, "grimble"), vec!["grimble.exe"]);
    assert_eq!(names(Platform::Windows, "grimble.exe"), vec!["grimble.exe"]);
    assert_eq!(names(Platform::Windows, "grimble.EXE"), vec!["grimble.EXE"]);
}

// frob:tests crates/gob-exec/src/discover.rs::plan
#[test]
fn a_windows_scripts_dir_copy_beats_path_and_both_are_reported() {
    let scripts = PathBuf::from("C:\\tools\\frob\\Scripts");
    let on_path = PathBuf::from("C:\\bin");
    let near = scripts.join("grimble.exe");
    let far = on_path.join("grimble.exe");
    let (beside, path) = plan(
        Platform::Windows,
        OsStr::new("grimble"),
        std::slice::from_ref(&scripts),
        std::slice::from_ref(&on_path),
        &existing(&[&near, &far]),
    );
    assert_eq!(beside, Some(near));
    assert_eq!(path, Some(far));
}

// frob:tests crates/gob-exec/src/discover.rs::plan
#[test]
fn windows_does_not_match_a_suffixless_file_and_unix_does_not_add_exe() {
    let dir = PathBuf::from("C:\\x");
    let bare = dir.join("grimble");
    let exe = dir.join("grimble.exe");
    let only_bare = existing(&[&bare]);
    let dirs = std::slice::from_ref(&dir);
    let n = OsStr::new("grimble");
    assert_eq!(plan(Platform::Windows, n, dirs, &[], &only_bare).0, None);
    assert_eq!(
        plan(Platform::Unix, n, dirs, &[], &only_bare).0,
        Some(bare.clone())
    );
    assert_eq!(
        plan(Platform::Unix, n, dirs, &[], &existing(&[&exe])).0,
        None
    );
}

// frob:tests crates/gob-exec/src/discover.rs::plan
#[test]
fn path_dirs_are_searched_in_order_and_a_missing_beside_falls_back_to_path() {
    let (a, b) = (PathBuf::from("/a"), PathBuf::from("/b"));
    let in_b = b.join("grimble");
    let (beside, path) = plan(
        Platform::Unix,
        OsStr::new("grimble"),
        &[PathBuf::from("/env/bin")],
        &[a, b],
        &existing(&[&in_b]),
    );
    assert_eq!(beside, None);
    assert_eq!(path, Some(in_b));
}

// frob:tests crates/gob-exec/src/discover.rs::beside_dirs
#[cfg(unix)]
#[test]
fn beside_dirs_resolve_symlinks_to_the_real_directory_first() {
    use gob_exec::beside_dirs;
    let real = tempfile::tempdir().expect("tempdir");
    let link_dir = tempfile::tempdir().expect("tempdir");
    let exe = real.path().join("frob");
    std::fs::write(&exe, "").expect("write");
    let link = link_dir.path().join("frob");
    std::os::unix::fs::symlink(&exe, &link).expect("symlink");
    let dirs = beside_dirs(&link);
    let real_dir = gob_exec::canonical(real.path()).expect("canonical");
    assert_eq!(dirs.first(), Some(&real_dir));
    assert_eq!(dirs.get(1).map(PathBuf::as_path), Some(link_dir.path()));
}

// frob:tests crates/gob-exec/src/discover.rs::find_sibling
#[test]
fn find_sibling_refuses_path_like_names_and_reports_absence() {
    assert!(find_sibling("a/b").is_err());
    assert!(find_sibling("").is_err());
    assert!(find_sibling("no-such-sibling-d87").is_err());
    let _ = Origin::Path.label();
}

/// An environment lookup over fixed variables.
fn vars(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<std::ffi::OsString> + use<> {
    let map: Vec<(String, String)> = pairs
        .iter()
        .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
        .collect();
    move |name| {
        map.iter()
            .find(|(k, _)| k == name)
            .map(|(_, v)| std::ffi::OsString::from(v))
    }
}

// frob:ticket 01M452Q6THBSZGVHRAYHA1TTRM
// frob:tests crates/gob-exec/src/discover.rs::tool_env_dirs
#[test]
fn a_windows_uv_tool_copy_in_the_bin_dir_finds_the_tool_environment_scripts() {
    // uv copies Scripts\frob.exe into the bin dir; grimble stays in the environment.
    let exe = PathBuf::from("C:/u/.local/bin/frob.exe");
    let env = vars(&[("APPDATA", "C:/u/AppData/Roaming")]);
    let venv = PathBuf::from("C:/u/AppData/Roaming")
        .join("uv")
        .join("tools")
        .join("frob");
    let scripts = venv.join("Scripts");
    let files = [
        venv.join("pyvenv.cfg"),
        scripts.join("frob.exe"),
        scripts.join("grimble.exe"),
    ];
    let probe = existing(&files.iter().collect::<Vec<_>>());
    let dirs = gob_exec::tool_env_dirs(Platform::Windows, &exe, &env, &probe);
    assert_eq!(dirs, vec![scripts.clone()]);
    let beside = [exe.parent().unwrap().to_path_buf(), scripts.clone()];
    let (near, far) = plan(
        Platform::Windows,
        OsStr::new("grimble"),
        &[beside[0].clone(), dirs[0].clone()],
        &[],
        &probe,
    );
    assert_eq!(near, Some(scripts.join("grimble.exe")));
    assert_eq!(far, None);
}

// frob:tests crates/gob-exec/src/discover.rs::tool_env_roots
#[test]
fn tool_roots_follow_the_installers_precedence_and_only_apply_on_windows() {
    let env = vars(&[
        ("UV_TOOL_DIR", "D:/tools"),
        ("PIPX_HOME", "D:/pipx"),
        ("USERPROFILE", "C:/u"),
        ("APPDATA", ""),
    ]);
    let roots = gob_exec::tool_env_roots(Platform::Windows, &env);
    assert_eq!(
        roots,
        vec![
            PathBuf::from("D:/tools"),
            PathBuf::from("D:/pipx").join("venvs"),
            PathBuf::from("C:/u").join("pipx").join("venvs"),
        ]
    );
    assert!(gob_exec::tool_env_roots(Platform::Unix, &env).is_empty());
}

// frob:tests crates/gob-exec/src/discover.rs::tool_env_dirs
#[test]
fn a_directory_that_is_not_a_venv_or_lacks_the_tool_is_never_searched() {
    let exe = PathBuf::from("C:/u/bin/frob.exe");
    let env = vars(&[("UV_TOOL_DIR", "D:/tools")]);
    let venv = PathBuf::from("D:/tools").join("frob");
    let no_cfg = [venv.join("Scripts").join("frob.exe")];
    let probe = existing(&no_cfg.iter().collect::<Vec<_>>());
    assert!(gob_exec::tool_env_dirs(Platform::Windows, &exe, &env, &probe).is_empty());
    let no_exe = [venv.join("pyvenv.cfg")];
    let probe = existing(&no_exe.iter().collect::<Vec<_>>());
    assert!(gob_exec::tool_env_dirs(Platform::Windows, &exe, &env, &probe).is_empty());
}
