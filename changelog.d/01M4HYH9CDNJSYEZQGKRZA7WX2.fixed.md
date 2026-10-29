Capability checks now treat a Python open in a write mode as fs.write, a non-literal mode as a May fs.write, and Rust Path method receivers such as exists and read_dir as fs.read.
