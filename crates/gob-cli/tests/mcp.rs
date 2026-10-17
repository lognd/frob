//! `serve`: the read-only MCP surface is generated from verb metadata.
// frob:ticket 01M44AZ69FG7NFQFNAWMQ1NM4Q

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, CliError, Command, Context, Outcome, Payload, run_for_test};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::{Value, json};

#[derive(Serialize, JsonSchema)]
struct Seen {
    cwd: String,
}

/// Report the working directory without changing anything.
#[derive(Debug, Default, Command)]
#[command(
    verb = "look around",
    product = "mcptest",
    idempotent = true,
    read_only,
    exits(ok)
)]
struct Look;

impl Command for Look {
    type Data = Seen;
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, ctx: &Context) -> Outcome<Seen> {
        Ok(Payload::new(Seen {
            cwd: ctx.cwd.display().to_string(),
        }))
    }
}

/// Change something (so it must never be a tool).
#[derive(Debug, Default, Command)]
#[command(verb = "mutate", product = "mcptest", exits(ok))]
struct Mutate;

impl Command for Mutate {
    type Data = Seen;
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, ctx: &Context) -> Outcome<Seen> {
        Ok(Payload::new(Seen {
            cwd: ctx.cwd.display().to_string(),
        }))
    }
}

fn cli() -> Cli {
    Cli::new("mcptest", "0.0.0")
        .register::<Look>()
        .register::<Mutate>()
}

/// Send `requests` (one JSON message per line) and return the replies.
fn talk(cli: &Cli, cwd: &std::path::Path, requests: &[Value]) -> Vec<Value> {
    let input = requests
        .iter()
        .map(Value::to_string)
        .collect::<Vec<_>>()
        .join("\n");
    let mut out = Vec::new();
    cli.serve_mcp(input.as_bytes(), &mut out, cwd)
        .expect("serve");
    String::from_utf8(out)
        .expect("utf8")
        .lines()
        .map(|l| serde_json::from_str(l).expect("json line"))
        .collect()
}

// frob:tests crates/gob-cli/src/mcp.rs::mcp_tools
#[test]
fn every_read_only_verb_is_a_tool_carrying_its_verb_schema() {
    let dir = tempfile::tempdir().expect("tmp");
    let cli = cli();
    let replies = talk(
        &cli,
        dir.path(),
        &[json!({"jsonrpc":"2.0","id":1,"method":"tools/list"})],
    );
    let tools = replies[0]["result"]["tools"].as_array().expect("tools");
    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();
    assert!(names.contains(&"look_around"), "{names:?}");
    let (_, schema_text, _) = run_for_test(&cli, &["look", "around", "--schema"], dir.path());
    let verb_schema: Value = serde_json::from_str(&schema_text).expect("schema json");
    let look = tools
        .iter()
        .find(|t| t["name"] == "look_around")
        .expect("tool");
    assert_eq!(look["inputSchema"]["x-verb-schema"], verb_schema);
}

// frob:tests crates/gob-cli/src/mcp.rs::serve_mcp
#[test]
fn a_tool_call_returns_the_cli_envelope() {
    let dir = tempfile::tempdir().expect("tmp");
    let cli = cli();
    let replies = talk(
        &cli,
        dir.path(),
        &[json!({"jsonrpc":"2.0","id":2,"method":"tools/call",
            "params":{"name":"look_around","arguments":{"args":[]}}})],
    );
    let text = replies[0]["result"]["content"][0]["text"]
        .as_str()
        .expect("text");
    let (_, cli_out, _) = run_for_test(&cli, &["look", "around", "--json"], dir.path());
    assert_eq!(text, cli_out.trim_end());
    assert_eq!(replies[0]["result"]["isError"], false);
}

// frob:tests crates/gob-cli/src/mcp.rs::mcp_tools
#[test]
fn a_mutating_verb_is_not_listed_and_cannot_be_called() {
    let dir = tempfile::tempdir().expect("tmp");
    let cli = cli();
    let replies = talk(
        &cli,
        dir.path(),
        &[
            json!({"jsonrpc":"2.0","id":1,"method":"tools/list"}),
            json!({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"mutate"}}),
            json!({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"serve"}}),
        ],
    );
    let tools = replies[0]["result"]["tools"].as_array().expect("tools");
    assert!(
        tools
            .iter()
            .all(|t| t["name"] != "mutate" && t["name"] != "serve")
    );
    assert_eq!(replies[1]["error"]["code"], -32602);
    assert_eq!(replies[2]["error"]["code"], -32602);
}

// frob:tests crates/gob-cli/src/mcp.rs::serve_mcp
#[test]
fn handshake_notifications_and_bad_input() {
    let dir = tempfile::tempdir().expect("tmp");
    let cli = cli();
    let replies = talk(
        &cli,
        dir.path(),
        &[
            json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}),
            json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
            json!({"jsonrpc":"2.0","id":2,"method":"nope"}),
        ],
    );
    assert_eq!(replies.len(), 2, "the notification gets no reply");
    assert_eq!(replies[0]["result"]["protocolVersion"], "2025-03-26");
    assert_eq!(replies[1]["error"]["code"], -32601);
    let mut out = Vec::new();
    cli.serve_mcp("not json\n".as_bytes(), &mut out, dir.path())
        .expect("serve");
    let reply: Value = serde_json::from_slice(&out).expect("json");
    assert_eq!(reply["error"]["code"], -32700);
}
