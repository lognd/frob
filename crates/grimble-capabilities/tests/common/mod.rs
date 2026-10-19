//! A tiny line format for building pack-pass inputs in tests and corpus pages.
//!
//! Lines: `lock NAME VER TREE [K=D ..]`, `live NAME VER TREE [K=D ..]`,
//! `unavailable NAME [required]`, `issue KIND PACK [ARG..]`.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

use std::collections::BTreeMap;

use gob_packs::lock::{Lock, LockedPack};
use grimble_capabilities::pack_rules::{PackIssue, PackState};

/// The parsed inputs of the pack pass.
#[derive(Default)]
pub struct Input {
    /// The lock, when any `lock` line is present.
    pub lock: Option<Lock>,
    /// The enabled packs.
    pub packs: Vec<PackState>,
    /// The per-pack issues.
    pub issues: Vec<PackIssue>,
}

/// One pack from `NAME VER TREE [K=D ..]` fields.
fn pack(f: &[&str]) -> LockedPack {
    let items: BTreeMap<String, String> = f[3..]
        .iter()
        .filter_map(|kv| kv.split_once('='))
        .map(|(k, d)| (k.to_owned(), d.to_owned()))
        .collect();
    LockedPack {
        name: f[0].to_owned(),
        version: f[1].to_owned(),
        tree: f[2].to_owned(),
        effects: BTreeMap::new(),
        items,
    }
}

/// Parse `text` into pack-pass inputs; a bad line is a test bug and panics.
pub fn parse(text: &str) -> Input {
    let mut inp = Input::default();
    let mut locked = Vec::new();
    let mut has_lock = false;
    for line in text.lines().filter(|l| !l.trim().is_empty()) {
        let f: Vec<&str> = line.split_whitespace().collect();
        match f[0] {
            "lock" => {
                has_lock = true;
                locked.push(pack(&f[1..]));
            }
            "live" => inp.packs.push(PackState::Loaded(pack(&f[1..]))),
            "unavailable" => inp.packs.push(PackState::Unavailable {
                name: f[1].to_owned(),
                required: f.get(2) == Some(&"required"),
            }),
            "issue" => {
                let (p, a) = (f[2].to_owned(), f[3..].join(" "));
                inp.issues.push(match f[1] {
                    "unknown-atom" => PackIssue::UnknownAtom { pack: p, atom: a },
                    "detector-unavailable" => PackIssue::DetectorUnavailable {
                        pack: p,
                        detector: a,
                    },
                    "duplicate" => PackIssue::Duplicate { pack: p, key: a },
                    "malformed" => PackIssue::Malformed { pack: p, detail: a },
                    "unknown-infer-rule" => PackIssue::UnknownInferRule { pack: p, rule: a },
                    "redundant-override" => PackIssue::RedundantOverride { pack: p, key: a },
                    k => panic!("unknown issue kind {k}"),
                });
            }
            k => panic!("unknown line kind {k}"),
        }
    }
    if has_lock {
        inp.lock = Some(Lock::new(locked));
    }
    inp
}
