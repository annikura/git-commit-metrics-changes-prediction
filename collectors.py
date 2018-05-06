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


class CommitTracker:
    def __init__(self):
        self.__current_commit = None

    def check_for_change(self, commit):
        if self.__current_commit is None or self.__current_commit.sha == commit.sha:
            self.__current_commit = commit
            self.flush()

    def flush(self):
        pass


class MethodCollector(Collector):
    def collect(self, commit, method_name, method_body):
        pass

    def clear(self):
        pass

    def process(self):
        pass

    def get_data(self):
        pass


class JavaMethodsDataCollector(Collector):
    def __init__(self, method_collectors):
        self.ID = "method_data"
        self.method_collectors = method_collectors

    def collect(self, commit):
        for file in commit.list_objects():
            content = file.get_content()
            file_analyzer = JavaFile(content)
            methods = file_analyzer.eval_blocks()

            for method in methods:
                method_block = methods[method]
                new_name = file.path + "::" + method
                for collector in self.method_collectors:
                    collector.collect(commit, new_name, method_block)

    def process(self):
        results = []
        for collector in self.method_collectors:
            results.append(collector.process())

    def get_data(self):
        return self.method_collectors


class MethodSignatureCollector(MethodCollector):
    def __init__(self):
        self.next_free = 0
        self.__name_map = {}
        self.__result = {}

    def collect(self, commit, method_name, method_body):
        if method_body[0] not in self.__name_map:
            self.__name_map = self.next_free
            self.next_free += 1
        self.__result[method_name] = self.__name_map[method_body[0]]

    def process(self):
        return self.get_data()

    def get_data(self):
        return self.__result


class MethodLengthCollector(MethodCollector):
    def __init__(self):
        self.__lengths = {}

    def collect(self, commit, method_name, method_body):
        if method_name not in self.__lengths:
            self.__lengths[method_name] = []
        self.__lengths[method_name].append(len(method_body))

    def process(self):
        return self.get_data()

    def get_data(self):
        return self.__lengths


class MethodCurrentChangeCollector(MethodCollector, CommitTracker):
    class MethodStatus(Enum):
        NO_CHANGE = auto()
        MODIFIED = auto()
        ADDED = auto()
        DELETED = auto()

    def __init__(self):
        super().__init__()
        self.__previous_implementations = {}
        self.__current_changes = set([])
        self.__change_status = {}

    def collect(self, commit, method_name, method_body):
        # filters out all deleted methods if there were any in the previous commit
        self.check_for_change(commit)
        if method_name not in self.__previous_implementations:
            self.__previous_implementations[method_name] = method_body
            self.__current_changes.add(method_name)
            self.__change_status[method_name] = self.MethodStatus.ADDED
            return
        # Then method name is in __previous_implementations (not deleted)
        if len(self.__previous_implementations) != len(method_body):
            self.__change_status[method_name] = self.MethodStatus.MODIFIED
            return
        # Method implementations have equal lengths. Now we they should be compared line by line
        for old, new in zip(self.__previous_implementations[method_name], method_body):
            if old != new:
                self.__change_status[method_name] = self.MethodStatus.MODIFIED
                return
        #  All the lines are equal
        self.__change_status[method_name] = self.MethodStatus.NO_CHANGE
        return

    def flush(self):
        to_be_removed = []
        for method in self.__previous_implementations:
            if method not in self.__current_changes:
                self.__change_status[method] = self.MethodStatus.DELETED
                to_be_removed.append(method)
        for item in to_be_removed:
            del self.__previous_implementations[item]
        self.__current_changes = {}

    def get_data(self):
        return self.__change_status


class MethodLatestChangesCollector(MethodCollector, CommitTracker):
    def __init__(self, stored_changes_max, method_current_change_collector):
        super().__init__()
        self.method_current_change_collector = method_current_change_collector
        self.__stored_changes_max = stored_changes_max
        self.__latest_changes = []

    def collect(self, commit, method_name, method_body):
        self.method_current_change_collector.collect(commit, method_name, method_body)

    def flush(self):
        self.__latest_changes.append(self.method_current_change_collector.get_data)
        while len(self.__latest_changes) > self.__stored_changes_max:
            self.__latest_changes.pop(0)

    def get_data(self):
        return self.__latest_changes


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
