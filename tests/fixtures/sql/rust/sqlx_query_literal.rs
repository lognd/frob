// Positive control: sqlx's query! macro with a literal SQL string.
//
// frob:ticket T-5334

async fn count_users(pool: &sqlx::PgPool) -> Result<i64, sqlx::Error> {
    let row = sqlx::query!("SELECT count(*) AS count FROM users")
        .fetch_one(pool)
        .await?;
    Ok(row.count.unwrap_or(0))
}
