//! The `TestsHost` contract and the in-place verb registration.

use frob_tests::TestsHost;
use gob_directives::DirectiveRecord;
use gob_symbols::SymbolGraph;

/// A host with no directives, an empty graph and one readable file.
struct Stub {
    graph: SymbolGraph,
    directives: Vec<DirectiveRecord>,
}

impl TestsHost for Stub {
    fn directives(&self) -> &[DirectiveRecord] {
        &self.directives
    }

    fn graph(&self) -> &SymbolGraph {
        &self.graph
    }

    fn read_source(&self, path: &str) -> Option<String> {
        (path == "t.rs").then(|| "#[test]\nfn t() {}\n".to_owned())
    }
}

fn stub() -> Stub {
    Stub {
        graph: SymbolGraph::default(),
        directives: Vec::new(),
    }
}

// frob:tests crates/frob-tests/src/host.rs::TestsHost.directives
#[test]
fn a_host_with_no_directives_serves_an_empty_slice() {
    assert!(TestsHost::directives(&stub()).is_empty());
}

// frob:tests crates/frob-tests/src/host.rs::TestsHost.graph
#[test]
fn a_host_serves_the_graph_it_holds() {
    let host = stub();
    assert!(std::ptr::eq(
        TestsHost::graph(&host),
        std::ptr::addr_of!(host.graph)
    ));
}

// frob:tests crates/frob-tests/src/host.rs::TestsHost.read_source
#[test]
fn a_host_reads_known_sources_and_none_for_unknown_ones() {
    let host = stub();
    assert!(TestsHost::read_source(&host, "t.rs").is_some_and(|t| t.contains("#[test]")));
    assert_eq!(TestsHost::read_source(&host, "missing.rs"), None);
}

// frob:tests crates/frob-tests/src/lib.rs::register_mut
#[test]
fn register_mut_adds_the_test_verb_in_place() {
    let mut cli = gob_cli::Cli::new("frob", "0.0.0");
    frob_tests::register_mut(&mut cli);
    let after = format!("{cli:?}");
    assert!(after.contains("\"test\""), "{after}");
}

// frob:tests crates/frob-tests/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = frob_tests::rules::bind::<Stub>();
    assert_eq!(rules.len(), frob_tests::rules::METAS.len());
}

// frob:tests crates/frob-tests/src/host.rs::TestsHost.repo_root
#[test]
fn a_host_with_no_disk_has_no_repo_root() {
    assert!(TestsHost::repo_root(&stub()).is_none());
}
