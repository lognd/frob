//! COH001 verdicts over fire, clean and unresolved fixtures in each supported language.

// frob:ticket 01M4CXSQB9YJGH0FRSHX5ECTEM


use gob_ir::{NodeId, Operator, Universal};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh001::{Coh001, CohOptions, coh001};

fn verdict(path: &str, lang: &str, text: &str) -> Coh001 {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    let folded = fold_file(&entry, text).expect("fold");
    let unit: NodeId = folded
        .term
        .ids()
        .find(|&i| {
            matches!(folded.term.node(i).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
                && folded.term.node(i).name() == Some("f")
        })
        .expect("function f");
    coh001(&folded, lang, unit, &CohOptions::default()).expect("supported language")
}

macro_rules! lang_tests {
    ($fire:ident, $clean:ident, $unres:ident, $lang:literal, $ext:literal) => {
        // frob:tests crates/grimble-check/src/coh001.rs::judge
        #[test]
        fn $fire() {
            let v = verdict(
                concat!("fire.", $ext),
                $lang,
                include_str!(concat!("fixtures/coh001/fire.", $ext)),
            );
            let Coh001::Fire { lo, fixes, .. } = v else {
                panic!("expected Fire, got {v:?}")
            };
            assert_eq!(lo, 2);
            assert_eq!(fixes.len(), 2);
            assert!(fixes.iter().all(|f| f.statements.len() == 2));
        }

        // frob:tests crates/grimble-check/src/coh001.rs::judge
        #[test]
        fn $clean() {
            let v = verdict(
                concat!("clean.", $ext),
                $lang,
                include_str!(concat!("fixtures/coh001/clean.", $ext)),
            );
            assert_eq!(v, Coh001::Clean);
        }

        // frob:tests crates/grimble-check/src/coh001.rs::judge
        #[test]
        fn $unres() {
            let v = verdict(
                concat!("unresolved.", $ext),
                $lang,
                include_str!(concat!("fixtures/coh001/unresolved.", $ext)),
            );
            let Coh001::Unresolved { lo, hi, witnesses } = v else {
                panic!("expected Unresolved, got {v:?}")
            };
            assert!(lo < 2 && hi >= 2, "lo {lo} hi {hi}");
            assert!(!witnesses.is_empty());
        }
    };
}

lang_tests!(
    coh001_python_fire,
    coh001_python_clean,
    coh001_python_unresolved,
    "python",
    "py"
);
lang_tests!(
    coh001_rust_fire,
    coh001_rust_clean,
    coh001_rust_unresolved,
    "rust",
    "rs"
);
lang_tests!(
    coh001_typescript_fire,
    coh001_typescript_clean,
    coh001_typescript_unresolved,
    "typescript",
    "ts"
);
