import difflib
from enum import Enum, auto

from java_metrics import JavaFile


class Collector:
    def collect(self, data):
        pass

    def clear(self):
        pass

    def process(self):
        pass

    def get_data(self):
        pass


class MethodCollector(Collector):
    def __init__(self):
        self.__first_commit = True

    def collect(self, commit, method_id, new_method_body, old_method_body):
        pass

    def clear(self):
        pass

    def process(self):
        pass

    def get_data(self):
        pass

    def flush(self):
        self.__first_commit = False
        self.__flush__()

    def __flush__(self):
        pass

    @staticmethod
    def code_changed(code1, code2):
        if code1 is None and code2 is None:
            return True
        if code1 is None or code2 is None:
            return False
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
            content = file.get_content()
            file_analyzer = JavaFile(content)
            methods = file_analyzer.eval_blocks()

            for method in methods:
                method_block = methods[method]
                full_method_signature = file.path + "::" + method
                if full_method_signature in self.__method_ids:
                    method_id = self.__method_ids[full_method_signature]
                else:
                    method_id = self.__id_counter
                    self.__method_ids[full_method_signature] = method_id
                    self.__id_counter += 1

                for collector in self.method_collectors:
                    collector.collect(commit, method_id, method_block, self.__previous_implementations[method_id])
                current_implementations[method_id] = method_block
        for collector in self.method_collectors:
            collector.flush()
        self.__previous_implementations = current_implementations

    def process(self):
        return self.get_data()

    def get_data(self):
        result = {}
        for method_id in range(0, self.__id_counter):
            result[method_id] = []
        for collector in self.method_collectors:
            collector_data = collector.get_data()
            for method_id in range(0, self.__id_counter):
                if type(collector_data[method_id]) == list:
                    result[method_id] += collector_data[method_id]
                else:
                    result[method_id].append(collector_data[method_id])
        return result


class MethodSignatureCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.next_free = 0
        self.__name_map = {}
        self.__result = {}

    def collect(self, commit, method_id, method_body, old_method_body):
        if method_body[0] not in self.__name_map:
            self.__name_map = self.next_free
            self.next_free += 1
        self.__result[method_id] = self.__name_map[method_body[0]]

    def process(self):
        return self.get_data()

    def get_data(self):
        return self.__result


class MethodLengthCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.__lengths = {}

    def collect(self, commit, method_id, method_body, old_method_body):
        self.__lengths[method_id] = len(method_body)

    def process(self):
        return self.get_data()

    def get_data(self):
        return self.__lengths


class MethodCurrentChangeCollector(MethodCollector):
    class MethodStatus(Enum):
        NOT_EXIST = -1
        ADDED = 1
        NO_CHANGE = 0
        MODIFIED = 2
        DELETED = 3

    def __init__(self):
        super().__init__()
        self.__current_changes = set([])
        self.__change_status = {}

    def collect(self, commit, method_id, method_body, old_method_body):
        # Checking for data initialization commit
        if self.__first_commit:
            self.__current_changes.add(method_id)
            return
        if old_method_body is None:
            self.__current_changes.add(method_id)
            self.__change_status[method_id] = self.MethodStatus.ADDED
            return
        # Then method also existed in the previous commit (not new and not deleted)
        if self.code_changed(method_body, old_method_body):
            self.__change_status[method_id] = self.MethodStatus.MODIFIED
        else:
            self.__change_status[method_id] = self.MethodStatus.NO_CHANGE
        return

    def __flush__(self):
        for method in self.__change_status:
            if method not in self.__current_changes:
                self.__change_status[method] = self.MethodStatus.DELETED

        self.__current_changes = {}

    def get_data(self):
        return self.__change_status


class MethodLatestChangesCollector(MethodCollector):
    def __init__(self, stored_changes_max):
        super().__init__()
        self.method_current_change_collector = MethodCurrentChangeCollector()
        self.__stored_changes_max = stored_changes_max
        self.__latest_changes = []

    def collect(self, commit, method_id, method_body, old_method_body):
        self.method_current_change_collector.collect(commit, method_id, method_body, old_method_body)

    def __flush__(self):
        self.method_current_change_collector.flush()
        self.__latest_changes.append(self.method_current_change_collector.get_data)
        while len(self.__latest_changes) > self.__stored_changes_max:
            self.__latest_changes.pop(0)

    def get_data(self):
        result = {}
        for data_list in self.__latest_changes:
            for element in data_list:
                if result[element] is None:
                    result[element] = []
                result[element].append(data_list[element])
        for method in result:
            num_to_be_added = self.__stored_changes_max - len(result[method])
            result[method] = [-1] * num_to_be_added + result[method]
        return result


class MethodCurrentTimeOfLastChangeCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.__change_timestamps = {}

    def collect(self, commit, method_id, method_body, old_method_body):
        if self.code_changed(method_body, old_method_body):
            self.__change_timestamps[method_id] = commit.committer_time

    def get_data(self):
        return self.__change_timestamps


class MethodLatestTimeOfLastChangesCollector(MethodCollector):
    def __init__(self, stored_changes_max):
        super().__init__()
        self.__method_current_time_of_last_change = MethodCurrentTimeOfLastChangeCollector()
        self.__change_timestamps = []
        self.__stored_changes_max = stored_changes_max

    def collect(self, commit, method_id, method_body, old_method_body):
        self.__method_current_time_of_last_change.collect(commit, method_id, method_body, old_method_body)

    def __flush__(self):
        self.__method_current_time_of_last_change.flush()
        self.__change_timestamps.append(self.__method_current_time_of_last_change.get_data())
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
        self.__commits_since_last_change = {}

    def collect(self, commit, method_id, new_method_body, old_method_body):
        if self.__first_commit or self.code_changed(old_method_body, new_method_body):
            self.__commits_since_last_change[method_id] = -1

    def __flush__(self):
        for method in self.__commits_since_last_change:
            self.__commits_since_last_change[method] += 1

    def get_data(self):
        return self.__commits_since_last_change


class MethodFadingLinesChangeRatioCollector(MethodCollector):
    def __init__(self):
        super().__init__()
        self.__fading_ratios = {}
        self.__new_ratios = {}

    def collect(self, commit, method_id, new_method_body, old_method_body):
        if method_id not in self.__fading_ratios:
            self.__fading_ratios[method_id] = 1
            return
        self.__new_ratios[method_id] = difflib.SequenceMatcher(
            isjunk=lambda x: x in " \t",
            a="\n".join(new_method_body),
            b="\n".join(old_method_body)).ratio()

    def __flush__(self):
        for method, old_ratio in self.__fading_ratios.items():
            new_ratio = self.__new_ratios[method]
            if new_ratio is None:
                new_ratio = 1.0
            self.__fading_ratios[method] = (new_ratio + old_ratio) / 2
        self.__new_ratios = {}

    def get_data(self):
        return self.__fading_ratios


class CommitSizeCollector(Collector):
    def __init__(self):
        self.ID = "commit_size"
        self.commit_sizes = []

    def collect(self, commit):
        cnt = 0
        for obj in commit.list_objects():
            content = obj.get_content()
            if content is not None:
                cnt += len(content)
        self.commit_sizes.append(cnt)

    def clear(self):
        self.commit_sizes = []

    def process(self):
        return self.commit_sizes


class AuthorsDataCollector(Collector):
    def __init__(self, collectors_generator):
        sample = collectors_generator()
        self.ID = "authors_data:" + sample.ID
        self.authors_collectors = {}
        self._collectors_generator = collectors_generator

    def collect(self, commit):
        if commit.author not in self.authors_collectors:
            self.authors_collectors[commit.author] = self._collectors_generator()
        self.authors_collectors[commit.author].collect(commit)

    def clear(self):
        self.authors_collectors = {}

    def process(self):
        for author, collector in self.authors_collectors.items():
            print("Processing", author)
            collector.process()

    def get_data(self):
        return self.authors_collectors
