//! Persistence of the linked call resolution (`link_calls`), keyed by everything it reads.
//!
//! Resolving every call site is the largest single cost of a warm graph build, yet its
//! result is a pure function of the per-file symbols, the checker facts and the manifest
//! data read through `CrateDeps`. The merged result is therefore stored in the artifact
//! cache under a digest of exactly those inputs and replayed on a hit. A payload that
//! fails to decode, or names a node the graph does not have, is a miss, never an error.

use std::collections::{HashMap, HashSet};
use std::fmt::Debug;

use gob_cache::{ArtifactKey, Cache};
use petgraph::graph::NodeIndex;
use serde::{Deserialize, Serialize};

use super::csharp::CsIndex;
use super::typescript::TsIndex;
use super::{CallEdge, CallSink, EdgeKind, Index, StatusEdge};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::types::TypeFacts;
use gob_ir::Status;

/// Bump when call resolution changes what it produces, so stored results are not replayed (mirrors `EXTRACTOR_VERSION`).
pub const LINK_VERSION: u32 = 1;

/// Hashes the per-file inputs of a build (path, content digest, adapter identity) into a cache key part.
#[derive(Default)]
pub struct InputsHasher(blake3::Hasher);

impl InputsHasher {
    /// Starts an empty hash.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds one file: its path, content digest and adapter identity (`opaque` when it has none).
    pub fn add(&mut self, path: &str, digest: &str, identity: &str) {
        for part in [path, digest, identity] {
            self.0.update(&(part.len() as u64).to_le_bytes());
            self.0.update(part.as_bytes());
        }
    }

    /// The hex digest of everything added.
    pub fn finish(&self) -> String {
        self.0.finalize().to_hex().to_string()
    }
}

/// Where to keep the linked call resolution, and the digest of the files it was computed from.
pub struct LinkCache<'a> {
    cache: &'a Cache,
    inputs: String,
}

/// The stored form of a [`CallSink`]; node indices are plain integers, checked on load.
#[derive(Serialize, Deserialize)]
struct Stored {
    nodes: u32,
    links: Vec<(u32, u32, EdgeKind, u8)>,
    calls: Vec<CallEdge>,
    status_edges: Vec<StatusEdge>,
    poisoned: Vec<u32>,
}

impl<'a> LinkCache<'a> {
    /// Keeps results in `cache`, valid for the file inputs digested as `inputs` (see [`InputsHasher`]).
    pub fn new(cache: &'a Cache, inputs: String) -> Self {
        Self { cache, inputs }
    }

    /// The artifact key of a resolution over these inputs, `facts` and the manifest-derived `deps` digest.
    pub(super) fn key(&self, facts: &TypeFacts, deps: &str) -> String {
        let mut h = blake3::Hasher::new();
        h.update(format!("{LINK_VERSION}/{EXTRACTOR_VERSION}/{facts:?}/{deps}").as_bytes());
        h.update(self.inputs.as_bytes());
        h.finalize().to_hex().to_string()
    }

    fn artifact(key: &str) -> ArtifactKey {
        ArtifactKey {
            content_digest: key.to_owned(),
            producer_identity: format!("link-calls-v{LINK_VERSION}"),
        }
    }

    /// The stored resolution under `key`, when it decodes and fits a graph of `nodes` nodes.
    pub(super) fn load(&self, key: &str, nodes: usize) -> Option<CallSink> {
        if self.cache.is_null() {
            return None;
        }
        let Some(bytes) = self.cache.get_artifact(&Self::artifact(key)) else {
            tracing::debug!("link cache miss");
            return None;
        };
        let stored: Stored = match postcard::from_bytes::<Stored>(&bytes) {
            Ok(s) => s,
            Err(err) => {
                tracing::warn!(%err, "link cache payload undecodable");
                return None;
            }
        };
        let sink = stored.into_sink(nodes);
        if sink.is_none() {
            tracing::warn!("link cache payload does not fit the graph");
        }
        sink
    }

    /// Keeps `sink` (computed over a graph of `nodes` nodes) under `key`; failure only costs the next build.
    pub(super) fn store(&self, key: &str, sink: &CallSink, nodes: usize) {
        if self.cache.is_null() {
            return;
        }
        match postcard::to_stdvec(&Stored::of(sink, nodes)) {
            Ok(bytes) => self.cache.put_artifact(&Self::artifact(key), &bytes),
            Err(err) => tracing::warn!(%err, "link cache payload not serializable"),
        }
    }
}

fn ix(n: NodeIndex) -> u32 {
    u32::try_from(n.index()).unwrap_or(u32::MAX)
}

impl Stored {
    fn of(sink: &CallSink, nodes: usize) -> Self {
        Self {
            nodes: u32::try_from(nodes).unwrap_or(u32::MAX),
            links: sink
                .links
                .iter()
                .map(|&(a, b, k, s)| (ix(a), ix(b), k, status_to_u8(s)))
                .collect(),
            calls: sink.calls.clone(),
            status_edges: sink.status_edges.clone(),
            poisoned: sink.poisoned.iter().map(|&n| ix(n)).collect(),
        }
    }

    fn into_sink(self, nodes: usize) -> Option<CallSink> {
        if self.nodes as usize != nodes {
            return None;
        }
        let ok = |n: u32| (n as usize) < nodes;
        if !self
            .links
            .iter()
            .all(|&(a, b, _, s)| ok(a) && ok(b) && s <= 2)
            || !self.poisoned.iter().all(|&n| ok(n))
        {
            return None;
        }
        Some(CallSink {
            links: self
                .links
                .into_iter()
                .map(|(a, b, k, s)| {
                    (
                        NodeIndex::new(a as usize),
                        NodeIndex::new(b as usize),
                        k,
                        status_of_u8(s),
                    )
                })
                .collect(),
            calls: self.calls,
            status_edges: self.status_edges,
            poisoned: self
                .poisoned
                .into_iter()
                .map(|n| NodeIndex::new(n as usize))
                .collect(),
        })
    }
}

fn status_to_u8(s: Status) -> u8 {
    match s {
        Status::Unknown => 0,
        Status::May => 1,
        Status::Must => 2,
    }
}

fn status_of_u8(n: u8) -> Status {
    match n {
        0 => Status::Unknown,
        1 => Status::May,
        _ => Status::Must,
    }
}

/// Serde adapter for [`Status`], which lives in a crate without serde.
pub(super) mod status_serde {
    use gob_ir::Status;
    use serde::{Deserialize, Deserializer, Serializer};

    /// Writes the status as its rank (0 Unknown, 1 May, 2 Must).
    #[allow(clippy::trivially_copy_pass_by_ref)] // serde `with` requires a reference
    // frob:defer DEAD001 because="named by a serde `with` attribute string, which the call graph cannot see" ticket=01M61DFC5ZCSJTKMNBP88AKFVS
    pub fn serialize<S: Serializer>(s: &Status, ser: S) -> Result<S::Ok, S::Error> {
        ser.serialize_u8(super::status_to_u8(*s))
    }

    /// Reads a status written by [`serialize`]; any other rank is an error.
    // frob:defer DEAD001 because="named by a serde `with` attribute string, which the call graph cannot see" ticket=01M61DFC5ZCSJTKMNBP88AKFVS
    pub fn deserialize<'de, D: Deserializer<'de>>(de: D) -> Result<Status, D::Error> {
        match u8::deserialize(de)? {
            n @ 0..=2 => Ok(super::status_of_u8(n)),
            n => Err(serde::de::Error::custom(format!("bad status rank {n}"))),
        }
    }
}

impl CallSink {
    /// Joins chunk results in order, which is the order `merge_sink` replays them.
    pub(super) fn concat(sinks: Vec<CallSink>) -> CallSink {
        let mut out = CallSink::default();
        for s in sinks {
            out.links.extend(s.links);
            out.calls.extend(s.calls);
            out.status_edges.extend(s.status_edges);
            out.poisoned.extend(s.poisoned);
        }
        out
    }
}

/// Feeds `map` into `h` in key order under `tag` (hash-map iteration order is not stable).
pub(super) fn feed_sorted<K: Ord + Debug, V: Debug>(
    h: &mut blake3::Hasher,
    tag: &str,
    map: &HashMap<K, V>,
) {
    let mut rows: Vec<(&K, &V)> = map.iter().collect();
    rows.sort_by(|a, b| a.0.cmp(b.0));
    h.update(tag.as_bytes());
    h.update(format!("{rows:?}").as_bytes());
}

fn feed_set(h: &mut blake3::Hasher, tag: &str, set: &HashSet<String>) {
    let mut rows: Vec<&String> = set.iter().collect();
    rows.sort();
    h.update(tag.as_bytes());
    h.update(format!("{rows:?}").as_bytes());
}

/// Digest of every table the manifest data (`CrateDeps`) shaped; the rest of the index follows from the files.
pub(super) fn deps_digest(idx: &Index) -> String {
    let mut h = blake3::Hasher::new();
    feed_set(&mut h, "unowned", &idx.unowned);
    h.update(format!("{:?}", idx.all_crates).as_bytes());
    feed_sorted(&mut h, "file_crate", &idx.file_crate);
    feed_sorted(&mut h, "externs", &idx.externs);
    feed_sorted(&mut h, "reach", &idx.reach);
    let (cs, ts): (&CsIndex, &TsIndex) = (&idx.cs, &idx.ts);
    cs.feed_deps(&mut h);
    ts.feed_deps(&mut h);
    h.finalize().to_hex().to_string()
}
