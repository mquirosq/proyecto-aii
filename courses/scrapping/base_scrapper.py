class BaseScraper:
    def fetch(self):
        """Download HTML or JSON from platform"""
        raise NotImplementedError

    def parse(self, html):
        """Extract raw data from the page"""
        raise NotImplementedError

    def normalize(self, data):
        """Convert raw data to consistent format"""
        raise NotImplementedError

    def run(self):
        html = self.fetch()
        data = self.parse(html)
        normalized = self.normalize(data)
        return normalized
