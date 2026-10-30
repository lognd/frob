//! CAP001 for Python receivers built by a socket constructor (ticket 01M6422ZRSX74XT6RD0BG4T2RC,
//! audit cases p12 and p13): the receiver keeps its type through an assignment, an aliased import,
//! a `with` target or a copy, so `connect` and `send` are reported; a receiver of unproven origin in
//! a file that reaches `socket` is reported unresolved (May), never passed silently.

// frob:ticket 01M6422ZRSX74XT6RD0BG4T2RC

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

fn bind_files(files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    let model = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n";
    std::fs::write(dir.path().join("design/model.grmb"), model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// (atom, certain) of every CAP001 finding, ungranted.
fn cap001(files: &[(&str, &str)]) -> Vec<(String, bool)> {
    let b = bind_files(files);
    let mut v: Vec<_> = b
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001")
        .map(|f| {
            (
                f.anchor
                    .trim_start_matches("cap/node/a/")
                    .trim_end_matches("/receiver")
                    .to_owned(),
                f.reason.is_none(),
            )
        })
        .collect();
    v.sort();
    v.dedup();
    v
}

fn one(src: &str) -> Vec<(String, bool)> {
    cap001(&[("src/x.py", src)])
}

fn has(found: &[(String, bool)], atom: &str, certain: bool) -> bool {
    found.iter().any(|(a, c)| a == atom && *c == certain)
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p12_cap_aliased_socket_constructor_keeps_its_type() {
    let f = one(
        "from socket import socket as S\n\ndef go():\n    s = S()\n    s.connect((\"h\", 1))\n    s.send(b\"x\")\n",
    );
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
    let f = one("import socket as sk\n\ndef go():\n    s = sk.socket()\n    s.listen()\n");
    assert!(has(&f, "net.listen", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p12_cap_send_alone_is_a_net_connect() {
    let f = one(
        "import socket\n\ndef go():\n    s = socket.create_connection((\"h\", 1))\n    s.sendall(b\"x\")\n",
    );
    assert!(has(&f, "net.connect", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p13_cap_with_target_and_copied_receiver_are_typed() {
    let f = one(
        "import socket\n\ndef go():\n    with socket.socket() as s:\n        t = s\n        t.connect((\"h\", 1))\n",
    );
    assert!(has(&f, "net.connect", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p13_cap_a_non_socket_receiver_in_a_socket_file_is_not_a_certain_hit() {
    let f = one(
        "import socket\nimport sqlite3\n\ndef go():\n    db = sqlite3.connect(\"x\")\n    db.connect()\n",
    );
    assert!(!has(&f, "net.connect", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p13_cap_an_untyped_receiver_beside_socket_is_unresolved_not_silent() {
    for src in [
        "import socket\n\ndef go(s):\n    s.connect((\"h\", 1))\n",
        "import socket\n\nclass A:\n    def go(self):\n        self.sock.connect((\"h\", 1))\n",
        "import socket\n\ndef go(c):\n    s = socket.socket()\n    if c:\n        s = make()\n    s.connect((\"h\", 1))\n",
    ] {
        let f = one(src);
        assert!(has(&f, "net.connect", false), "{src}: {f:?}");
        assert!(!has(&f, "net.connect", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p13_cap_a_socket_free_file_stays_silent() {
    let f = one("def go(server):\n    server.connect()\n    server.send(1)\n");
    assert!(f.is_empty(), "{f:?}");
}
