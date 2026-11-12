//! `TEST002`: a committed heavy profile that telemetry no longer supports is a finding.

// frob:ticket 01M4P2N1XMDZAGS1EAZPR6WQMQ

use std::path::{Path, PathBuf};

use frob_tests::heavy::{self, Thresholds};
use frob_tests::{Test002, TestsHost};
use gob_directives::DirectiveRecord;
use gob_rules::RelayRule;
use gob_symbols::SymbolGraph;
use gob_text::FileInterner;

const LIMITS: Thresholds = Thresholds {
    wall_ms: 1000,
    disk_bytes: 1_000_000,
};

/// A host that only knows its repository root.
struct Disk {
    root: PathBuf,
    graph: SymbolGraph,
}

impl TestsHost for Disk {
    fn directives(&self) -> &[DirectiveRecord] {
        &[]
    }

    fn graph(&self) -> &SymbolGraph {
        &self.graph
    }

    fn read_source(&self, _path: &str) -> Option<String> {
        None
    }

    fn repo_root(&self) -> Option<&Path> {
        Some(&self.root)
    }
}

/// Write the telemetry file under `root`.
fn telemetry(root: &Path, command: &str) {
    std::fs::create_dir_all(root.join(".frob")).expect("mkdir");
    let row =
        format!(r#"{{"kind":"command","command":"{command}","wall_ms":5000,"disk_bytes":0}}"#);
    std::fs::write(root.join(heavy::TELEMETRY_FILE), format!("{row}\n")).expect("write");
}

/// Relay `TEST002` over a fresh host rooted at `root`; the finding count.
fn findings(root: &Path) -> usize {
    let host = Disk {
        root: root.to_path_buf(),
        graph: SymbolGraph::default(),
    };
    Test002.relay(&host, &mut FileInterner::default()).len()
}

// frob:tests crates/frob-tests/src/rules/test002.rs::Test002.relay
#[test]
fn a_profile_telemetry_no_longer_supports_is_a_finding() {
    let dir = tempfile::tempdir().expect("tempdir");
    telemetry(dir.path(), "cargo test");
    heavy::refresh(dir.path(), LIMITS).expect("refresh");
    assert_eq!(findings(dir.path()), 0);
    telemetry(dir.path(), "make all");
    assert_eq!(findings(dir.path()), 1);
}
