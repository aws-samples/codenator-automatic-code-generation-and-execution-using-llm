import uuid
import utils
import json

CONVERSATIONS = {}

class Conversation:
    def __init__(
        self, 
        roles, 
        prompt, 
        agent,
        scanner,
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
        self.scanner = scanner
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
                utils.LANGUAGES[self.language]["tag_name"]
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

    def scan_script(self, script):
        res = {}
        res["vulnerabilities"] = self.scanner(script, self.language)
        res["script"] = script
        res["conv_id"] = self.id
        return res
    
    def exec_script(self, script, expected_output):
        output_res = ""
        if utils.LANGUAGES[self.language]["pre_exec_script"]:
            output_res += self.executor(
                utils.LANGUAGES[self.language]["pre_exec_script"], 
                utils.LANGUAGES[self.language]["kernel_name"]
            )["output"]
        res = self.executor(script, utils.LANGUAGES[self.language]["kernel_name"])
        res["output"] = output_res + res["output"]
        if utils.LANGUAGES[self.language]["post_exec_script"]:
            res["output"] += self.executor(
                utils.LANGUAGES[self.language]["post_exec_script"], 
                utils.LANGUAGES[self.language]["kernel_name"]
            )["output"]
        res["script"] = script
        res["expected_output"] = expected_output
        res["conv_id"] = self.id
        return res