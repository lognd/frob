//! CLAIM004: `claim never NODE uses ATOM` is judged against the code the node owns, directly and
//! through callees (ticket 01M5XNNJQN463MG3PT8NBEC70D).

// frob:ticket 01M5XNNJQN463MG3PT8NBEC70D

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n}\nnode b : trusted {\n  owns \"src/b/**\";\n  may net.connect;\n}\nclaim a_offline {\n  never a uses net.connect;\n}\n";

fn bind_files(files: &[(&str, &str)]) -> Binding {
    bind_model(MODEL, files)
}

fn bind_model(text: &str, files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    std::fs::write(dir.path().join("design/model.grmb"), text).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", text.as_bytes().to_vec());
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

/// (message, certain) of every CLAIM004 finding.
fn claim004(files: &[(&str, &str)]) -> Vec<(String, bool)> {
    bind_files(files)
        .findings
        .iter()
        .filter(|f| f.rule == "CLAIM004")
        .map(|f| (f.message.clone(), f.reason.is_none()))
        .collect()
}

const DIAL: (&str, &str) = (
    "src/b/net.rs",
    "pub fn dial() {\n    let _ = std::net::TcpStream::connect(\"127.0.0.1:1\");\n}\n\npub fn wrap() {\n    dial();\n}\n",
);

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn direct_connect_refutes_the_never_claim() {
    let f = claim004(&[(
        "src/a/x.rs",
        "pub fn go() {\n    let _ = std::net::TcpStream::connect(\"127.0.0.1:1\");\n}\n",
    )]);
    assert!(
        f.iter().any(|(m, c)| m.contains("net.connect") && *c),
        "{f:?}"
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn transitive_connect_refutes_the_never_claim_with_the_call_path() {
    let f = claim004(&[
        DIAL,
        (
            "src/a/x.rs",
            "use crate::b::net::wrap;\n\npub fn go() {\n    wrap();\n}\n",
        ),
    ]);
    assert!(f.iter().any(|(m, c)| m.contains("wrap") && *c), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn code_that_never_connects_satisfies_the_claim() {
    let f = claim004(&[DIAL, ("src/a/x.rs", "pub fn go() -> u32 {\n    1\n}\n")]);
    assert!(f.is_empty(), "{f:?}");
}

/// The never-claim model with the claim written `claim`.
fn with_claim(claim: &str) -> String {
    MODEL.replace("never a uses net.connect;", claim)
}

/// (message, certain) of CLAIM004 for a model with `claim`.
fn claim004_with(claim: &str, files: &[(&str, &str)]) -> Vec<(String, bool)> {
    bind_model(&with_claim(claim), files)
        .findings
        .iter()
        .filter(|f| f.rule == "CLAIM004")
        .map(|f| (f.message.clone(), f.reason.is_none()))
        .collect()
}

const CONNECT_API: (&str, &str) = (
    "src/a/x.rs",
    "pub fn go() {\n    let _ = std::net::TcpStream::connect(\"api.example.com:443\");\n}\n",
);

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn argument_claim_is_refuted_by_a_matching_argument() {
    let f = claim004_with(
        "never a uses net.connect(\"api.example.com:443\");",
        &[CONNECT_API],
    );
    assert!(f.iter().any(|(_, c)| *c), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn argument_claim_ignores_a_use_with_another_argument() {
    let f = claim004_with(
        "never a uses net.connect(\"other.example.org:443\");",
        &[CONNECT_API],
    );
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn argument_claim_with_an_unfoldable_argument_is_unresolved_not_refuted() {
    let f = claim004_with(
        "never a uses net.connect(\"api.example.com:443\");",
        &[(
            "src/a/x.rs",
            "pub fn go(h: &str) {\n    let _ = std::net::TcpStream::connect(h);\n}\n",
        )],
    );
    assert!(!f.is_empty() && f.iter().all(|(_, c)| !*c), "{f:?}");
}
