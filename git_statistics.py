#! /bin/python3

import os
import tempfile
import traceback
from argparse import ArgumentParser

import collectors
import git_repo


def writeDataOnDisk(data, directory, file):
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(os.sep.join([directory, file]), 'w') as file:
        for key in data:
            line = key.__str__() + ", " + data[key].__str__()[1:-1]
            file.writelines(line)
            file.writelines("\n")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--repository", help="url to the git repository")
    parser.add_argument("--destination", help="directory where all calculated data will be put into", default="data")
    parser.add_argument("--branch", help="branch that will be observed", default="master")
    args = parser.parse_args()
    destination = args.destination

    repo_url = args.repository
    branch = args.branch.encode()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = git_repo.Repo(repo_url, tmpdir)
        per_file = 110
        result_gap = 10
        for i in range(0, 20):
            start_commit = per_file * i
            end_commit = per_file * (i + 1) - 1
            collectors_list_main = [
                collectors.JavaMethodsDataCollector(
                    [
                        collectors.MethodSignatureCollector(),
                        collectors.MethodCommitsSinceLastChangeCollector(),
                        collectors.MethodFadingLinesChangeRatioCollector(),
                        collectors.MethodCurrentTimeOfLastChangeCollector(),
                        collectors.MethodLatestChangesSummary(result_gap),
                        collectors.MethodChangeRatio()
                    ]
                )
            ]
            collectors_list_result = [
                collectors.JavaMethodsDataCollector(
                    [
                        collectors.MethodSignatureCollector(),
                        collectors.MethodCommitsSinceLastChangeCollector(),
                        collectors.MethodFadingLinesChangeRatioCollector(),
                        collectors.MethodCurrentTimeOfLastChangeCollector(),
                        collectors.MethodLatestChangesSummary(result_gap),
                        collectors.MethodChangeRatio()
                    ]
                )
            ]
            try:
                repo.iterate_through_commits(branch, collectors_list_main,
                                             from_commit=start_commit, to_commit=end_commit - result_gap)
                for collector in collectors_list_main:
                    writeDataOnDisk(collector.get_data(), destination, "test" + i.__str__())
                repo.iterate_through_commits(branch, collectors_list_result,
                                             from_commit=start_commit, to_commit=end_commit)
                for collector in collectors_list_result:
                    writeDataOnDisk(collector.process(), destination, "result" + i.__str__())
            except Exception:
                traceback.print_exc()
