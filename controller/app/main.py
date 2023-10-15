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

app = FastAPI()
code_block_symbol = "```"
output_tags = ["<output>", "</output>"]
ROLES = ["Human", "Assistant"]
CONVERSATIONS = {}

def send_req_to_agent(text, model_family, model_name, stream=False):
    def iter_func(result):
        for chunk in result.iter_lines():
            yield json.loads(chunk)["generated_text"]
    
    data = {
        "body": {
            "prompt": text
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
        return iter_func(ret)
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

def extract_script(text, tag_name):
    try:
        if code_block_symbol + tag_name in text:
            script = text.split(code_block_symbol + tag_name + "\n")[1].split( "\n" + code_block_symbol)[0]
            expected_output = ""
            if output_tags[0] in text and output_tags[1] in text:
                expected_output = text.split(output_tags[0] + "\n")[1].split("\n" + output_tags[1])[0]
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
        
    def append_chat(self, text, role=0):
        self.history += "\n" + self.roles[role] + ":" + text
        CONVERSATIONS[self.id]["history"] = self.history
        
    def send_to_agent(self, stream):
        def form_response(text=None):
            CONVERSATIONS[self.id]["history"] = self.history
            CONVERSATIONS[self.id]["last_agent_message"] = self.last_agent_message
            script = self.script_extractor(
                self.last_agent_message,
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
    conv_id = params.get("conv_id", "")
    stream = params.get("stream", False)
    
    params = {
        "display_name": LANGUAGES[language]["display_name"],
        "tag_name": LANGUAGES[language]["tag_name"],
        "error_message": "",
        "script_output": "",
        "language_instructions": LANGUAGES[language]["language_instructions"]
    }
    conv = Conversation(
        ROLES, 
        prompt_store.get_prompt_from_template(
            "CI_SYSTEM_PROMPT",
            params
        ),
        send_req_to_agent,
        send_script_to_exc,
        extract_script,
        language,
        model_family,
        model_name,
        conv_id
    )
    conv.append_chat(
        prompt_store.get_prompt_from_template(
            "CI_AGENT_REPLY",
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
        return f"An error occurred: {str(e)}"

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
    
    params = {
        "display_name": LANGUAGES[language]["display_name"],
        "tag_name": LANGUAGES[language]["tag_name"],
        "error_message": "",
        "script_output": "",
        "language_instructions": LANGUAGES[language]["language_instructions"]
    }
    conv = Conversation(
        ROLES, 
        prompt_store.get_prompt_from_template(
            "CI_SYSTEM_PROMPT",
            params
        ),
        send_req_to_agent,
        send_script_to_exc,
        extract_script,
        language,
        model_family,
        model_name,
        conv_id
    )
    try:
        res = conv.exec_script(script, expected_output)
        if res["error"]:
            params["error_message"] = res["output"]
            conv.append_chat(
                prompt_store.get_prompt_from_template(
                    "CI_SCRIPT_ERROR",
                    params
                )
            )
            ret = conv.send_to_agent(stream)
            if stream:
                print(ret)
                print(res)
                return StreamingResponse(
                    iter_func(res, ret),
                    media_type="application/x-ndjson"
                )
            else:
                ret["output"] = res["output"]
                ret["error"] = res["error"]
                return ret
        else:
            # params["script_output"] = res["output"]
            # conv.append_chat(
            #     prompt_store.get_prompt_from_template(
            #         "CI_SCRIPT_SUCCESS",
            #         params
            #     )
            # )
            # ret = conv.send_to_agent()
            if stream:
                return StreamingResponse(
                    iter_func(res),
                    media_type="application/x-ndjson"
                )
            else:
                return res
    except Exception as e:
        # Handle any exceptions that occur during execution
        return f"An error occurred: {str(e)}"

if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api-layer-host", type=str, default="localhost")
    parser.add_argument("--api-layer-port", type=int, default=8080)
    parser.add_argument("--code-executor-host", type=str, default="localhost")
    parser.add_argument("--code-executor-port", type=int, default=8080)
    parser.add_argument("--prompt-database-file", type=str, default="prompt/database.json")
    parser.add_argument("--languages-file", type=str, default="config/languages.json")
    parser.add_argument("--max-exec-iter", type=int, default=3)
    args = parser.parse_args()
    logger.info(f"args: {args}")
    max_iterations = args.max_exec_iter
    api_layer_url = f"http://{args.api_layer_host}:{args.api_layer_port}/invoke"
    code_executor_url = f"http://{args.code_executor_host}:{args.code_executor_port}/execute_code"
    prompt_store = TemplateStore()
    prompt_store.read_from_json(args.prompt_database_file)
    with open(args.languages_file, "r") as json_f:
        LANGUAGES = json.load(json_f)    
    
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info"
    )