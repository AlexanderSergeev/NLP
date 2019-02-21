from parser import parse_og_tags
import urllib3
from urllib.parse import urljoin, urlparse
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from typing import List, Generator, Union
from collections import namedtuple
from urllib.parse import urlparse
from urllib3.exceptions import ReadTimeoutError, NewConnectionError, MaxRetryError
from urllib3.response import HTTPResponse

def drop_query(url: str) -> str:
    return urlparse(url)._replace(query=None).geturl()

Link = namedtuple('Link', ['url', 'name'], defaults = [None, ''])

class Connection:
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:65.0) Gecko/20100101 Firefox/65.0'
    }

    def __init__(self, timeout: float = 5.0, num_pools: int = 50, parser: str = 'html.parser') -> None:
        self.http = urllib3.PoolManager(num_pools = num_pools, timeout = timeout)
        self.parser = parser
    
    def get(self, link: Link, stream: bool = False) -> Union[BeautifulSoup, HTTPResponse]:
        try:
            r = self.http.request('GET', link.url, preload_content = not stream, headers = self.headers)
            if r.status == 200:
                if stream:
                    return r
                else:
                    return BeautifulSoup(r.data, self.parser)
            else:
                print("Code", r.status, "at", link.url)
        except (NewConnectionError, MaxRetryError, ReadTimeoutError) as e:
            print(e.__class__.__name__, "at", link.url)
    
    def children(self, link: Link, css: str, query: bool = True) -> Generator[Link, None, None]:
        page = self.get(link)
        if page:
            for match in page.select(css):
                url = urljoin(link.url, match['href'])
                if not query:
                    url = drop_query(url)
                yield Link(url, match.text)

    def meta_tags(self, link: Link, tags: List[str]) -> dict:
        r = self.get(link, stream = True)
        if r:
            return parse_og_tags(r, tags)
