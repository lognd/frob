import subprocess


def handler():
    return subprocess.run("echo hello", shell=True)
