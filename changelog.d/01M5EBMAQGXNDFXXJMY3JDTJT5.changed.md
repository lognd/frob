mirror: `RunHost::pending`, `execute` and `after_items` now receive the driver's store and adapter, so `MirrorHost` no longer holds `Shared` handles (the Rc/RefCell aliasing workaround is removed).
