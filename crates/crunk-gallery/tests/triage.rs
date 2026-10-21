//! Triage: the store writes valid v3 manifests, the loopback server saves verdicts, and the crate
//! stays free of an async runtime.

// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::Path;

use crunk_gallery::cells::Cell;
use crunk_gallery::manifest::{self, Status};
use crunk_gallery::render::Rendered;
use crunk_gallery::triage::server::{Request, Session, bind, handle, serve};
use crunk_gallery::triage::store::{self, Reviewer};

fn cell() -> Cell {
    Cell {
        screen: "home".into(),
        state: "default".into(),
        platform: "web".into(),
    }
}

fn reviewer(expires: Option<i64>) -> Reviewer {
    Reviewer {
        name: "ada".into(),
        today: "2026-10-21".parse().expect("day"),
        expires_in_days: expires,
    }
}

fn rendered() -> Rendered {
    Rendered {
        path: "home__default__web.png".into(),
        sha256: "a".repeat(64),
    }
}

fn session(dir: &Path, token: &str) -> Session {
    let mut m = store::empty();
    store::apply_render(&mut m, &cell(), &rendered());
    std::fs::write(dir.join("home__default__web.png"), b"\x89PNG").expect("png");
    Session {
        cells: vec![cell()],
        manifest: m,
        manifest_path: dir.join("manifest.json"),
        artifacts: dir.to_path_buf(),
        reviewer: reviewer(Some(30)),
        token: token.into(),
        done: false,
    }
}

fn req(method: &str, target: &str, headers: &[(&str, &str)], body: &str) -> Request {
    let mut h: Vec<(String, String)> = vec![("host".into(), "127.0.0.1:1".into())];
    h.extend(
        headers
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned())),
    );
    Request {
        method: method.into(),
        target: target.into(),
        headers: h,
        body: body.as_bytes().to_vec(),
    }
}

fn http(
    addr: std::net::SocketAddr,
    method: &str,
    target: &str,
    token: Option<&str>,
    body: &str,
) -> String {
    let mut s = TcpStream::connect(addr).expect("connect");
    let tok = token.map_or(String::new(), |t| format!("X-Triage-Token: {t}\r\n"));
    write!(
        s,
        "{method} {target} HTTP/1.1\r\nHost: {addr}\r\n{tok}Content-Length: {}\r\n\r\n{body}",
        body.len()
    )
    .expect("write");
    let mut out = Vec::new();
    s.read_to_end(&mut out).expect("read");
    String::from_utf8_lossy(&out).into_owned()
}

// frob:tests crates/crunk-gallery/src/triage/store.rs::save
// frob:tests crates/crunk-gallery/src/triage/store.rs::set_verdict
#[test]
fn saved_manifest_is_valid_v3_and_keeps_the_verdict() {
    let dir = tempfile::tempdir().expect("tmp");
    let mut m = store::empty();
    store::apply_render(&mut m, &cell(), &rendered());
    store::set_verdict(&mut m, &cell(), Status::Approved, &reviewer(Some(30))).expect("verdict");
    let path = dir.path().join("m.json");
    store::save(&path, &m).expect("save");
    let back = manifest::parse(&std::fs::read_to_string(&path).expect("read")).expect("v3 parses");
    let v = back.entries[0].verdict.as_ref().expect("verdict");
    assert_eq!(v.status, Status::Approved);
    assert_eq!(v.expires_at.as_deref(), Some("2026-11-20"));
}

// frob:tests crates/crunk-gallery/src/triage/store.rs::apply_render
#[test]
fn a_changed_render_clears_the_verdict() {
    let mut m = store::empty();
    store::apply_render(&mut m, &cell(), &rendered());
    store::set_verdict(&mut m, &cell(), Status::Approved, &reviewer(None)).expect("verdict");
    store::apply_render(&mut m, &cell(), &rendered());
    assert!(
        m.entries[0].verdict.is_some(),
        "same pixels keep the verdict"
    );
    let other = Rendered {
        sha256: "b".repeat(64),
        ..rendered()
    };
    store::apply_render(&mut m, &cell(), &other);
    assert!(m.entries[0].verdict.is_none());
}

// frob:tests crates/crunk-gallery/src/triage/store.rs::set_verdict
#[test]
fn an_unrendered_cell_cannot_be_judged() {
    let mut m = store::empty();
    assert!(store::set_verdict(&mut m, &cell(), Status::Approved, &reviewer(None)).is_err());
}

// frob:tests crates/crunk-gallery/src/triage/server.rs::serve
// frob:tests crates/crunk-gallery/src/triage/server.rs::bind
#[test]
fn contact_sheet_serves_and_verdicts_reach_the_manifest() {
    let dir = tempfile::tempdir().expect("tmp");
    let s = session(dir.path(), "tok");
    let path = s.manifest_path.clone();
    let l = bind(0).expect("bind");
    let addr = l.local_addr().expect("addr");
    let t = std::thread::spawn(move || serve(&l, s).expect("serve"));
    let page = http(addr, "GET", "/", None, "");
    assert!(page.contains("200 OK") && page.contains("home"), "{page}");
    let img = http(addr, "GET", "/img/0?t=tok", None, "");
    assert!(img.contains("image/png"), "{img}");
    let v = http(
        addr,
        "POST",
        "/verdict",
        Some("tok"),
        r#"{"index":0,"status":"approved"}"#,
    );
    assert!(v.contains("200 OK"), "{v}");
    assert!(http(addr, "POST", "/done", Some("tok"), "").contains("200 OK"));
    let done = t.join().expect("join");
    assert!(done.done);
    let saved = manifest::parse(&std::fs::read_to_string(path).expect("read")).expect("parse");
    assert_eq!(
        saved.entries[0].verdict.as_ref().expect("v").status,
        Status::Approved
    );
}

// frob:tests crates/crunk-gallery/src/triage/server.rs::handle
#[test]
fn requests_without_the_token_or_with_a_foreign_host_or_origin_are_refused() {
    let dir = tempfile::tempdir().expect("tmp");
    let mut s = session(dir.path(), "tok");
    let body = r#"{"index":0,"status":"approved"}"#;
    assert_eq!(
        handle(&mut s, &req("POST", "/verdict", &[], body)).status,
        403
    );
    let wrong = [("x-triage-token", "nope")];
    assert_eq!(
        handle(&mut s, &req("POST", "/verdict", &wrong, body)).status,
        403
    );
    let evil_origin = [("x-triage-token", "tok"), ("origin", "http://evil.example")];
    assert_eq!(
        handle(&mut s, &req("POST", "/verdict", &evil_origin, body)).status,
        403
    );
    let mut rebound = req("GET", "/", &[], "");
    rebound.headers[0].1 = "evil.example".into();
    assert_eq!(handle(&mut s, &rebound).status, 403);
    assert_eq!(handle(&mut s, &req("GET", "/img/0", &[], "")).status, 403);
    assert!(s.manifest.entries[0].verdict.is_none());
    let ok = [("x-triage-token", "tok")];
    assert_eq!(
        handle(&mut s, &req("POST", "/verdict", &ok, body)).status,
        200
    );
}

// frob:tests crates/crunk-gallery/src/triage/server.rs::handle
#[test]
fn image_paths_never_escape_the_artifacts_dir() {
    let dir = tempfile::tempdir().expect("tmp");
    let mut s = session(dir.path(), "tok");
    s.manifest.entries[0].render.as_mut().expect("render").path = "../secret.png".into();
    assert_eq!(
        handle(&mut s, &req("GET", "/img/0?t=tok", &[], "")).status,
        404
    );
}

#[test]
fn the_crate_does_not_depend_on_tokio_directly() {
    let toml = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/Cargo.toml"))
        .expect("Cargo.toml");
    assert!(
        !toml.lines().any(|l| l.trim_start().starts_with("tokio")),
        "crunk-gallery must not depend on tokio (boundaries.md section 6)"
    );
}

// frob:tests crates/crunk-gallery/src/triage/server.rs::new_token
// frob:tests crates/crunk-gallery/src/triage/store.rs::parse_status
// frob:tests crates/crunk-gallery/src/triage/store.rs::load_or_empty
// frob:tests crates/crunk-gallery/src/triage/store.rs::expand_wildcards
#[test]
fn tokens_statuses_and_missing_manifests_behave() {
    let a = crunk_gallery::triage::server::new_token().expect("token");
    let b = crunk_gallery::triage::server::new_token().expect("token");
    assert_eq!(a.len(), 32);
    assert_ne!(a, b);
    assert_eq!(store::parse_status("approved"), Some(Status::Approved));
    assert_eq!(store::parse_status("nonsense"), None);
    let dir = tempfile::tempdir().expect("tmp");
    let m = store::load_or_empty(&dir.path().join("absent.json")).expect("empty");
    assert!(m.entries.is_empty());
    let mut m = store::empty();
    store::expand_wildcards(&mut m, &[cell()]);
    assert!(m.entries.is_empty());
}
