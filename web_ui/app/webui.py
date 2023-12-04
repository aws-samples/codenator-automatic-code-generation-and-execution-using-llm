import gradio as gr
import requests
import json
import base64
import io
import os
from constants import (
    out_tag,
    ex_out_tag,
    max_security_scan_retries,
    css,
    welcome_message,
    instructions,
    output_err_msg,
    output_wrn_msg,
    output_info_msg,
    scan_fail_msg,
    scan_pass_msg,
    scan_empty_msg,
    sec_out_err_msg,
    sec_out_info_msg,
    files_path
)

# Global
languages = {}
controller_url = ""
models_list = {}
l_mapping ={}

class ConvState:
    def __init__(self):
        self.conv_id = ""
        self.passed_security_scan = False
        self.scan_retries = 0

def scan_fn_with_stream(
    conv: gr.State, 
    history, 
    code, 
    scan_status, 
    exp_out, 
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    output = gr.Textbox(
        value="",
        label=sec_out_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True,
        lines=7,
        max_lines=7
    )
    if conv.conv_id != "":
        if code != "" and conv.scan_retries < max_security_scan_retries and not conv.passed_security_scan:
            data = json.dumps(
                {
                    "script": code,
                    "model_family": models_list[model]["model_family"], 
                    "model_name": models_list[model]["model_name"], 
                    "language": language,
                    "expected_output": exp_out,
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
                            lines=7,
                            max_lines=7
                        )
                        code = json_obj["script"]

                        scan_status = scan_fail_msg
                        if flag:
                            history.append(
                                [
                                    "Securit scan produced shown recommendations.",
                                    # to avoid Gradio Markdown bug related to <output></output> bug
                                    (
                                        json_obj["generated_text"] + "▌"
                                    ).replace(
                                        out_tag[0], 
                                        ex_out_tag[0]
                                    ).replace(
                                        out_tag[1], 
                                        ex_out_tag[1]
                                    )
                                ]
                            )
                            conv.scan_retries += 1
                            flag = False
                        else:
                            history[-1][-1] = (
                                json_obj["generated_text"] + "▌"
                            ).replace(
                                out_tag[0], 
                                ex_out_tag[0]
                            ).replace(
                                out_tag[1], 
                                ex_out_tag[1]
                            )
                        yield {
                            state: conv,
                            chatbot: history,
                            sec_out: output
                        }
                    else:
                        scan_status = scan_pass_msg
                        conv.scan_retries = 0
                        conv.passed_security_scan = True
                        yield {
                            state: conv
                        }            
            history[-1][1] = history[-1][1].rstrip("▌")
    ret = {
        chatbot: history, 
        scan_stat: scan_status,
        sec_out:output
    }
    if not conv.passed_security_scan:
        ret[script] = code
    yield ret

def scan_fn(
    conv: gr.State, 
    history, 
    code, 
    scan_status, 
    exp_out, 
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    output = gr.Textbox(
        value="",
        label=sec_out_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True,
        lines=7,
        max_lines=7
    )
    if conv.conv_id != "":
        if code != "" and conv.scan_retries < max_security_scan_retries and not conv.passed_security_scan:
            data = json.dumps(
                {
                    "script": code,
                    "model_family": models_list[model]["model_family"], 
                    "model_name": models_list[model]["model_name"], 
                    "language": language,
                    "expected_output": exp_out,
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
                    lines=7,
                    max_lines=7
                )
                history.append(["Securit scan produced shown recommendations.", response["generated_text"]])
                code = response["script"]
                return {
                    state: conv,
                    chatbot: history,
                    sec_out: output, 
                    scan_stat: scan_fail_msg
                }
            else:
                conv.scan_retries = 0
                conv.passed_security_scan = True
                return {
                    state: conv,
                    scan_stat: scan_pass_msg,
                    sec_out: output
                }
    else:
        return {}

def execute_fn(
    conv: gr.State, 
    history, 
    code, 
    exp_out, 
    model, 
    language, 
    stream,
    temprature, 
    top_p, 
    top_k
):
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "expected_output": exp_out,
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
            lines=12,
            max_lines=12
        )
        history.append(["The script failed with shown error message", response["generated_text"]])
        code = response["script"]
    else:
        if response["output"] != exp_out:
            output = gr.Textbox(
                value=response["output"],
                label=output_wrn_msg, 
                elem_id="amber", 
                interactive=False, 
                show_copy_button=True, 
                lines=12,
                max_lines=12
            )
        else:
            output = gr.Textbox(
                value=response["output"],
                label=output_info_msg,
                elem_id="--primary-50",
                interactive=False,
                show_copy_button=True,
                lines=12,
                max_lines=12
            )
    images = []
    if "files" in json_obj:
        for file in json_obj["files"]:
            file_name, content = file.values()
            image_content = base64.b64decode(content)
            with open(os.path.join(files_path, file_name), "wb") as img:
                img.write(image_content)
            images.append(os.path.join(files_path, file_name))
    return [history, output, code, images] 

def execute_fn_with_stream(
    conv: gr.State, 
    history, 
    code, 
    exp_out, 
    model, 
    language,
    timeout,
    stream,
    temprature, 
    top_p, 
    top_k
):
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "expected_output": exp_out,
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
                    lines=12,
                    max_lines=12
                )
                if flag:
                    history.append(
                        [
                            "The script failed with shown error message",
                            # to avoid Gradio Markdown bug related to <output></output> bug
                            (
                                json_obj["generated_text"] + "▌"
                            ).replace(
                                out_tag[0], 
                                ex_out_tag[0]
                            ).replace(
                                out_tag[1], 
                                ex_out_tag[1]
                            )
                        ]
                    )
                    flag = False
                else:
                    history[-1][-1] = (
                        json_obj["generated_text"] + "▌"
                    ).replace(
                        out_tag[0], 
                        ex_out_tag[0]
                    ).replace(
                        out_tag[1], 
                        ex_out_tag[1]
                    )
                code = json_obj["script"]
            else:
                if json_obj["output"] != exp_out:
                    output = gr.Textbox(
                        value=json_obj["output"],
                        label=output_wrn_msg, 
                        elem_id="amber", 
                        interactive=False, 
                        show_copy_button=True, 
                        lines=12,
                        max_lines=12
                    )
                else:
                    output = gr.Textbox(
                        value=json_obj["output"],
                        label=output_info_msg, 
                        elem_id="--primary-50", 
                        interactive=False, 
                        show_copy_button=True,
                        lines=12,
                        max_lines=12
                    )
            yield [history, output, code, images]
    history[-1][1] = history[-1][1].rstrip("▌")
    yield history, output, code, images

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

    conv.passed_security_scan = False
    conv.scan_retries = 0
    data = json.dumps(
        {
            "prompt": history[-1][0],
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
                    script: "",
                    exp_out: ""
                }
                break
            # to avoid Gradio Markdown bug related to <output></output> bug
            history[-1][1] = (
                json_obj["generated_text"] + "▌"
            ).replace(
                out_tag[0], 
                ex_out_tag[0]
            ).replace(
                out_tag[1], 
                ex_out_tag[1]
            )
            conv.conv_id = json_obj.get("conv_id", "")
            yield {
                state: conv,
                chatbot: history
            }
    
    last_response = history[-1][1].rstrip("▌")
    
    history[-1][1] = last_response
    conv.conv_id = json_obj.get("conv_id", "")
    
    yield {
        state: conv,
        chatbot: history,
        script: json_obj.get("script",""),
        exp_out: json_obj.get("expected_output","")
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
    data = json.dumps(
        {
            "prompt": history[-1][0],
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
    history[-1][1] = json_obj["generated_text"]
    return [conv, history, res["script"], res["expected_output"]]

def save_fn(
    code,
    model,
    language,
    temprature, 
    top_p, 
    top_k
):
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
            "embedding_model_family": "bedrock", 
            "embedding_model_name": "amazon.titan-embed-text-v1"
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
        return gr.update(interactive=True)

    gr.Info(res)
    return gr.update(interactive=False)

def load_fn(
    prompt,
    model,
    language
):
    data = json.dumps(
        {
            "prompt": prompt,
            "language": language,
            "stream": False,
            "model_family": models_list[model]["model_family"],
            "model_name": models_list[model]["model_name"],
            "embedding_model_family": "bedrock", 
            "embedding_model_name": "amazon.titan-embed-text-v1",
            "threshold": 0.5
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
    
    if len(response["matches"]) > 0:
        ret = clear_fn()
        ret[0].passed_security_scan = True
        ret[2] = response["matches"][0]["code"]
        ret[1] = [[f'Load the following task:\n{response["matches"][0]["task_desc"]}', f"Task code:\n```{l_mapping[language]}\n{ret[2]}\n```"]]
        ret[8] = scan_pass_msg
    else:
        gr.Info("No matches found to load.")
    return ret + [""] + [scan_empty_msg]

def can_exec(conv, code):
    if code != "" and conv.passed_security_scan:
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
    return [ConvState(), []] + [gr.Code(value="", language=l_mapping[language], interactive=False)] + [""] * 2 + [[]]

def change_model():
    empty_folder()
    return [ConvState(), []] + [""] * 3 + [[]]

def clear_fn():
    empty_folder()
    return [ConvState(), [], "", ""] + [gr.Textbox(
        value="",
        label=output_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True, 
        lines=12, 
        max_lines=12
    )] + [[]] + [gr.Textbox(
        value="",
        label=sec_out_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True, 
        lines=7, 
        max_lines=7
    ), "", scan_empty_msg]

def vote(data: gr.LikeData, conv):
    if data.liked:
        print("You upvoted this response: " + data.value + conv.conv_id)
    else:
        print("You downvoted this response: " + data.value)   

def add_text(message, history):
    history += [[message, None]]
    return ["", history]

def web_ui():
    global state, chatbot, script, out, exp_out, scan_stat, sec_out

    theme = gr.themes.Default(
        neutral_hue="slate"
    )

    with gr.Blocks(css=css, theme=theme) as webUI:
        state = gr.State(ConvState())
        gr.Markdown(welcome_message)
        with gr.Row():
            with gr.Column(scale=8):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=4):
                        with gr.Group(elem_id="chatbot-group"):
                            with gr.Row():
                                chatbot = gr.Chatbot(elem_id="chatbot-window", show_copy_button=True, height=450)
                            with gr.Row():
                                textbox = gr.Textbox(
                                    show_label=False, 
                                    placeholder="Enter your prompt here and press ENTER", 
                                    container=False, 
                                    scale=16
                                )
                                submit = gr.Button(
                                    value="💬️", 
                                    variant="primary", 
                                    scale=2, 
                                    elem_id="chatbot-button"
                                )
                                clear_btn = gr.ClearButton(
                                    value="🗑️", 
                                    scale=1, 
                                    elem_id="chatbot-button"
                                )
                        out = gr.Textbox(value="",label=output_info_msg, interactive=False, show_copy_button=True, lines=12, max_lines=12)
                    with gr.Column(scale=3):
                        with gr.Group(elem_id="script-group"):
                            script = gr.Code(value="",label="Script", language = l_mapping[languages[0]], interactive=False, lines=16)
                            scan_stat = gr.Markdown(scan_empty_msg)
                            with gr.Row():
                                load_box = gr.Textbox(show_label=False, placeholder="Enter detailed task description to load.", scale=30, container=False)
                                load = gr.Button(variant="primary", value="Load", scale=1)
                                save = gr.Button(value="Save 💾️", interactive=False, scale=1)
                                execute = gr.Button(value="Execute", interactive=False, variant="primary", scale=1)
                        image = gr.Gallery(label="Image", show_download_button=True, preview=True, object_fit="fill", selected_index=0)

                with gr.Accordion(label="Other Outputs", open=False):
                    exp_out = gr.Textbox(value="",label="Expected Output", interactive=False, lines=7, max_lines=7)
                    sec_out = gr.Textbox(value="",label=sec_out_info_msg, interactive=False, lines=7, max_lines=7)
                    
            with gr.Column(scale=1):
                language = gr.Dropdown(languages,label='Langauge Selection', value=languages[0]) # Langauge Selection
                model = gr.Dropdown(models_list.keys(),label="Model Selection", value=list(models_list.keys())[0]) # Model Selection
                temprature = gr.Slider(label="Temprature", step=0.1, minimum=0, maximum=1, value=0.1)
                top_p = gr.Slider(label="Top_p", step=0.1, minimum=0, maximum=1, value=0.1)
                top_k = gr.Slider(label="Top_k", step=1, minimum=1, maximum=500, value=5)
                streaming = gr.Checkbox(label='Stream chat response', value=True)
                timeout = gr.Number(label="Execution Timeout", precision=0, minimum=10, maximum=3600, value=30)
                with gr.Accordion(label="Instructions:", open=False):
                    gr.Markdown(instructions)
            
        language.change(change_language, [language], [state, chatbot, script, out, exp_out, image], queue=False)
        model.change(change_model, None, [state, chatbot, script, out, exp_out, image], queue=False)
        gr.on(
            [submit.click, textbox.submit],
            add_text, 
            [textbox, chatbot], 
            [textbox, chatbot],
            show_progress=False,
            queue=False,
            trigger_mode="once"
        ).then(
            generate_response_with_stream if streaming.value else generate_response, 
            [state, chatbot, model, language, streaming, temprature, top_p, top_k], 
            [state, chatbot, script, exp_out],
            show_progress=False,
            queue=streaming.value
        )
        script.change(
        #     critique_fn_with_stream if streaming.value else critique_fn, 
        #     [state, chatbot, script, scan_stat, exp_out, model, language, streaming, temprature, top_p, top_k], 
        #     [state, chatbot, sec_out, script, scan_stat], queue=streaming,
        #     show_progress=False
        # ).then(
            scan_fn_with_stream if streaming.value else scan_fn, 
            [state, chatbot, script, scan_stat, exp_out, model, language, streaming, temprature, top_p, top_k], 
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
            [state, chatbot, script, exp_out, out, image, sec_out, load_box, scan_stat],
            show_progress=False,
            queue=False,
            trigger_mode="once"
        )
        execute.click(
            disable_exec,
            None,
            execute
        ).then(
            execute_fn_with_stream if streaming.value else execute_fn, 
            [state, chatbot, script, exp_out, model, language, timeout, streaming, temprature, top_p, top_k], 
            [chatbot, out, script, image],
            show_progress=False,
            queue=streaming,
            trigger_mode="once"
        )
        save.click(
            save_fn, 
            [script, model, language, temprature, top_p, top_k], 
            [save],
            show_progress=False,
            trigger_mode
        )
        gr.on(
            [load.click, load_box.sumbit],
            load_fn,
            [load_box, model, language],
            [state, chatbot, script, exp_out, out, image, sec_out, load_box, scan_stat]
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
    UI.queue(status_update_rate=10, api_open=False).launch(debug=False, max_threads=200)