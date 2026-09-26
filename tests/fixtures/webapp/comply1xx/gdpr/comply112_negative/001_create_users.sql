CREATE TABLE users (
    id uuid PRIMARY KEY,
    email text NOT NULL,
    expires_at timestamptz
);
