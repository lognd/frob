import subprocess


def handler(user_cmd):
    return subprocess.run(user_cmd, shell=True)
