from importlib import import_module
from prompt.store import TemplateStore
import requests
import logging as logger
import json
import boto3
import base64
import time
import os

class EncryptorClass:
    def __init__(self, key_id):
        self.kms_client = boto3.client("kms")
        self.key_id = key_id
    def encrypt(self, text):
        ret = self.kms_client.encrypt(
            KeyId=self.key_id,
            Plaintext=text
        )
        return base64.b64encode(ret["CiphertextBlob"]).decode()
    def decrypt(self, cipher_text_blob):
        ret = self.kms_client.decrypt(
            KeyId=self.key_id,
            CiphertextBlob=base64.b64decode(cipher_text_blob)
        )
        return ret["Plaintext"].decode()

def publish_metrics(latency) -> None:
    cw_client = boto3.client("cloudwatch")
    namespace = os.getenv("CW_NAMESPACE", "Codenator/controller/")
    logger.debug(f"Publishing CW metrics (Namespace: {namespace})")
    cw_client.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                'MetricName': "invocations",
                'Value': 1,
                'Unit': 'Count'
            },
            {
                'MetricName': "latency",
                'Value': latency,
                'Unit': 'Count'
            }
        ]
    )

def get_models_list():
    ret = requests.get(url=os.getenv("APP_API_LAYER_URL").split("/invoke")[0] + "/list_models")
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
    models_metadata_db = os.getenv("APP_MODELS_METADATA_DB")
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
        with open(os.getenv("APP_MODELS_METADATA_FILE"), "r") as json_f:
            models_metadata = json.load(json_f)
        return models_metadata[model_type]

def get_languages():
    models_metadata_db = os.getenv("APP_MODELS_METADATA_DB")
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
        with open(os.getenv("APPP_LANGUAGES_FILE"), "r") as json_f:
            LANGUAGES = json.load(json_f)
        return LANGUAGES

def send_req_to_agent(body, model_family, model_name, model_metadata):
    def iter_func(result, model_metadata):
        start = time.perf_counter()
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
                elif model_metadata["ROLES"][1] in res["generated_text"]:
                    result = res["generated_text"].split(model_metadata["ROLES"][1])[0]
                    if result == "":
                        break
                    else:
                        yield result
                        break
                elif res["generated_text"] != "":
                    yield res["generated_text"]
            elif "error"  in res:
                raise Exception(f'Error {res["error"]}\StackTrace: {res.get("stacktrace","")}')
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
    
    data = {
        "body": body, 
        "model_family": model_family, 
        "model_name": model_name
    }
    ret = requests.post(
        url=os.getenv("APP_API_LAYER_URL") + ("" if not body["stream"] else "_stream"), 
        data=json.dumps(data),
        stream=body["stream"]
    )
    if body["stream"]:
        return iter_func(ret, model_metadata)
    else:
        resp = ret.json()
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
        url=os.getenv("APP_CODE_SCANNER_URL"), 
        data=json.dumps(data)
    )
    return ret.json()

def send_script_to_exc(script, kernel_name, timeout=10):
    kms = os.getenv("APP_KMS_KEY")
    cypher = EncryptorClass(kms)
    script_blob = cypher.encrypt(script)
    data = {
        "code": script_blob, 
        "kernel_name": kernel_name,
        "timeout": timeout
    }
    ret = requests.post(
        url=os.getenv("APP_CODE_EXECUTOR_URL"), 
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

def get_prompt_store():
    prompt_store_db = os.getenv("APP_PROMPT_STORE", "")
    prompt_store = TemplateStore()
    if prompt_store_db == "":
        prompt_store.read_from_json(os.getenv("APP_PROMPT_STORE_FILE"))
    return prompt_store