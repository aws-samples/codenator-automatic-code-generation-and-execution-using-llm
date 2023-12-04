import uuid
import json
from utils import (
    send_req_to_agent,
    security_scan_script,
    send_script_to_exc,
    extract_script,
    get_languages
)
import boto3
import os

class Conversation:
    def __init__(
        self, 
        roles, 
        prompt,
        language,
        model_family,
        model_name,
        model_metadata,
        model_params,
        conv_id: str=""
    ):
        self.s3_client = boto3.client("s3")
        self.bucket = os.getenv("APP_CONV_BUCKET")
        self.prefix = os.getenv("APP_CONV_KEY")
        self.id = conv_id if conv_id != "" else uuid.uuid4().hex
        self.roles = roles
        self.system_prompt = prompt
        self.agent = send_req_to_agent
        self.scanner = security_scan_script
        self.executor = send_script_to_exc
        self.script_extractor = extract_script
        self.language = language
        self.model_family = model_family
        self.model_name = model_name
        self.model_metadata = model_metadata
        self.params = model_params
        if conv_id == "":
            self.history = ""
            self.last_agent_message = ""
            self.append_chat(prompt, 0)
        else:
            self.load()

    def save(self):
        data = {
            "history": self.history,
            "last_agent_message": self.last_agent_message,
            "language": self.language,
            "model_family": self.model_family,
            "model_name": self.model_name,
            "model_params": self.params
        }
        self.s3_client.put_object(
            Body=json.dumps(data).encode(), 
            Bucket=self.bucket, 
            Key=os.path.join(self.prefix, self.id + ".json")
        )
    
    def load(self):
        data = self.s3_client.get_object(
            Bucket=self.bucket,
            Key=os.path.join(self.prefix, self.id + ".json")
        )
        data_dict = json.loads(data["Body"].read())
        self.history = data_dict["history"]
        self.last_agent_message = data_dict["last_agent_message"]
        self.language = data_dict["language"]
        if data_dict["model_family"] != "" and data_dict["model_name"] != "":
            self.model_family = data_dict["model_family"]
            self.model_name = data_dict["model_name"]
        self.params = data_dict["model_params"]
        
        
    def append_chat(self, text, role=0):
        self.history += "\n" + self.roles[role] + text
        self.save()
        
    def send_to_agent(self, stream=False):
        def form_response(text=None):
            self.save()
            LANGUAGES = get_languages()
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
        self.params["prompt"] = self.history
        self.params["stream"] = stream
        res = self.agent(
            self.params,
            self.model_family,
            self.model_name,
            self.model_metadata
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

    def scan_script(self, script):
        res = {}
        res["vulnerabilities"] = self.scanner(script, self.language)
        res["script"] = script
        res["conv_id"] = self.id
        return res
    
    def exec_script(self, script, expected_output, timeout=10):
        LANGUAGES = get_languages()
        full_script = ""
        if LANGUAGES[self.language]["pre_exec_script"]:
            full_script += LANGUAGES[self.language]["pre_exec_script"] + "\n"
        full_script += script
        if LANGUAGES[self.language]["post_exec_script"]:
            full_script += "\n" + LANGUAGES[self.language]["post_exec_script"]
        res = self.executor(full_script, LANGUAGES[self.language]["kernel_name"], timeout)
        res["script"] = script
        res["expected_output"] = expected_output
        res["conv_id"] = self.id
        return res