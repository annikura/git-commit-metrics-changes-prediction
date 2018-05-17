import os

from dulwich import porcelain
from dulwich.diff_tree import tree_changes
from dulwich.objects import Tree

HEADS_PATH = (os.path.join("refs", "heads") + os.sep).encode()


class Repo:
    def __init__(self, source, destination):
        self.repo_path = destination
        self.source = source
        self.repo = porcelain.clone(source, destination)

        if self.repo is None:
            raise ValueError("Repository does not exist")

    def branch_exists(self, branch_name):
        return branch_name in self.branches_list()

    def branches_list(self):
        return porcelain.branch_list(self.repo_path)

    def iterate_through_commits(self, branch_name, collectors, from_commit=0, to_commit=int(1e9)):
        if not self.branch_exists(branch_name):
            raise ValueError(b"Branch " + branch_name + b" does not exist")

        prev_commit = None
        i = 0
        for entry in self.repo.get_walker(include=[self.repo[HEADS_PATH + branch_name].id], reverse=True):
            if i > to_commit:
                return
            commit = entry.commit
            if from_commit <= i:
                print("Iterating...", i)
                for collector in collectors:
                    collector.collect(Commit(commit, prev_commit, self.repo))
            prev_commit = commit
            i += 1


class Commit:
    _EMPTY_TREE = Tree.from_string(b"")

    def __init__(self, commit, prev_commit, repo):
        self._commit = commit
        self._prev_commit = prev_commit
        self._repo = repo

        self.author = commit.author.decode()
        self.author_time = commit.author_time
        self.committer = commit.committer.decode()
        self.committer_time = commit.commit_time
        self.sha = commit.id

    @staticmethod
    def get_tree(commit):
        if commit is None:
            return Commit._EMPTY_TREE
        else:
            return commit.tree

    def list_objects(self, want_unchanged=True):
        result = []
        for tree_change in tree_changes(self._repo.object_store,
                                        self.get_tree(self._prev_commit), self.get_tree(self._commit),
                                        want_unchanged=want_unchanged):
            if tree_change.new[0] is not None:
                result.append(Object(self._repo, self, tree_change.new, tree_change.old))
        return result


class Object:
    def __init__(self, repo, commit, new, old):
        self._repo = repo
        self._commit = commit
        self._old_version = old
        (self.path, self.mode, self.sha) = new
        self.path = self.path.decode()
        self.sha = self.sha.decode()

    def get_content(self):
        if self.sha is None:
            return None
        else:
            return self._repo.object_store[self.sha].splitlines()
