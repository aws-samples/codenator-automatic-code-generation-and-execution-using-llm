max_security_scan_retries = 6
css_app = """
/* Gradio app */
gradio-app{
 background-color:#eaeaea !important;
 background-image:url("https://images.unsplash.com/photo-1633174524827-db00a6b7bc74?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wzNTc5fDB8MXxzZWFyY2h8Mnx8YW1hem9ufGVufDB8fHx8MTcwMTc2MTE2Mnww&ixlib=rb-4.0.3&q=80&w=2560") !important;
}
/* Prose */
#main-banner .svelte-1ed2p3z .prose{
 transform:translatex(0px) translatey(0px);
}

/* Main banner */
#main-banner {
 color:white;
 background-color: #232F3E;
 border-top-left-radius:0px;
 border-top-right-radius:0px;
 border-bottom-left-radius:0px;
 border-bottom-right-radius:0px;
 padding-left:40px;
 padding-right:40px;
 padding-top:10px;
 padding-bottom:10px;
}
#red {background-color: #FA9F9D}
#amber {background-color: #FFD966}
#green {background-color: #2ECC71}
/* Gradio container */
gradio-app .gradio-container{
 max-width:90% !important;
 width:90% !important;
 transform:translatex(0px) translatey(0px);
 padding-top:0px !important;
}
"""
css_chatbot = """
/* Tab nav */
.contain .gap .tab-nav{
 background-color:#ecf0f1;
}
/* Tabitem */
.contain .gap .tabitem{
 background-color:#ffffff;
}
/* Chatbot window */
#chatbot-window{
 height:636px !important;
}

/* Text Area */
#chatbot-group .gap textarea{
 min-height:121px;
 max-height:121px;
}
"""
css_output = """
/* Min */
#script-group .styler .min{
 min-height:28px;
 height:28px;
 max-height:28px;
}
/* Tabitem */
.contain .gap .tabitem{
 height:779px;
 max-height:779px;
}

/* Script group */
#script-group{
 height:760px;
 max-height:760px;
}

/* Block */
#script-group .gap .block{
 min-width:4px !important;
 width:100% !important;
 height:123px;
}

/* Gap */
#script-group .styler .gap{
 min-width:4px !important;
}

/* Gap */
gradio-app .gradio-container .main .wrap .contain .gap .stretch .gap .tabs .tabitem .gap #script-group .styler .stretch .gap{
 width:408px !important;
}

/* Editor */
#script-group .wrap .cm-editor{
 height:580px;
}

/* Text Area */
#script-group .gap textarea{
 height:122px !important;
}

/* Unpadded box */
.contain .gap .unpadded_box{
 transform:translatex(0px) translatey(0px);
 height:527px;
}
/* Unpadded box */
#script-group .block .unpadded_box{
 height:579px;
 min-height:579px;
 max-height:579px;
}
"""
css = css_app + css_chatbot + css_output
welcome_message="""
<a href="https://aws.amazon.com/what-is-cloud-computing"><img style="color:white; background-color: #232F3E;float: right;" src="https://d0.awsstatic.com/logos/powered-by-aws-white.png" alt="Powered by AWS Cloud Computing"></a>
# <span style="color:white; background-color: #232F3E">Welcome to Codenator 🤖️</span>
### <span style="color:white; background-color: #232F3E">Allow me to help you develop secure and robust code</span>
"""
instructions="""
🤖️ **CODENATOR:** Is a *Genarative AI* solution that helps you generate code and execute it in a sandbox environment. It will perform security scan on every generated code then allows user to execute the script. It will also automatically fix issues with the generated script if it generates error after execution or if security scan generates recommendations.<br>
**How to use:**
* Interact with agent through chat to generate and modify code.<br>
* Only the First text you send will be used to devise a code structure.<br>
* Each time agent will generate code, the code will be scanned for security vulnerabilities.<br>
* If the code fails security scan it will be automatically sent back to agent to modify it. Code with security issues are not allowed to be executed.<br>
* Failed scan results will appear under **Security Scan Output**.<br>
* You can approve and execute scanned code. The output of that execution will show in the **Output** section.<br>
* If the execution resulted in an error, the **Output** section will be colored in red and feedback will be sent to agent. The agent will automatically try to generate new fixed code.<br>
* If code generates plots or animations, it will show under **Plots and Images** tab.<br>
* You can modify application parameters found in the **Parameters** tab.<br>
* **Script** tab will have latest script and allows you to save and load script using text prompt.
"""
output_err_msg = "Execution Output: ❌️ ERROR ❌️"
output_info_msg = "Execution Output:"
output_lines = 20
scan_fail_msg = "🔍️ Code Security scan status: ⛔️"
scan_pass_msg = "🔍️ Code Security scan status: ✅️"
scan_empty_msg = "🔍️ Code Security scan status: None"
sec_out_err_msg = "Security Scan Output: ❌️ ERROR ❌️"
sec_out_info_msg = "Security Scan Output:"
sec_out_pass_msg = "Security Scan Output: PASS"
sec_out_lines = 11
files_path = "tmp"
