from logging import Logger
from uuid import UUID
import uuid
import reactivex as rx
from reactivex import operators as ops
from pymongo import MongoClient
from bson.binary import Binary
from src.config import *


class MongoService:
    """
    Service that handles all mongo db operations
    """

    def __init__(self, logger, scheduler):
        self.logger = logger
        self.scheduler = scheduler
        self.client = MongoClient("mongodb://{}:{}/".format(MONGO_HOST, MONGO_PORT), 
                                  username=MONGO_USERNAME, 
                                  password=MONGO_PASSWORD,
                                  uuidRepresentation='standard')
        self.collection = self.client[MONGO_DB_NAME][MONGO_COLLECTION]
    
    def insertWebScrapArticle(self, id, web_scrap):
        """
        Insert article web scrap into db
        """
        self.collection.update_one({"_id": id}, {"$set": {"web_scrap": web_scrap}}) # dump web scraped article into db
        self.logger.debug('Added web scrap to database')
    
    def getNonWebScrapArticles(self):
        """
        Gets article info for articles that has not been web scraped 
        :return: list of article info that requires web scraping 
        """
        query = {
                "$or": [
                    {"web_scrap": {"$exists": False}},  # New articles to be fully scraped
                    {"clean_full_text": {"$exists": False, "$ne": ""}}  # Articles that lack clean text
                ]}
        result = self.collection.find(query)

        # create array of Article Info 
        articles = []
        for r in result:
            articles.append(ArticleInfo(r["_id"], r["link"]))
        return articles

    def getNonWebScrapArticleAsStream(self):
        """
        Gets article info for articles that has not been web scrap as a stream
        :return: Observable that emits all article info that requires web scraping
        """
        # Start stream with value so when database calls are called, errors are transmitted into stream
        return rx.of(0).pipe(
            ops.do_action(on_next=lambda v: self.logger.info("Reading Articles to web scrap")),
            # Extract id
            ops.map(lambda b: self.getNonWebScrapArticles()),
            # Retry
            ops.do_action(on_error=lambda err: self.logger.error("Failed to read from db", exc_info=err)),
            ops.retry(DB_MAX_RETRIES),
            ops.do_action(on_error=lambda err: self.logger.error("Retries Exhausted", exc_info=err)),
            ops.catch(rx.empty()),
            # Split array into individual elements
            ops.do_action(on_next=lambda articleInfoList: self.logger.info("Found %s articles to process", str(len(articleInfoList)))),
            ops.flat_map(lambda articleInfoList: rx.from_iterable(articleInfoList)),
            # Scheduler setup
            ops.subscribe_on(self.scheduler)
        )
        

    def insertCleanFullText(self, article_id: str, clean_text: str):
        """Insert the cleaned text into Mongo"""
        if not clean_text:
            return
        try:
            if isinstance(article_id, uuid.UUID):
                db_id = Binary(article_id.bytes, subtype=4)
            else:
                db_id = Binary(uuid.UUID(article_id).bytes, subtype=4)

            self.collection.update_one(
                {"_id": db_id},
                {"$set": {"clean_full_text": clean_text}},
                upsert=True
            )
        except Exception as e:
            self.logger.error("Failed to insert clean full text", exc_info=e)


    def get_articles_without_summary(self, limit=10):
        """
        Returns articles where the 'summary' field is missing or null.
        """
        return list(self.db.articleContent.find(
            {"summary": {"$exists": False}},
            {"clean_full_text": 1, "link": 1}
        ).limit(limit))


    def update_article_summary(self, article_id, summary):
        """
        Updates an article with its generated summary.
        """
        self.db.articleContent.update_one(
            {"_id": article_id},
            {"$set": {"summary": summary}}
        )
class ArticleInfo:
    """
    Object containing Article URL and id
    """
    def __init__(self, articleId: UUID, articleUrl: str):
        self.articleId = articleId
        self.articleUrl = articleUrl

    def __eq__(self, other):
        return (isinstance(other, ArticleInfo)
                and self.articleId == other.articleId
                and self.articleUrl == other.articleUrl)