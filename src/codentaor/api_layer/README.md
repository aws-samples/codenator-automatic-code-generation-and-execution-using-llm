# API Layer
---
API layer component unifies the way an LLM model is invoked to generate predictions. It is designed to run as a docker container that can access DynamoDB to retrieve model metadata. The aim is to enable users to add/remove models as they become available without the need to change any code or redeploy resources regardless of underlying service provider.

We achieve that by inluding handler code in the handlers folder where each handler can resemble a service. When adding new handlers, some code needs to be added and the components needs to be redeployed.

However, for new models, we would only need to add model metadata to DynamoDB and it should allow us to use new models.

## Starting the server
To start API Layer server, you can use the below command:
```
$ main.py [optional args]
```

`[optional args]` can be any combination of:<br>
`--host`: host url, default value `localhost`<br>
`--port`: host port, default value `8080`<br>
`--table-name`: DynamoDB table name, if non provided, the app will use metadata provided under [schema](app/handlers/schemas/) folder.<br>
`--workers`: number of uvicorn workers, default value `3`<br>
`--namespace`: namespace used to publish CloudWatc Metrics, default value `Codenator/api-layer/`<br>

## API endpoints

API Layer has the following API endpoints:
- `/ping` (GET): A standard health check endpoint.
- `/invoke` (POST): Invokes a model to generate a response. 
    - Required parameters:
        `model_family`: currently supports `bedrock` or `sagemaker`.<br>
        `model_name`: name of the model to invoke (see [DynamoDB section](README.md#DynamoDB-schema) for more information)<br>
        `body`: invocation body (see [DynamoDB section](README.md#DynamoDB-schema) for more information)<br>
- `/invoke_stream` (POST): Same as `/invoke` but with response streaming.


## DynamoDB schema
Below is a description of DynamoDB table schema:
- have partition key of type `String` and called `pk` and sort key of type `String` called `sk`.
- For each model, the partion key value should `models`
- For each SageMaker endpoint there should be one record in the following format:

| Attribute name | Value |
| -------------- | ----- |
| `pk` | `models` |
| `sk` | `model_family-model_name` |
| `schema` | `JSON configuration, explained below` |

- `shcema` field should contain details about the model request, response and respose with stream structure. The JSON configuration should have the below keys:
    - `request`: This is where you specify the request configuration that will be sent to your SageMaker Endpoint. It must have two sub attributes `defaults` where you provide a request example with all default values and `mapping` where you provide jsonpath mapping to each required value (see TGI example below)
    - `response`: This is where you specify the response configuration that will be recieved from your SageMaker Endpoint. I must have two sub attributes `regex_sub` where you provide a regix string used to substitute the response text to make sure it is in JSON format. The second response attribute is`mapping` where you provide jsonpath mapping to each required value (see examples below)
    - `response-with-stream`: Same as `response` but for streaming.
    
Below is a `schema` example for Bedrcok Claude models

```
{
    "request": {
        "defaults": {
            "prompt": "My name is Olivier and I",
            "max_tokens_to_sample": 4096,
            "stop_sequences": [],
            "temperature": 1.0,
            "top_p": 1.0,
            "top_k": 1
        },
        "mapping": {
            "prompt": "$.prompt",
            "max_new_tokens": "$.max_tokens_to_sample",
            "temperature": "$.temperature",
            "top_p": "$.top_p",
            "top_k": "$.top_k",
            "stop": "$.stop_sequences"
        }
    },
    "response": {
        "regex_sub": "",
        "mapping": {
            "generated_text": "$.completion",
            "finish_reason": "$.stop_reason"
        }
    },
    "response-with-stream": {
        "regex_sub": "",
        "mapping": {
            "generated_text": "$.completion",
            "finish_reason": "$.stop_reason"
        }
    }
}
```

Below is an example that is valid for SageMaker TGI deep learning containers

```
{
    "request": {
        "defaults": {
            "inputs": "My name is Olivier and I",
            "parameters": {
                "best_of": null,
                "decoder_input_details": false,
                "details": true,
                "do_sample": false,
                "max_new_tokens": 1024,
                "repetition_penalty": null,
                "return_full_text": false,
                "seed": null,
                "stop": [
                  "photographer"
                ],
                "temperature": null,
                "top_k": null,
                "top_p": null,
                "truncate": null,
                "typical_p": null,
                "watermark": false
            },
            "stream": false
        },
        "mapping": {
            "prompt": "$.inputs",
            "stream": "$.stream",
            "max_new_tokens": "$.parameters.max_new_tokens",
            "repetition_penalty": "$.parameters.repetition_penalty",
            "return_full_text": "$.parameters.return_full_text",
            "temperature": "$.parameters.temperature",
            "top_p": "$.parameters.top_p",
            "top_k": "$.parameters.top_k",
            "stop": "$.parameters.stop",
            "best_of": "$.parameters.best_of",
            "decoder_input_details": "$.parameters.decoder_input_details",
            "details": "$.parameters.details",
            "do_sample": "$.parameters.do_sample",
            "seed": "$.parameters.seed",
            "truncate": "$.parameters.truncate",
            "typical_p": "$.parameters.typical_p",
            "watermark": "$.parameters.watermark"
        }
    },
    "response": {
        "regex_sub": "",
        "mapping": {
            "text": "$.[0].token.text",
            "logprobs": "$.[0].token.logprob",
            "finish_reason": "$.[0].details.finish_reason",
            "generated_tokens": "$.[0].details.generated_tokens",
            "seed": "$.[0].details.seed",
            "generated_text": "$.[0].generated_text",
            "id": "$.[0].token.id",
            "special": "$.[0].token.special"
        }
    },
    "response-with-stream": {
        "regex_sub": "^data:",
        "mapping": {
            "text": "$.token.text",
            "logprobs": "$.token.logprob",
            "finish_reason": "$.details.finish_reason",
            "generated_tokens": "$.details.generated_tokens",
            "seed": "$.details.seed",
            "generated_text": "$.token.text",
            "id": "$.token.id",
            "special": "$.token.special"
        }
    }
}
```

- The table should have a special record that has a list of models properties of all active models in the below format:

| Attribute name | Value |
| -------------- | ----- |
| `pk` | `models` |
| `sk` | `all-models` |
| `models` | `[<model_1>,<model_2>,<model_3>,...<model_n>]` |

model properties should have the following format:
```
 {
    "model_type": <type of model>,
    "model_name": <name of model>,
    "model_family": <model family>,
    "streaming": true or false
}
```

example:
```
[
    {
        "model_type": "Claude",
        "model_name": "anthropic.claude-instant-v1",
        "model_family": "bedrock",
        "streaming": true
    },    
    {
        "model_type": "Claude",
        "model_name": "anthropic.claude-v2:1",
        "model_family": "bedrock",
        "streaming": true
    },
    {
        "model_type": "Cohere",
        "model_name": "cohere.command-light-text-v14",
        "model_family": "bedrock",
        "streaming": true
    },
    {
        "model_type": "Llama2",
        "model_name": "llama2js.jumpstart-dft-meta-textgeneration-llama-2-13b",
        "model_family": "sagemaker",
        "streaming": false
    }
]
```

