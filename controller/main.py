from importlib import import_module
import argparse
import requests
import json
import uuid
import logging as logger
from fastapi import FastAPI, Request
from prompt.template import PromptTemplate
from prompt.store import TemplateStore
import uvicorn

app = FastAPI()
code_block_symbol = "```"
output_tags = ["<output>", "</output>"]
ROLES = ["Human", "Assistant"]
CONVERSATIONS = {}

def send_req_to_agent(text, model_family, model_name):
    data = {
        "body": {
            "prompt": text
        }, 
        "model_family": model_family, 
        "model_name": model_name
    }
    ret = requests.post(
        url=api_layer_url, 
        data=json.dumps(data)
    )
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
            script = text.split(code_block_symbol + tag_name + "\n")[1].split(code_block_symbol)[0]
            expected_output = ""
            if output_tags[0] in text and output_tags[1] in text:
                expected_output = text.split(output_tags[0])[1].split(output_tags[1])[0]
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
        
    def send_to_agent(self):
        self.append_chat("", 1)
        res = self.agent(
            self.history,
            self.model_family,
            self.model_name
        )
        self.history += res
        CONVERSATIONS[self.id]["history"] = self.history
        self.last_agent_message = res
        CONVERSATIONS[self.id]["last_agent_message"] = self.last_agent_message
    
    def send_to_agent_and_exec_script(self):
        self.send_to_agent()
        result = self.script_extractor(
            self.last_agent_message,
            LANGUAGES[self.language]["tag_name"]
        )
        if result:
            script, expected_output = result
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
            return res
        else:
            return None

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

@app.get("/list_languages")
def list_languages():
    return json.dumps(LANGUAGES)


#     params = {
#         "display_name": LANGUAGES[language]["display_name"],
#         "tag_name": LANGUAGES[language]["tag_name"],
#         "error_message": "",
#         "script_output": "",
#         "language_instructions": LANGUAGES[language]["language_instructions"]
#     }

#     for test in test_prompts:
#         conv = Conversation(
#             ROLES, 
#             prompt_store.get_prompt_from_template(
#                 "CI_SYSTEM_PROMPT",
#                 params
#             ),
#             send_req_to_agent,
#             send_script_to_exc,
#             extract_script,
#             language
#         )
#         conv.append_chat(
#             prompt_store.get_prompt_from_template(
#                 "CI_AGENT_REPLY",
#                 params
#             ),
#             1
#         )
#         conv.append_chat(test)
#         res = conv.send_to_agent_and_exec_script()
#         max_iterations = 3
#         i = 0
#         while i < max_iterations and res["error"]:
#             i += 1
#             params["error_message"] = res["output"]
#             conv.append_chat(
#                 prompt_store.get_prompt_from_template(
#                     "CI_SCRIPT_ERROR",
#                     params
#                 )
#             )
#             conv.send_to_agent_and_exec_script()   
#         if not res["error"]:
#             params["script_output"] = res["output"]
#             conv.append_chat(
#                 prompt_store.get_prompt_from_template(
#                     "CI_SCRIPT_SUCCESS",
#                     params
#                 )
#             )
#             conv.send_to_agent()
#         print(conv.history)

@app.post("/generate")
async def generate(request: Request):
    params = await request.json()
    model_family = params.get("model_family")
    model_name = params.get("model_name")
    language = params.get("language")
    if not (model_family and model_name and language):
        raise
    conv_id = params.get("conv_id", "")
    
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
    conv.append_chat(test)
    try:
        res = conv.send_to_agent_and_exec_script()
        if not res:
            raise
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
    parser.add_argument("--code-execurtor-port", type=int, default=8080)
    parser.add_argument("--prompt-database-file", type=str, default="prompt/database.json")
    parser.add_argument("--languages-file", type=str, default="config/languages.json")
    args = parser.parse_args()
    logger.info(f"args: {args}")
    
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