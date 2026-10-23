//! The layer source of COH003 (cohesion.md 1.2): which layer each callee sits on.
//!
//! Two sources, tried in this order and never mixed:
//!
//! 1. The grimble model. A `node` that declares `attr layer = N;` and `owns SEL;` puts every
//!    function defined in a file the selector surely matches on layer `N`. A file owned by no
//!    layered node, or by layered nodes that disagree, has no layer.
//! 2. Module depth, used only when the model declares no layer at all. A function defined in a
//!    deeper directory is a lower-level helper: the layer is the distance to the deepest file,
//!    above the primitive layer. When every file sits at one depth the depth says nothing, so no
//!    layer is produced.
//!
//! The two scales are not comparable, so a partial model does not fall back per file: the files
//! it leaves out stay unplaced and COH003 reports their callees as Unresolved instead of guessing.
//! A callee name defined in several files is placed only when every definition agrees.

// frob:ticket 01M5HJDX1Q27XGZ77ACWXQ03KP
// frob:ticket 01M5M1TVWKJPZX3BMF736VJAHT

use std::collections::{BTreeMap, BTreeSet};

use gob_symbols::Folded;
use gob_walk::Selector;
use gob_walk::selector::Tri;
use grimble_bind::owner::PathLeaves;
use grimble_model::ModelFiles;
use grimble_model::ast::{ClauseKind, EntityKind, Value};
use grimble_model::model::{Index, load_roots};
use tracing::{debug, warn};

use crate::coh_pass::function_units;
use crate::coh003::Coh003Options;

/// The attribute key a model node carries its layer in.
pub const LAYER_ATTR: &str = "layer";

/// Where the layers of a run came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LayerSource {
    /// `attr layer` of the grimble model's nodes.
    Model,
    /// The depth of the directory a function is defined in.
    ModuleDepth,
    /// Neither source placed anything.
    None,
}

/// One model node that declares a layer and the paths it owns.
#[derive(Debug, Clone)]
struct LayeredNode {
    /// The node's declared name.
    name: String,
    /// The declared layer.
    layer: u32,
    /// The parsed `owns` selectors.
    owns: Vec<Selector>,
}

/// The layered nodes of a grimble model.
#[derive(Debug, Clone, Default)]
pub struct ModelLayers {
    nodes: Vec<LayeredNode>,
}

/// What the model says about one file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FileLayer {
    /// Exactly one layer is declared for the file.
    At(u32),
    /// Layered nodes owning the file declare different layers.
    Conflict(Vec<String>),
    /// No layered node surely owns the file.
    Unowned,
}

/// The layer a node's clauses declare: none, one, or `Err` when two values disagree or one is not a number.
fn declared_layer(name: &str, clauses: &[grimble_model::ast::Clause]) -> Result<Option<u32>, ()> {
    let mut seen: BTreeSet<u32> = BTreeSet::new();
    for c in clauses {
        let ClauseKind::Attr { key, value } = &c.kind else {
            continue;
        };
        if key.text != LAYER_ATTR {
            continue;
        }
        let parsed = match value.as_ref().map(|v| &v.value) {
            Some(Value::Number(n)) => n.parse::<u32>().ok(),
            _ => None,
        };
        let Some(layer) = parsed else {
            warn!(
                node = name,
                "layer attribute is not a non-negative integer; node ignored"
            );
            return Err(());
        };
        seen.insert(layer);
    }
    match seen.len() {
        0 => Ok(None),
        1 => Ok(seen.pop_first()),
        _ => {
            warn!(node = name, layers = ?seen, "node declares several layers; node ignored");
            Err(())
        }
    }
}

impl ModelLayers {
    /// Read the layered nodes out of `files`; nodes without a layer, or with an unreadable one, are skipped.
    pub fn from_model(files: &ModelFiles) -> Self {
        let mut nodes = Vec::new();
        for root in &load_roots(files) {
            let idx = Index::build(root);
            for rec in &idx.entities {
                let e = rec.entity;
                if e.kind != EntityKind::Node || e.extension {
                    continue;
                }
                let Ok(Some(layer)) = declared_layer(&rec.full, &e.clauses) else {
                    continue;
                };
                let owns = e
                    .clauses
                    .iter()
                    .filter_map(|c| {
                        let ClauseKind::Owns(sel) = &c.kind else {
                            return None;
                        };
                        if let Ok(parsed) = &sel.parsed {
                            Some(parsed.clone())
                        } else {
                            warn!(node = %rec.full, selector = %sel.text, "unparsable owns selector skipped");
                            None
                        }
                    })
                    .collect();
                nodes.push(LayeredNode {
                    name: rec.full.clone(),
                    layer,
                    owns,
                });
            }
        }
        debug!(layered_nodes = nodes.len(), "model layers read");
        Self { nodes }
    }

    /// True when the model declares no layer anywhere.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    /// The layer the model gives the file at `path`.
    #[must_use]
    pub fn layer_of(&self, path: &str) -> FileLayer {
        let leaves = PathLeaves::new(path);
        let owners: Vec<&LayeredNode> = self
            .nodes
            .iter()
            .filter(|n| n.owns.iter().any(|s| s.truth(&leaves) == Tri::Yes))
            .collect();
        let layers: BTreeSet<u32> = owners.iter().map(|n| n.layer).collect();
        match layers.len() {
            0 => FileLayer::Unowned,
            1 => FileLayer::At(owners[0].layer),
            _ => FileLayer::Conflict(owners.iter().map(|n| n.name.clone()).collect()),
        }
    }
}

/// The function names one file defines.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Definitions {
    /// Repo-relative path of the file.
    pub path: String,
    /// Names of the file's function units.
    pub functions: BTreeSet<String>,
}

/// The function names defined in the folded file at `path`.
pub fn definitions(path: &str, folded: &Folded) -> Definitions {
    let functions = function_units(folded)
        .into_iter()
        .filter_map(|u| folded.term.node(u).name().map(str::to_owned))
        .collect();
    Definitions {
        path: path.to_owned(),
        functions,
    }
}

/// The callee-to-layer table of a run and where it came from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CalleeLayers {
    /// Which source produced the table.
    pub source: LayerSource,
    /// Callee name to layer; names no source places are absent.
    pub layers: BTreeMap<String, u32>,
}

/// The number of directories above a repo-relative path.
fn depth_of(path: &str) -> u32 {
    u32::try_from(path.matches('/').count()).unwrap_or(u32::MAX)
}

/// The layer of each file under module depth: one above the primitive layer for the deepest file.
fn depth_layers(defs: &[Definitions], primitive_layer: u32) -> Vec<Option<u32>> {
    let depths: Vec<u32> = defs.iter().map(|d| depth_of(&d.path)).collect();
    let (Some(&deepest), Some(&shallowest)) = (depths.iter().max(), depths.iter().min()) else {
        return Vec::new();
    };
    if deepest == shallowest {
        debug!(
            depth = deepest,
            "every file at one depth; module depth places nothing"
        );
        return vec![None; defs.len()];
    }
    depths
        .iter()
        .map(|d| {
            Some(
                primitive_layer
                    .saturating_add(1)
                    .saturating_add(deepest - d),
            )
        })
        .collect()
}

/// Fold per-file layers into a table: a name is placed when all its definitions share one layer.
fn fold_names(defs: &[Definitions], per_file: &[Option<u32>]) -> BTreeMap<String, u32> {
    let mut by_name: BTreeMap<&str, Option<u32>> = BTreeMap::new();
    for (d, &layer) in defs.iter().zip(per_file) {
        for f in &d.functions {
            by_name
                .entry(f)
                .and_modify(|cur| {
                    if *cur != layer {
                        *cur = None;
                    }
                })
                .or_insert(layer);
        }
    }
    by_name
        .into_iter()
        .filter_map(|(n, l)| l.map(|l| (n.to_owned(), l)))
        .collect()
}

/// Place every defined function on a layer: from the model when it declares any layer, else from module depth.
pub fn callee_layers(
    model: &ModelLayers,
    defs: &[Definitions],
    primitive_layer: u32,
) -> CalleeLayers {
    let (source, per_file) = if model.is_empty() {
        (
            LayerSource::ModuleDepth,
            depth_layers(defs, primitive_layer),
        )
    } else {
        let per_file = defs
            .iter()
            .map(|d| match model.layer_of(&d.path) {
                FileLayer::At(l) => Some(l),
                other => {
                    debug!(file = %d.path, ?other, "model places no layer on file");
                    None
                }
            })
            .collect();
        (LayerSource::Model, per_file)
    };
    let layers = fold_names(defs, &per_file);
    let source = if layers.is_empty() {
        LayerSource::None
    } else {
        source
    };
    debug!(?source, placed = layers.len(), "callee layers built");
    CalleeLayers { source, layers }
}

/// COH003 options with `layers` filled from the model, falling back to module depth.
#[must_use]
pub fn coh003_options(model: &ModelLayers, defs: &[Definitions]) -> Coh003Options {
    let mut opts = Coh003Options::default();
    opts.layers = callee_layers(model, defs, opts.primitive_layer).layers;
    opts
}
