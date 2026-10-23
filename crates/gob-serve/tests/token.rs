//! The per-launch token gate and JSON-RPC edge cases of `gob-serve`.

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ

use gob_serve::{CODE_INVALID_PARAMS, CODE_UNAUTHORIZED, Server, Token, ToolSpec, Tools};
use serde_json::{Map, Value, json};

const TOKEN: &str = "placeholder-launch-token";

struct Echo;

impl Tools for Echo {
    fn list(&self) -> Vec<ToolSpec> {
        vec![ToolSpec {
            name: "echo".to_owned(),
            description: "Echo.".to_owned(),
            input_schema: json!({ "type": "object" }),
        }]
    }

    fn call(&self, _name: &str, arguments: &Map<String, Value>) -> Result<Value, String> {
        Ok(Value::Object(arguments.clone()))
    }
}

fn server() -> Server<Echo> {
    Server::new("t", "0", Token::from_value(TOKEN).expect("token"), Echo)
}

fn ask(method: &str, token: Option<&str>, params: &Value) -> Value {
    let mut params = params.clone();
    if let Some(t) = token {
        params["_meta"] = json!({ "token": t });
    }
    let line = json!({ "jsonrpc": "2.0", "id": 1, "method": method, "params": params });
    server().handle_line(&line.to_string()).expect("a reply")
}

// frob:tests crates/gob-serve/src/lib.rs::Token.verify
#[test]
fn missing_empty_and_wrong_tokens_are_refused_for_every_method() {
    for method in ["initialize", "ping", "tools/list", "tools/call", "nope"] {
        for token in [
            None,
            Some(""),
            Some("wrong"),
            Some("placeholder-launch-token-x"),
        ] {
            let reply = ask(method, token, &json!({}));
            assert_eq!(
                reply["error"]["code"], CODE_UNAUTHORIZED,
                "{method} {token:?}"
            );
            assert!(reply.get("result").is_none());
        }
    }
    let reply = ask("tools/list", Some(TOKEN), &json!({}));
    assert_eq!(reply["result"]["tools"][0]["name"], "echo");
}

// frob:tests crates/gob-serve/src/lib.rs::Token.from_value
#[test]
fn an_empty_token_cannot_be_configured_and_never_matches() {
    assert!(Token::from_value("").is_none());
    let token = Token::from_value("x").expect("token");
    assert!(!token.verify(""));
    assert!(token.verify("x"));
}

// frob:tests crates/gob-serve/src/lib.rs::Token.generate
#[test]
fn generated_tokens_are_long_hex_unique_and_redacted_in_debug() {
    let a = Token::generate().expect("a");
    let b = Token::generate().expect("b");
    assert_eq!(a.expose().len(), 64);
    assert!(a.expose().bytes().all(|c| c.is_ascii_hexdigit()));
    assert_ne!(a.expose(), b.expose());
    assert!(!format!("{a:?}").contains(a.expose()));
}

// frob:tests crates/gob-serve/src/lib.rs::Server.handle_line
#[test]
fn notifications_get_no_reply_and_malformed_input_gets_an_error() {
    let s = server();
    let note = json!({ "jsonrpc": "2.0", "method": "notifications/initialized" });
    assert!(s.handle_line(&note.to_string()).is_none());
    let reply = s.handle_line("{not json").expect("reply");
    assert_eq!(reply["error"]["code"], -32700);
    let reply = s.handle_line("[1,2]").expect("reply");
    assert_eq!(reply["error"]["code"], -32600);
}

// frob:tests crates/gob-serve/src/lib.rs::Server.handle_line
// frob:tests crates/gob-serve/src/lib.rs::Tools.list
// frob:tests crates/gob-serve/src/lib.rs::Tools.call
#[test]
fn unknown_tool_and_bad_arguments_are_invalid_params() {
    let reply = ask("tools/call", Some(TOKEN), &json!({ "name": "rm" }));
    assert_eq!(reply["error"]["code"], CODE_INVALID_PARAMS);
    let reply = ask(
        "tools/call",
        Some(TOKEN),
        &json!({ "name": "echo", "arguments": [1] }),
    );
    assert_eq!(reply["error"]["code"], CODE_INVALID_PARAMS);
    let reply = ask(
        "tools/call",
        Some(TOKEN),
        &json!({ "name": "echo", "arguments": { "a": 1 } }),
    );
    assert_eq!(reply["result"]["isError"], false);
    let listing = ask("tools/list", Some(TOKEN), &json!({}));
    assert_eq!(
        listing["result"]["tools"][0]["annotations"]["readOnlyHint"],
        true
    );
}

// frob:tests crates/gob-serve/src/lib.rs::Server.serve
#[test]
fn serve_answers_each_line_and_stops_at_eof() {
    let input = format!(
        "{}\n\n{}\n",
        json!({"jsonrpc":"2.0","id":1,"method":"ping","params":{"_meta":{"token":TOKEN}}}),
        json!({"jsonrpc":"2.0","id":2,"method":"ping"}),
    );
    let mut out = Vec::new();
    server().serve(input.as_bytes(), &mut out).expect("serve");
    let lines: Vec<Value> = String::from_utf8(out)
        .expect("utf8")
        .lines()
        .map(|l| serde_json::from_str(l).expect("json"))
        .collect();
    assert_eq!(lines.len(), 2);
    assert!(lines[0].get("result").is_some());
    assert_eq!(lines[1]["error"]["code"], CODE_UNAUTHORIZED);
}
