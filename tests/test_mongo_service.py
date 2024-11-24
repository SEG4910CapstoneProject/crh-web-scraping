import unittest
from logging import Logger
from unittest.mock import *
from uuid import UUID
from pymongo import MongoClient
from pymongo.collection import Collection

from reactivex.scheduler import CurrentThreadScheduler
import reactivex.operators as ops

from src.mongo_service import MongoService, ArticleInfo

UUID_1 = UUID("5d8a48c7-8799-49ba-8a61-b96c6f0d08e8")
UUID_2 = UUID("2c398d08-22e0-4f69-955b-69fb39666a9c")
UUID_3 = UUID("8c819db1-3dfa-4343-b6e7-9b73495fcdec")

def getMockObjects():
    loggerMock = Mock(spec_set=Logger)
    collectionMock = Mock(spec_set=Collection)
    documentMock = MagicMock()

    return loggerMock, collectionMock, documentMock

def getPatches(config):
    mongoPatch = patch("src.mongo_service.MongoClient", spec=MongoClient, **config)

    return mongoPatch

class MongoServiceTests(unittest.TestCase):
    def test_getNonWebScrapArticleAsStream_success(self):
        loggerMock, collectionMock, documentMock = getMockObjects()
        scheduler = CurrentThreadScheduler()

        documentMock1 = documentMock
        documentMock2 = documentMock
        documentMock3 = documentMock

        expectedArticle1 = ArticleInfo(UUID_1, "link 1")
        expectedArticle2 = ArticleInfo(UUID_2, "link 2")
        expectedArticle3 = ArticleInfo(UUID_3, "link 3")

        documentMock1 = {"_id": expectedArticle1.articleId, "link" : expectedArticle1.articleUrl}
        documentMock2 = {"_id": expectedArticle2.articleId, "link" : expectedArticle2.articleUrl}
        documentMock3 = {"_id": expectedArticle3.articleId, "link" : expectedArticle3.articleUrl}

        collectionMock.find.return_value = [documentMock1, documentMock2, documentMock3]

        mongoPatch = getPatches({"__getitem__.return_value.__getitem__.return_value": collectionMock})

        mongoMock = mongoPatch.start()
        mongoService = MongoService(loggerMock, scheduler)

        # Actual
        actual = mongoService.getNonWebScrapArticleAsStream().pipe(
            ops.to_list()
        ).run()

        # Assert
        self.assertIn(expectedArticle1, actual)
        self.assertIn(expectedArticle2, actual)
        self.assertIn(expectedArticle3, actual)
        loggerMock.error.assert_not_called()
        collectionMock.find.assert_called_once()

        mongoPatch.stop()

    def test_getNonWebScrapArticleAsStream_error_retry_success(self):
        loggerMock, collectionMock, documentMock = getMockObjects()
        scheduler = CurrentThreadScheduler()

        expectedArticle1 = ArticleInfo(UUID_1, "link 1")

        documentMock = {"_id": expectedArticle1.articleId, "link" : expectedArticle1.articleUrl}

        collectionMock.find.side_effect = [Exception("Test Exception"), [documentMock]]

        mongoPatch = getPatches({"__getitem__.return_value.__getitem__.return_value": collectionMock})

        mongoMock = mongoPatch.start()
        mongoService = MongoService(loggerMock, scheduler)

        # Actual
        actual = mongoService.getNonWebScrapArticleAsStream().pipe(
            ops.to_list()
        ).run()

        # Assert
        self.assertIn(expectedArticle1, actual)
        loggerMock.error.assert_called()
        self.assertEqual(2, collectionMock.find.call_count)

        mongoPatch.stop()

    def test_getNonWebScrapArticleAsStream_error_retry_fail_complete(self):
        loggerMock, collectionMock, documentMock = getMockObjects()
        scheduler = CurrentThreadScheduler()

        mongoPatch = getPatches({"__getitem__.return_value.__getitem__.return_value": collectionMock})

        collectionMock.find.side_effect = Exception("Test Exception")

        mongoMock = mongoPatch.start()
        mongoService = MongoService(loggerMock, scheduler)

        # Actual
        actual = mongoService.getNonWebScrapArticleAsStream().pipe(
            ops.to_list()
        ).run()

        # Assert
        self.assertEqual(0, len(actual))
        loggerMock.error.assert_called()
        self.assertEqual(3, collectionMock.find.call_count)
        documentMock.__getitem__.assert_not_called()

        mongoPatch.stop()
    
    def test_insertWebScrapArticle_success(self):
        loggerMock, collectionMock, documentMock = getMockObjects()
        scheduler = CurrentThreadScheduler()

        documentMock1 = documentMock

        expectedArticle1 = ArticleInfo(UUID_1, "link 1")

        web_scrap = "Article Content Example"

        documentMock1 = {"_id": expectedArticle1.articleId, "link" : expectedArticle1.articleUrl}

        collectionMock.find.return_value = [documentMock1]

        mongoPatch = getPatches({"__getitem__.return_value.__getitem__.return_value": collectionMock})

        mongoMock = mongoPatch.start()
        mongoService = MongoService(loggerMock, scheduler)

        # Actual
        actual = mongoService.insertWebScrapArticle(expectedArticle1.articleId, web_scrap),

        # Assert
        loggerMock.debug.assert_called_once()
        collectionMock.update_one.assert_called_once()

        mongoPatch.stop()


if __name__ == '__main__':
    unittest.main()