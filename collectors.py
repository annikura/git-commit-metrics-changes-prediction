import matplotlib.pyplot as plt


class Collector:
    def collect(self, data):
        pass

    def clear(self):
        pass

    def process(self):
        pass

    def get_data(self):
        pass


class CommitSizeCollector(Collector):
    def __init__(self):
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
        plt.plot(list(range(1, len(self.commit_sizes) + 1)), self.commit_sizes)
        plt.show()

    def get_data(self):
        return self.commit_sizes


class AuthorsDataCollector(Collector):
    def __init__(self, collectors_generator):
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

