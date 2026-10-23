//! `status`: grant count, breadth and the delta since `grimble.lock` (the grant ratchet).
//!
//! The current model is bound over the working tree; the baseline is the model as of the newest
//! first-parent commit that changed `grimble.lock`. Both are measured over the SAME current walk,
//! so a delta is a grant that changed, never a repo that grew. Without a committed lock there is
//! no baseline: counts only, `baseline: none`.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67
// frob:ticket 01M4GYBZZB9Z4QPMW451DC0JFG

use std::fmt::Write as _;
use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_git::Repo;
use gob_walk::WalkResult;
use grimble_bind::grants::{self, GrantFacts, Ratchet};
use grimble_bind::model as bind_model;
use grimble_check::MODEL_EXTENSION;
use grimble_check::config::GrimbleTable;
use grimble_model::ModelFiles;
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, config_refusal, locate_root};

/// Most first-parent commits searched for the commit that last changed the lock.
const LOCK_SEARCH_LIMIT: usize = 2000;
/// The lock file, repo-relative.
const LOCK: &str = grimble_bind::drift::LOCK_ANCHOR;

/// Report grant count, breadth per node and the delta since the lock.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "status",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Status;

/// `Status` takes no flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct StatusArgs {}

/// One node's grants now and at the baseline.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct NodeRow {
    /// The node anchor.
    pub node: String,
    /// Grants now.
    pub grants: usize,
    /// Distinct files the node's grants cover now.
    pub breadth: usize,
    /// Grants at the lock; absent without a baseline.
    pub base_grants: Option<usize>,
    /// Distinct files covered at the lock; absent without a baseline.
    pub base_breadth: Option<usize>,
}

/// One grant that differs from the lock.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ChangeRow {
    /// The node anchor.
    pub node: String,
    /// The grant as written.
    pub grant: String,
    /// `added`, `widened`, `narrowed` or `removed`.
    pub change: String,
    /// Files covered at the lock.
    pub before: usize,
    /// Files covered now.
    pub after: usize,
}

/// Output of `status`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct StatusData {
    /// The commit whose model is the baseline; absent when there is none (no committed lock).
    pub baseline: Option<String>,
    /// Total grants now.
    pub grants: usize,
    /// Total grants at the baseline.
    pub base_grants: Option<usize>,
    /// Per-node counts and breadth.
    pub nodes: Vec<NodeRow>,
    /// Grants that differ from the lock, widenings first.
    pub changes: Vec<ChangeRow>,
    /// Names of the widened grants, `node: grant`.
    pub widened: Vec<String>,
    /// Current grants that state no `because=` or `ticket=`.
    pub unreasoned: Vec<String>,
    /// Every-atom grants at a broad glob: declared trust zones, covered but not enforced.
    pub trust_zones: Vec<ZoneRow>,
    /// Distinct files covered by any trust zone (overlapping zones count a file once).
    pub trust_zone_files: usize,
    /// Nodes with a code-owning selector, the subjects of the capability rules.
    pub gated_nodes: usize,
    /// Nodes with no code-owning selector (not external): no capability rule judges them.
    pub ungated_nodes: Vec<String>,
    /// External nodes, which own no code by definition and are not counted as ungated.
    pub external_nodes: usize,
}

/// One trust zone: a node granting every atom at one broad glob.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ZoneRow {
    /// The node anchor.
    pub node: String,
    /// The glob the atoms are granted at.
    pub at: String,
    /// Distinct files the zone covers.
    pub files: usize,
}

impl Command for Status {
    type Data = StatusData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<StatusArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        gob_cli::parse::<StatusArgs>(m)?;
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<StatusData> {
        let root = locate_root(&ctx.cwd);
        let entries = grimble_check::walk_repo(&root).map_err(check_error)?;
        let table = GrimbleTable::load(&root).map_err(|e| config_refusal(&e))?;
        let content = gob_walk::ContentSource::locate(&root);
        let current_files = content.with_reader(|r| {
            grimble_check::read_models(&root, &entries, &table, &mut |p| r.read(p))
        });
        let walk = WalkResult {
            files: entries,
            oversized: Vec::new(),
        };
        let current = bind_model::load(&current_files);
        let now = grants::facts(&current, &walk);
        let base = baseline(&root, &table);
        let base_facts = base
            .as_ref()
            .map(|(_, files)| grants::facts(&bind_model::load(files), &walk));
        let report = grants::ratchet(&now, base_facts.as_deref());
        let zones = grants::trust_zones(&now, &grants::leaf_atoms());
        let gating = grants::gating(&current);
        let mut data = to_data(
            &report,
            base.map(|(rev, _)| rev),
            &now,
            base_facts.as_deref(),
        );
        add_coverage(&mut data, &zones, gating);
        Ok(Payload::new(data.clone()).with_rendered(render(&data)))
    }
}

fn to_data(
    r: &Ratchet,
    rev: Option<String>,
    now: &[GrantFacts],
    base: Option<&[GrantFacts]>,
) -> StatusData {
    let changes: Vec<ChangeRow> = r
        .changes
        .iter()
        .map(|c| ChangeRow {
            node: c.node.clone(),
            grant: c.grant.clone(),
            change: c.kind.as_str().to_owned(),
            before: c.before,
            after: c.after,
        })
        .collect();
    let widened = r
        .changes
        .iter()
        .filter(|c| c.kind == grants::ChangeKind::Widened)
        .map(|c| format!("{}: {}", c.node, c.grant))
        .collect();
    StatusData {
        baseline: rev,
        grants: now.len(),
        base_grants: base.map(<[_]>::len),
        nodes: r
            .nodes
            .iter()
            .map(|n| NodeRow {
                node: n.node.clone(),
                grants: n.grants,
                breadth: n.breadth,
                base_grants: n.base_grants,
                base_breadth: n.base_breadth,
            })
            .collect(),
        changes,
        widened,
        unreasoned: r.unreasoned.clone(),
        trust_zones: Vec::new(),
        trust_zone_files: 0,
        gated_nodes: 0,
        ungated_nodes: Vec::new(),
        external_nodes: 0,
    }
}

/// Fill the trust zone and ungated-node sections, so coverage is never read as enforcement.
fn add_coverage(d: &mut StatusData, zones: &grants::Zones, gating: grants::Gating) {
    d.trust_zones = zones
        .zones
        .iter()
        .map(|z| ZoneRow {
            node: z.node.clone(),
            at: z.at.clone(),
            files: z.files,
        })
        .collect();
    d.trust_zone_files = zones.files;
    d.gated_nodes = gating.gated;
    d.external_nodes = gating.external;
    d.ungated_nodes = gating.ungated;
}

/// Human lines: totals, one row per node, then the changes with widenings named.
fn render(d: &StatusData) -> Vec<String> {
    let mut out = Vec::new();
    let mut head = format!("grants: {}", d.grants);
    match (&d.baseline, d.base_grants) {
        (Some(rev), Some(was)) => {
            let _ = write!(head, " (was {was} at {rev}, {:+})", signed(d.grants, was));
        }
        _ => head.push_str(" (baseline: none, no committed grimble.lock)"),
    }
    out.push(head);
    for n in &d.nodes {
        let mut line = format!("  {}: {} grants, {} files", n.node, n.grants, n.breadth);
        if let (Some(g), Some(b)) = (n.base_grants, n.base_breadth) {
            let _ = write!(
                line,
                " (was {g} grants, {b} files; {:+}, {:+})",
                signed(n.grants, g),
                signed(n.breadth, b)
            );
        }
        out.push(line);
    }
    for c in &d.changes {
        out.push(format!(
            "{}: {} {} ({} -> {} files)",
            c.change, c.node, c.grant, c.before, c.after
        ));
    }
    for u in &d.unreasoned {
        out.push(format!("no reason: {u}"));
    }
    out.push(format!(
        "trust zones: {} ({} files; every atom granted, declared not enforced)",
        d.trust_zones.len(),
        d.trust_zone_files
    ));
    for z in &d.trust_zones {
        out.push(format!(
            "  zone: {} at {} ({} files)",
            z.node, z.at, z.files
        ));
    }
    out.push(format!(
        "ungated nodes: {} ({} gated, {} external; no code-owning selector, no capability check)",
        d.ungated_nodes.len(),
        d.gated_nodes,
        d.external_nodes
    ));
    for n in &d.ungated_nodes {
        out.push(format!("  ungated: {n}"));
    }
    out
}

fn signed(now: usize, was: usize) -> i64 {
    i64::try_from(now).unwrap_or(i64::MAX) - i64::try_from(was).unwrap_or(i64::MAX)
}

/// The model as of the newest commit that changed the lock, with that commit's short id.
///
/// `None` when there is no repo, no committed lock, or the history cannot be read.
fn baseline(root: &Path, table: &GrimbleTable) -> Option<(String, ModelFiles)> {
    let repo = Repo::discover(root).ok()?;
    let commits = repo
        .first_parent_subjects("HEAD", LOCK_SEARCH_LIMIT)
        .map_err(|err| tracing::warn!(%err, "history unreadable; no grant baseline"))
        .ok()?;
    let head = repo.read_blob_at("HEAD", LOCK).ok()??;
    // Walk back until the lock content differs: the commit before that one wrote this lock.
    let mut lock_commit = commits.first()?.0;
    for (oid, _) in &commits {
        let same = repo
            .read_blob_at(&oid.to_string(), LOCK)
            .ok()
            .flatten()
            .is_some_and(|b| b == head);
        if !same {
            break;
        }
        lock_commit = *oid;
    }
    let rev = lock_commit.to_string();
    tracing::info!(%rev, "grant baseline is the commit that last wrote the lock");
    let mut files = ModelFiles::new();
    let mut walk = Vec::new();
    for (path, oid) in repo.blobs_at(&rev).ok()? {
        walk.push(path.clone());
        if path.ends_with(MODEL_EXTENSION)
            && let Ok(bytes) = repo.read_blob(&oid)
        {
            files.files.insert(path, bytes);
        }
    }
    files.walk = Some(walk);
    let files = files.with_declared_roots(table.models.clone());
    Some((rev.chars().take(10).collect(), files))
}
