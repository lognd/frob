//! CLAIM005: a secret environment value reaching print/log/HTTP is a finding unless it is routed
//! through a declared declassify symbol (ticket 01M6QA50A5BK89J2G8SCZ4WBPR).

// frob:ticket 01M6QA50A5BK89J2G8SCZ4WBPR

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n  provides secret.declassify via \"src/a/redact.py::redact\" because=\"the redactor\";\n}\n";

fn bind(files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    std::fs::write(dir.path().join("design/model.grmb"), MODEL).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", MODEL.as_bytes().to_vec());
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

/// Messages of every CLAIM005 finding.
fn claim005(files: &[(&str, &str)]) -> Vec<String> {
    bind(files)
        .findings
        .iter()
        .filter(|f| f.rule == "CLAIM005")
        .map(|f| f.message.clone())
        .collect()
}

const REDACT: (&str, &str) = ("src/a/redact.py", "def redact(v):\n    return \"***\"\n");

// frob:tests crates/grimble-bind/src/caps/taint.rs::claim005
#[test]
fn python_secret_env_to_print_fires() {
    let f = claim005(&[
        REDACT,
        (
            "src/a/x.py",
            "import os\n\ndef go():\n    tok = os.environ[\"API_TOKEN\"]\n    print(tok)\n",
        ),
    ]);
    assert_eq!(f.len(), 1, "{f:?}");
    assert!(f[0].contains("API_TOKEN"), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps/taint.rs::claim005
#[test]
fn python_secret_env_to_http_fires() {
    let f = claim005(&[
        REDACT,
        (
            "src/a/x.py",
            "import os, requests\n\ndef go():\n    k = os.getenv(\"SVC_SECRET\")\n    requests.post(\"http://h\", data=k)\n",
        ),
    ]);
    assert_eq!(f.len(), 1, "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps/taint.rs::claim005
#[test]
fn routing_through_the_declassify_symbol_is_clean() {
    let f = claim005(&[
        REDACT,
        (
            "src/a/x.py",
            "import os\nfrom src.a.redact import redact\n\ndef go():\n    tok = os.environ[\"API_TOKEN\"]\n    print(redact(tok))\n",
        ),
    ]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps/taint.rs::claim005
#[test]
fn rust_secret_env_to_log_fires() {
    let f = claim005(&[
        REDACT,
        (
            "src/a/x.rs",
            "pub fn go() {\n    let k = std::env::var(\"DB_PASSWORD\").unwrap();\n    println!(\"{k}\");\n}\n",
        ),
    ]);
    assert_eq!(f.len(), 1, "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps/taint.rs::claim005
#[test]
fn non_secret_env_is_clean() {
    let f = claim005(&[
        REDACT,
        (
            "src/a/x.py",
            "import os\n\ndef go():\n    h = os.environ[\"HOME\"]\n    print(h)\n",
        ),
    ]);
    assert!(f.is_empty(), "{f:?}");
}
