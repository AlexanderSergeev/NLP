from connection import Connection, Link
from collections import defaultdict
from typing import Generator, List, Tuple
from concurrent.futures import ThreadPoolExecutor

class Crawler:
    def __init__(self, n_workers: int = 4, **kwargs):
        self.conn = Connection(**kwargs)
        self.exec = ThreadPoolExecutor(max_workers = n_workers)

    def categories(self) -> Generator[Link, None, None]:
        root = Link('https://www.eurosport.ru/')
        cats = self.conn.children(root, '.categorylist__item a')
        for cat in cats:
            subcats = self.conn.children(cat, '.categorylist__item a')
            if subcats:
                for subcat in subcats:
                    yield Link(subcat.url, cat.name + '/' + subcat.name)
            else:
                yield cat

    def get_stories(self) -> defaultdict:
        res = defaultdict(set)
        story_css = '.storylist-container__main-title a'
        for cat in self.categories():
            stories = self.conn.children(cat, story_css, query = False)
            for story in stories:
                res[story].add(cat.name)
        return res
    
    def get_tags(self, links: List[Link]) -> Generator[Tuple[Link, dict], None, None]:
        res = self.exec.map(lambda x: self.conn.meta_tags(x, ['og:title', 'og:description']), links)
        for link, tags in zip(links, res):
            if tags:
                yield link, tags

    def traverse(self) -> Generator[dict, None, None]:
        for story, meta in self.get_stories().items():
            links = self.conn.children(story, '.ob-dynamic-rec-container .ob-dynamic-rec-link')
            for link, tags in self.get_tags(list(links)):
                yield {
                    'story': story.url,
                    'meta': list(meta),
                    'url': link.url,
                    'title': tags['og:title'],
                    'descr': tags['og:description']
                }