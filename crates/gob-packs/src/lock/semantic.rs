//! Semantic item digests: the pack's findings-relevant content, documentation excluded.

use std::collections::BTreeMap;
use std::fmt::Write as _;

use super::LockedPack;
use crate::digest::{Digest, to_hex};
use crate::manifest::Manifest;
use crate::tier1::Content;

/// Digests one canonical item string as `blake3:` plus hex.
pub fn item_digest(canonical: &str) -> String {
    format!("blake3:{}", blake3::hash(canonical.as_bytes()).to_hex())
}

fn strs(v: &[String]) -> String {
    let mut s = String::from("[");
    for (i, x) in v.iter().enumerate() {
        if i > 0 {
            s.push(',');
        }
        let _ = write!(s, "{x:?}");
    }
    s.push(']');
    s
}

fn sorted(v: &[String]) -> Vec<String> {
    let mut o = v.to_vec();
    o.sort();
    o.dedup();
    o
}

/// Snapshots a live pack into the lock's shape: tree digest plus semantic item digests of
/// `content` (documentary `doc` text is never parsed into [`Content`], so it cannot matter).
pub fn snapshot(manifest: &Manifest, content: Option<&Content>, tree: &Digest) -> LockedPack {
    let mut items: BTreeMap<String, String> = BTreeMap::new();
    if let Some(c) = content {
        for a in &c.atoms {
            let canon = format!("{:?}{}", a.name, strs(&sorted(&a.aliases)));
            items.insert(format!("atom:{}", a.name), item_digest(&canon));
        }
        for v in &c.vocabs {
            let canon = format!("{:?}{:?}{}", v.lang, v.class, strs(&sorted(&v.names)));
            items.insert(format!("vocab:{}/{}", v.lang, v.class), item_digest(&canon));
        }
        let mut seen: BTreeMap<String, usize> = BTreeMap::new();
        for d in &c.detectors {
            let kind = format!("{:?}", d.kind).to_lowercase();
            let base = format!("detector:{}/{}/{kind}", d.atom, d.lang);
            let n = seen.entry(base.clone()).or_insert(0);
            let key = if *n == 0 { base } else { format!("{base}#{n}") };
            *n += 1;
            let canon = format!("{:?}{:?}{:?}", d.atom, d.lang, d.kind);
            items.insert(key, item_digest(&canon));
        }
        for t in &c.templates {
            let canon = format!("{:?}{:?}{:?}{:?}", t.name, t.atom, t.selector, t.reason);
            items.insert(format!("template:{}", t.name), item_digest(&canon));
        }
    }
    tracing::debug!(pack = %manifest.pack.name, items = items.len(), "pack snapshot built");
    LockedPack {
        name: manifest.pack.name.clone(),
        version: manifest.pack.version.clone(),
        tree: format!("blake3:{}", to_hex(tree)),
        effects: manifest.effects.clone(),
        items,
    }
}
