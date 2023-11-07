from importlib import import_module
import argparse
import requests
import json
import uuid
import logging as logger
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from prompt.template import PromptTemplate
from prompt.store import TemplateStore
import uvicorn
import boto3

app = FastAPI()
CONVERSATIONS = {}

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
                yield res["generated_text"]
    
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
        return json.loads(ret.text)["generated_text"]

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

class Conversation:
    def __init__(
        self, 
        roles, 
        prompt, 
        agent, 
        executor,
        script_extractor,
        language,
        model_family,
        model_name,
        model_metadata,
        conv_id: str=""
    ):
        self.id = conv_id if conv_id != "" and conv_id in CONVERSATIONS else uuid.uuid4().hex[:16]
        self.roles = roles
        self.system_prompt = prompt
        if conv_id == "":
            self.history = ""
            self.last_agent_message = ""
            CONVERSATIONS[self.id] = {}
            self.append_chat(prompt, 0)
        else:
            self.history = CONVERSATIONS[self.id]["history"]
            self.last_agent_message = CONVERSATIONS[self.id]["last_agent_message"]
        self.agent = agent
        self.executor = executor
        self.script_extractor = script_extractor
        self.language = language
        self.model_family = model_family
        self.model_name = model_name
        self.model_metadata = model_metadata
        
    def append_chat(self, text, role=0):
        self.history += "\n" + self.roles[role] + text
        CONVERSATIONS[self.id]["history"] = self.history
        
    def send_to_agent(self, stream):
        def form_response(text=None):
            CONVERSATIONS[self.id]["history"] = self.history
            CONVERSATIONS[self.id]["last_agent_message"] = self.last_agent_message
            script = self.script_extractor(
                self.last_agent_message,
                self.model_metadata,
                LANGUAGES[self.language]["tag_name"]
            )

            if script:
                ret["script"], ret["expected_output"] = script
            else:
                ret["script"], ret["expected_output"] = ("", "")
            ret["generated_text"] = self.last_agent_message
            if text:
                ret["text"] = text
            ret["conv_id"] = self.id
            return ret
            
        
        def iter_func(results):
            for result in results:
                self.history += result
                self.last_agent_message += result
                ret = form_response(result)
                yield json.dumps(ret) + "\n"
        
        self.append_chat("", 1)
        res = self.agent(
            self.history,
            self.model_family,
            self.model_name,
            self.model_metadata,
            stream
        )
        ret = {}
        if stream:
            self.last_agent_message = ""
            return iter_func(res)
        else:
            self.history += res
            self.last_agent_message = res
            ret = form_response()
            return ret
    
    def exec_script(self, script, expected_output):
        output_res = ""
        if LANGUAGES[self.language]["pre_exec_script"]:
            output_res += self.executor(
                LANGUAGES[self.language]["pre_exec_script"], 
                LANGUAGES[self.language]["kernel_name"]
            )["output"]
        res = self.executor(script, LANGUAGES[self.language]["kernel_name"])
        res["output"] = output_res + res["output"]
        if LANGUAGES[self.language]["post_exec_script"]:
            res["output"] += self.executor(
                LANGUAGES[self.language]["post_exec_script"], 
                LANGUAGES[self.language]["kernel_name"]
            )["output"]
        res["script"] = script
        res["expected_output"] = expected_output
        res["conv_id"] = self.id
        return res

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

@app.get("/list_languages")
def list_languages():
    LANGUAGES = get_languages()
    return json.dumps(LANGUAGES)

@app.post("/generate")
async def generate(request: Request):
    params = await request.json()
    prompt = params.get("prompt")
    model_family = params.get("model_family")
    model_name = params.get("model_name")
    language = params.get("language")
    if not (prompt and model_family and model_name and language):
        raise
    model_type, can_stream = get_model_type(model_family, model_name)
    if model_type == "":
        return {"error": "Unknown model"}
    conv_id = params.get("conv_id", "")
    stream = params.get("stream", False)
    if stream:
        stream = can_stream
    LANGUAGES = get_languages()
    params = {
        "display_name": LANGUAGES[language]["display_name"],
        "tag_name": LANGUAGES[language]["tag_name"],
        "error_message": "",
        "script_output": "",
        "language_instructions": LANGUAGES[language]["language_instructions"]
    }
    
    model_metadata = get_model_metadata(model_type)
    
    conv = Conversation(
        model_metadata["ROLES"], 
        prompt_store.get_prompt_from_template(
            model_metadata["SYSTEM_PROMPT_TMPLT"],
            params
        ),
        send_req_to_agent,
        send_script_to_exc,
        extract_script,
        language,
        model_family,
        model_name,
        model_metadata,
        conv_id
    )
    conv.append_chat(
        prompt_store.get_prompt_from_template(
            model_metadata["AGENT_REPLY_TMPLT"],
            params
        ),
        1
    )
    conv.append_chat(prompt)
    try:
        res = conv.send_to_agent(stream)
        if not res:
            raise
        if stream:
            return StreamingResponse(
                res, 
                media_type="application/x-ndjson"
            )
        else:
            return res
    except Exception as e:
        # Handle any exceptions that occur during execution
        return {"error": f"An error occurred: {str(e)}"}

@app.post("/execute")
async def execute(request: Request):
    
    def iter_func(exec_result, results=None):
        if results:
            for json_result in results:
                result = json.loads(json_result)
                result["error"] = exec_result["error"]
                result["output"] = exec_result["output"]
                yield json.dumps(result) + "\n"
        else:
            yield json.dumps(exec_result) + "\n"
            
    params = await request.json()
    script = params.get("script")
    expected_output = params.get("expected_output", "")
    model_family = params.get("model_family")
    model_name = params.get("model_name")
    language = params.get("language")
    conv_id = params.get("conv_id")
    if not (script and conv_id and model_family and model_name and language):
        raise
    stream = params.get("stream", False)
    LANGUAGES = get_languages()
    params = {
        "display_name": LANGUAGES[language]["display_name"],
        "tag_name": LANGUAGES[language]["tag_name"],
        "error_message": "",
        "script_output": "",
        "language_instructions": LANGUAGES[language]["language_instructions"]
    }
    
    model_metadata = get_model_metadata(model_type)
    conv = Conversation(
        model_metadata["ROLES"], 
        prompt_store.get_prompt_from_template(
            model_metadata["SYSTEM_PROMPT_TMPLT"],
            params
        ),
        send_req_to_agent,
        send_script_to_exc,
        extract_script,
        language,
        model_family,
        model_name,
        model_metadata,
        conv_id
    )
    try:
        res = conv.exec_script(script, expected_output)
        if res["error"]:
            params["error_message"] = res["output"]
            conv.append_chat(
                prompt_store.get_prompt_from_template(
                    model_metadata["SCRIPT_ERROR_TMPLT"],
                    params
                )
            )
            ret = conv.send_to_agent(stream)
            if stream:
                return StreamingResponse(
                    iter_func(res, ret),
                    media_type="application/x-ndjson"
                )
            else:
                ret["output"] = res["output"]
                ret["error"] = res["error"]
                return ret
        else:
            if stream:
                return StreamingResponse(
                    iter_func(res),
                    media_type="application/x-ndjson"
                )
            else:
                return res
    except Exception as e:
        # Handle any exceptions that occur during execution
        return {"error": f"An error occurred: {str(e)}"}

    
if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api-layer-host", type=str, default="localhost")
    parser.add_argument("--api-layer-port", type=int, default=8080)
    parser.add_argument("--code-executor-host", type=str, default="localhost")
    parser.add_argument("--code-executor-port", type=int, default=8080)
    parser.add_argument("--prompt-database-file", type=str, default="prompt/database.json")
    parser.add_argument("--prompt-store-name", type=str, default="")
    parser.add_argument("--models-metadata-db", type=str, default="")
    parser.add_argument("--models-metadata-file", type=str, default="config/model_meta.json")
    parser.add_argument("--languages-file", type=str, default="config/languages.json")
    parser.add_argument("--max-exec-iter", type=int, default=3)
    args = parser.parse_args()
    logger.info(f"args: {args}")
    max_iterations = args.max_exec_iter
    api_layer_url = f"http://{args.api_layer_host}:{args.api_layer_port}/invoke"
    code_executor_url = f"http://{args.code_executor_host}:{args.code_executor_port}/execute_code"
    models_metadata = {}
    models_metadata_db = ""
    LANGUAGES = {}
    prompt_store = TemplateStore(
        external_store=True if args.prompt_store_name != "" else False, 
        ddb_table_name=args.prompt_store_name
    )
    if args.prompt_store_name == "":
        prompt_store.read_from_json(args.prompt_database_file)
    if args.models_metadata_db == "":
        with open(args.models_metadata_file, "r") as json_f:
            models_metadata = json.load(json_f)
        with open(args.languages_file, "r") as json_f:
            LANGUAGES = json.load(json_f)
    else:
        models_metadata_db = args.models_metadata_db
        LANGUAGES = get_languages()
    
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info"
    )