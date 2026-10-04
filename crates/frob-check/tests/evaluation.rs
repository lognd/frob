//! A rule producer never maps an evaluation error to zero findings (`~A6C2R1C`, P-05 inventory).

/// The sources whose rule producers must route failures through `settle`.
const PRODUCERS: [&str; 2] = ["src/product.rs", "src/snapshot.rs"];

// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
// frob:tests crates/frob-check/src/product.rs::settle
#[test]
fn no_producer_logs_not_evaluated_and_returns_nothing() {
    for path in PRODUCERS {
        let full = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(path);
        let text = std::fs::read_to_string(&full).expect("source");
        for (n, line) in text.lines().enumerate() {
            let swallows = line.contains("tracing::")
                && line.contains("not evaluated")
                && !line.contains("reporting required Unresolved")
                && !line.trim_start().starts_with("//");
            assert!(
                !swallows,
                "{path}:{} swallows an evaluation error as no findings: {line}",
                n + 1
            );
        }
    }
}
