class RepoPath:
    def __init__(self, value):
        self.value = value

    def child(self, name):
        return RepoPath(self.value + "/" + name)
