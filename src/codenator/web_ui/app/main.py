from webui import web_ui, get_languages_list
import webui
import argparse
import gradio as gr
import boto3
import json

def get_value_from_ddb(item, ddb_table_name):
    if ddb_table_name != "":
        ddb_client = boto3.client("dynamodb")
        ret = ddb_client.get_item(
            TableName=ddb_table_name,
            Key={
                "pk": {
                    "S": "webui"
                },
                "sk": {
                    "S": item
                }
            }
        )["Item"]["value"]["S"]
        return json.loads(ret)
    else:
        return {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--controller-host", type=str, default="localhost")
    parser.add_argument("--controller-port", type=int, default=8080)
    parser.add_argument("--models-metadata-db", type=str, default="")
    parser.add_argument("--feedback-bucket", type=str, default="")
    parser.add_argument("--feedback-prefix", type=str, default="")
    parser.add_argument("--debug", type=bool, default=False)
    parser.add_argument("--share", type=bool, default=False)
    args = parser.parse_args()
    webui.l_mapping = get_value_from_ddb("language_mappings", args.models_metadata_db)
    webui.models_list = get_value_from_ddb("models_list", args.models_metadata_db)
    webui.embedding_models_list = get_value_from_ddb("embedding_models_list", args.models_metadata_db)
    webui.scanners_list = get_value_from_ddb("scanners_list", args.models_metadata_db)
    webui.controller_url = f"{args.controller_host}:{args.controller_port}"
    webui.languages = get_languages_list(webui.controller_url)
    webui.feedback_bucket = args.feedback_bucket
    webui.feedback_prefix = args.feedback_prefix
    UI = web_ui()
    UI.queue(
        status_update_rate=10,
        api_open=False,
        default_concurrency_limit=30
    ).launch(
        debug=args.debug,
        share=args.share,
        inline=False,
        show_error=True,
        server_name=args.host,
        server_port=args.port,
        show_api=False,
        max_threads=200
    )