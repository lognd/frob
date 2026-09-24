-- Positive control: adding a NOT NULL column with no default -- squawk's
-- own adding-not-nullable-field rule.
-- frob:ticket T-5333
ALTER TABLE users ADD COLUMN age integer NOT NULL;
