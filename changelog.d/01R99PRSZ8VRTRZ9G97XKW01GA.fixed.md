LOG001/LOG002 no longer let the caller's imports and shadows leak into `exec(src, {...})` when globals is a dict literal; only the listed names are bound.
