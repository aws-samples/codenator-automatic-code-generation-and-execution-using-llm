import gradio as gr
import requests
import json
from constants import (
    controller_url,
    l_mapping,
    models_list,
    out_tag,
    ex_out_tag,
    max_security_scan_retries,
    css,
    welcome_message,
    output_err_msg,
    output_wrn_msg,
    output_info_msg,
    scan_fail_msg,
    scan_pass_msg,
    scan_empty_msg,
    sec_out_err_msg,
    sec_out_info_msg
)

# Global

class ConvState:
    def __init__(self):
        self.conv_id = ""
        self.passed_security_scan = False
        self.scan_retries = 0

def scan_fn_with_stream(conv: gr.State, history, code, scan_status, exp_out, model, language, stream):
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
                    "stream": stream
                }
            )
            response = requests.post(
                "http://" + controller_url + "/scan",
                data=data,
                stream=stream
            )
            flag = True
            for chunk in response.iter_lines():
                json_obj = json.loads(chunk)
                if json_obj["vulnerabilities"] and len(json_obj["vulnerabilities"]) > 0:
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
            history[-1][1] = history[-1][1][:-1]
    ret = {
        chatbot: history, 
        scan_stat: scan_status,
        sec_out:output
    }
    if not conv.passed_security_scan:
        ret[script] = code
    yield ret

def scan_fn(conv: gr.State, history, code, scan_status, exp_out, model, language, stream):
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
                    "stream": stream
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

def execute_fn(conv: gr.State, history, code, exp_out, model, language, stream):
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "expected_output": exp_out,
            "conv_id": conv.conv_id,
            "stream": stream
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
            lines=15,
            max_lines=15
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
                lines=15,
                max_lines=15
            )
        else:
            output = gr.Textbox(
                value=response["output"],
                label=output_info_msg,
                elem_id="--primary-50",
                interactive=False,
                show_copy_button=True,
                lines=15,
                max_lines=15
            )
    return [history, output, code] 

def execute_fn_with_stream(conv: gr.State, history, code, exp_out, model, language, stream):
    data = json.dumps(
        {
            "script": code,
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "expected_output": exp_out,
            "conv_id": conv.conv_id,
            "stream": stream
        }
    )
    response = requests.post(
        "http://" + controller_url + "/execute",
        data=data,
        stream=stream
    )
    flag = True
    for chunk in response.iter_lines():
        json_obj = json.loads(chunk)
        if json_obj["error"]:
            output = gr.Textbox(
                value=json_obj["output"],
                label=output_err_msg,
                elem_id="red",
                lines=15,
                max_lines=15
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
                    lines=15,
                    max_lines=15
                )
            else:
                output = gr.Textbox(
                    value=json_obj["output"],
                    label=output_info_msg, 
                    elem_id="--primary-50", 
                    interactive=False, 
                    show_copy_button=True,
                    lines=15,
                    max_lines=15
                )
        yield [history, output, code]
    history[-1][1] = history[-1][1][:-1]
    yield history, output, code

def can_exec(conv, code):
    if code != "" and conv.passed_security_scan:
        return gr.Button(value="Approve and Execute", interactive=True)
    else:
        return gr.Button(value="Approve and Execute", interactive=False)

    
def change_language(language):
    """
    Code Languages
    approved language: [('python', 'markdown', 'json', 'html', 'css', 'javascript', 'typescript', 'yaml', 'dockerfile', 'shell', 'r')]
    """
    return [ConvState(), []] + [gr.Code(value="", language=l_mapping[language], interactive=False)] + [""] * 2

def change_model():
    return [ConvState(), []] + [""] * 3

def clear_fn():
    return [ConvState(), [], "", ""] + [gr.Textbox(
        value="",
        label=output_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True, 
        lines=15, 
        max_lines=15
    )] + [gr.Textbox(
        value="",
        label=sec_out_info_msg, 
        elem_id="--primary-50", 
        interactive=False, 
        show_copy_button=True, 
        lines=7, 
        max_lines=7
    )]

def vote(data: gr.LikeData):
    if data.liked:
        print("You upvoted this response: " + data.value)
    else:
        print("You downvoted this response: " + data.value)   

def add_text(message, history):
    history += [[message, None]]
    return ["", history]

def generate_response_with_stream(conv: gr.State, history, model, language, stream): 
    """
    Sample Response - to be deleted
    """
    conv.passed_security_scan = False
    conv.scan_retries = 0
    data = json.dumps(
        {
            "prompt": history[-1][0],
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "conv_id": conv.conv_id,
            "stream": stream
        }
    )
    response = requests.post(
        "http://" + controller_url + "/generate",
        data=data,
        stream=stream
    )
    
    for chunk in response.iter_lines():
        json_obj = json.loads(chunk)
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
        conv.conv_id = json_obj["conv_id"]
        yield {
            state: conv,
            chatbot: history
        }
    
    last_response = history[-1][1][:-1]
    
    history[-1][1] = last_response
    conv.conv_id = json_obj["conv_id"]
    
    yield {
        state: conv,
        chatbot: history,
        script: json_obj["script"],
        exp_out: json_obj["expected_output"]
    }

def generate_response(conv: gr.State, history, model, language, stream): 
    """
    Sample Response - to be deleted
    """
    conv.passed_security_scan = False
    conv.scan_retries = 0
    data = json.dumps(
        {
            "prompt": history[-1][0],
            "model_family": models_list[model]["model_family"], 
            "model_name": models_list[model]["model_name"], 
            "language": language,
            "conv_id": conv.conv_id,
            "stream": stream
        }
    )
    response = requests.post(
            "http://" + controller_url + "/generate",
            data=data
        )

    res = json.loads(response.text)["generated_text"]
    conv.conv_id = res["conv_id"]
    history[-1][1] = json_obj["generated_text"]
    return [conv, history, res["script"], res["expected_output"]]


def web_ui():
    global state, chatbot, script, out, exp_out, scan_stat, sec_out
    with gr.Blocks(css=css, theme=gr.themes.Base(neutral_hue="slate")) as webUI:
        state = gr.State(ConvState())
        gr.Markdown(welcome_message)
        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                with gr.Group(elem_id="chatbot-group"):
                    with gr.Row():
                        chatbot = gr.Chatbot(elem_id="chatbot-window", height=600)
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
            with gr.Column(scale=3):
                with gr.Group(elem_id="script-group"):
                    with gr.Row():
                        language = gr.Dropdown(languages,label='Langauge Selection', value=languages[0]) # Langauge Selection
                        model = gr.Dropdown(models_list.keys(),label="Model Selection", value=list(models_list.keys())[0]) # Model Selection
                    scan_stat = gr.Markdown(scan_empty_msg)
                    script = gr.Code(value="",label="Script", language = l_mapping[languages[0]], interactive=False, lines=16)
                    execute = gr.Button(value="Approve and Execute", interactive=False)
        out = gr.Textbox(value="",label=output_info_msg, interactive=False, show_copy_button=True, lines=15, max_lines=15)
        with gr.Accordion(label="Other Outputs", open=False):
            exp_out = gr.Textbox(value="",label="Expected Output", interactive=False, lines=7, max_lines=7)
            sec_out = gr.Textbox(value="",label=sec_out_info_msg, interactive=False, lines=7, max_lines=7)
        with gr.Accordion(label="Parameters", open=False):
            streaming = gr.Checkbox(label='Stream chat response', value=True)
            timeout = gr.Number(label="Timeout", precision=0, minimum=10, maximum=300, value=10)
            
        language.change(change_language, [language], [state, chatbot, script, out, exp_out], queue=False)
        model.change(change_model, None, [state, chatbot, script, out, exp_out], queue=False)
        gr.on(
            [submit.click, textbox.submit],
            add_text, 
            [textbox, chatbot], 
            [textbox, chatbot],
            show_progress=False,
            queue=False
        ).then(
            generate_response_with_stream if streaming.value else generate_response, 
            [state, chatbot, model, language, streaming], 
            [state, chatbot, script, exp_out],
            show_progress=False,
            queue=streaming.value
        )
        script.change(
            scan_fn_with_stream if streaming.value else scan_fn, 
            [state, chatbot, script, scan_stat, exp_out, model, language, streaming], 
            [state, chatbot, sec_out, script, scan_stat], queue=streaming,
            show_progress=False
        ).then(
            can_exec, 
            [state, script], 
            [execute],
            show_progress=False,
            queue=False
        )
        
        clear_btn.click(
            clear_fn, 
            None, 
            [state, chatbot, script, exp_out, out, sec_out],
            show_progress=False,
            queue=False
        )
        execute.click(
            execute_fn_with_stream if streaming.value else execute_fn, 
            [state, chatbot, script, exp_out, model, language, streaming], 
            [chatbot, out, script],
            show_progress=False,
            queue=streaming
        )
        chatbot.like(
            vote, 
            None, 
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
    UI.queue(status_update_rate=10, api_open=False).launch(debug=True, max_threads=200)

    # create events, when chaning model/language selection, it will clear the chat history, scirpt, expected output and output