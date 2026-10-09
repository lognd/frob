//! `serve`: the MCP tool list and calls are generated from verb metadata.

use std::io::Cursor;

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{Cli, CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::{Value, json};

#[derive(Serialize, JsonSchema)]
struct Seen {
    name: String,
    loud: bool,
    tags: Vec<String>,
}

/// Read a thing.
#[derive(Debug, Default, Command)]
#[command(
    verb = "thing peek",
    product = "dummy",
    idempotent = true,
    read_only,
    exits(ok, usage)
)]
struct Peek {
    name: String,
    loud: bool,
    tags: Vec<String>,
}

impl Command for Peek {
    type Data = Seen;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(Arg::new("name").required(true).help("What to read"))
            .arg(Arg::new("loud").long("loud").action(ArgAction::SetTrue))
            .arg(Arg::new("tag").long("tag").action(ArgAction::Append))
            .arg(Arg::new("fix").long("fix").action(ArgAction::SetTrue))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            name: m.get_one::<String>("name").cloned().unwrap_or_default(),
            loud: m.get_flag("loud"),
            tags: m
                .get_many::<String>("tag")
                .into_iter()
                .flatten()
                .cloned()
                .collect(),
        })
    }

    fn run(&self, _: &Context) -> Outcome<Seen> {
        Ok(Payload::new(Seen {
            name: self.name.clone(),
            loud: self.loud,
            tags: self.tags.clone(),
        }))
    }
}

/// Change a thing.
#[derive(Debug, Default, Command)]
#[command(verb = "thing poke", product = "dummy", exits(ok, usage))]
struct Poke;

impl Command for Poke {
    type Data = ();
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, _: &Context) -> Outcome<()> {
        Ok(Payload::new(()))
    }
}

fn cli() -> Cli {
    Cli::new("dummy", "1.2.3")
        .register::<Peek>()
        .register::<Poke>()
}

/// Send `requests` (one JSON value per line) and return the parsed replies.
fn talk(requests: &[Value]) -> Vec<Value> {
    let input: String = requests.iter().map(|r| format!("{r}\n")).collect();
    let mut out = Vec::new();
    let cwd = std::env::temp_dir();
    cli()
        .serve_mcp(Cursor::new(input), &mut out, &cwd)
        .expect("serve ends at EOF");
    String::from_utf8(out)
        .expect("utf8")
        .lines()
        .map(|l| serde_json::from_str(l).expect("reply is JSON"))
        .collect()
}

fn call(name: &str, arguments: Value) -> Value {
    let replies = talk(&[json!({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": { "name": name, "arguments": arguments }
    })]);
    replies.into_iter().next().expect("one reply")
}

#[test]
fn lists_every_read_only_verb_with_the_verb_input_schema() {
    let replies = talk(&[json!({"jsonrpc":"2.0","id":1,"method":"tools/list"})]);
    let tools = replies[0]["result"]["tools"].as_array().expect("tools");
    let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();
    assert_eq!(names, ["dummy_schema", "dummy_thing_peek"]);
    let peek = &tools[1]["inputSchema"];
    assert_eq!(peek["required"], json!(["name"]));
    assert_eq!(peek["additionalProperties"], json!(false));
    assert_eq!(peek["properties"]["name"]["type"], "string");
    assert_eq!(peek["properties"]["name"]["description"], "What to read");
    assert_eq!(peek["properties"]["loud"]["type"], "boolean");
    assert_eq!(peek["properties"]["tag"]["type"], "array");
}

#[test]
fn a_mutating_verb_is_absent_and_uncallable() {
    let replies = talk(&[json!({"jsonrpc":"2.0","id":1,"method":"tools/list"})]);
    let text = replies[0].to_string();
    assert!(!text.contains("dummy_thing_poke"), "{text}");
    let reply = call("dummy_thing_poke", json!({}));
    assert_eq!(reply["error"]["code"], -32602, "{reply}");
}

#[test]
fn write_flags_are_not_exposed() {
    let replies = talk(&[json!({"jsonrpc":"2.0","id":1,"method":"tools/list"})]);
    let props = &replies[0]["result"]["tools"][1]["inputSchema"]["properties"];
    assert!(props.get("fix").is_none(), "{props}");
    let reply = call("dummy_thing_peek", json!({"name": "a", "fix": true}));
    assert_eq!(reply["error"]["code"], -32602, "{reply}");
}

#[test]
fn a_call_returns_the_cli_envelope() {
    let reply = call(
        "dummy_thing_peek",
        json!({"name": "-dash", "loud": true, "tag": ["x", "y"]}),
    );
    assert_eq!(reply["result"]["isError"], false, "{reply}");
    let text = reply["result"]["content"][0]["text"].as_str().unwrap();
    let env: Value = serde_json::from_str(text).expect("envelope");
    assert_eq!(env["ok"], true);
    assert_eq!(env["verb"], "thing.peek");
    assert_eq!(
        env["data"],
        json!({"name": "-dash", "loud": true, "tags": ["x", "y"]})
    );
}

#[test]
fn a_usage_failure_is_an_error_result_with_the_envelope() {
    let reply = call("dummy_thing_peek", json!({}));
    assert_eq!(reply["result"]["isError"], true, "{reply}");
    let text = reply["result"]["content"][0]["text"].as_str().unwrap();
    let env: Value = serde_json::from_str(text).expect("envelope");
    assert_eq!(env["ok"], false);
    assert_eq!(env["error"]["code"], "E-USAGE");
}

#[test]
fn the_handshake_and_notifications_follow_mcp() {
    let replies = talk(&[
        json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}),
        json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
        json!({"jsonrpc":"2.0","id":2,"method":"ping"}),
        json!({"jsonrpc":"2.0","id":3,"method":"nope"}),
    ]);
    assert_eq!(replies.len(), 3, "a notification gets no reply");
    assert_eq!(replies[0]["result"]["protocolVersion"], "2025-03-26");
    assert_eq!(replies[0]["result"]["serverInfo"]["name"], "dummy");
    assert_eq!(replies[1]["result"], json!({}));
    assert_eq!(replies[2]["error"]["code"], -32601);
}

#[test]
fn garbage_gets_a_parse_error() {
    let mut out = Vec::new();
    cli()
        .serve_mcp(Cursor::new("not json\n"), &mut out, &std::env::temp_dir())
        .expect("serve");
    let reply: Value = serde_json::from_slice(&out).expect("json");
    assert_eq!(reply["error"]["code"], -32700);
}
