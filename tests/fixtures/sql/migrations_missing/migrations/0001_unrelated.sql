-- frob:ticket T-5337
CREATE INDEX idx_order_created_at ON orders (created_at);
