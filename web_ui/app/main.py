from webui import web_ui, get_languages_list
import webui
import argparse
import gradio as gr

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--controller-host", type=str, default="localhost")
    parser.add_argument("--controller-port", type=int, default=8080)
    parser.add_argument("--debug", type=bool, default=False)
    parser.add_argument("--share", type=bool, default=False)
    args = parser.parse_args()
    webui.controller_url = f"{args.controller_host}:{args.controller_port}"
    webui.languages = get_languages_list(webui.controller_url)
    print(webui.languages)
    UI = web_ui()
    UI.queue(
        status_update_rate=10,
        api_open=False
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