use axum::{routing::{get, post}, Router};

async fn health() {}
async fn make() {}

pub fn app() -> Router {
    Router::new().nest("/api", Router::new().route("/ping", get(health).post(make)))
}

pub fn flat() -> Router {
    Router::new().route("/flat", get(health))
}
