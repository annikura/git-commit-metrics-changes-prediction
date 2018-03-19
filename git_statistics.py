#! /bin/python3

import shutil

import collectors
import git_repo


if __name__ == "__main__":
    repo_url = 'https://github.com/annikura/java.git'
    destination = 'repo'
    branch = b"master"

    commitSizeCollector = collectors.CommitSizeCollector()
    authorCollector = collectors.AuthorsDataCollector(lambda: collectors.CommitSizeCollector())
    try:
        repo = git_repo.Repo(repo_url, destination)
        print(repo.branches_list())
        repo.iterate_through_commits(branch, [commitSizeCollector, authorCollector])
    finally:
        shutil.rmtree(destination)
    commitSizeCollector.process()
    authorCollector.process()
