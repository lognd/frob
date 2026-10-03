//! Walk digests and content reads follow git's clean conversion (core.autocrlf, symlinks).

// frob:ticket 01M40THSWB75TFY8949M4T7MXR

use gob_walk::{ContentSource, Digest, WalkConfig, walk};

/// A git repository in `dir` with `core.autocrlf=true`.
fn autocrlf_repo(dir: &std::path::Path) {
    gob_git::Repo::init(dir).expect("git init");
    let cfg = dir.join(".git/config");
    let mut text = std::fs::read_to_string(&cfg).expect("config");
    text.push_str("[core]\n\tautocrlf = true\n");
    std::fs::write(cfg, text).expect("write config");
}

// frob:tests crates/gob-walk/src/lib.rs::walk
#[test]
fn crlf_checkout_digests_like_its_lf_twin_and_a_real_edit_differs() {
    let a = tempfile::tempdir().expect("tempdir");
    let b = tempfile::tempdir().expect("tempdir");
    autocrlf_repo(a.path());
    autocrlf_repo(b.path());
    std::fs::write(a.path().join("f.rs"), "fn f() {}\nfn g() {}\n").unwrap();
    std::fs::write(b.path().join("f.rs"), "fn f() {}\r\nfn g() {}\r\n").unwrap();
    let digest = |root: &std::path::Path| {
        let w = walk(root, &WalkConfig::default()).expect("walk");
        let f = w.files.iter().find(|f| f.path == "f.rs").expect("f.rs");
        (f.digest, f.size)
    };
    assert_eq!(digest(a.path()), digest(b.path()));
    assert_eq!(digest(a.path()).0, Digest::of(b"fn f() {}\nfn g() {}\n"));
    std::fs::write(b.path().join("f.rs"), "fn f() {}\r\nfn h() {}\r\n").unwrap();
    assert_ne!(digest(a.path()), digest(b.path()));
}

// frob:tests crates/gob-walk/src/content.rs::ContentReader.read
#[test]
fn symlink_reads_as_its_target_string_and_crlf_text_as_lf() {
    let dir = tempfile::tempdir().expect("tempdir");
    autocrlf_repo(dir.path());
    std::fs::write(dir.path().join("real.txt"), "one\r\ntwo\r\n").unwrap();
    #[cfg(unix)]
    std::os::unix::fs::symlink("real.txt", dir.path().join("link")).unwrap();
    let source = ContentSource::locate(dir.path());
    source.with_reader(|r| {
        #[cfg(unix)]
        assert_eq!(r.read("link").unwrap(), b"real.txt");
        assert_eq!(r.read_text("real.txt").unwrap(), "one\ntwo\n");
        assert_eq!(
            r.read("nope").unwrap_err().kind(),
            std::io::ErrorKind::NotFound
        );
    });
}

// frob:tests crates/gob-walk/src/content.rs::ContentSource.locate
#[test]
fn outside_a_repository_bytes_are_read_raw() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("a.txt"), "x\r\ny\r\n").unwrap();
    let source = ContentSource::locate(dir.path());
    source.with_reader(|r| assert_eq!(r.read("a.txt").unwrap(), b"x\r\ny\r\n"));
}
