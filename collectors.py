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


class JavaMethodsDataCollector(Collector):
    def __init__(self, collectors):
        self.ID = "method_data"
        self.collectors = collectors

    def collect(self, commit):
        for file in commit.list_objects():
            content = file.get_content()
            file_analyzer = JavaFile(content)
            methods = file_analyzer.eval_blocks()

            for method in methods:
                method_block = methods[method]
                new_name = file.path + "::" + method
                for collector in self.collectors:
                    collector.collect(new_name, method_block)

    def process(self):
        results = []
        for collector in self.collectors:
            results.append(collector.process())

    def get_data(self):
        return self.collectors


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
