import threading
from logging import Logger
import reactivex as rx
from reactivex import operators as ops
from reactivex.subject import Subject
from bs4 import BeautifulSoup
import html 
import re
import requests
import warnings
from readability import Document


from src.config import *


class WebScrap:
    """
    Class for Web Scraping articles
    """

    def __init__(self, logger: Logger, mongoService, scheduler, webScrapProcessor):
        self.completeSubject = Subject()
        self.countingLock = threading.Lock()
        self.articleCount = 0
        self.scrapLock = threading.Lock()
        self.articleScrapCount = 0

        self.mongoService = mongoService
        self.scheduler = scheduler
        self.logger = logger
        self.webScrapProcessor = webScrapProcessor

    def complete(self):
        """
        Called when web scrap is complete. Logs completed articles and unblocks main thread
        """
        self.logger.info("Completed extraction for %s articles", self.articleCount)
        self.completeSubject.on_next(1)
        self.completeSubject.on_completed()

    def countAndLog(self):
        """
        Counts articles that goes through the stream. Logs based off the frequency defined in {LOG_FREQUENCY}.
        Is a synchronous function that only allows 1 thread to execute.
        """
        # Avoid race conditions by adding a lock
        with self.countingLock:
            self.articleCount += 1
            if self.articleCount % LOG_FREQUENCY == 0:
                self.logger.info("Completed web scraping for %s articles", self.articleCount)

    def run(self):
        """
        Starts Web Scraping. Will block main thread until complete or program timeout.
        """
        self.buildWebScrapPipeline().subscribe(on_completed=lambda: self.complete())

        # Stream that blocks main thread until main stream completes
        # If main stream takes longer than {PROGRAM_TIMEOUT} this stream completes and unblocks main for shutdown
        self.completeSubject.pipe(
            ops.timeout(PROGRAM_TIMEOUT),
            ops.do_action(on_error=lambda err: self.logger.error("Error occurred during web scraping", exc_info=err))
        ).run()

    def buildWebScrapPipeline(self):
        """
        Builds observable stream for web scraping
        :return: Observable containing Web Scrap pipeline
        """
        # Call Mongo to get web scrap ids
        return self.mongoService.getNonWebScrapArticleAsStream().pipe(
            # web scrap content
            ops.flat_map(lambda article: self.submitArticleToProcessor(article)),
            # Counts article
            ops.do_action(on_next=lambda article: self.countAndLog()),
            # Error handling
            ops.do_action(on_error=lambda err: self.logger.error("Error occurred.", exc_info=err)),
            ops.catch(rx.empty()),
            # Scheduler setup for entire stream
            ops.subscribe_on(scheduler=self.scheduler),
        )

    def submitArticleToProcessor(self, article):
        return rx.of(article).pipe(
            ops.do_action(on_next=lambda a: self.webScrapProcessor.submitArticle(a)),
            ops.do_action(on_error=lambda err: self.logger.error("Error occurred.", exc_info=err)),
            ops.catch(rx.empty()),
            # Scheduler setup for entire stream
            ops.subscribe_on(scheduler=self.scheduler),
        )


def get_raw_page(url, logger: Logger):
    """
    Get raw web scrap page for given url
    :param url: the url of the page to web scrap
    :return: web scrap page in unicode
    """
    page = requests.get(url, timeout=REQUEST_TIMEOUT)
    if page.status_code != 200:
        logger.error("Web scrapping failed (status %s): %s", page.status_code, url)
        raise Exception("Web scrapping failed (status " + str(page.status_code) + "):" + url)

    # page.text is the content of the response in Unicode
    # page.content is the content of the response in bytes
    return page.text

def html_escape(html_content):
     # convert to HTML-safe sequence
    res = html.escape(html_content, quote=True)

    return res

# This function has been deprecated, since it is too strong and may remove actual article content.
def remove_ads(page_content):
    """
    Removes ads from html page
    :param page_content: raw html page content
    :return: html page content without the identifed ads
    """
    warnings.warn("deprecated", DeprecationWarning)

    soup = BeautifulSoup(page_content, 'html.parser')

    # check all div and iframe for ads
    for ad in soup.find_all(["div", "iframe"]):
        # regex : (non alphanumeric char) ad (optional s) (non alphanumeric char)
        if ( re.match('.*[^a-zA-Z0-9](ads?|ADS?)[^a-zA-Z0-9].*', str(soup).replace("\n", "")) ):
            ad.decompose() # remove ad content
    
    return soup.prettify()
    

def extract_full_text_from_html(html_content):
    """
    Extracts and cleans main text content by targeting the specific article container
    on The Hacker News (and similar sites).
    """

    doc = Document(html_content)
    html = doc.summary()  # returns main article html
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text

def web_scrap(url, logger: Logger, scheduler):
    """
    Web scrap given article page
    :param url: the url of the page to web scrap
    :return: html web scraped page content (or null if web scrap failed)
    """
    return rx.of(url).pipe(
        ops.map(lambda url: get_raw_page(url, logger)),  # raw HTML
        ops.catch(rx.of(None)),
        ops.subscribe_on(scheduler))


def logIfFailed(result, url, logger: Logger):
    if result is None:
        logger.error('Web scrap failed (return null) : %s', url)


def webScrap(article, logger: Logger, mongoService, scheduler):
    """
    Web Scrap page for a given article.
    :param articleContent: article to web scrap
    :return: Observable Stream that web scraps article page
    """
    return rx.of(article).pipe(
        # Get link
        ops.map(lambda article: article.articleUrl),
        # Web scrap the article at the URL
        ops.flat_map(lambda url: web_scrap(url, logger, scheduler)),
        # Insert into mongo db
        ops.do_action(lambda web_scrap: mongoService.insertWebScrapArticle(article.articleId, web_scrap)),
        # Extract and save cleaned full text
        ops.do_action(lambda raw_html: (
            mongoService.insertCleanFullText(
                article.articleId, extract_full_text_from_html(raw_html)
            ) if raw_html else None
        )),
        # Error handling
        ops.do_action(on_error=lambda err: logger.error("Error occurred while web scraping", exc_info=err)),
        ops.catch(rx.of(0)),
        ops.subscribe_on(scheduler=scheduler),
        ops.to_list()
    )