import scrapy
import datetime
from scrapy.item import Item, Field
from scrapy.http import Request
from scrapy.linkextractors import LinkExtractor


def error(msg):
    print(str(datetime.datetime.now()) + " ERROR: " + msg)


def info(msg):
    print(str(datetime.datetime.now()) + " INFO: " + msg)


class AnalyzedItem(Item):
    url = scrapy.Field()

    # URL of parent page
    parent = scrapy.Field()

    # Link text in parent page
    link_text = scrapy.Field()

    # True, if this URL in allowed to crawl
    is_allowed = scrapy.Field()

    # True, if 4XX or 5XX error while getting the page
    is_broken_link = scrapy.Field()

    # True if the page in the page is relevant with respect to the link_text in the parent page
    is_valid_page = scrapy.Field()


class AnalyzeLinks(scrapy.Spider):
    # Name of the crawler
    name = "AnalyzeLinks"

    # list of domains that will be allowed to be crawled
    allowed_domains = [ "github.com" ]

    # list of starting urls for the crawler
    start_urls = [ 'https://github.com/ajnavi/analyze-links' ]

    # Don't crawl following URLs
    not_allowed_urls = set(['https://github.com', 'https://github.com/ajnavi',
        'https://github.com/ajnavi/analyze-links/commits', 'https://github.com/ajnavi/analyze-links/security',
        'https://github.com/ajnavi/analyze-links/pulse'])

    # Throttle crawl speed to prevent hitting site too hard
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, # requests at the same time
        'DOWNLOAD_DELAY': 0.5, # delay between requests
        'DEPTH_LIMIT': 2 # maximum depth allowed to crawl
    }


    def __init__(self):
        # Restrict crawling to links in the main#js-repo-pjax-container of the page only
        self.link_extractor = LinkExtractor(unique=('yes'), restrict_css='main#js-repo-pjax-container')


    def get_status_code(self, status):
        return int(status / 100)


    # Return True if the page in the response object is relevant with respect to the link_text in the parent page
    def check_page(self, response, link_text):
        return True if link_text in response.css('title') else False


    def get_item(self, url, parent, link_text, is_allowed, is_broken_link, is_valid_page):
        item = AnalyzedItem()
        item['url'] = url
        item['parent'] = parent
        item['link_text'] = link_text
        item['is_allowed'] = is_allowed
        item['is_broken_link'] = is_broken_link
        item['is_valid_page'] = is_valid_page
        return item


    def analyze_page(self, response, parent, link_text):
        url = response.url
        is_allowed = True
        is_broken_link = False
        is_valid_page = False
        
        response_code = self.get_status_code(response.status)
        if response_code == 4 or response_code == 5:
            # Response is 4XX or 5XX
            error("Invalid URL: " + response.url)
            is_broken_link = True

        is_valid_page = self.check_page(response, link_text)

        return self.get_item(url, parent, link_text, is_allowed, is_broken_link, is_valid_page)


    def check_allowed_url(self, link_url, parent, link_text):
        item = self.get_item(link_url, parent, link_text, is_allowed=False, is_broken_link=False, is_valid_page=True)

        if link_url not in AnalyzeLinks.not_allowed_urls:
            for ad in AnalyzeLinks.allowed_domains:
                if ad in link_url:
                    item['is_allowed'] = True
                    break

        if not item['is_allowed']:
            return item
        else:
            return None


    def parse(self, response, parent=None, text=None):
        info("Visiting URL: {} parent: {} link text: {}".format(response.url, parent, text))

        yield self.analyze_page(response, parent, text)

        parent = response.url
        for link in self.link_extractor.extract_links(response):
            link_text = link.text.strip()
            item = self.check_allowed_url(link.url, response.url, link_text)
            if item:
                info("Found not allowed link: {} parent: {} text: {}".format(link.url, parent, link_text))
                yield item
            else:
                info("Found link: {} parent: {} text: {}".format(link.url, parent, link_text))
                yield Request(link.url, callback=self.parse, cb_kwargs=dict(parent=parent, text=link_text))


