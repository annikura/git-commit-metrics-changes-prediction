import difflib
import enum
import os
import re

import matplotlib.pyplot as plt

from java_metrics import JavaFile, retrieve_signature


class Collector:
    """Data collector interface."""

    def collect(self, data):
        """Retrieves data wanted from the given data structure to store or process it. Expected to return nothing."""
        pass

    def process(self):
        """Returns collected data as a dictionary {id : collected_data} (which is usually the result of get_data).
        Also produces visual representation of the collected data, if possible.
        """
        pass

    def clear(self):
        """
        Clears collector static data.
        """
        pass

    def get_data(self):
        """Returns collected data as a dictionary {id : collected_data}."""
        pass


class MethodCollector(Collector):
    """Interface for collecting data about methods."""
    image_num = 0

    def __init__(self):
        self.first_commit = True
        self.ID = ""

    def collect(self, commit, method_id, new_method, old_method):
        """
        Retrieves required data about method from the given data structures to store or process it.
        Expected to return nothing.

        Args:
        :param commit: current commit, where new_method_body was extracted from.
        :type commit: git_repo.Commit
        :param method_id: method id number. This id will later be used as a key in the dictionary
            returned by get_data method.
        :type method_id: int
        :param new_method: method represented in the current commit.
            None if method was deleted in current commit.
        :type new_method: java_metrics.Method
        :param old_method: method represented in the previous commit.
            None if method was just created.
        :type old_method: java_metrics.Method

        :return nothing
        :rtype None
        """
        pass

    def process(self):
        """
        Generates visualisation of the collected data, if possible.
        The only purpose of this method is optimize the number of calls of get_method.
        It returns exactly the same data as get_method but uses it to generate a graphic before returning.
        As get_data can be working slow, it can be time-consuming to call
        this method explicitly for generating of the visualisation.

        :return: get_data result
        """

        result: dict = self.get_data()

        max_x = -1000000000
        max_y = -1000000000
        min_x = 1000000000
        min_y = 1000000000

        xs = []
        ys = []

        can_be_represented = True
        number_types = [int, float, complex]

        for key, value in result.items():
            if type(key) not in number_types or type(value) not in number_types:
                can_be_represented = False
                break
            max_x = max(max_x, key)
            min_x = min(min_x, key)
            max_y = max(max_y, value)
            min_y = min(min_y, value)
            xs.append(key)
            ys.append(value)

        if can_be_represented:
            plt.plot(xs, ys, 'ro')
            plt.axis([min_x, max_x, min_y, max_y])
            plt.title(self.ID)
            plt.grid(True)
            plt.savefig(MethodCollector.image_num.__str__() + ".png")
            plt.clf()
            MethodCollector.image_num += 1
        return result

    def get_data(self):
        """
        Processes collected data into the dictionary.

        :returns collected data in a dictionary representation {id : collected_data}.
        :rtype dict{id : data}
        """
        pass

    def flush(self):
        self.__flush__()
        self.first_commit = False

    def __flush__(self):
        pass

    @staticmethod
    def code_changed(method1, method2):

        if method1 is None and method2 is None:
            return False
        if method1 is None or method2 is None:
            return True
        code1 = method1.code
        code2 = method2.code
        if len(code1) != len(code2):
            return True
        for old, new in zip(code1, code2):
            if old != new:
                return True
        return False


class JavaMethodsDataCollector(Collector):
    def __init__(self, method_collectors):
        self.ID = "method_data"
        self.method_collectors = method_collectors
        self.__method_ids = {}
        self.__id_counter = 0
        self.__previous_implementations = {}

    def collect(self, commit):
        current_implementations = {}

        for file in commit.list_objects():
            _, file_extension = os.path.splitext(file.path)
            if file_extension != ".java":
                continue

            content = file.get_content()
            file_analyzer = JavaFile(content)
            methods = file_analyzer.eval_blocks()

            for method in methods:
                method.file = file.path

                # mapping signature into the method id
                full_method_signature = file.path + "::" + method.id

                if full_method_signature in self.__method_ids:
                    method_id = self.__method_ids[full_method_signature]
                else:
                    method_id = self.__id_counter
                    self.__method_ids[full_method_signature] = method_id
                    self.__id_counter += 1

                old_method = None
                if method_id in self.__previous_implementations:
                    old_method = self.__previous_implementations[method_id]
                for collector in self.method_collectors:
                    collector.collect(commit, method_id, method, old_method)
                current_implementations[method_id] = method
        for collector in self.method_collectors:
            collector.flush()
        self.__previous_implementations = current_implementations

    def process(self):
        result = {}
        for method_id in range(0, self.__id_counter):
            result[method_id] = []
        for collector in self.method_collectors:
            print(collector.ID)
            collector_data = collector.process()
            for method_id in range(0, self.__id_counter):
                if type(collector_data[method_id]) == list:
                    result[method_id] += collector_data[method_id]
                else:
                    result[method_id].append(collector_data[method_id])
        return result

    def get_data(self):
        result = {}
        for method_id in range(0, self.__id_counter):
            result[method_id] = []
        for collector in self.method_collectors:
            print(collector.ID)
            collector_data = collector.get_data()
            for method_id in range(0, self.__id_counter):
                if type(collector_data[method_id]) == list:
                    result[method_id] += collector_data[method_id]
                else:
                    result[method_id].append(collector_data[method_id])
        return result


class MethodCurrentChangeCollector(MethodCollector):
    class MethodStatus(enum.IntEnum):
        UNKNOWN = -2
        NOT_EXIST = -1
        ADDED = 1
        NO_CHANGE = 0
        MODIFIED = 2
        DELETED = 3

    def __init__(self):
        super().__init__()
        self.ID = "method_change_type"
        self.__current_changes = set([])
        self.__change_status = {}

    def collect(self, commit, method_id, method, old_method):
        # Checking for data initialization commit
        if self.first_commit:
            self.__current_changes.add(method_id)
            self.__change_status[method_id] = self.MethodStatus.UNKNOWN.__int__()
            return
        if old_method is None:
            self.__current_changes.add(method_id)
            self.__change_status[method_id] = self.MethodStatus.ADDED.__int__()
            return
        # Then method also existed in the previous commit (not new and not deleted)
        if self.code_changed(method, old_method):
            self.__current_changes.add(method_id)
            self.__change_status[method_id] = self.MethodStatus.MODIFIED.__int__()
        else:
            self.__current_changes.add(method_id)
            self.__change_status[method_id] = self.MethodStatus.NO_CHANGE.__int__()
        return

    def __flush__(self):
        for method in self.__change_status:
            if method not in self.__current_changes:
                self.__change_status[method] = self.MethodStatus.DELETED.__int__()

        self.__current_changes = set([])

    def get_data(self):
        return self.__change_status


class MethodLatestChangesCollector(MethodCollector):
    def __init__(self, stored_changes_max):
        super().__init__()
        self.ID = "method_latest_changes_types"
        self.method_current_change_collector = MethodCurrentChangeCollector()
        self.__stored_changes_max = stored_changes_max
        self.__latest_changes = []

    def collect(self, commit, method_id, method, old_method):
        self.method_current_change_collector.collect(commit, method_id, method, old_method)

    def __flush__(self):
        self.method_current_change_collector.flush()
        self.__latest_changes.append(self.method_current_change_collector.get_data().copy())
        while len(self.__latest_changes) > self.__stored_changes_max:
            self.__latest_changes.pop(0)

    def get_data(self):
        result = {}
        for data_list in self.__latest_changes:
            for element in data_list:
                if element not in result:
                    result[element] = []
                result[element].append(data_list[element])
        for method in result:
            num_to_be_added = self.__stored_changes_max - len(result[method])
            result[method] = [-1] * num_to_be_added + result[method]
        return result


class MethodLatestChangesSummary(MethodCollector):
    def __init__(self, stored_changes_max):
        super().__init__()
        self.ID = "method_latest_changes_summary"
        self.method_latest_changes_collector = MethodLatestChangesCollector(stored_changes_max)

    def collect(self, commit, method_id, new_method, old_method):
        self.method_latest_changes_collector.collect(commit, method_id, new_method, old_method)

    def __flush__(self):
        self.method_latest_changes_collector.__flush__()

    def get_data(self):
        result = {}
        data = self.method_latest_changes_collector.get_data()
        for method, latest_changes in data.items():
            recently_added = MethodCurrentChangeCollector.MethodStatus.ADDED in latest_changes
            recently_modified = MethodCurrentChangeCollector.MethodStatus.MODIFIED in latest_changes
            recently_deleted = MethodCurrentChangeCollector.MethodStatus.DELETED in latest_changes
            result[method] = [int(recently_added), int(recently_modified), int(recently_deleted)]
        return result


class MethodCurrentTimeOfLastChangeCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_change_time"
        self.__change_timestamps = {}
        self.__last_commit_timestamp = -1
        self.__first_commit_timestamp = -1

    def collect(self, commit, method_id, method, old_method):
        if self.__first_commit_timestamp == -1:
            self.__first_commit_timestamp = commit.committer_time
        self.__last_commit_timestamp = commit.committer_time
        if self.code_changed(method, old_method):
            self.__change_timestamps[method_id] = commit.committer_time

    def get_data(self):
        result = {}
        for method, timestamp in self.__change_timestamps.items():
            result[method] = (self.__last_commit_timestamp - timestamp) / \
                             (self.__last_commit_timestamp - self.__first_commit_timestamp)
        return result


class MethodLatestTimeOfLastChangesCollector(MethodCollector):
    def __init__(self, stored_changes_max):
        super().__init__()
        self.ID = "method_latest_change_times"
        self.__method_current_time_of_last_change = MethodCurrentTimeOfLastChangeCollector()
        self.__change_timestamps = []
        self.__stored_changes_max = stored_changes_max

    def collect(self, commit, method_id, method, old_method):
        self.__method_current_time_of_last_change.collect(commit, method_id, method, old_method)

    def __flush__(self):
        self.__method_current_time_of_last_change.flush()
        self.__change_timestamps.append(self.__method_current_time_of_last_change.get_data().copy())
        while len(self.__change_timestamps) > self.__stored_changes_max:
            self.__change_timestamps.pop(0)

    def get_data(self):
        result = {}
        for data_list in self.__change_timestamps:
            for element in data_list:
                if result[element] is None:
                    result[element] = []
                result[element].append(data_list[element])
        for method in result:
            num_to_be_added = self.__stored_changes_max - len(result[method])
            result[method] = [-1] * num_to_be_added + result[method]
        return result


class MethodCommitsSinceLastChangeCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_commits_since_last_change"
        self.__commits_since_last_change = {}

    def collect(self, commit, method_id, new_method, old_method):
        if self.first_commit or self.code_changed(old_method, new_method):
            self.__commits_since_last_change[method_id] = -1

    def __flush__(self):
        for method in self.__commits_since_last_change:
            self.__commits_since_last_change[method] += 1

    def get_data(self):
        return self.__commits_since_last_change


class MethodCommitChangeExpectationCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_commits_change_expectation"
        self.__commits_since_change_collector = MethodCommitsSinceLastChangeCollector()
        self.__method_change_ratio = MethodChangeRatio()

    def collect(self, commit, method_id, new_method, old_method):
        self.__commits_since_change_collector.collect(commit, method_id, new_method, old_method)
        self.__method_change_ratio.collect(commit, method_id, new_method, old_method)

    def __flush__(self):
        self.__commits_since_change_collector.flush()
        self.__method_change_ratio.flush()

    def get_data(self):
        result = {}

        ratios = self.__method_change_ratio.get_data()
        for method, commits_cnt in self.__commits_since_change_collector.get_data().items():
            result[method] = commits_cnt * ratios[method]
        return result


class MethodExistenceRatio(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_existence_ratio"
        self.__counter = {}
        self.__total_commits = 0

    def collect(self, commit, method_id, new_method, old_method):
        if method_id not in self.__counter:
            self.__counter[method_id] = 0
        self.__counter[method_id] += 1

    def __flush__(self):
        self.__total_commits += 1

    def get_data(self):
        result = {}

        for method, commits_existed in self.__counter.items():
            result[method] = commits_existed / self.__total_commits
            if result[method] > 1:
                print(method, commits_existed, self.__total_commits)
        return result


class MethodFadingLinesChangeRatioCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_fading_lines_change_ratio"
        self.__fading_ratios = {}
        self.__new_ratios = {}

    def collect(self, commit, method_id, new_method, old_method):
        if method_id not in self.__fading_ratios:
            self.__fading_ratios[method_id] = 0.0
            return
        self.__new_ratios[method_id] = 0.0
        if old_method is not None:
            self.__new_ratios[method_id] = difflib.SequenceMatcher(
                isjunk=lambda x: x in " \t",
                a="\n".join(new_method.code),
                b="\n".join(old_method.code)).ratio()

    def __flush__(self):
        for method, old_ratio in self.__fading_ratios.items():
            new_ratio = 1.0
            if method in self.__new_ratios:
                new_ratio = self.__new_ratios[method]
            self.__fading_ratios[method] = (new_ratio + old_ratio) / 2
        self.__new_ratios = {}

    def get_data(self):
        return self.__fading_ratios


class MethodCommittersCountingCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_commiters_counter"
        self.__committers = {}

    def collect(self, commit, method_id, new_method, old_method):
        if method_id not in self.__committers:
            self.__committers[method_id] = set([])
        if self.code_changed(new_method, old_method):
            self.__committers[method_id].add(commit.committer)

    def get_data(self):
        result = {}

        for method, committers in self.__committers.items():
            result[method] = len(committers)
        return result


class MethodLastCommitterCollector(MethodCollector):
    committers = {}
    next_free = 0

    def __init__(self):
        super().__init__()
        self.ID = "method_last_committer"
        self.__last_committer = {}

    def collect(self, commit, method_id, new_method, old_method):
        if self.code_changed(new_method, old_method):
            self.__last_committer[method_id] = commit.committer

    def get_data(self):
        result = {}

        for method, committer in self.__last_committer.items():
            if committer not in MethodLastCommitterCollector.committers:
                MethodLastCommitterCollector.committers[committer] = MethodLastCommitterCollector.next_free
                MethodLastCommitterCollector.next_free += 1
            result[method] = MethodLastCommitterCollector.committers[committer]
        return result


class MethodChangeRatio(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_change_ratio"
        self.__change_info = {}
        self.__commits_in_total = 0

    def collect(self, commit, method_id, new_method, old_method):
        if method_id not in self.__change_info:
            self.__change_info[method_id] = (1, self.__commits_in_total)
            return
        if self.code_changed(new_method, old_method):
            changed, existed = self.__change_info[method_id]
            self.__change_info[method_id] = (changed + 1, existed)

    def __flush__(self):
        self.__commits_in_total += 1

    def get_data(self):
        result = {}
        for key, value in self.__change_info.items():
            commits_changed, commits_not_existed = value
            result[key] = commits_changed / (self.__commits_in_total - commits_not_existed)
        return result


class MethodLatestChangeRatio(MethodCollector):
    def __init__(self, stored_changes_max):
        super().__init__()
        self.__stored_changes_max = stored_changes_max
        self.ID = "method_latest_change_ratio"
        self.__change_info = {}
        self.__commits_in_total = 0

    def collect(self, commit, method_id, new_method, old_method):
        if method_id not in self.__change_info:
            self.__change_info[method_id] = []
        if self.code_changed(new_method, old_method):
            self.__change_info[method_id].append(1)
        else:
            self.__change_info[method_id].append(0)
        if len(self.__change_info[method_id]) > self.__stored_changes_max:
            self.__change_info[method_id].pop(0)

    def get_data(self):
        result = {}

        for method, changes in self.__change_info.items():
            result[method] = changes.count(1) / self.__stored_changes_max
        return result


# Local metrics #


class MethodSignatureCollector(MethodCollector):
    name_map = {}
    next_free = 0

    def __init__(self):
        super().__init__()
        self.ID = "method_signature"
        self.__bodies = {}

    def collect(self, commit, method_id, new_method, old_method):
        if new_method is not None:
            self.__bodies[method_id] = new_method.code

    def clear(self):
        MethodSignatureCollector.name_map = {}
        MethodSignatureCollector.next_free = {}

    def get_data(self):
        result = {}

        for method_id, body in self.__bodies.items():
            signature = retrieve_signature("\n".join(body))
            if signature not in MethodSignatureCollector.name_map:
                MethodSignatureCollector.name_map[signature] = MethodSignatureCollector.next_free
                MethodSignatureCollector.next_free += 1
            result[method_id] = MethodSignatureCollector.name_map[signature]

        return result


class MethodLengthCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_length"
        self.__lengths = {}

    def collect(self, commit, method_id, method, old_method):
        self.__lengths[method_id] = len(method.code)

    def get_data(self):
        return self.__lengths


class MethodReturnCountingCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_return_counter"
        self.__bodies = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__bodies[method_id] = new_method.code

    def get_data(self):
        result = {}

        for method, body in self.__bodies.items():
            result[method] = 0
            if body is not None:
                for line in body:
                    result[method] += line.split().count("return")
        return result


class MethodClassDepthCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_class_depth"
        self.__locations = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__locations[method_id] = new_method.location

    def get_data(self):
        result = {}

        for method, location in self.__locations.items():
            result[method] = location.count('.')
        return result


class MethodReturnTypeCollector(MethodCollector):
    types = {}
    next_free = 0

    def __init__(self):
        super().__init__()
        self.ID = "method_return_type_collector"
        self.__return_types = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__return_types[method_id] = new_method.return_type

    def get_data(self):
        result = {}
        for method, type in self.__return_types.items():
            if type not in MethodReturnTypeCollector.types:
                MethodReturnTypeCollector.types[type] = MethodReturnTypeCollector.next_free
                MethodReturnTypeCollector.next_free += 1
            result[method] = MethodReturnTypeCollector.types[type]
        return result

    def clear(self):
        MethodReturnTypeCollector.types = {}
        MethodReturnTypeCollector.next_free = 0


class MethodMaxLineLengthCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_max_line_length"
        self.__bodies = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__bodies[method_id] = new_method.code

    def get_data(self):
        result = {}

        for method, body in self.__bodies.items():
            local_max = 0
            for line in body:
                local_max = max(len(line), local_max)
            result[method] = local_max
        return result


class MethodNumbersCountingCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_numbers_count"
        self.__bodies = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__bodies[method_id] = new_method.code

    def get_data(self):
        result = {}

        for method, body in self.__bodies.items():
            result[method] = len(re.findall(r"\d+", "\n".join(body))) / len(body)
        return result


class MethodAssignmentCountingCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.ID = "method_assignment_count"
        self.__bodies = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__bodies[method_id] = new_method.code

    def get_data(self):
        result = {}

        for method, body in self.__bodies.items():
            result[method] = "\n".join(body).replace("==", "").count("=") / len(body)
        return result


class MethodDirectoryCollector(MethodCollector):
    dirs = {}
    next_free = 0

    def __init__(self):
        super().__init__()
        self.ID = "method_directory_name_collector"
        self.__directories = {}

    def collect(self, commit, method_id, new_method, old_method):
        self.__directories[method_id] = new_method.file[:new_method.file.rfind(os.path.sep)]

    def get_data(self):
        result = {}
        for method, dir_name in self.__directories.items():
            if dir_name not in MethodDirectoryCollector.dirs:
                MethodDirectoryCollector.dirs[dir_name] = MethodDirectoryCollector.next_free
                MethodDirectoryCollector.next_free += 1
            result[method] = MethodDirectoryCollector.dirs[dir_name]
        return result

    def clear(self):
        MethodDirectoryCollector.dirs = {}
        MethodDirectoryCollector.next_free = 0
