import os

# Db Variables
MONGO_PORT = os.getenv('MONGO_PORT', "27017")
MONGO_HOST = os.getenv('MONGO_HOST', "localhost")
MONGO_USERNAME = os.getenv('MONGO_USERNAME')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', "articleContent")
DB_MAX_RETRIES = int(os.getenv('DB_MAX_RETRIES', "3"))

# Threading Variables
THREADS_PER_CORE = int(os.getenv('THREADS_PER_CORE', "3"))

# Retry mechanism
PROGRAM_TIMEOUT = float(os.getenv('PROGRAM_TIMEOUT', "10800"))

# Logging
LOG_FREQUENCY = int(os.getenv('LOG_FREQUENCY', "25"))
WEB_SCRAP_RETRIES = int(os.getenv('WEB_SCRAP_RETRIES', "3"))
LOGGER_FORMAT = "%(asctime)s %(levelname)s P%(process)d [%(name)s]: %(message)s"

# Request 
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', "60"))
