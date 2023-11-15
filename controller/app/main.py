import argparse
import requests
import traceback
import json
import logging as logger
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
from prompt.store import TemplateStore
from conversation import Conversation
import utils
from utils import (
    get_model_type,
    get_model_metadata,
    get_languages,
    send_req_to_agent,
    security_scan_script,
    send_script_to_exc,
    extract_script
)

app = FastAPI()

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

@app.get("/list_languages")
def list_languages():
    try:
        utils.LANGUAGES = get_languages()
        return json.dumps(utils.LANGUAGES)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return json.dumps({"error": e, "stacktrace": tb})

@app.post("/generate")
async def generate(request: Request):
    try:
        params = await request.json()
        prompt = params.get("prompt")
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")    
        if not (prompt and model_family and model_name and language):
            return {"error": f"Request must supply `prompt`, `model_family`, `model_name` and `language` paramaters"}
        model_type, can_stream = get_model_type(model_family, model_name)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        conv_id = params.get("conv_id", "")
        stream = params.get("stream", False)
        if stream:
            stream = can_stream

        utils.LANGUAGES = get_languages()
        params = {
            "display_name": utils.LANGUAGES[language]["display_name"],
            "tag_name": utils.LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": utils.LANGUAGES[language]["language_instructions"]
        }
    
        model_metadata = get_model_metadata(model_type)

        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                model_metadata["SYSTEM_PROMPT_TMPLT"],
                params
            ),
            send_req_to_agent,
            security_scan_script,
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
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

@app.post("/scan")
async def scan(request: Request):
    
    def iter_func(scan_result, results=None):
        if results:
            for json_result in results:
                result = json.loads(json_result)
                result["vulnerabilities"] = scan_result
                yield json.dumps(result) + "\n"
        else:
            yield json.dumps(scan_result) + "\n"
    try:
        params = await request.json()
        script = params.get("script")
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")
        conv_id = params.get("conv_id")
        if not (script and conv_id and model_family and model_name and language):
            return {"error": f"Request must supply `script`, `conv_id`, `model_family`, `model_name` and `language` paramaters"}
        model_type, can_stream = get_model_type(model_family, model_name)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        stream = params.get("stream", False)
        if stream:
            stream = can_stream

        utils.LANGUAGES = get_languages()
        params = {
            "display_name": utils.LANGUAGES[language]["display_name"],
            "tag_name": utils.LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": utils.LANGUAGES[language]["language_instructions"]
        }
    
        model_metadata = get_model_metadata(model_type)
        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                model_metadata["SYSTEM_PROMPT_TMPLT"],
                params
            ),
            send_req_to_agent,
            security_scan_script,
            send_script_to_exc,
            extract_script,
            language,
            model_family,
            model_name,
            model_metadata,
            conv_id
        )

        res = conv.scan_script(script)
        if len(res["vulnerabilities"]) > 0:
            params["vulnerabilities"] = res["vulnerabilities"]
            conv.append_chat(
                prompt_store.get_prompt_from_template(
                    model_metadata["UNSECURE_SCRIPT_TMPLT"],
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
                ret["vulnerabilities"] = res["vulnerabilities"]
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
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

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
    try:
        params = await request.json()
        script = params.get("script")
        expected_output = params.get("expected_output", "")
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")
        conv_id = params.get("conv_id")
        if not (script and conv_id and model_family and model_name and language):
            return {"error": f"Request must supply `script`, `conv_id`, `model_family`, `model_name` and `language` paramaters"}
        model_type, can_stream = get_model_type(model_family, model_name)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        stream = params.get("stream", False)
        if stream:
            stream = can_stream

        utils.LANGUAGES = get_languages()
        params = {
            "display_name": utils.LANGUAGES[language]["display_name"],
            "tag_name": utils.LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": utils.LANGUAGES[language]["language_instructions"]
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
        res = conv.exec_script(script, expected_output)
        if "error" in res:
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
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

    
if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api-layer-host", type=str, default="localhost")
    parser.add_argument("--api-layer-port", type=int, default=8080)
    parser.add_argument("--code-executor-host", type=str, default="localhost")
    parser.add_argument("--code-executor-port", type=int, default=8080)
    parser.add_argument("--code-scanner-host", type=str, default="localhost")
    parser.add_argument("--code-scanner-port", type=int, default=8080)
    parser.add_argument("--prompt-database-file", type=str, default="prompt/database.json")
    parser.add_argument("--prompt-store-name", type=str, default="")
    parser.add_argument("--models-metadata-db", type=str, default="")
    parser.add_argument("--models-metadata-file", type=str, default="config/model_meta.json")
    parser.add_argument("--languages-file", type=str, default="config/languages.json")
    parser.add_argument("--max-exec-iter", type=int, default=3)
    args = parser.parse_args()
    logger.info(f"args: {args}")
    max_iterations = args.max_exec_iter
    utils.api_layer_url = f"http://{args.api_layer_host}:{args.api_layer_port}/invoke"
    utils.code_executor_url = f"http://{args.code_executor_host}:{args.code_executor_port}/execute_code"
    utils.code_scanner_url = f"http://{args.code_scanner_host}:{args.code_scanner_port}/scan"
    prompt_store = TemplateStore(
        external_store=True if args.prompt_store_name != "" else False, 
        ddb_table_name=args.prompt_store_name
    )
    if args.prompt_store_name == "":
        prompt_store.read_from_json(args.prompt_database_file)
    if args.models_metadata_db == "":
        with open(args.models_metadata_file, "r") as json_f:
            utils.models_metadata = json.load(json_f)
        with open(args.languages_file, "r") as json_f:
            utils.LANGUAGES = json.load(json_f)
    else:
        utils.models_metadata_db = args.models_metadata_db
        utils.LANGUAGES = get_languages()
    
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info"
    )