import json
from jsonpath_ng import jsonpath, parse
import re

class BaseModel:
    def inovke_api(self):
        raise NotImplementedError("Not implemented in base model, make sure to override this method.")
    
    def load_mappings(self, schema_path):
        mappings = {}
        with open(schema_path, "r") as schema_file:
            mappings = json.load(schema_file)
        return (
            mappings["request"]["defaults"],
            mappings["request"]["mapping"],
            mappings["response"]["regex_sub"],
            mappings["response"]["mapping"],
            mappings["response-with-stream"]["regex_sub"],
            mappings["response-with-stream"]["mapping"]
        )
    
    def form_request(self, params, defaults, mapping):
        for attrib, jpath in mapping.items():
            if attrib in params.keys():
                jsonpath_expr = parse(jpath)
                jsonpath_expr.update(defaults, params[attrib])
        return defaults

    def parse_response(self, response_body, mapping, regex_sub=None):
        res = None
        if regex_sub:
            res = json.loads(re.sub(regex_sub, "", response_body))
        else:
            res = json.loads(response_body)
        ret = {}
        for attrib, jpath in mapping.items():
            jsonpath_expr = parse(jpath)
            results = jsonpath_expr.find(res)
            if results and len(results) > 0:
                ret[attrib] = results[0].value
        return ret