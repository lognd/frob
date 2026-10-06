//! Offline client tests: every exchange is a recorded fixture; no socket is ever opened.

use std::sync::Mutex;
use std::time::Duration;

use frob_gh::{Client, Error, FixtureTransport, Pause, Policy, Token};

#[derive(Debug, Default)]
struct RecordingPause(Mutex<Vec<Duration>>);

impl Pause for &'static RecordingPause {
    async fn pause(&self, duration: Duration) {
        self.0.lock().unwrap().push(duration);
    }
}

fn leak_pause() -> &'static RecordingPause {
    Box::leak(Box::default())
}

fn client(fixture: &str) -> Client<FixtureTransport, TokioPauseAlias> {
    Client::new(
        FixtureTransport::from_json(fixture).unwrap(),
        Token::new("placeholder-token"),
    )
}

type TokioPauseAlias = frob_gh::TokioPause;

const RATE_LIMITED: &str = include_str!("fixtures/rate_limited_then_ok.json");
const ETAG: &str = include_str!("fixtures/etag_roundtrip.json");
const GRAPHQL: &str = include_str!("fixtures/graphql_ok.json");
const TOO_LONG: &str = include_str!("fixtures/retry_after_too_long.json");
const FORBIDDEN: &str = include_str!("fixtures/forbidden.json");

#[tokio::test(flavor = "current_thread")]
async fn waits_at_least_retry_after_then_retries() {
    let pause = leak_pause();
    let c = client(RATE_LIMITED).with_pause(pause);
    let reply = c.get("/repos/o/r/issues/1").await.unwrap();
    assert_eq!(reply.status, 200);
    assert_eq!(*pause.0.lock().unwrap(), vec![Duration::from_secs(7)]);
    assert_eq!(c.transport().requests().len(), 2);
    assert_eq!(c.transport().remaining(), 0);
    let rl = reply.rate_limit.unwrap();
    assert_eq!(
        (rl.remaining, rl.used, rl.limit, rl.reset),
        (4999, Some(1), Some(5000), Some(1_700_000_000))
    );
}

#[tokio::test(flavor = "current_thread")]
async fn retry_after_beyond_the_cap_stops_instead_of_waiting() {
    let pause = leak_pause();
    let c = client(TOO_LONG).with_pause(pause);
    let err = c.get("/x").await.unwrap_err();
    assert!(matches!(err, Error::RetryAfterExceedsCap { .. }), "{err}");
    assert!(pause.0.lock().unwrap().is_empty());
}

#[tokio::test(flavor = "current_thread")]
async fn attempts_are_capped() {
    let one = r#"{"request":{"method":"GET","url":"https://api.github.com/x"},"response":{"status":429,"headers":{"Retry-After":"1"}}}"#;
    let fixture = format!("[{one},{one}]");
    let pause = leak_pause();
    let c = client(&fixture).with_pause(pause).with_policy(Policy {
        max_attempts: 2,
        ..Policy::default()
    });
    let err = c.get("/x").await.unwrap_err();
    assert!(
        matches!(err, Error::RetriesExhausted { attempts: 2 }),
        "{err}"
    );
    assert_eq!(pause.0.lock().unwrap().len(), 1);
}

#[tokio::test(flavor = "current_thread")]
async fn second_get_is_conditional_and_served_from_cache_on_304() {
    let c = client(ETAG);
    let first = c.get("/repos/o/r").await.unwrap();
    assert!(!first.from_cache);
    assert_eq!(first.etag.as_deref(), Some("\"v1\""));
    let second = c.get("/repos/o/r").await.unwrap();
    assert!(second.from_cache);
    assert_eq!(second.body, first.body);
    let sent = c.transport().requests();
    assert_eq!(sent[0].headers.get("if-none-match"), None);
    assert_eq!(
        sent[1].headers.get("if-none-match").map(String::as_str),
        Some("\"v1\"")
    );
    assert_eq!(second.rate_limit.unwrap().remaining, 4998);
}

#[tokio::test(flavor = "current_thread")]
async fn missing_rate_limit_headers_are_an_explicit_none() {
    let c = client(FORBIDDEN.replace("403", "200").as_str());
    assert_eq!(c.get("/x").await.unwrap().rate_limit, None);
}

#[tokio::test(flavor = "current_thread")]
async fn graphql_posts_query_and_exposes_the_body() {
    let c = client(GRAPHQL);
    let reply = c
        .graphql("query { viewer { login } }", &serde_json::json!({}))
        .await
        .unwrap();
    let v: serde_json::Value = reply.json().unwrap();
    assert_eq!(v["data"]["viewer"]["login"], "bot");
    let sent = &c.transport().requests()[0];
    assert_eq!(sent.method.as_str(), "POST");
    let body: serde_json::Value = serde_json::from_slice(sent.body.as_ref().unwrap()).unwrap();
    assert_eq!(body["query"], "query { viewer { login } }");
}

#[tokio::test(flavor = "current_thread")]
async fn plain_403_is_a_status_error_and_the_token_never_prints() {
    let c = client(FORBIDDEN);
    let err = c.get("/x").await.unwrap_err();
    assert!(matches!(err, Error::Status { status: 403, .. }));
    let sent = &c.transport().requests()[0];
    assert!(!format!("{sent:?}").contains("placeholder-token"));
    assert_eq!(sent.headers["authorization"], "Bearer placeholder-token");
}

#[tokio::test(flavor = "current_thread")]
async fn unrecorded_requests_fail_instead_of_reaching_the_network() {
    let c = client("[]");
    assert!(matches!(
        c.get("/anything").await.unwrap_err(),
        Error::Unrecorded { .. }
    ));
}

#[test]
fn plain_http_base_is_refused() {
    let c = client("[]");
    assert!(matches!(
        c.with_base("http://example.com"),
        Err(Error::InsecureBase(_))
    ));
}
