The Windows CI rust job no longer runs out of disk while linking test binaries: it builds without debug info and clears restored test executables first.
