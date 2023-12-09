# Controller
This component is responsible for orchastrating the main logic for ***Codenator***. It has five main actions:
- Generate: This action Takes a prompt and generates text and script in context of a conversation.
- Scan: Takes a script and send it to *Code Scanner*, if recommendations found to fix vulnrabilities, it sends back the recomendations to the LLM model to generate new text and script.
- Execute: Takes a script, encrypt it and send to *Code Executor*, if zthe execution fails, it sends back failure message to LLM model to generate new text and script.
- Save: Uses LLM to generate task description embedding then send it with script to *Task Store* to save it.
- Load: Uses LLM to generate input text embedding and send it to *Task Store* to search for similar stored tasks.

## IAM permissions
*Controller* component requires the following IAM permissions 

```
dynamodb:GetItem
kms:encrypt
```

## Starting the server
To start *Controller* server, you can use the below command:
```
$ main.py [optional args]
```

`[optional args]` can be any combination of:<br>
`--host`: host url, default value `localhost`<br>
`--port`: host port, default value `8080`<br>
`--api-layer-host`: *API Layer* host url, default value `localhost`<br>
`--api-layer-port`: *API Layer* host port, default value `8080`<br>
`--code-scanner-host`: *Code Scanner* host url, default value `localhost`<br>
`--code-scanner-port`: *Code Scanner* host port, default value `8080`<br>
`--code-executor-host`: *Code Executor* host url, default value `localhost`<br>
`--code-executor-port`: *Code Executor* host port, default value `8080`<br>
`--task-store-host`: *Task Store* host url, default value `localhost`<br>
`--task-store-port`: *Task Store* host port, default value `8080`<br>
`--workers`: number of uvicorn workers, default value `3`<br>
`--namespace`: namespace used to publish CloudWatc Metrics, default value `Codenator/controller/`<br>
`--kms`: *Amazon KMS* key id or alias used to encrypt script sent to *Code Executor*.<br>
`--prompt-database-file`: Loads *Prompt Store* from file if no *DynamoDB* table name was provided in `--prompt-store-name` option.<br>
`--prompt-store-name`: *DynamoDB* table name used for *Prompt Store*.<br>
`--models-metadata-db`: *DynamoDB* table name used to load languages and models metadata.<br>
`--models-metadata-file`: Loads models metadata from file if no *DynamoDB* table name was provided in `--models-metadata-db` option.<br>
`--languages-file`: Loads languages metadata from file if no *DynamoDB* table name was provided in `--models-metadata-db` option.<br>
`--conv-bucket`: *Amazon S3* bucket name used for conversation memory and logging.<br>
`--conv-prefix`: *Amazon S3* prefix name used for conversation memory and logging.<br>

## API endpoints

*Task Store* has the following API endpoints:
- `/ping` (GET): A standard health check endpoint.
- `/list_languages` (GET): Lists all supported programming languages.
- `/generate` (POST): for Generate action
    - Required parameters:<br>
    `prompt`: Text prompt.<br>
    `model_family`: currently supports `bedrock` or `sagemaker`.<br>
    `model_name`: name of the model to invoke (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information)<br>
    `language`: programing language to use.<br>
    - Optional parameters:<br>
    `model_params`: parameters used for model, (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information).<br>
    `conv_id`: conversation id, if empty a new conversation is started.<br>
    `stream`: a `boolean` value used to stream response.
- `/scan` (POST): for Scan action
    - Required parameters:<br>
    `script`: Script to scan.<br>
    `model_family`: currently supports `bedrock` or `sagemaker`.<br>
    `model_name`: name of the model to invoke (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information)<br>
    `language`: programing language to use.<br>
    `conv_id`: conversation id.<br>
    - Optional parameters:<br>
    `model_params`: parameters used for model, (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information).<br>
    `scanner`: defaults to `semgrep`. valid values `codeguru` or `semgrep`.<br>
    `stream`: a `boolean` value used to stream response.
- `/execute` (POST): for Execute action
    - Required parameters:<br>
    `script`: Script to execute.<br>
    `model_family`: currently supports `bedrock` or `sagemaker`.<br>
    `model_name`: name of the model to invoke (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information)<br>
    `language`: programing language to use.<br>
    `conv_id`: conversation id.<br>
    - Optional parameters:<br>
    `model_params`: parameters used for model, (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information).<br>
    `stream`: a `boolean` value used to stream response.
- `/save` (POST): for Save action
    - Required parameters:<br>
    `script`: Script to save.<br>
    `model_family`: currently supports `bedrock` or `sagemaker`.<br>
    `model_name`: name of the model to invoke (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information)<br>
    `language`: programing language to use.<br>
    `embedding_model_family`: same as `model_family` but for embedding.<br>
    `embedding_model_name`: same as `model_name` but for embedding.<br>
    - Optional parameters:<br>
    `model_params`: parameters used for model, (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information).<br>
    `embedding_model_params`: same as `model_params` but for embedding.<br>
- `/load` (POST): for Load action
    - Required parameters:<br>
    `prompt`: text prompt used to load a task.<br>
    `model_family`: currently supports `bedrock` or `sagemaker`.<br>
    `model_name`: name of the model to invoke (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information)<br>
    `language`: programing language to use.<br>
    `embedding_model_family`: same as `model_family` but for embedding.<br>
    `embedding_model_name`: same as `model_name` but for embedding.<br>
    - Optional parameters:<br>
    `model_params`: parameters used for model, (see [DynamoDB section](../api_layer/README.md#DynamoDB-schema) for more information).<br>
    `embedding_model_params`: same as `model_params` but for embedding.<br>
    `threshold`: similarity threshold, defaulst to `0.1`.<br>
    `limit`: number of search results to return, defaults to `1`
