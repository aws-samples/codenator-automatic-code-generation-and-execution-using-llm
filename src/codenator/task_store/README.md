# Task Store
Task store can store generated tasks in *Amazon Opensearch Serverless` and retrieve them using an embedding a vecor and vector search


## IAM permissions for *Amazon Opensearch Serverless*
Using *Amazon Opensearch Serverless* to to store and load tasks requires the following IAM permissions 

```
aoss:ReadDocument
aoss:WriteDocument
```

## Starting the server
To start *Task Store* server, you can use the below command:
```
$ main.py [optional args]
```

`[optional args]` can be any combination of:<br>
`--host`: host url, default value `localhost`<br>
`--port`: host port, default value `8080`<br>
`--workers`: number of uvicorn workers, default value `3`<br>
`--namespace`: namespace used to publish CloudWatc Metrics, default value `Codenator/task-store/`<br>
`--aoss-endpoint`: *Amazon Opensearch Serverless* endpoint url.<br>
`--aoss-index`: *Amazon Opensearch Serverless* index name.

## API endpoints

*Task Store* has the following API endpoints:
- `/ping` (GET): A standard health check endpoint.
- `/aoss/list_tasks` (GET): Lists all availble tasks.
- `/save_task` (POST): Save a task to * Amazon Opensearch Serverless*.
    - Required parameters:<br>
    `embedding`: Vector embedding.<br>
    `task_dec`: description of the task being saved.<br>
    `script`: script being saved.<br>
    `language`: programing language of the script.<br>
    - Optional parameters:<br>
    `store_type`: defaults to `aoss`. Currently it only supports `aoss`.
- `/load_task` (POST): Save a task to * Amazon Opensearch Serverless*.
    - Required parameters:<br>
    `embedding`: Vector embedding used for searching.<br>
    - Optional parameters:<br>
    `store_type`: defaults to `aoss`. Currently it only supports `aoss`.<br>
    `similarity`: defaults to `Cosine`. Allowed values `Cosine` and `Euclidean`.<br>
    `threshold`: similarity threshold, defaulst to `0.1`.<br>
    `limit`: number of search results to return, defaults to `1`
