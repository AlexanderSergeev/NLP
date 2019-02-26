from html.parser import HTMLParser
import codecs
from typing import List, Tuple
from urllib3.response import HTTPResponse
from bs4 import BeautifulSoup, SoupStrainer
from ftfy import fix_text
import re
import atexit
from urllib3.exceptions import IncompleteRead, ReadTimeoutError, ProtocolError
import logging

def preprocess(string: str) -> str:
    string = fix_text(string)
    if re.search('[А-яЁё]', string):
        string = BeautifulSoup(string, "html.parser").text
        return " ".join(string.split())

class OGParser(HTMLParser):
    def __init__(self, tags: List[str]):
        HTMLParser.__init__(self)
        self.tags = dict.fromkeys(tags, None)

    def handle_starttag(self, html_tag: str, attrs: List[Tuple[str]]) -> bool:
        attrs = dict(attrs)
        if html_tag == 'meta':
            for og_tag in self.tags.keys():
                if attrs.get('property') == og_tag and attrs.get('content'):
                    self.tags[og_tag] = preprocess(attrs.get('content'))
                    if all(self.tags.values()):
                        return True
    
    def handle_endtag(self, html_tag: str) -> bool:
        if html_tag == 'head':
            return True

def get_encoding(r: HTTPResponse) -> codecs.StreamReader:
    encoding = re.search(r'charset=([^\s;]+)', r.getheader('Content-Type'))
    if encoding:
        encoding = encoding.groups(1)[0]
        try:
            return codecs.getreader(encoding)
        except LookupError:
            pass

def parse_og_tags(r: HTTPResponse, tags: List[str], chunk_size: int = 128) -> dict:
    atexit.register(lambda: r.release_conn())
    parser = OGParser(tags)
    reader = get_encoding(r)

    if reader:
        streamer = reader(r)
        while not streamer.isclosed():
            try:
                chunk = streamer.read(chunk_size)
            except UnicodeDecodeError:
                logging.error("Failed to decode chunk from %s", r.geturl())
                return None
            except (ReadTimeoutError, IncompleteRead, ProtocolError):
                logging.error("Broken connection at %s", r.geturl())
                return None
            if parser.feed(chunk): 
                break
    else:
        page = BeautifulSoup(r.read(), parse_only = SoupStrainer('meta'))
        for tag in tags:
            match = page.find('meta', property = tag, content = True)
            if match:
                parser.tags[tag] = match['content']

    if all(parser.tags.values()):
        return parser.tags