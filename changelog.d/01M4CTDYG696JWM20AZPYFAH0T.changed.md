A timed-out command now has its whole process tree killed (including children that left the process group, and via taskkill /T on Windows), and waiting for its output is bounded to one second.
