import gradio as gr
import requests
import json
import base64
import io
import os
from constants import (
    max_security_scan_retries,
    css,
    welcome_message,
    instructions,
    output_err_msg,
    output_info_msg,
    output_lines,
    scan_fail_msg,
    scan_pass_msg,
    scan_empty_msg,
    sec_out_err_msg,
    sec_out_info_msg,
    sec_out_pass_msg,
    sec_out_lines,
    files_path
)

# Global
languages = {}
controller_url = ""
models_list = {}
embedding_models_list = {}
scanners_list = {}
l_mapping ={}

class ConvState:
    def __init__(self):
        self.conv_id = ""
        self.passed_security_scan = False
        self.scan_retries = 0
        self.task = ""
        self.plan = ""
        self.generating = False
    
    
def scan_fn_with_stream(
    conv: gr.State, 
    history, 
    code,
    scanner,
    scan_status,
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    if conv.conv_id != "":
        conv.passed_security_scan = False
        output = gr.Textbox(
            value="",
            label=sec_out_info_msg, 
            elem_id="--primary-50", 
            interactive=False, 
            show_copy_button=True,
            lines=sec_out_lines,
            max_lines=sec_out_lines
        )
        yield {
            sec_out: output
        }
        if code != "" and conv.scan_retries < max_security_scan_retries and not conv.generating:
            history.append([None,"🤖️ Security scan in progress ..."])
            conv.generating = True
            yield {
                state: conv,
                chatbot: history
            }
            del history[-1]
            data = json.dumps(
                {
                    "script": code,
                    "model_family": models_list[model]["model_family"], 
                    "model_name": models_list[model]["model_name"], 
                    "language": language,
                    "scanner": scanners_list[scanner],
                    "conv_id": conv.conv_id,
                    "stream": stream,
                    "model_params": {
                        "temprature": temprature,
                        "top_p": top_p,
                        "top_k": top_k
                    }
                }
            )
            response = requests.post(
                "http://" + controller_url + "/scan",
                data=data,
                stream=stream
            )
            flag = True
            for chunk in response.iter_lines():
                if chunk != b'':
                    json_obj = json.loads(chunk)
                    if "error" in json_obj:
                        message = f'\nStack Trace: {json_obj["stacktrace"]}' if "stacktrace" in json_obj else ""
                        history[-1][1] = f'## ⛔️ **Agent encountered an error.**\n**Error:**{json_obj["error"]}{message}'
                        conv = ConvState()
                        yield {
                            chatbot: history, 
                            scan_stat: scan_empty_msg,
                            sec_out:"",
                            script: code
                        }
                        break
                    if "vulnerabilities" in json_obj and len(json_obj["vulnerabilities"]) > 0:
                        # gr.Warning("Code security scan detected some issues.")
                        output = gr.Textbox(
                            value=json_obj["vulnerabilities"],
                            label=sec_out_err_msg, 
                            elem_id="red",
                            lines=output_lines,
                            max_lines=output_lines
                        )
                        code = json_obj["script"]

                        scan_status = scan_fail_msg
                        if flag:
                            history.append(
                                [
                                    "Securit scan produced shown recommendations.",
                                    (
                                        json_obj["generated_text"] + "▌"
                                    )
                                ]
                            )
                            conv.scan_retries += 1
                            flag = False
                        else:
                            history[-1][-1] = (
                                json_obj["generated_text"] + "▌"
                            )
                        yield {
                            state: conv,
                            chatbot: history,
                            sec_out: output
                        }
                    else:
                        output = gr.Textbox(
                            value="",
                            label=sec_out_pass_msg, 
                            elem_id="green",
                            lines=sec_out_lines,
                            max_lines=sec_out_lines
                        )
                        scan_status = scan_pass_msg
                        conv.scan_retries = 0
                        conv.passed_security_scan = True
                        yield {
                            state: conv,
                            sec_out: output
                        }            
            history[-1][1] = history[-1][1].rstrip("▌")
            conv.generating = False
    else:
        output = gr.Textbox(
            value="",
            label=sec_out_info_msg, 
            elem_id="--primary-50", 
            interactive=False, 
            show_copy_button=True,
            lines=sec_out_lines,
            max_lines=sec_out_lines
        )
    ret = {
        chatbot: history, 
        scan_stat: scan_status,
        sec_out:output,
        state: conv
    }
    if not conv.passed_security_scan:
        ret[script] = code
    
    yield ret

def scan_fn(
    conv: gr.State, 
    history, 
    code,
    scanner,
    scan_status,
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    if conv.conv_id != "":
        output = gr.Textbox(
            value="",
            label=sec_out_info_msg, 
            elem_id="--primary-50" if not conv.passed_security_scan else "green", 
            interactive=False, 
            show_copy_button=True,
            lines=sec_out_lines,
            max_lines=sec_out_lines
        )
        history.append([None,"Security scan in progress ..."])
        yield {
            chatbot: history,
            sec_out: output
        }
        del history[-1]
        if code != "" and conv.scan_retries < max_security_scan_retries and not conv.passed_security_scan:
            data = json.dumps(
                {
                    "script": code,
                    "model_family": models_list[model]["model_family"], 
                    "model_name": models_list[model]["model_name"], 
                    "language": language,
                    "scanner": scanners_list[scanner],
                    "conv_id": conv.conv_id,
                    "stream": stream,
                    "model_params": {
                        "temprature": temprature,
                        "top_p": top_p,
                        "top_k": top_k
                    }
                }
            )
            response = requests.post(
                "http://" + controller_url + "/scan",
                data=data,
                stream=stream
            ).json()
            if response["vulnerabilities"] and len(response["vulnerabilities"]) > 0:
                gr.Warning("Code security scan detected some issues.")
                conv.scan_retries += 1
                output = gr.Textbox(
                    value=response["vulnerabilities"],
                    label=sec_out_err_msg,
                    elem_id="red",
                    lines=output_lines,
                    max_lines=output_lines
                )
                history.append(["Securit scan produced shown recommendations.", response["generated_text"]])
                code = response["script"]
                yield {
                    state: conv,
                    chatbot: history,
                    sec_out: output, 
                    scan_stat: scan_fail_msg
                }
            else:
                output = gr.Textbox(
                            value="",
                            label=sec_out_pass_msg, 
                            elem_id="green",
                            lines=sec_out_lines,
                            max_lines=sec_out_lines
                        )
                conv.scan_retries = 0
                conv.passed_security_scan = True
                yield {
                    state: conv,
                    scan_stat: scan_pass_msg,
                    sec_out: output
                }
    else:
        yield {}

def execute_fn(
    conv: gr.State, 
    history, 
    code,
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    history.append([None,"Executing script ..."])
    yield {
        chatbot: history
    }
    del history[-1]
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "conv_id": conv.conv_id,
            "stream": stream,
            "model_params": {
                "temprature": temprature,
                "top_p": top_p,
                "top_k": top_k
            }
        }
    )
    response = requests.post(
        "http://" + controller_url + "/execute",
        data=data,
        stream=stream
    ).json()
    if response["error"]:
        output = gr.Textbox(
            value=response["output"],
            label=output_err_msg,
            elem_id="red",
            lines=output_lines,
            max_lines=output_lines
        )
        history.append(["The script failed with shown error message", response["generated_text"]])
        code = response["script"]
    else:        
        output = gr.Textbox(
            value=response["output"],
            label=output_info_msg,
            elem_id="--primary-50",
            interactive=False,
            show_copy_button=True,
            lines=output_lines,
            max_lines=output_lines
        )
    images = []
    if "files" in json_obj:
        for file in json_obj["files"]:
            file_name, content = file.values()
            image_content = base64.b64decode(content)
            with open(os.path.join(files_path, file_name), "wb") as img:
                img.write(image_content)
            images.append(os.path.join(files_path, file_name))
    yield {
        chatbot: history,
        out: output,
        script: code,
        image: images
    }

def execute_fn_with_stream(
    conv: gr.State, 
    history, 
    code, 
    model, 
    language,
    timeout,
    stream,
    temprature, 
    top_p, 
    top_k
):
    history.append([None,"🤖️ Executing script ..."])
    yield {
        chatbot: history
    }
    del history[-1]
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "conv_id": conv.conv_id,
            "timeout": timeout,
            "stream": stream,
            "model_params": {
                "temprature": temprature,
                "top_p": top_p,
                "top_k": top_k
            }
        }
    )
    response = requests.post(
        "http://" + controller_url + "/execute",
        data=data,
        stream=stream
    )
    images = []
    flag = True
    conv.generating = True
    yield {
        state: conv
    }
    for chunk in response.iter_lines():
        if chunk != b'':
            json_obj = json.loads(chunk)
            if "files" in json_obj:
                for file in json_obj["files"]:
                    file_name, content = file.values()
                    image_content = base64.b64decode(content)
                    with open(os.path.join(files_path, file_name), "wb") as img:
                        img.write(image_content)
                    images.append(os.path.join(files_path, file_name))
            if json_obj["error"]:
                output = gr.Textbox(
                    value=json_obj["output"],
                    label=output_err_msg,
                    elem_id="red",
                    lines=output_lines,
                    max_lines=output_lines
                )
                if flag:
                    history.append(
                        [
                            "The script failed with shown error message",
                            (
                                json_obj["generated_text"] + "▌"
                            )
                        ]
                    )
                    flag = False
                else:
                    history[-1][-1] = (
                        json_obj["generated_text"] + "▌"
                    )
                code = json_obj["script"]
            else:
                output = gr.Textbox(
                    value=json_obj["output"],
                    label=output_info_msg, 
                    elem_id="--primary-50", 
                    interactive=False, 
                    show_copy_button=True,
                    lines=output_lines,
                    max_lines=output_lines
                )
            yield {
                state: conv,
                chatbot: history,
                out: output,
                # script: code,
                image: images
            }
    history[-1][1] = history[-1][1].rstrip("▌")
    conv.generating = False
    yield {
        state: conv,
        chatbot: history,
        out: output,
        script: code,
        image: images
    }

def generate_response_with_stream(
    conv: gr.State, 
    history, 
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    history.append([None, "🤖️ Generating response ..." ])
    yield {
        chatbot: history
    }
    del history[-1]
    conv.passed_security_scan = False
    conv.scan_retries = 0
    prompt = history[-1][0]
    if len(history) == 1:
        prompt = conv.plan
    data = json.dumps(
        {
            "prompt": prompt,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "conv_id": conv.conv_id,
            "stream": stream,
            "model_params": {
                "temprature": temprature,
                "top_p": top_p,
                "top_k": top_k
            }
        }
    )
    response = requests.post(
        "http://" + controller_url + "/generate",
        data=data,
        stream=stream
    )
    conv.generating = True
    yield {
        state: conv
    }
    for chunk in response.iter_lines():
        if chunk != b'':
            json_obj = json.loads(chunk)
            if "error" in json_obj:
                message = f'\nStack Trace: {json_obj["stacktrace"]}' if "stacktrace" in json_obj else ""
                history[-1][1] = f'## ⛔️ **Agent encountered an error.**\n**Error:** {json_obj["error"]}{message}'
                conv = ConvState()
                yield {
                    state: conv,
                    chatbot: history,
                    script: ""
                }
                break
            history[-1][1] = (
                json_obj["generated_text"] + "▌"
            )
            conv.conv_id = json_obj.get("conv_id", "")
            yield {
                state: conv,
                chatbot: history
            }
    
    last_response = history[-1][1].rstrip("▌")
    
    history[-1][1] = last_response
    conv.conv_id = json_obj.get("conv_id", "")
    conv.generating = False
    yield {
        state: conv,
        chatbot: history,
        script: json_obj.get("script","")
    }

def generate_response(
    conv: gr.State, 
    history, 
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    conv.passed_security_scan = False
    conv.scan_retries = 0
    prompt = history[-1][0]
    if len(history) == 1:
        prompt = conv.plan
    data = json.dumps(
        {
            "prompt": prompt,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "conv_id": conv.conv_id,
            "stream": stream,
            "model_params": {
                "temprature": temprature,
                "top_p": top_p,
                "top_k": top_k
            }
        }
    )
    response = json.loads(
        requests.post(
            "http://" + controller_url + "/generate",
            data=data
        ).text
    )
    if "error" in response:
        message = f'\nStack Trace: {response["stacktrace"]}' if "stacktrace" in response else ""
        history[-1][1] = f'## ⛔️ **Agent encountered an error.**\n**Error:**{response["error"]}{message}'
        conv = ConvState()
        return [conv, history, "", ""]

    res = response["generated_text"]
    conv.conv_id = res.get("conv_id", "")
    history[-1][1] = res
    return [conv, history, res["script"]]

def plan_fn(
    conv: gr.State, 
    history, 
    model, 
    language,
    temprature, 
    top_p, 
    top_k
):
    if len(history) <= 1:
        conv.passed_security_scan = False
        conv.scan_retries = 0
        conv.task = history[0][0]
        history[0][1] = "🤖️ Brainstorming and meditating ..." 
        yield {
            state: conv,
            chatbot: history
        }
        history[0][1] = None
        data = json.dumps(
            {
                "prompt": history[-1][0],
                "model_family": models_list[model]["model_family"], 
                "model_name": models_list[model]["model_name"], 
                "language": language,
                "conv_id": "",
                "stream": False,
                "model_params": {
                    "temprature": temprature,
                    "top_p": top_p,
                    "top_k": top_k
                }
            }
        )
        response = json.loads(
            requests.post(
                "http://" + controller_url + "/plan",
                data=data
            ).text
        )
        if "error" in response:
            message = f'\nStack Trace: {response["stacktrace"]}' if "stacktrace" in response else ""
            history[0][1] = f'## ⛔️ **Agent encountered an error.**\n**Error:**{response["error"]}{message}'
            conv = ConvState()
            return [conv, history, "", ""]

        res = response["generated_text"]
        conv.conv_id = ""
        conv.plan = res
    yield {
        state: conv,
        chatbot: history
    }

def save_fn(
    history,
    code,
    model,
    embed_model,
    language,
    temprature, 
    top_p, 
    top_k
):
    history.append([None,"Saving task ..."])
    yield {
        chatbot: history
    }
    del history[-1]
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"],
            "model_name": models_list[model]["model_name"],
            "language": language,
            "stream": False,
            "model_params": {
                "temprature": temprature,
                "top_p": top_p,
                "top_k": top_k
            },
            "embedding_model_family": embedding_models_list[embed_model]["model_family"],
            "embedding_model_name": embedding_models_list[embed_model]["model_name"],
        }
    )
    res = requests.post(
            "http://" + controller_url + "/save",
            data=data
        ).text
    response = json.loads(res)
    if "error" in response:
        message = f'\nStack Trace: {response["stacktrace"]}' if "stacktrace" in response else ""
        gr.Error(message)
        yield {
            chatbot: history,
            save: gr.update(interactive=True)
        }

    gr.Info(res)
    yield {
        save: gr.update(interactive=False),
        chatbot: history
    }

def load_fn(
    prompt,
    model,
    embed_model,
    language,
    threshold
):
    data = json.dumps(
        {
            "prompt": prompt,
            "language": language,
            "stream": False,
            "model_family": models_list[model]["model_family"],
            "model_name": models_list[model]["model_name"],
            "embedding_model_family": embedding_models_list[embed_model]["model_family"],
            "embedding_model_name": embedding_models_list[embed_model]["model_name"],
            "threshold": threshold
        }
    )
    res = requests.post(
        "http://" + controller_url + "/load",
        data=data
    ).text
    response = json.loads(res)
    ret = clear_fn()
    if "error" in response:
        message = f'\nStack Trace: {response["stacktrace"]}' if "stacktrace" in response else ""
        gr.Error(message)
        return ret + [""] + [scan_empty_msg]

    # gr.Info(response[0]["task_desc"])
    # [state, chatbot, script, out, image, sec_out, load_box, scan_stat]
    if len(response["matches"]) > 0:
        ret[5] = gr.Textbox(
            value="",
            label=sec_out_pass_msg, 
            elem_id="green",
            lines=sec_out_lines,
            max_lines=sec_out_lines
        )
        ret = clear_fn()
        ret[0].conv_id = response["conv_id"]
        ret[0].passed_security_scan = True
        ret[2] = response["matches"][0]["code"]
        ret[1] = [
            [
                f'Load the following task:\n{response["matches"][0]["task_desc"]}',
                f"Here is the loaded task script:\n```{l_mapping[language]}\n{ret[2]}\n```"
            ]
        ]
        ret[7] = scan_pass_msg
    else:
        gr.Info("No matches found to load.")
    return ret + [""] + [scan_empty_msg]

def can_exec(conv, code):
    if code != "" and conv.passed_security_scan and not conv.generating:
        return (
            gr.update(interactive=True),
            gr.update(interactive=True)
        )
    else:
        return (
            gr.update(interactive=False),
            gr.update(interactive=False)
        )

def disable_exec():
    return gr.update(interactive=False)
    
def empty_folder():
    files = os.listdir(files_path)
    for file in files:
        file_path = os.path.join(files_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
def change_language(language):
    """
    Code Languages
    approved language: [('python', 'markdown', 'json', 'html', 'css', 'javascript', 'typescript', 'yaml', 'dockerfile', 'shell', 'r')]
    """
    empty_folder()
    return [ConvState(), []] + [gr.Code(value="", language=l_mapping[language], interactive=False)] + [""] + [[]]

def change_model():
    empty_folder()
    return [ConvState(), []] + [""] * 2 + [[]]

def clear_fn():
    empty_folder()
    return [ConvState(), [], ""] + [gr.Textbox(
        value="",
        label=output_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True, 
        lines=output_lines, 
        max_lines=output_lines
    )] + [[]] + [gr.Textbox(
        value="",
        label=sec_out_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True, 
        lines=sec_out_lines, 
        max_lines=sec_out_lines
    ), "", scan_empty_msg]

def vote(data: gr.LikeData, conv):
    if data.liked:
        print("You upvoted this response: " + data.value + conv.conv_id)
    else:
        print("You downvoted this response: " + data.value)   

def add_text(message, history):
    if message != "":
        history += [[message, None]]
    return ["", history]

def web_ui():
    global state, chatbot, script, out, scan_stat, sec_out, image, save

    theme = gr.themes.Default(
        neutral_hue="slate"
    )

    with gr.Blocks(css=css, theme=theme) as webUI:
        state = gr.State(ConvState())
        gr.Markdown(welcome_message, elem_id="main-banner")
        with gr.Row():
            with gr.Column(scale=6):
                with gr.Tab("Chatbot"):
                    with gr.Group(elem_id="chatbot-group"):
                        with gr.Row():
                            chatbot = gr.Chatbot(elem_id="chatbot-window", show_copy_button=True, height=450)
                        with gr.Row():                                
                            with gr.Column(scale=8): 
                                textbox = gr.Textbox(
                                    show_label=False, 
                                    placeholder="Enter your prompt here and press ENTER", 
                                    container=False, 
                                    scale=16
                                )
                            with gr.Column(scale=1):
                                submit = gr.Button(
                                    value="Submit 💬️", 
                                    variant="primary",
                                    elem_id="chatbot-button",
                                    interactive=False
                                )
                                clear_btn = gr.ClearButton(
                                    value="Clear 🗑️",
                                    elem_id="chatbot-button"
                                )
                                execute = gr.Button(value="Execute", interactive=False, variant="primary")
                with gr.Tab("Properties"):
                    with gr.Row():
                        with gr.Column():
                            language = gr.Dropdown(languages,label='Programing Langauge', value=languages[0])
                        with gr.Column():
                            model = gr.Dropdown(models_list.keys(),label="LLM Model", value=list(models_list.keys())[0])
                    with gr.Row():
                        with gr.Column():
                            temprature = gr.Slider(label="Temprature", step=0.1, minimum=0, maximum=1, value=0)
                        with gr.Column():
                            top_p = gr.Slider(label="Top_p", step=0.1, minimum=0, maximum=1, value=0)
                        with gr.Column():
                            top_k = gr.Slider(label="Top_k", step=1, minimum=1, maximum=500, value=5)
                    streaming = gr.Checkbox(label='Stream chat response', value=True)
                    embed_model = gr.Dropdown(embedding_models_list.keys(),label="Embedding Model", value=list(embedding_models_list.keys())[0])                    
                    threshold = gr.Slider(label="Loading Match Threshold", step=0.05, minimum=0.05, maximum=1.00, value=0.30)
                    scanner = gr.Dropdown(scanners_list.keys(),label="Security Scanner", value=list(scanners_list.keys())[0])
                    timeout = gr.Number(label="Execution Timeout", precision=0, minimum=10, maximum=3600, value=30)
                with gr.Tab("Help"):
                    gr.Markdown(instructions)

            with gr.Column(scale=4):
                with gr.Tab("Outputs"):
                    out = gr.Textbox(
                        value="",
                        label=output_info_msg,
                        interactive=False,
                        show_copy_button=True,
                        lines=output_lines,
                        max_lines=output_lines
                    )
                    sec_out = gr.Textbox(value="",label=sec_out_info_msg, interactive=False, lines=sec_out_lines, max_lines=sec_out_lines) 

                with gr.Tab("Plots and Images"):
                    image = gr.Gallery(label="Image", show_download_button=True, preview=True, object_fit="fill", selected_index=0)
                with gr.Tab("Current Script"):
                    with gr.Group(elem_id="script-group"):
                        script = gr.Code(value="",label="Script", language = l_mapping[languages[0]], interactive=False, lines=16)
                        scan_stat = gr.Markdown(scan_empty_msg)
                        with gr.Row():
                            with gr.Column(scale=2):
                                load_box = gr.Textbox(
                                    show_label=False,
                                    placeholder="Enter detailed task description to load.",
                                    container=False
                                )
                            with gr.Column(scale=1):
                                load = gr.Button(variant="primary", value="Load", interactive=False)
                                save = gr.Button(value="Save 💾️", interactive=False)
                
            
        language.change(change_language, [language], [state, chatbot, script, out, image], queue=False)
        model.change(change_model, None, [state, chatbot, script, out, image], queue=False)
        
        gr.on(
            [submit.click, textbox.submit],
            add_text, 
            [textbox, chatbot], 
            [textbox, chatbot],
            show_progress=False,
            queue=False
        ).then(
            plan_fn,
            [state, chatbot, model, language, temprature, top_p, top_k],
            [state, chatbot],
            show_progress=False,
            queue=True
        ).then(
            generate_response_with_stream if streaming.value else generate_response, 
            [state, chatbot, model, language, streaming, temprature, top_p, top_k], 
            [state, chatbot, script],
            show_progress=False,
            queue=streaming.value
        )
        
        textbox.change(
            lambda x: {submit: gr.update(interactive=True)} if x != "" else {submit: gr.update(interactive=False)},
            [textbox],
            [submit],
            show_progress=False
        )
        
        load_box.change(
            lambda x: {load: gr.update(interactive=True)} if x != "" else {load: gr.update(interactive=False)},
            [load_box],
            [load],
            show_progress=False
        )
        
        script.change(
            scan_fn_with_stream if streaming.value else scan_fn, 
            [state, chatbot, script, scanner, scan_stat, model, language, streaming, temprature, top_p, top_k], 
            [state, chatbot, sec_out, script, scan_stat], queue=streaming,
            show_progress=False
        ).then(
            can_exec, 
            [state, script], 
            [execute, save],
            show_progress=False,
            queue=False
        )
        
        clear_btn.click(
            clear_fn, 
            None, 
            [state, chatbot, script, out, image, sec_out, load_box, scan_stat],
            show_progress=False,
            queue=False
        )
        
        execute.click(
            disable_exec,
            None,
            execute
        ).then(            
            execute_fn_with_stream if streaming.value else execute_fn, 
            [state, chatbot, script, model, language, timeout, streaming, temprature, top_p, top_k], 
            [state, chatbot, out, script, image],
            show_progress=False,
            queue=streaming
        )
        
        save.click(
            save_fn, 
            [chatbot, script, model, embed_model, language, temprature, top_p, top_k], 
            [chatbot, save],
            show_progress=False
        )
        gr.on(
            [load.click, load_box.submit],
            load_fn,
            [load_box, model, embed_model, language, threshold],
            [state, chatbot, script, out, image, sec_out, load_box, scan_stat],
            show_progress=False,
            queue=False
        )
        chatbot.like(
            vote, 
            state, 
            None,
            show_progress=False,
            queue=False
        )
    return webUI

def get_languages_list(url):
    return list(json.loads(requests.get("http://" + url + "/list_languages").json()).keys())
    
if __name__ == "__main__":
    languages = get_languages_list(controller_url)
    UI = web_ui()
    UI.queue(status_update_rate=10, api_open=False).launch(debug=False, max_threads=output_lines0)