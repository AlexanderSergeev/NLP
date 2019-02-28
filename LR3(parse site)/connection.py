from myParser import parse_og_tags
from bs4 import BeautifulSoup
from typing import List, Generator, Union
from collections import namedtuple
import time

import urllib3
from urllib.parse import urljoin
urllib3.disable_warnings()
from urllib.parse import urlparse
from urllib3.exceptions import ReadTimeoutError, NewConnectionError, MaxRetryError
from urllib3.response import HTTPResponse

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

def drop_query(url: str) -> str:
    return urlparse(url)._replace(query=None).geturl()

Link = namedtuple('Link', ['url', 'name'], defaults=[None, ''])

class Connection:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36'
    }

    def __init__(self, timeout: float = 5.0, num_pools: int = 50, parser: str = 'html.parser') -> None:
        self.http = urllib3.PoolManager(num_pools=num_pools, timeout=timeout)
        self.parser = parser
        caps = DesiredCapabilities().CHROME
        caps["pageLoadStrategy"] = "normal"
        prefs = {'profile.managed_default_content_settings.images': 2, 'profile.managed_default_content_settings.script': 2, 'profile.managed_default_content_settings.stylesheet': 2, 'profile.managed_default_content_settings.subdocument': 2}
        options = webdriver.ChromeOptions()
        options.add_experimental_option("prefs", prefs)
        options.add_argument(
            'user-agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36')

        self.browser = webdriver.Chrome(chrome_options=options,
                                        executable_path=r'/home/asergeev/Downloads/chromedriver_linux64/chromedriver',
                                        desired_capabilities=caps)

    def get(self, link: Link, stream: bool = False, scroll: bool = True) -> Union[BeautifulSoup, HTTPResponse]:
        try:
            result = ''
            if scroll:
                self.browser.get(link.url)
                time.sleep(0.1)
                elem = self.browser.find_element_by_tag_name("body")
                no_of_pagedowns = 1000
                while no_of_pagedowns:
                    try:
                        elem.send_keys(Keys.PAGE_DOWN)
                    except:
                        elem = self.browser.find_element_by_tag_name("body")
                        elem.send_keys(Keys.PAGE_DOWN)
                    no_of_pagedowns -= 1
                time.sleep(1)
                result = self.browser.page_source
            else:
                request = self.http.request('GET', link.url, preload_content=not stream, headers=self.headers)
                if request.status == 200:
                    result = request.data
                else:
                    print("Code", request.status, "at", link.url)
            if stream:
                return result
            else:
                return BeautifulSoup(result, self.parser)

        except (NewConnectionError, MaxRetryError, ReadTimeoutError) as e:
            print(e.__class__.__name__, "at", link.url)

    def children(self, link: Link, css: str, query: bool = True, scroll: bool = True) -> Generator[Link, None, None]:
        page = self.get(link, scroll=scroll)
        if page:
            if len(page.select(css)) == 0:
                yield link
            else:
                for match in page.select(css):
                    url = urljoin(link.url, match['href'])
                    if not query:
                        url = drop_query(url)
                    yield Link(url, match.text)

    def get_categories(self, link: Link, selector: str) -> Generator[Link, None, None]:
        self.browser.get(link.url)
        time.sleep(0.1)
        self.browser.find_element_by_css_selector('.hamburger_zone > button').click()
        page = BeautifulSoup(self.browser.page_source, self.parser)
        self.browser.find_element_by_xpath('//*[@id="modal_navallsport"]/div[1]').click()
        for match in page.select(selector):
            url = urljoin(link.url, match['href'])
            yield Link(url, match.text)

    def meta_tags(self, link: Link, tags: List[str]) -> dict:
        r = self.get(link, stream=True, scroll=False)
        if r:
            return parse_og_tags(r, tags)
