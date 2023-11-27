import os
import json
import boto3
from typing import List, Dict
from prompt.template import PromptTemplate

class TemplateStore:
    database = {}
    def __init__(self):
        ddb_table_name = os.getenv("APP_PROMPT_STORE", "")
        external_store = True if ddb_table_name!="" else False
        self.external_store = external_store
        if external_store:
            if ddb_table_name=="":
                raise ValueError("Must supply valid ddb_table_name for external store")
            else:
                self.table_name = ddb_table_name
                self.ddb_client = boto3.client("dynamodb")
        
    def add_template(self, template_id: str, template: PromptTemplate):
        self.database[template_id] = template
        if self.external_store:
            # TODO: Add template to DDB table
            pass
    
    def get_prompt_from_template(self, template_id: str, param_values: Dict[str, str]):
        if self.external_store:
            item = self.ddb_client.get_item(
                TableName=self.table_name, 
                Key={
                    "template_id":{
                        "S": template_id
                    }
                }
            )["Item"]
            record = PromptTemplate(item["template"]["S"], json.loads(item["params"]["S"]))
        else:
            record = self.database[template_id]
        kwargs = {}
        for param in record.params:
            kwargs[param] = param_values[param]
        return record.template.format(**kwargs)
    
    def read_from_json(self, store_file: str):
        with open(store_file, "r") as json_f:
            json_db = json.load(json_f)
            for line in json_db:
                self.add_template(
                    template_id=line["template_id"],
                    template=PromptTemplate(
                        line["template"],
                        line["params"]
                    )
                )
        

