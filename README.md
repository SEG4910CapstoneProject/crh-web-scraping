# Web Scraping 

Python script to retrieve article information via url link using web scraping. 

## Required Environment variables

### Database
| Environment Variable | Description                                                                              |
|----------------------|------------------------------------------------------------------------------------------|
| MONGO_USERNAME       | Mongodb username for access. Should contain write permissions                            |
| MONGO_PASSWORD       | Mongodb password for authentication                                                      |
| MONGO_DB_NAME        | The name of the db for the mongodb database                                              |
| MONGO_COLLECTION     | The name of the collection used in the mongodb database (default value = articleContent) |
| MONGO_HOST           | The hostname of the mongodb databas (default value = localhost)                          |
| MONGO_PORT           | The port of the mongodb database (default value = 27017)                                 |
| DB_MAX_RETRIES       | The maximum allowable retries when db commands fail (default value = 3)                  |

### Other 
| Environment Variable | Description                                                                                                                                                           |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| THREADS_PER_CORE     | The number of threads to create per core. This number should be greater than 1 due to the large number of blocking Database read and write calls. (default value = 3) |
| PROGRAM_TIMEOUT      | If the execution of this service exceeds this time in seconds. It will automatically force shutdown. (default value = 10800 seconds / 3 hours)                        |
| LOG_FREQUENCY        | The frequency the program will report completed article extraction. For example if 10, then every 10th completion will log to console. (default value = 25)           |
| WEB_SCRAP_RETRIES    | The maximum allowable retries when web scraping commands fail (default value = 3)                                                                                     |
| REQUEST_TIMEOUT      | The maximum time in seconds for requests to waiting for a response (default value = 60)                                                                                     |