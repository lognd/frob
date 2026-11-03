//! The `AckHost` contract and the `Inputs` digest the repo-rule cache keys on.

use frob_ack::{AckHost, Inputs};

/// A host that serves one collected input bundle.
struct Stub(Inputs);

impl AckHost for Stub {
    fn inputs(&self) -> &Inputs {
        &self.0
    }
}

fn collected(files: &[(&str, &str)]) -> Inputs {
    let dir = tempfile::tempdir().expect("tempdir");
    for (name, text) in files {
        std::fs::write(dir.path().join(name), text).expect("write");
    }
    Inputs::collect(dir.path()).expect("collect")
}

// frob:tests crates/frob-ack/src/host.rs::AckHost.inputs
#[test]
fn a_host_serves_the_bundle_it_was_built_from() {
    let host = Stub(collected(&[("a.md", "# Title\n\nbody\n")]));
    let served = AckHost::inputs(&host);
    assert!(std::ptr::eq(served, std::ptr::addr_of!(host.0)));
    assert!(served.docs.is_empty());
}

// frob:tests crates/frob-ack/src/inputs.rs::Inputs.digest
#[test]
fn the_digest_is_stable_and_follows_the_repository_content() {
    let one = collected(&[("lib.rs", "pub fn a() {}\n")]);
    let again = collected(&[("lib.rs", "pub fn a() {}\n")]);
    let other = collected(&[("lib.rs", "pub fn b() { let _ = 1; }\n")]);
    assert_eq!(one.digest(), again.digest());
    assert_ne!(one.digest(), other.digest());
}

// frob:tests crates/frob-ack/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = frob_ack::rules::bind::<Stub>();
    assert_eq!(rules.len(), frob_ack::rules::METAS.len());
}
