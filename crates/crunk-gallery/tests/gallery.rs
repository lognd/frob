//! Gallery tests: manifest v1-v3 vs the shipped schemas, enumeration, rules and the report.

use std::path::Path;

use crunk_gallery::cells::{CellFilter, cells, enumerate};
use crunk_gallery::manifest::{ManifestError, Status, parse};
use crunk_gallery::report::check_report;
use crunk_gallery::rules::{check_routes, normalize_route};
use crunk_gallery::schema::{CHECK_V1, validate};
use crunk_spec::{DesignSpec, Severity, parse_spec};
use gob_time::Day;

const V1: &str = r#"{"version":1,"entries":[{"screen":"landing","platform":"chromium-desktop","image":"a.png","status":"approved"}]}"#;
const V2: &str = r#"{"version":2,"cells":[{"screen":"landing","state":"default","platform":"chromium-desktop","image":"a.png","sha256":null,"status":"pending"}]}"#;
const V3: &str = r#"{"version":3,"cells":[{"screen":"landing","state":"default","platform":"chromium-desktop","render":{"path":"a.png","sha256":"0000000000000000000000000000000000000000000000000000000000000000"},"verdict":{"status":"approved","reviewer":"ana","reviewed_at":"2026-10-01","expires_at":"2026-10-10"}}]}"#;

fn fixture(name: &str) -> DesignSpec {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../crunk-spec/tests/fixtures/valid")
        .join(name);
    let text = std::fs::read_to_string(&path).expect("fixture");
    parse_spec(&text, &path, path.parent().expect("dir")).expect("fixture parses")
}

fn day(s: &str) -> Day {
    s.parse().expect("day")
}

// frob:tests parse
#[test]
fn manifest_v1_v2_v3_pass_their_schemas() {
    assert_eq!(parse(V1).expect("v1").version, 1);
    assert_eq!(
        parse(V2).expect("v2").entries[0]
            .verdict
            .as_ref()
            .expect("verdict")
            .status,
        Status::Pending
    );
    let v3 = parse(V3).expect("v3");
    assert_eq!(
        v3.entries[0]
            .verdict
            .as_ref()
            .expect("verdict")
            .expires_at
            .as_deref(),
        Some("2026-10-10")
    );
}

// frob:tests parse
#[test]
fn broken_manifest_fails_with_a_located_error() {
    let broken = V3.replace("\"approved\"", "\"maybe\"");
    match parse(&broken) {
        Err(ManifestError::Schema { version: 3, errors }) => {
            assert!(
                errors
                    .iter()
                    .any(|e| e.pointer == "/cells/0/verdict/status"),
                "{errors:?}"
            );
        }
        other => panic!("expected a located schema error, got {other:?}"),
    }
    assert_eq!(parse("{\"version\":9}"), Err(ManifestError::Version));
    assert!(matches!(parse("nope"), Err(ManifestError::Json(_))));
}

// frob:tests enumerate
#[test]
fn enumerate_orders_screen_state_platform() {
    let spec = fixture("screens_v1_1.toml");
    let all = enumerate(&spec);
    assert!(!all.is_empty());
    let screens: Vec<&str> = spec.screens.keys().map(String::as_str).collect();
    let mut last = 0;
    for c in &all {
        let at = screens.iter().position(|s| *s == c.screen).expect("screen");
        assert!(at >= last, "screens stay in declaration order");
        last = at;
    }
    // No cell repeats, and every platform used is declared.
    let mut seen = std::collections::HashSet::new();
    assert!(
        all.iter()
            .all(|c| seen.insert(c.clone()) && spec.platforms.contains_key(&c.platform))
    );
    // State-level applies_to narrows: some screen has fewer cells for one state than another.
    let per_state = |state: &str| all.iter().filter(|c| c.state == state).count();
    let counts: Vec<usize> = all.iter().map(|c| per_state(&c.state)).collect();
    assert!(counts.iter().any(|n| *n < spec.platforms.len()));
}

// frob:tests cells
#[test]
fn cells_filter_narrows() {
    let spec = fixture("screens_v1_1.toml");
    let all = enumerate(&spec);
    let first = all[0].clone();
    let only = cells(
        &spec,
        &CellFilter {
            screen: Some(first.screen.clone()),
            state: Some(first.state.clone()),
            platform: Some(first.platform.clone()),
        },
    );
    assert_eq!(only, vec![first]);
    assert_eq!(cells(&spec, &CellFilter::default()), all);
}

// frob:tests check_report
#[test]
fn report_counts_and_validates_against_its_schema() {
    let spec = fixture("screens_v1_1.toml");
    let manifest = parse(V3).expect("v3");
    let routes = vec!["/nowhere".to_owned()];
    let report = check_report(&spec, &manifest, &routes, day("2026-10-15"));
    assert_eq!(report.cells, enumerate(&spec).len());
    assert_eq!(report.errors + report.warnings, report.findings.len());
    assert!(
        report.findings.iter().any(|f| f.rule == "GALLERY003"),
        "expired approval"
    );
    assert!(
        report.findings.iter().any(|f| f.rule == "GALLERY001"),
        "unrendered cells"
    );
    assert!(
        report
            .findings
            .iter()
            .any(|f| f.rule == "GALLERY005" && f.severity == Severity::Warn)
    );
    assert!(!report.passed());
    let value = serde_json::to_value(&report).expect("serializes");
    assert_eq!(validate(CHECK_V1, &value), vec![]);
}

// frob:tests check_cells
#[test]
fn rejected_and_pending_are_distinct_rules() {
    let spec = fixture("screens_v1_1.toml");
    let first = &enumerate(&spec)[0];
    let doc = |status: &str| {
        format!(
            r#"{{"version":2,"cells":[{{"screen":"{}","state":"{}","platform":"{}","image":"a.png","sha256":null,"status":"{status}"}}]}}"#,
            first.screen, first.state, first.platform
        )
    };
    let rules_for = |status: &str| -> Vec<&'static str> {
        let m = parse(&doc(status)).expect("manifest");
        let r = check_report(&spec, &m, &[], day("2026-10-15"));
        r.findings
            .iter()
            .filter(|f| {
                f.screen.as_deref() == Some(&first.screen)
                    && f.state.as_deref() == Some(&first.state)
                    && f.platform.as_deref() == Some(&first.platform)
            })
            .map(|f| f.rule)
            .collect()
    };
    assert_eq!(rules_for("pending"), vec!["GALLERY002"]);
    assert_eq!(rules_for("rejected"), vec!["GALLERY004"]);
    assert!(rules_for("approved").is_empty());
}

// frob:tests check_routes
#[test]
fn gallery005_routes_normalize_and_ignore_catch_all() {
    let spec = fixture("gallery005_routes.toml");
    let routes: Vec<String> = [
        "/",
        "/portal/",
        "/portal/invoices",
        "/login",
        "*",
        "/missing",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect();
    let found = check_routes(&spec, &routes);
    let msgs: Vec<&str> = found.iter().map(|f| f.message.as_str()).collect();
    assert_eq!(found.len(), 1, "{msgs:?}");
    assert!(found[0].message.contains("/missing"));
    assert_eq!(found[0].rule, "GALLERY005");
}

// frob:tests normalize_route
#[test]
fn normalize_route_strips_query_fragment_and_trailing_slash() {
    assert_eq!(
        normalize_route("/portal/invoices?state=empty"),
        "/portal/invoices"
    );
    assert_eq!(normalize_route("/login/"), "/login");
    assert_eq!(normalize_route("/"), "/");
    assert_eq!(normalize_route("/a#b"), "/a");
}
