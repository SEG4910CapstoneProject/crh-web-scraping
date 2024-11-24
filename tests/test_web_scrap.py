import unittest
from unittest.mock import *

from logging import Logger
from reactivex.scheduler import CurrentThreadScheduler

from src.web_scrap import WebScrap, get_raw_page, webScrap, remove_ads, html_escape, logIfFailed
from src.mongo_service import *
from unittest import mock

from src.web_scrap_processor import WebScrapProcessor

UUID_1 = UUID("5d8a48c7-8799-49ba-8a61-b96c6f0d08e8")
UUID_2 = UUID("2c398d08-22e0-4f69-955b-69fb39666a9c")
UUID_3 = UUID("8c819db1-3dfa-4343-b6e7-9b73495fcdec")

def getMockObjects():
    loggerMock = Mock(spec_set=Logger)
    mongoServiceMock = Mock(spec_set=MongoService)
    webScrapProcessorMock = Mock(spec_set=WebScrapProcessor)

    return loggerMock, mongoServiceMock, webScrapProcessorMock

class WebScrapingTests(unittest.TestCase):
    def _mock_response(
            self,
            status=200,
            text="TEST"):
        mock_resp = mock.Mock()
        # set status code and content
        mock_resp.status_code = status
        mock_resp.text = text
        return mock_resp

    @mock.patch('src.web_scrap.requests.get')
    def test_processed_web_scrap_success(self, mock_get):
        # assembly
        loggerMock, mongoServiceMock, webScrapProcessorMock = getMockObjects()
        mock_resp = self._mock_response(text="TEST")
        mock_get.return_value = mock_resp

        article = ArticleInfo(UUID_1, "http://test.com")

        scheduler = CurrentThreadScheduler()


        # Actual
        webScrap(article, loggerMock, mongoServiceMock, scheduler).run()

        # Assert
        mongoServiceMock.insertWebScrapArticle.assert_called_once()
        loggerMock.error.assert_not_called()

    def test_web_scrap_success(self):
        # assembly
        loggerMock, mongoServiceMock, webScrapProcessorMock = getMockObjects()

        article = ArticleInfo(UUID_1, "http://test.com")

        scheduler = CurrentThreadScheduler()

        mongoServiceMock.getNonWebScrapArticleAsStream.return_value = rx.of(article)

        web_scraper = WebScrap(
            loggerMock,
            mongoServiceMock,
            scheduler,
            webScrapProcessorMock
        )

        # Actual
        web_scraper.buildWebScrapPipeline().subscribe(scheduler=scheduler)

        # Assert
        mongoServiceMock.getNonWebScrapArticleAsStream.assert_called_once()
        webScrapProcessorMock.submitArticle.assert_called_once()
        loggerMock.error.assert_not_called()

    def test_extractor_error_db_read_handled(self):
        # assembly
        loggerMock, mongoServiceMock, webScrapProcessorMock = getMockObjects()

        scheduler = CurrentThreadScheduler()

        mongoServiceMock.getNonWebScrapArticleAsStream.return_value = rx.throw(Exception("Test Exception"))

        web_scraper = WebScrap(
            loggerMock,
            mongoServiceMock,
            scheduler,
            webScrapProcessorMock
        )

        # Actual
        web_scraper.buildWebScrapPipeline().subscribe(scheduler=scheduler)

        # Assert
        mongoServiceMock.getNonWebScrapArticleAsStream.assert_called_once()
        loggerMock.error.assert_called()
    
    def test_get_raw_page(self):
        loggerMock, _, _ = getMockObjects()
        # Note : test dependent on scrapethissite.com working as a dummy website 
        test_url = "https://scrapethissite.com"
        result = get_raw_page(test_url, loggerMock)
        self.assertIn("Scrape This Site", result)
        loggerMock.error.assert_not_called()
    
    def test_get_raw_page_fail(self):
        loggerMock, _, _ = getMockObjects()
        # Note : test dependent on testtest2024.com NOT working as a dummy website 
        test_url = "https://testtest2024.com/"
        isExcept = False
        try:
            result = get_raw_page(test_url, loggerMock)
            loggerMock.error.assert_called_once()
        except:
            isExcept = True
        self.assertTrue(isExcept)    

    def test_remove_ads(self):
        test_page_content = """<!DOCTYPE html>
                                <html>
                                <body>
                                <div id="this-is-an-ad-test">
                                <h1>Remove this ad</h1>
                                </div>
                                <div id="keep-this-additional-test">
                                <h1>Additional test</h1>
                                </div>
                                </body>
                                </html>"""
        result = remove_ads(test_page_content)
        self.assertNotIn("Remove this ad", result)
        self.assertIn("Additional test", result)
    
    def test_html_escape(self):
        test_page_content = """<!DOCTYPE html>
                                <html>
                                <body>
                                <div id="this-is-an-ad-test">
                                <h1>Header</h1>
                                <p><a href="https://www.google.com/">Visit Google</a></p>
                                </div>
                                </body>
                                </html>"""
        result = html_escape(test_page_content)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_logIfFailed(self):
        loggerMock, _, _ = getMockObjects()
        rs = None
        url = "https://test.com" # url does not matter for this test
        result = logIfFailed(rs,  url, loggerMock)
        loggerMock.error.assert_called_once()

    def test_countAndLog(self):
        loggerMock, mongoMock, processorMock = getMockObjects()
        ws = WebScrap(loggerMock, mongoMock, None, processorMock)
        for i in range (LOG_FREQUENCY):
            ws.countAndLog()
        loggerMock.info.assert_called_once()
    
    def test_complete_log(self):
        loggerMock, mongoMock, processorMock = getMockObjects()
        ws = WebScrap(loggerMock, mongoMock, None, processorMock)
        ws.complete()
        loggerMock.info.assert_called_once()
        

if __name__ == '__main__':
    unittest.main()
