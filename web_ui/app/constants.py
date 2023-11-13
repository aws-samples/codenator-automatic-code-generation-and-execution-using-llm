controller_url = "internal-codenator-899847730.us-west-2.elb.amazonaws.com" + ":8012"

l_mapping = {
    "Bash":"shell", 
    "Python":"python", 
    "Java":"javascript",
    "JavaScript":"javascript", 
    "R":"r"
}
models_list = {
    "Claude-v2": {
        "model_family": "bedrock",
        "model_name": "anthropic.claude-v2"
    },
    "Claude-v1": {
        "model_family": "bedrock",
        "model_name": "anthropic.claude-v1"
    },
    "CodeLlama7b": {
        "model_family": "sagemaker",
        "model_name": "tgi.code-llama-endpoint"
    },
    "CodeLlama13b-instruct": {
        "model_family": "sagemaker",
        "model_name": "tgi.code-llama-13b-instruct-endpoint"
    }
}

out_tag = ["<output>", "/output>"]
ex_out_tag = ["<expected_output>", "/expected_output>"]
max_security_scan_retries = 3

css = """
#red {background-color: #FA9F9D}
#amber {background-color: #FFD966}
/* Wrap */
#script-group .styler .block > .wrap{
 max-height:457px;
}
/* Script group */
#script-group{
 min-height:643px;
}

/* Unpadded box */
#script-group .block .unpadded_box{
 min-height:457px;
 height:457px;
}
/* Svelte 1ed2p3z */
#script-group .styler .svelte-1ed2p3z{
 max-height:28px;
}
.codemirror-wrapper .cm-editor .cm-scroller{
 min-height:457px;
}
"""
welcome_message="""
# Welcome to Codenator 🤖️
### Use this tool to generate and test code using LLMs
"""
output_err_msg = "Output: ❌️ ERROR ❌️"
output_wrn_msg = "Output: ⚠️ WARNING ⚠️ value does not match `Expected Output`"
output_info_msg = "Output:"
scan_fail_msg = "🔍️ Code Security scan status: ⛔️"
scan_pass_msg = "🔍️ Code Security scan status: ✅️"
scan_empty_msg = "🔍️ Code Security scan status: None"
sec_out_err_msg = "Security Scan Output: ❌️ ERROR ❌️"
sec_out_info_msg = "Security Scan Output:"