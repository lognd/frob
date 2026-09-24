-- Positive control: CREATE INDEX without CONCURRENTLY -- squawk's own
-- require-concurrent-index-creation rule.
-- frob:ticket T-5333
CREATE INDEX idx_users_email ON users (email);
