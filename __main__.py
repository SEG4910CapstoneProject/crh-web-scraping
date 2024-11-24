import logging
import multiprocessing
from reactivex.scheduler import ThreadPoolScheduler

from src.config import *
from src.mongo_service import MongoService
from src.web_scrap import WebScrap
from src.web_scrap_processor import WebScrapProcessor


def main():
    #Setup logger
    logging.basicConfig(level=logging.INFO, format=LOGGER_FORMAT)
    logging.info('Starting web scrapping')

    # Create scheduler
    processesToMake = multiprocessing.cpu_count()
    threadsToMake = THREADS_PER_CORE * multiprocessing.cpu_count()
    logging.info('Starting Main Threadpool with %s threads', str(threadsToMake))
    logging.info('Starting Processpool with %s processes each with %s threads', str(processesToMake),
                 str(THREADS_PER_CORE))
    scheduler = ThreadPoolScheduler(threadsToMake)
    processScheduler = WebScrapProcessor(processesToMake)

    # Instantiate Database services
    try:
        mongoService = MongoService(logging.getLogger('MongoService'), scheduler)
    except Exception as e:
        logging.error('Failed to Initialize Databases', exc_info=e)
        return

    webScrap = WebScrap(logging.getLogger('WebScrap'), mongoService, scheduler, processScheduler)

    logging.info('Startup Completed')
    # Start Web Scraper 
    webScrap.run()

    logging.info('Shutting down web scraper')

    # Cleanup
    processScheduler.dispose()

    logging.info('Done')


if __name__ == "__main__":
    main()