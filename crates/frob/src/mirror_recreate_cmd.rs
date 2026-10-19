//! `mirror recreate`: a person-run replacement of an issue the tracker deleted (mirror.md 3.3).
//!
//! The mirror never recreates an issue by itself. A person runs recreate for a ticket whose issue
//! returned 410; the old identity is dropped from the shard and a new issue is made through the
//! create protocol, after which the ticket is mirrored again. A 404 is refused: the token may
//! simply be unable to see the issue, so it is not known to be deleted. `recreate` is the
//! transport-free core; `MirrorRecreate` is the verb that supplies the branch shard store, the
//! GitHub adapter (over a `curl` transport) and the ticket projection.

// frob:ticket 01M4052V7BG4YBHSW863YZEJ9X
// frob:ticket 01M5AREAW91T16PSWFS1KH6CCV

use std::collections::BTreeSet;
use std::fmt;
use std::fmt::Write as _;
use std::io::{IsTerminal, Write};
use std::process::{Command as Process, Stdio};
use std::time::{Duration, Instant};

use frob_ledger::mirror_map::MAP_DIR;
use frob_mirror::github::adapter::{
    GithubAdapter, GithubRest, HttpRequest, HttpResponse, HttpTransport, Method, TransportError,
};
use frob_mirror::github::read::{BodyRevisions, HistorySource, TimelineEvent};
use frob_mirror::github::write::Clock as WriteClock;
use frob_mirror::keyring::Keyring;
use frob_mirror::mapfile::Shard;
use frob_mirror::projection;
use frob_mirror::shardstore::BranchShardStore;
use gob_cli::clap::{self, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_trust::prompt::{Presence, presence};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::mirror_cmd::facts_of;
use crate::ticket::{cli_err, open, resolve};
use crate::workspace::Located;

use frob_mirror::adapter::{AdapterError, AdapterResult, IssueRef, IssueState, TrackerAdapter};
use frob_mirror::blind::{Disposition, classify};
use frob_mirror::create::{CreateError, CreateStep, create_issue};
use frob_mirror::cursor::PendingCursor;
use frob_mirror::mapfile::{MapError, ShardStore, read_shard, write_shard};
use frob_mirror::projection::IssueProjection;
use tracing::{info, warn};

/// Why a recreate did not run to a create.
#[derive(Debug, PartialEq, Eq)]
pub enum RecreateRefusal {
    /// No shard, or the shard names no issue: there is nothing to recreate.
    NotMirrored,
    /// The issue still reads fine: it is not deleted.
    StillExists(String),
    /// The issue returned 404: it may be invisible to the token, not deleted.
    MayBeInvisible(String),
    /// The issue moved (301); the location must be verified, not recreated.
    Moved(String),
}

impl fmt::Display for RecreateRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotMirrored => write!(f, "ticket has no mirrored issue to recreate"),
            Self::StillExists(i) => write!(f, "issue {i} still exists; nothing to recreate"),
            Self::MayBeInvisible(i) => write!(
                f,
                "issue {i} returned 404: it may be invisible to this token, not deleted; \
                 recreate only follows a 410"
            ),
            Self::Moved(to) => write!(f, "issue moved to {to}; verify the move, do not recreate"),
        }
    }
}

/// Failures of a recreate that are not refusals.
#[derive(Debug, PartialEq, Eq)]
pub enum RecreateError {
    /// Refused before any change.
    Refused(RecreateRefusal),
    /// The probe of the old issue failed without a status meaning.
    Probe(AdapterError),
    /// The shard could not be read or committed.
    Map(MapError),
    /// The create protocol failed.
    Create(CreateError),
}

impl fmt::Display for RecreateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Refused(r) => write!(f, "{r}"),
            Self::Probe(e) => write!(f, "probing the old issue failed: {e}"),
            Self::Map(e) => write!(f, "map store: {e}"),
            Self::Create(e) => write!(f, "create: {e}"),
        }
    }
}

/// Recreate the issue of ticket `ulid` after a 410, through the create protocol.
///
/// The old issue is probed first: only a 410 (`Disposition::Unmirrored`) proceeds. The shard's
/// tracker identity and cursors are dropped, then `create_issue` runs; on a confirmed create the
/// returned step's shard names the new issue.
///
/// # Errors
/// `RecreateError::Refused` unless the old issue is gone (410); other variants for store, probe
/// and create failures.
pub fn recreate<S: ShardStore, A: TrackerAdapter>(
    store: &mut S,
    adapter: &mut A,
    ulid: &str,
    projection: &IssueProjection,
    run_id: &str,
    started: &str,
    pending: PendingCursor,
) -> Result<CreateStep, RecreateError> {
    let mut shard = read_shard(store, ulid)
        .map_err(RecreateError::Map)?
        .ok_or(RecreateError::Refused(RecreateRefusal::NotMirrored))?;
    let Some(number) = shard.issue_number else {
        warn!(ulid, "recreate: refused, shard names no issue");
        return Err(RecreateError::Refused(RecreateRefusal::NotMirrored));
    };
    let old = IssueRef(number.to_string());
    match adapter.read(&old) {
        Ok(_) => {
            warn!(ulid, issue = %old.0, "recreate: refused, issue still exists");
            return Err(RecreateError::Refused(RecreateRefusal::StillExists(old.0)));
        }
        Err(e) => match classify(&e) {
            Some(Disposition::Unmirrored) => {}
            Some(Disposition::NotVisible) => {
                warn!(ulid, issue = %old.0, "recreate: refused, 404 may be invisible");
                return Err(RecreateError::Refused(RecreateRefusal::MayBeInvisible(
                    old.0,
                )));
            }
            Some(Disposition::Moved(to)) => {
                warn!(ulid, issue = %old.0, %to, "recreate: refused, issue moved");
                return Err(RecreateError::Refused(RecreateRefusal::Moved(to)));
            }
            None => return Err(RecreateError::Probe(e)),
        },
    }
    info!(ulid, issue = %old.0, "recreate: issue gone (410), dropping old identity");
    shard.issue_number = None;
    shard.node_id = None;
    shard.location = None;
    shard.history_cursor = None;
    shard.observed.clear();
    write_shard(store, &shard).map_err(RecreateError::Map)?;
    let step = create_issue(store, adapter, shard, projection, run_id, started, pending)
        .map_err(RecreateError::Create)?;
    info!(ulid, "recreate: create protocol finished");
    Ok(step)
}

/// Environment variable holding the 64-hex marker signing key.
const KEY_VAR: &str = "FROB_MIRROR_KEY";
/// Environment variable naming the marker key id; `DEFAULT_KID` when unset.
const KID_VAR: &str = "FROB_MIRROR_KID";
/// Marker key id used when `FROB_MIRROR_KID` is unset.
const DEFAULT_KID: &str = "k1";
/// Token variables, first set one wins.
const TOKEN_VARS: [&str; 2] = ["GH_TOKEN", "GITHUB_TOKEN"];
/// GitHub API root.
const API_ROOT: &str = "https://api.github.com";
/// Refusal code when a person is not at a terminal.
const CODE_NEEDS_HUMAN: &str = "E-MIRROR-NEEDS-HUMAN";
/// Refusal code for a recreate that did not run.
const CODE_RECREATE: &str = "E-MIRROR-RECREATE";

/// What `frob mirror recreate` did.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RecreateReport {
    /// The ticket ULID.
    pub ticket: String,
    /// `created`, `uncertain`, `blocked` or `rejected`.
    pub result: String,
    /// The new issue number when one was confirmed.
    pub issue: Option<u64>,
}

/// Replace the issue the tracker deleted (a 410) with a new one; a person runs this at a terminal.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "mirror recreate",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct MirrorRecreate {
    ticket: String,
    repo: Option<String>,
}

/// Arguments of `mirror recreate`.
#[derive(Debug, Clone, clap::Args)]
struct RecreateArgs {
    /// The ticket as typed: full ULID, `~handle` or alias.
    #[arg(value_name = "TICKET")]
    ticket: String,
    /// `owner/name` of the GitHub repository; defaults to the `origin` remote.
    #[arg(long, value_name = "OWNER/NAME")]
    repo: Option<String>,
}

/// The `(owner, name)` of a GitHub remote URL (https or scp-like), if it is one.
fn parse_remote(url: &str) -> Option<(String, String)> {
    let tail = url
        .split_once("github.com/")
        .or_else(|| url.split_once("github.com:"))?
        .1;
    let tail = tail.trim_end_matches('/').trim_end_matches(".git");
    let (owner, name) = tail.split_once('/')?;
    (!owner.is_empty() && !name.is_empty() && !name.contains('/'))
        .then(|| (owner.to_owned(), name.to_owned()))
}

/// Percent-encode a query component.
fn enc(s: &str) -> String {
    let mut out = String::new();
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'~') {
            out.push(char::from(b));
        } else {
            let _ = write!(out, "%{b:02X}");
        }
    }
    out
}

/// Quote `s` as a curl config string.
fn curl_quote(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Split a `curl --include` capture into status, `Location` and body.
fn parse_response(raw: &str) -> Option<HttpResponse> {
    let (head, body) = raw
        .split_once("\r\n\r\n")
        .or_else(|| raw.split_once("\n\n"))?;
    let mut lines = head.lines();
    let status = lines.next()?.split_whitespace().nth(1)?.parse().ok()?;
    let location = lines.find_map(|l| {
        let (k, v) = l.split_once(':')?;
        k.eq_ignore_ascii_case("location")
            .then(|| v.trim().to_owned())
    });
    Some(HttpResponse {
        status,
        location,
        body: body.to_owned(),
    })
}

/// An [`HttpTransport`] that shells out to `curl`; the token goes over stdin, never argv.
#[derive(Clone)]
struct CurlTransport {
    token: String,
}

impl HttpTransport for CurlTransport {
    fn send(&self, req: &HttpRequest) -> Result<HttpResponse, TransportError> {
        let mut url = format!("{API_ROOT}{}", req.path);
        for (i, (k, v)) in req.query.iter().enumerate() {
            url.push(if i == 0 { '?' } else { '&' });
            let _ = write!(url, "{}={}", enc(k), enc(v));
        }
        let method = match req.method {
            Method::Get => "GET",
            Method::Post => "POST",
            Method::Patch => "PATCH",
            Method::Delete => "DELETE",
        };
        let mut cfg = format!(
            "url = {}\nrequest = {method}\nheader = {}\nheader = \"Accept: application/vnd.github+json\"\nheader = \"X-GitHub-Api-Version: 2022-11-28\"\nheader = \"User-Agent: frob-mirror\"\n",
            curl_quote(&url),
            curl_quote(&format!("Authorization: Bearer {}", self.token)),
        );
        if let Some(body) = &req.body {
            let _ = write!(
                cfg,
                "header = \"Content-Type: application/json\"\ndata = {}\n",
                curl_quote(&body.to_string())
            );
        }
        tracing::debug!(%method, path = %req.path, "mirror recreate: http");
        let mut child = Process::new("curl")
            .args([
                "--silent",
                "--show-error",
                "--include",
                "--max-time",
                "30",
                "--config",
                "-",
            ])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| TransportError::Other(format!("cannot run curl: {e}")))?;
        child
            .stdin
            .take()
            .ok_or_else(|| TransportError::Other("curl stdin unavailable".into()))?
            .write_all(cfg.as_bytes())
            .map_err(|e| TransportError::Other(format!("curl stdin: {e}")))?;
        let out = child
            .wait_with_output()
            .map_err(|e| TransportError::Other(format!("curl: {e}")))?;
        if out.status.code() == Some(28) {
            return Err(TransportError::Timeout);
        }
        if !out.status.success() {
            return Err(TransportError::Other(
                String::from_utf8_lossy(&out.stderr).trim().to_owned(),
            ));
        }
        parse_response(&String::from_utf8_lossy(&out.stdout))
            .ok_or_else(|| TransportError::Other("unparseable http response".into()))
    }
}

/// Monotonic clock with real sleeps, for the adapter's write spacing.
struct StdClock(Instant);

impl WriteClock for StdClock {
    fn now(&self) -> Duration {
        self.0.elapsed()
    }
    fn sleep(&self, d: Duration) {
        std::thread::sleep(d);
    }
}

/// A history source that has seen nothing: the new issue starts with no cursor.
struct NoHistory;

impl HistorySource for NoHistory {
    fn issue(&self, i: &IssueRef) -> AdapterResult<IssueState> {
        Err(AdapterError::Other(format!("no history for {}", i.0)))
    }
    fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
        Ok(vec![])
    }
    fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
        Ok(BodyRevisions::default())
    }
}

/// Refuse unless a person is at a terminal and no agent marker is set.
fn gate(
    stdin_tty: bool,
    stdout_tty: bool,
    env: impl Fn(&str) -> Option<String>,
) -> Result<(), Refusal> {
    match presence(stdin_tty, stdout_tty, env) {
        Presence::Human => Ok(()),
        other => {
            tracing::warn!(?other, "mirror recreate refused: no person at a terminal");
            Err(Refusal::new(
                CODE_NEEDS_HUMAN,
                RefusalClass::GuardNeedsAction,
                "mirror recreate is a decision a person makes at a terminal",
            )
            .with_remedy("ask the user to run `frob mirror recreate` in their own terminal")
            .requiring_human())
        }
    }
}

fn refuse(message: impl Into<String>) -> CliError {
    Refusal::new(CODE_RECREATE, RefusalClass::GuardNeedsAction, message).into()
}

/// A JSON string field of an API object, or a refusal naming `what`.
fn field(v: &Value, key: &str, what: &str) -> Result<String, CliError> {
    v.get(key)
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| refuse(format!("GitHub returned no {what}")))
}

/// One GET through the transport, 2xx only.
fn get_json(http: &CurlTransport, path: &str) -> Result<Value, CliError> {
    let req = HttpRequest {
        method: Method::Get,
        path: path.to_owned(),
        query: vec![],
        body: None,
    };
    let resp = http
        .send(&req)
        .map_err(|e| refuse(format!("GET {path}: {e}")))?;
    if !(200..300).contains(&resp.status) {
        return Err(refuse(format!("GET {path}: http {}", resp.status)));
    }
    serde_json::from_str(&resp.body).map_err(CliError::internal)
}

impl Command for MirrorRecreate {
    type Data = RecreateReport;

    fn configure(cmd: clap::Command) -> clap::Command {
        gob_cli::augment::<RecreateArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RecreateArgs>(m)?;
        Ok(Self {
            ticket: a.ticket,
            repo: a.repo,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RecreateReport> {
        gate(
            std::io::stdin().is_terminal(),
            std::io::stdout().is_terminal(),
            |k| std::env::var(k).ok(),
        )?;
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let view = ledger.show(id).map_err(cli_err)?;
        let (repo, _) = Located::discover(&ctx.cwd).into_repo()?;
        let remote = repo.remote_url("origin").unwrap_or_default();
        let (owner, name) = match &self.repo {
            Some(r) => parse_remote(&format!("github.com/{r}")),
            None => parse_remote(&remote),
        }
        .ok_or_else(|| refuse("no GitHub repository: pass --repo OWNER/NAME"))?;
        let token = TOKEN_VARS
            .iter()
            .find_map(|v| std::env::var(v).ok().filter(|t| !t.is_empty()))
            .ok_or_else(|| {
                refuse("set GH_TOKEN or GITHUB_TOKEN to a token that can write issues")
            })?;
        let http = CurlTransport { token };
        let node_id = field(
            &get_json(&http, &format!("/repos/{}/{}", enc(&owner), enc(&name)))?,
            "node_id",
            "repository node id",
        )?;
        let bot = field(&get_json(&http, "/user")?, "login", "token login")?;
        let kid = std::env::var(KID_VAR).unwrap_or_else(|_| DEFAULT_KID.to_owned());
        let keyring = Keyring::from_env(&kid, KEY_VAR, &[])
            .map_err(|e| refuse(format!("marker key: {e}")))?;

        let facts = facts_of(&ledger, &view, remote)?;
        let projection = projection::project(&facts, &BTreeSet::new(), env!("CARGO_PKG_VERSION"));
        let ulid = id.to_string();
        let mut store =
            BranchShardStore::new(repo, &ledger.ledger_ref().map_err(cli_err)?, MAP_DIR, None);
        // The old issue is gone, so the new one starts with no cursor.
        let mut blank = Shard::new(&ulid);
        blank.history_cursor = None;
        let pending = frob_mirror::cursor::begin_read(&NoHistory, &IssueRef(String::new()), &blank)
            .map_err(CliError::internal)?
            .pending;
        let clock = StdClock(Instant::now());
        let mut adapter = GithubAdapter::new(
            GithubRest::new(http, &owner, &name, &bot),
            &keyring,
            &node_id,
            &clock,
        );
        let started = ctx.clock.now().to_string();
        let run_id = format!("recreate-{started}");
        let step = recreate(
            &mut store,
            &mut adapter,
            &ulid,
            &projection,
            &run_id,
            &started,
            pending,
        )
        .map_err(|e| refuse(e.to_string()))?;
        let (result, issue) = match &step {
            CreateStep::Created(c) => ("created", c.shard.issue_number),
            CreateStep::Uncertain(_) => ("uncertain", None),
            CreateStep::Blocked(_) => ("blocked", None),
            CreateStep::Rejected(..) => ("rejected", None),
        };
        tracing::info!(ticket = %ulid, result, ?issue, "mirror recreate done");
        Ok(Payload::new(RecreateReport {
            ticket: ulid,
            result: result.to_owned(),
            issue,
        }))
    }
}

#[cfg(test)]
mod tests {
    use std::collections::{BTreeSet, HashMap};

    use frob_mirror::adapter::{
        AdapterResult, Capabilities, CreateOutcome, EventId, HistoryEntry, HistoryRetention,
        Inventory, IssueState, IssueSummary, MarkdownDialect, StateReasons,
    };
    use frob_mirror::cursor::begin_read;
    use frob_mirror::github::read::{BodyRevisions, HistorySource, TimelineEvent};
    use frob_mirror::mapfile::{Shard, content_hash};
    use frob_mirror::projection::{
        Category, Classification, Identity, People, RelationKind, State, TicketFacts, project,
    };

    use super::*;

    #[derive(Default)]
    struct Mem(HashMap<String, Vec<u8>>);

    impl ShardStore for Mem {
        fn get(&self, key: &str) -> Option<Vec<u8>> {
            self.0.get(key).cloned()
        }
        fn put_if(
            &mut self,
            key: &str,
            expected: Option<&str>,
            bytes: Vec<u8>,
        ) -> Result<(), MapError> {
            let found = self.get(key).map(|b| content_hash(&b));
            if found.as_deref() != expected {
                return Err(MapError::Conflict {
                    key: key.into(),
                    expected: expected.map(String::from),
                    found,
                });
            }
            self.0.insert(key.into(), bytes);
            Ok(())
        }
    }

    /// Reads of the old issue fail with `read_err`; creates yield issue 99.
    struct Fake {
        read_err: Option<AdapterError>,
        creates: usize,
    }

    impl TrackerAdapter for Fake {
        fn capabilities(&self) -> Capabilities {
            Capabilities {
                native_sub_issues: false,
                native_links: false,
                custom_fields: false,
                state_reasons: StateReasons::Unsupported,
                history_retention: HistoryRetention::None,
                markdown: MarkdownDialect::Github,
            }
        }
        fn create(&mut self, _: &IssueProjection, _: &str) -> CreateOutcome {
            self.creates += 1;
            CreateOutcome::Created(IssueRef("99".into()))
        }
        fn update(&mut self, _: &IssueRef, _: &IssueProjection) -> AdapterResult<()> {
            Ok(())
        }
        fn close(
            &mut self,
            _: &IssueRef,
            _: frob_mirror::projection::Outcome,
        ) -> AdapterResult<()> {
            Ok(())
        }
        fn list_by_creator(&self, _: u64) -> AdapterResult<Vec<IssueSummary>> {
            Ok(vec![])
        }
        fn read(&self, i: &IssueRef) -> AdapterResult<IssueState> {
            match &self.read_err {
                Some(e) => Err(e.clone()),
                None => Ok(IssueState {
                    issue: i.clone(),
                    title: String::new(),
                    body: String::new(),
                    labels: vec![],
                    assignees: vec![],
                    closed: false,
                }),
            }
        }
        fn history_after(
            &self,
            _: &IssueRef,
            _: Option<&EventId>,
        ) -> AdapterResult<Vec<HistoryEntry>> {
            Ok(vec![])
        }
        fn add_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn remove_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn add_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn remove_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn link(&mut self, _: &IssueRef, _: RelationKind, _: &IssueRef) -> AdapterResult<()> {
            Ok(())
        }
        fn inventory(&self) -> AdapterResult<Inventory> {
            Ok(Inventory::default())
        }
    }

    struct NoHistory;

    impl HistorySource for NoHistory {
        fn issue(&self, i: &IssueRef) -> AdapterResult<IssueState> {
            Ok(IssueState {
                issue: i.clone(),
                title: String::new(),
                body: String::new(),
                labels: vec![],
                assignees: vec![],
                closed: false,
            })
        }
        fn timeline(&self, _: &IssueRef) -> AdapterResult<Vec<TimelineEvent>> {
            Ok(vec![])
        }
        fn body_revisions(&self, _: &IssueRef) -> AdapterResult<BodyRevisions> {
            Ok(BodyRevisions::default())
        }
    }

    fn projection() -> IssueProjection {
        let facts = TicketFacts {
            identity: Identity {
                ulid: "U1".into(),
                handle: "~U1".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/U1.md".into(),
            },
            title: "t".into(),
            summary: "s".into(),
            acceptance: vec![],
            scope: vec![],
            evidence: vec![],
            classification: Classification::default(),
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![],
            people: People::default(),
            last_event: "E".into(),
        };
        project(&facts, &BTreeSet::new(), "test")
    }

    fn store_with_issue(n: u64) -> Mem {
        let mut s = Mem::default();
        let mut shard = Shard::new("U1");
        shard.issue_number = Some(n);
        shard.history_cursor = Some("E1".into());
        write_shard(&mut s, &shard).unwrap();
        s
    }

    fn run(store: &mut Mem, adapter: &mut Fake) -> Result<CreateStep, RecreateError> {
        let shard = read_shard(store, "U1").unwrap().unwrap();
        let pending = begin_read(&NoHistory, &IssueRef("1".into()), &shard)
            .unwrap()
            .pending;
        recreate(
            store,
            adapter,
            "U1",
            &projection(),
            "run1",
            "2026-01-01T00:00:00Z",
            pending,
        )
    }

    #[test]
    fn a_410_issue_is_recreated_and_the_shard_points_at_the_new_one() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::recreate
        let mut store = store_with_issue(7);
        let mut adapter = Fake {
            read_err: Some(AdapterError::Gone),
            creates: 0,
        };
        let step = run(&mut store, &mut adapter).unwrap();
        assert!(matches!(step, CreateStep::Created(_)));
        assert_eq!(adapter.creates, 1);
        let shard = read_shard(&store, "U1").unwrap().unwrap();
        assert_eq!(shard.issue_number, Some(99));
        assert!(shard.create_uncertain.is_none());
        assert_eq!(shard.history_cursor, None);
    }

    #[test]
    fn a_404_issue_is_refused_as_possibly_invisible() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::recreate
        let mut store = store_with_issue(7);
        let mut adapter = Fake {
            read_err: Some(AdapterError::NotFound),
            creates: 0,
        };
        let err = run(&mut store, &mut adapter).unwrap_err();
        assert_eq!(
            err,
            RecreateError::Refused(RecreateRefusal::MayBeInvisible("7".into()))
        );
        assert!(err.to_string().contains("invisible"));
        assert!(err.to_string().contains("not deleted"));
        assert_eq!(adapter.creates, 0);
        let shard = read_shard(&store, "U1").unwrap().unwrap();
        assert_eq!(shard.issue_number, Some(7));
    }

    #[test]
    fn a_live_issue_is_refused() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::recreate
        let mut store = store_with_issue(7);
        let mut adapter = Fake {
            read_err: None,
            creates: 0,
        };
        let err = run(&mut store, &mut adapter).unwrap_err();
        assert!(matches!(
            err,
            RecreateError::Refused(RecreateRefusal::StillExists(_))
        ));
        assert_eq!(adapter.creates, 0);
    }

    #[test]
    fn remote_urls_parse_to_owner_and_name() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::parse_remote
        let want = Some(("o".to_owned(), "r".to_owned()));
        assert_eq!(parse_remote("https://github.com/o/r.git"), want);
        assert_eq!(parse_remote("git@github.com:o/r.git"), want);
        assert_eq!(parse_remote("https://example.com/o/r"), None);
    }

    #[test]
    fn curl_output_parses_status_location_and_body() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::parse_response
        let r = parse_response("HTTP/2 301\r\nLocation: /x\r\n\r\n{}").unwrap();
        assert_eq!(
            (r.status, r.location.as_deref(), r.body.as_str()),
            (301, Some("/x"), "{}")
        );
        assert_eq!(curl_quote("a\"b\\"), "\"a\\\"b\\\\\"");
    }

    #[test]
    fn recreate_refuses_without_a_person() {
        // frob:tests crates/frob/src/mirror_recreate_cmd.rs::gate
        assert!(gate(false, false, |_| None).is_err());
        assert!(gate(true, true, |_| None).is_ok());
    }
}
