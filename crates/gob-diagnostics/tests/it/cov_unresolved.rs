//! Direct call to `RefusalClass::doc`.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use gob_diagnostics::RefusalClass;

// frob:tests crates/gob-diagnostics/src/refusal.rs::RefusalClass.doc
#[test]
fn every_class_has_a_nonempty_one_line_doc() {
    for class in [
        RefusalClass::DomainNegative,
        RefusalClass::UsageError,
        RefusalClass::GuardRetryByWaiting,
        RefusalClass::GuardNeedsAction,
        RefusalClass::Timeout,
        RefusalClass::Internal,
    ] {
        let doc = RefusalClass::doc(class);
        assert!(!doc.is_empty() && !doc.contains('\n'));
    }
}
