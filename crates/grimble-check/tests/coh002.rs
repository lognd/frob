//! COH002 verdicts over fire, clean and unresolved fixtures in each supported language.

// frob:ticket 01M4CXSRE3YHY7FV30R8GMB58A

#![allow(unused_crate_dependencies)]

use gob_ir::{NodeId, Operator, Universal};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh002::{Coh002, Coh002Options, Coh002Unresolved, UnitRole, coh002};

fn verdict(path: &str, lang: &str, text: &str, role: UnitRole) -> Coh002 {
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
    coh002(&folded, lang, unit, role, &Coh002Options::default()).expect("supported language")
}

macro_rules! lang_tests {
    ($fire:ident, $clean:ident, $unres:ident, $shell:ident, $lang:literal, $ext:literal) => {
        // frob:tests crates/grimble-check/src/coh002.rs::judge
        #[test]
        fn $fire() {
            let text = include_str!(concat!("fixtures/coh002/fire.", $ext));
            let v = verdict(concat!("fire.", $ext), $lang, text, UnitRole::None);
            let Coh002::Fire { decisions, .. } = v else {
                panic!("expected Fire, got {v:?}")
            };
            assert_eq!(decisions.len(), 1);
            assert_eq!(decisions[0].effects[0].callee, "send");
            let v = verdict(concat!("fire.", $ext), $lang, text, UnitRole::Core);
            assert!(
                matches!(
                    v,
                    Coh002::Fire {
                        role: UnitRole::Core,
                        ..
                    }
                ),
                "{v:?}"
            );
        }

        // frob:tests crates/grimble-check/src/coh002.rs::judge
        #[test]
        fn $clean() {
            let text = include_str!(concat!("fixtures/coh002/clean.", $ext));
            let v = verdict(concat!("clean.", $ext), $lang, text, UnitRole::None);
            assert_eq!(v, Coh002::Clean);
        }

        // frob:tests crates/grimble-check/src/coh002.rs::judge
        #[test]
        fn $unres() {
            let text = include_str!(concat!("fixtures/coh002/unresolved.", $ext));
            let v = verdict(concat!("unresolved.", $ext), $lang, text, UnitRole::None);
            assert_eq!(
                v,
                Coh002::Unresolved(Coh002Unresolved::UnknownCallees {
                    callees: vec!["mystery".to_owned()]
                })
            );
        }

        // frob:tests crates/grimble-check/src/coh002.rs::judge
        #[test]
        fn $shell() {
            let text = include_str!(concat!("fixtures/coh002/fire.", $ext));
            let ok = verdict(
                concat!("fire.", $ext),
                $lang,
                text,
                UnitRole::Shell { verified: true },
            );
            assert_eq!(ok, Coh002::Clean);
            let bad = verdict(
                concat!("fire.", $ext),
                $lang,
                text,
                UnitRole::Shell { verified: false },
            );
            assert!(
                matches!(
                    bad,
                    Coh002::Unresolved(Coh002Unresolved::UnverifiedShell { .. })
                ),
                "{bad:?}"
            );
        }
    };
}

lang_tests!(fire_py, clean_py, unres_py, shell_py, "python", "py");
lang_tests!(fire_rs, clean_rs, unres_rs, shell_rs, "rust", "rs");
lang_tests!(fire_ts, clean_ts, unres_ts, shell_ts, "typescript", "ts");
