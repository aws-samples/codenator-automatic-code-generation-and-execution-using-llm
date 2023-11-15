from importlib import import_module
import requests
import json
import boto3


LANGUAGES = {}
api_layer_url = ""
code_executor_url = ""
code_scanner_url = ""
model_metadata = {}
models_metadata_db  = ""

def get_models_list():
    ret = requests.get(url=api_layer_url.split("/invoke")[0] + "/list_models")
    return json.loads(ret.text)["models"]

def get_model_type(model_family, model_name):
    models = get_models_list()
    model_type = ""
    can_stream = False
    for model in models:
        if model["model_family"] == model_family and model["model_name"] == model_name:
            model_type = model["model_type"]
            can_stream = model["streaming"]
    return model_type, can_stream

def get_model_metadata(model_type):
    if models_metadata_db != "":
        ddb_client = boto3.client("dynamodb")
        ret = ddb_client.get_item(
            TableName=models_metadata_db,
            Key={
                "pk": {
                    "S": "model_types"
                },
                "sk": {
                    "S": model_type
                }
            }
        )["Item"]["metadata"]["S"]
        return json.loads(ret)
    else:
        return models_metadata[model_type]

def get_languages():
    if models_metadata_db != "":
        ddb_client = boto3.client("dynamodb")
        ret = ddb_client.get_item(
            TableName=models_metadata_db,
            Key={
                "pk": {
                    "S": "languages"
                },
                "sk": {
                    "S": "languages"
                }
            }
        )["Item"]["data"]["S"]
        return json.loads(ret)
    else:
        return LANGUAGES

def send_req_to_agent(text, model_family, model_name, model_metadata, stream=False):
    def iter_func(result, model_metadata):
        for chunk in result.iter_lines():
            res = json.loads(chunk)
            if "generated_text"  in res and res["generated_text"] != model_metadata["EOS"]:
                if model_metadata["ROLES"][0] in res["generated_text"]:
                    result = res["generated_text"].split(model_metadata["ROLES"][0])[0]
                    if result == "":
                        break
                    else:
                        yield result
                        break
                elif res["generated_text"] != "":
                    yield res["generated_text"]
            elif "error"  in res:
                raise Exception(f'Error {res["error"]}\StackTrace: {res.get("stacktrace","")}')
    
    data = {
        "body": {
            "prompt": text,
            "stream": stream
        }, 
        "model_family": model_family, 
        "model_name": model_name
    }
    ret = requests.post(
        url=api_layer_url + ("" if not stream else "_stream"), 
        data=json.dumps(data),
        stream=stream
    )
    if stream:
        return iter_func(ret, model_metadata)
    else:
        resp = json.loads(ret.text)
        if "generated_text" in resp:
            return resp["generated_text"]
        else:
            raise Exception(f'Error {resp["error"]}\StackTrace: {resp.get("stacktrace","")}')

def security_scan_script(script, language, scanner="semgrep"):
    data = {
        "script": script, 
        "language": language, 
        "scanner": scanner
    }
    ret = requests.post(
        url=code_scanner_url, 
        data=json.dumps(data)
    )
    return json.loads(ret.text)

def send_script_to_exc(script, kernel_name):
    data = {
        "code": script, 
        "kernel_name": kernel_name
    }
    ret = requests.post(
        url=code_executor_url, 
        data=json.dumps(data)
    )
    return json.loads(ret.text)

def extract_script(text, model_metadata, tag_name):
    try:
        if model_metadata["CODE_BLOCK_SYMS"][0].format(
            **{
                "language": tag_name
            }
        ) in text:
            script = text.split(
                model_metadata["CODE_BLOCK_SYMS"][0].format(
                    **{
                        "language": tag_name
                    }
                )
            )[1].split(
                "\n" + model_metadata["CODE_BLOCK_SYMS"][1].format(
                    **{
                        "language": tag_name
                    }
                )
            )[0].lstrip("\n")
            expected_output = ""
            if model_metadata["OUTPUT_TAGS"][0] in text and model_metadata["OUTPUT_TAGS"][1] in text:
                expected_output = text.split(
                    model_metadata["OUTPUT_TAGS"][0]
                )[1].split(
                    "\n" + model_metadata["OUTPUT_TAGS"][1]
                )[0].lstrip("\n")
            return (script, expected_output)
    except:
        return None
    return None