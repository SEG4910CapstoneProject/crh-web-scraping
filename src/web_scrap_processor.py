import logging

from reactivex import operators as ops, Subject
import reactivex as rx
from multiprocess.synchronize import Lock
from multiprocess import Process, Queue, Manager
import dill
from reactivex.scheduler import ThreadPoolScheduler
from threading import Semaphore as ThreadedSemaphore

from src.config import THREADS_PER_CORE, LOGGER_FORMAT
from src.exceptions import DisposedException
from src.mongo_service import ArticleInfo, MongoService
from src.web_scrap import webScrap


class WebScrapProcessor:
    def __init__(self, max_workers=1):
        dill.settings['recurse'] = True
        self.max_workers = max_workers
        self._processes = []
        self._manager = Manager()
        self._taskQueue = self._manager.Queue()
        self._disposedValue = self._manager.Value(bool, False)

        startLocks = []
        for pid in range(max_workers):
            startLock: Lock = self._manager.Lock()
            startLock.acquire()
            p = Process(target=self._processRun, args=[self._taskQueue, startLock, self._disposedValue])
            p.daemon = True
            self._processes.append(p)
            startLocks.append(startLock)
            p.start()

        # Wait for all processes to start
        for lock in startLocks:
            lock.acquire()

    def dispose(self):
        """
        Releases resources for processes
        """
        self._disposedValue.value = True
        # unblock all processes
        for i in range(self.max_workers):
            self._taskQueue.put(i)

        self._taskQueue._close()
        for p in self._processes:
            # Wait 10 seconds max for shutdown
            p.join(10)

    def submitArticle(self, articleInfo: ArticleInfo):
        if self._disposedValue.value:
            raise DisposedException()

        completeLock: Lock = self._manager.Lock()
        # Lock is initially unlocked, lock it before submitting
        completeLock.acquire()
        self._taskQueue.put([articleInfo, completeLock])
        # Wait for completion
        completeLock.acquire()

    def _processRun(self, queue, startLock, disposedValue):
        try:
            scheduler = ThreadPoolScheduler(THREADS_PER_CORE)
            logging.basicConfig(level=logging.INFO, format=LOGGER_FORMAT)
            logger = logging.getLogger('Web Scrap Processor')

            # Instantiate Database services
            try:
                mongoService = MongoService(logging.getLogger('MongoService'), scheduler)
            except Exception as e:
                logging.error('Failed to Initialize Databases', exc_info=e)
                return

            sourceSubject = Subject()
            maxAllowedData = ThreadedSemaphore(THREADS_PER_CORE)

            logger.info("Web Scrap Processor started")
            startLock.release()

            try:
                _runWebscrap(sourceSubject, logger, mongoService, scheduler, maxAllowedData)
            except Exception:
                pass

            while not disposedValue.value:
                try:
                    maxAllowedData.acquire()
                    request = queue.get(block=True)
                except Exception:
                    # Queue has closed
                    break

                if disposedValue.value:
                    break
                sourceSubject.on_next(request)

            # Shutdown
            sourceSubject.on_completed()
            sourceSubject.dispose()

        except Exception as err:
            logging.error('Something went wrong', exc_info=err)


def _runWebscrap(source, logger, mongoService, scheduler, maxAllowedData):
    source.pipe(
        ops.flat_map(lambda request: _callScrapFromTest(request, logger, mongoService, scheduler, maxAllowedData)),
        ops.do_action(on_error=lambda err: logger.error("Error occurred.", exc_info=err)),
        ops.catch(rx.empty()),
        # Ensures something is always returned
        ops.to_list()
    ).subscribe(scheduler=scheduler, on_completed=logger.info("Completed Processing"))


def _callScrapFromTest(request, logger, mongoService, scheduler, maxAllowedData):
    return rx.of(request).pipe(
        ops.flat_map(lambda rd: webScrap(request[0], logger, mongoService, scheduler)),
        # Release the lock for this object as scraping is complete
        ops.do_action(on_next=lambda rd: request[1].release()),
        ops.do_action(on_next=lambda rd: maxAllowedData.release())
    )

