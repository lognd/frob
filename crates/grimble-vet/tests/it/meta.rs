//! Licence, yanked, maintenance and typosquat checks.

// frob:ticket 01M5A63T0R2D5DKF95XEZ00NZ6

use grimble_vet::meta::{self, Meta, licence_allowed, parse_date};
use grimble_vet::typosquat::lookalike;
use grimble_vet::{Allowlist, Package, Rule, Snapshot, vet_command};

/// An allowed set of MIT and Apache-2.0.
fn allowed() -> Vec<String> {
    vec!["MIT".to_owned(), "Apache-2.0".to_owned()]
}

#[test]
fn spdx_or_needs_one_allowed_and_needs_all() {
    // frob:tests crates/grimble-vet/src/meta.rs::licence_allowed
    let a = allowed();
    assert!(licence_allowed("MIT", &a));
    assert!(licence_allowed("MIT OR GPL-3.0-only", &a));
    assert!(licence_allowed("MIT/Apache-2.0", &a));
    assert!(licence_allowed("(MIT OR GPL-3.0-only) AND Apache-2.0", &a));
    assert!(!licence_allowed("MIT AND GPL-3.0-only", &a));
    assert!(!licence_allowed("GPL-3.0-only", &a));
    assert!(licence_allowed("Apache-2.0 WITH LLVM-exception", &a));
    assert!(licence_allowed("MIT+", &a));
}

#[test]
fn dates_parse_to_day_counts() {
    // frob:tests crates/grimble-vet/src/meta.rs::parse_date
    assert_eq!(parse_date("1970-01-01"), Some(0));
    assert_eq!(parse_date("1970-03-01"), Some(59));
    assert_eq!(parse_date("2000-03-01"), Some(11_017));
    assert_eq!(parse_date("2026-13-01"), None);
    assert_eq!(parse_date("nope"), None);
}

/// A registry package named `name` at `version`.
fn package(name: &str, version: &str) -> Package {
    Package {
        name: name.to_owned(),
        version: version.to_owned(),
        source: Some("registry+x".to_owned()),
        dependencies: Vec::new(),
    }
}

#[test]
fn check_reports_licence_yank_and_staleness() {
    // frob:tests crates/grimble-vet/src/meta.rs::check
    // frob:tests crates/grimble-vet/src/meta.rs::Meta.parse
    let meta = Meta::parse(
        "as_of = \"2026-11-06\"\n[policy]\nallowed_licenses = [\"MIT\"]\nmax_age_days = 365\n\
         [[package]]\nname = \"a\"\nversion = \"1.0.0\"\nlicense = \"GPL-3.0-only\"\nyanked = true\nlast_release = \"2020-01-01\"\n\
         [[package]]\nname = \"b\"\nversion = \"1.0.0\"\n",
    )
    .expect("meta");
    let (a, b, c) = (
        package("a", "1.0.0"),
        package("b", "1.0.0"),
        package("c", "1.0.0"),
    );
    let found = meta::check(&[&a, &b, &c], &meta, &Allowlist::default());
    let rules: Vec<_> = found.iter().map(|f| (f.package.as_str(), f.rule)).collect();
    assert_eq!(
        rules,
        [
            ("a", Rule::Licence),
            ("a", Rule::Yanked),
            ("a", Rule::Maintenance),
            ("b", Rule::Licence),
        ]
    );
}

#[test]
fn allowlist_exempts_licence_and_maintenance_but_not_yank() {
    // frob:tests crates/grimble-vet/src/meta.rs::check
    let meta = Meta::parse(
        "as_of = \"2026-11-06\"\n[policy]\nallowed_licenses = [\"MIT\"]\n\
         [[package]]\nname = \"a\"\nversion = \"1.0.0\"\nlicense = \"GPL-3.0-only\"\nyanked = true\nlast_release = \"2020-01-01\"\n",
    )
    .expect("meta");
    let a = package("a", "1.0.0");
    let allow = Allowlist::parse("allow = [\"a\"]").expect("allow");
    let found = meta::check(&[&a], &meta, &allow);
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].rule, Rule::Yanked);
}

#[test]
fn bad_metadata_is_a_parse_error() {
    // frob:tests crates/grimble-vet/src/meta.rs::Meta.parse
    assert!(Meta::parse("[[package").is_err());
}

#[test]
fn lookalikes_are_one_edit_from_a_popular_crate() {
    // frob:tests crates/grimble-vet/src/typosquat.rs::lookalike
    assert_eq!(lookalike("serd", &[]).as_deref(), Some("serde"));
    assert_eq!(lookalike("tokoi", &[]).as_deref(), Some("tokio"));
    assert_eq!(lookalike("reqwestt", &[]).as_deref(), Some("reqwest"));
    assert_eq!(lookalike("serde", &[]), None);
    assert_eq!(lookalike("totally-different", &[]), None);
    let extra = vec!["mycrate".to_owned()];
    assert_eq!(lookalike("mycrat", &extra).as_deref(), Some("mycrate"));
    assert_eq!(
        lookalike("mycrat", &["mycrat".to_owned(), "mycrate".to_owned()]),
        None
    );
}

#[test]
fn the_install_hook_flags_a_typosquat() {
    // frob:tests crates/grimble-vet/src/hook.rs::vet_command
    let allow = Allowlist::parse("allow = [\"serd\"]").expect("allow");
    let report = vet_command(
        "cargo add tokoi",
        &Allowlist::default(),
        &Snapshot::default(),
    );
    assert!(report.findings.iter().any(|f| f.rule == Rule::Typosquat));
    let report = vet_command("cargo add serd", &allow, &Snapshot::default());
    assert!(!report.findings.iter().any(|f| f.rule == Rule::Typosquat));
}
