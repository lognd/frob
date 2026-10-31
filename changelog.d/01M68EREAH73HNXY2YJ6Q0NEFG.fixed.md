Go declared-type tracking now follows methods returning reflect.Value and members promoted from an embedded reflect.Value, so .Call on them reports Unresolved code.eval.
