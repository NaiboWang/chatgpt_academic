import os; os.environ['no_proxy'] = '*' # 避免代理网络产生意外污染
import gradio as gr
from request_llm.bridge_chatgpt import predict
from toolbox import format_io, find_free_port, on_file_uploaded, on_report_generated, get_conf, ArgsGeneralWrapper, DummyWith

# 建议您复制一个config_private.py放自己的秘密, 如API和代理网址, 避免不小心传github被别人看到
proxies, WEB_PORT, LLM_MODEL, CONCURRENT_COUNT, AUTHENTICATION, CHATBOT_HEIGHT, LAYOUT = \
    get_conf('proxies', 'WEB_PORT', 'LLM_MODEL', 'CONCURRENT_COUNT', 'AUTHENTICATION', 'CHATBOT_HEIGHT', 'LAYOUT')

# 如果WEB_PORT是-1, 则随机选取WEB端口
PORT = find_free_port() if WEB_PORT <= 0 else WEB_PORT
if not AUTHENTICATION: AUTHENTICATION = None

from check_proxy import get_current_version
initial_prompt = "Serve me as a writing and programming assistant."
# title_html = f"<h1 align=\"center\">ChatGPT Academic For IDS students and staffs</h1><p style='text-align: center'>Dark theme is not friendly for display, so if you are in dark mode, we suggest you change to <a href='/?__dark-theme=false'>Light Theme</a>.</p>"
title_html = f"<h1 align=\"center\">ChatGPT Academic For IDS students and staffs</h1><p style='text-align: center; font-size:16px'>See the <a href='https://docs.google.com/document/d/1GvTj_j_f9kFRCDDAsKV2xiWG8tTS6Ey_/edit?usp=sharing&ouid=117207524901851213899&rtpof=true&sd=true' target='_blank'>Instruction Manual</a> here to use this tool.</p><p style='text-align: center; font-size:16px'>If you find any problems when using this tool, or you want to add more functions (such as more quick actions), please contact Naibo at: <a href='mailto:naibowang@comp.nus.edu.sg' target='_blank'>naibowang@comp.nus.edu.sg</a>.</p>"
description =  """代码开源和更新[地址🚀](https://github.com/binary-husky/chatgpt_academic)，感谢热情的[开发者们❤️](https://github.com/binary-husky/chatgpt_academic/graphs/contributors)"""

# 问询记录, python 版本建议3.9+（越新越好）
import logging
os.makedirs("gpt_log", exist_ok=True)
try:logging.basicConfig(filename="gpt_log/chat_secrets.log", level=logging.INFO, encoding="utf-8")
except:logging.basicConfig(filename="gpt_log/chat_secrets.log", level=logging.INFO)
print("所有问询记录将自动保存在本地目录./gpt_log/chat_secrets.log, 请注意自我隐私保护哦！")

# 一些普通功能模块
from core_functional import get_core_functions
functional = get_core_functions()
# print(functional)

# 高级函数插件
from crazy_functional import get_crazy_functions
crazy_fns = get_crazy_functions()

# 处理markdown文本格式的转变
gr.Chatbot.postprocess = format_io

# 做一些外观色彩上的调整
from theme import adjust_theme, advanced_css
set_theme = adjust_theme()

# 代理与自动更新
# from check_proxy import check_proxy, auto_update
# proxy_info = check_proxy(proxies)

gr_L1 = lambda: gr.Row(visible=False).style()
gr_L2 = lambda scale: gr.Column(scale=scale)
gr_login = lambda: gr.Row(visible=True).style()
if LAYOUT == "TOP-DOWN": 
    gr_L1 = lambda: DummyWith()
    gr_L2 = lambda scale: gr.Row()
    CHATBOT_HEIGHT /= 2

cancel_handles = []
js = """window.addEventListener('load', function () {
  gradioURL = window.location.href
  if (!gradioURL.endsWith('?__theme=light')) {
    window.location.replace(gradioURL + '?__theme=light');
  }
});"""

idd = ""

with gr.Blocks(title="ChatGPT Academic", theme=set_theme, analytics_enabled=False, css=advanced_css) as demo:
    identity = gr.State("anonymous")
    # def login(username, password):
    #     global idd, identity
    #     print("Inner: ", identity.value)
    #     if username == "ids" and password == "ids_gpt4":
    #         idd = username
    #         # identity = gr.State(idd)
    #         print("Changed: ", identity.value)
    #         return True
    #     return False
    def login(usr, password):
        with open("identity.txt", "r") as f:
            passwords = {}
            for line in f.readlines():
                id = line.strip().split(",")[0]
                pswd = line.strip().split(",")[1]
                passwords[pswd] = id
        # print(password, passwords)
        try:
            username = passwords[password]
            return {identity: username, hint: gr.update(visible=False), login_section: gr.update(visible=False), function_section: gr.update(visible=True), chatbot: [(f"Hello **{username}**, welcome to the demo of the **GPT-4** API. Please type your question in the input section.", "Hello, I am a GPT-4 model. I can answer your questions about programming, math, or can help you to do English academic writing improvement, translation between different languages, etc.")]}
        except:
            return {hint: gr.update(visible=True), identity: "anonymous", login_section: gr.update(visible=True), function_section: gr.update(visible=False)}
            
    print("identity:", identity.value)
    gr.HTML(title_html)
    demo.load(__js = js)
    with gr_L1() as function_section:
        with gr_L2(scale=2):
            chatbot = gr.Chatbot([("Welcome to the demo of the **GPT-4** API. Please type your question in the input section.", "Hello, I am a GPT-4 model. I can answer your questions about programming, math, or can help you to do English academic writing improvement, translation between different languages, etc.")])
            chatbot.style(height=CHATBOT_HEIGHT)
            history = gr.State([])
        with gr_L2(scale=1):
            with gr.Accordion("Input Section", open=True) as area_input_primary:
                with gr.Row():
                    txt = gr.Textbox(show_label=False, placeholder="Input question here.").style(container=False)
                with gr.Row():
                    submitBtn = gr.Button("Submit", variant="primary")
                with gr.Row():
                    resetBtn = gr.Button("Reset", variant="secondary");
                    # stopBtn = gr.Button("停止/Stop", variant="secondary"); stopBtn.style(size="sm")
                with gr.Row():
                    status = gr.Markdown(f"Tip: Press Enter to submit, press Shift+Enter to start a new line. Current model: {LLM_MODEL} \n")
            with gr.Accordion("Quick Actions (Will automatically reset the conversation when you click the buttons)", open=True) as area_basic_fn:
                with gr.Row():
                    for k in functional:
                        variant = functional[k]["Color"] if "Color" in functional[k] else "secondary"
                        functional[k]["Button"] = gr.Button(k, variant=variant)
            with gr.Accordion("函数插件区", open=True) as area_crazy_fn:
                with gr.Row():
                    gr.Markdown("注意：以下“红颜色”标识的函数插件需从输入区读取路径作为参数.")
                with gr.Row():
                    for k in crazy_fns:
                        if not crazy_fns[k].get("AsButton", True): continue
                        variant = crazy_fns[k]["Color"] if "Color" in crazy_fns[k] else "secondary"
                        crazy_fns[k]["Button"] = gr.Button(k, variant=variant)
                        crazy_fns[k]["Button"].style(size="sm")
                with gr.Row():
                    with gr.Accordion("更多函数插件", open=True):
                        dropdown_fn_list = [k for k in crazy_fns.keys() if not crazy_fns[k].get("AsButton", True)]
                        with gr.Column(scale=1):
                            dropdown = gr.Dropdown(dropdown_fn_list, value=r"打开插件列表", label="").style(container=False)
                        with gr.Column(scale=1):
                            switchy_bt = gr.Button(r"请先从插件列表中选择", variant="secondary")
                with gr.Row():
                    with gr.Accordion("点击展开“文件上传区”。上传本地文件可供红色函数插件调用。", open=False) as area_file_up:
                        file_upload = gr.Files(label="任何文件, 但推荐上传压缩文件(zip, tar)", file_count="multiple")
            with gr.Accordion("展开SysPrompt & 交互界面布局 & Github地址", open=(LAYOUT == "TOP-DOWN")):
                system_prompt = gr.Textbox(show_label=True, placeholder=f"System Prompt", label="System prompt", value=initial_prompt)
                top_p = gr.Slider(minimum=-0, maximum=1.0, value=1.0, step=0.01,interactive=True, label="Top-p (nucleus sampling)",)
                temperature = gr.Slider(minimum=-0, maximum=2.0, value=1.0, step=0.01, interactive=True, label="Temperature",)
                checkboxes = gr.CheckboxGroup(["Quick Actions (Will automatically reset the conversation when you click the buttons)", "函数插件区", "底部输入区"], value=["Quick Actions (Will automatically reset the conversation when you click the buttons)", "函数插件区"], label="显示/隐藏功能区")
                gr.Markdown(description)
            with gr.Accordion("备选输入区", open=True, visible=False) as area_input_secondary:
                with gr.Row():
                    txt2 = gr.Textbox(show_label=False, placeholder="Input question here.", label="输入区2").style(container=False)
                with gr.Row():
                    submitBtn2 = gr.Button("Submit", variant="primary")
                with gr.Row():
                    resetBtn2 = gr.Button("Reset", variant="secondary"); resetBtn.style(size="sm")
                    stopBtn2 = gr.Button("停止/Stop", variant="secondary");
    
    with gr.Row() as login_section:
        with gr.Column(scale=0.3, min_width=500):
            with gr.Row():
                hint = gr.Label("Incorrect username or password.", visible = False)
            with gr.Row():
                username = gr.Textbox(value = "ids", show_label=False, placeholder="Username")
            with gr.Row():
                password = gr.Textbox(show_label=False, placeholder="Password", type="password")
            with gr.Row():
                login_btn = gr.Button("Login", variant="primary")
            with gr.Row():
                img = gr.Image("hint.png")
            login_btn.click(fn = login, inputs = [username, password], outputs = [identity, hint, login_section, function_section, chatbot])
            username.submit(fn = login, inputs = [username, password], outputs = [identity, hint, login_section, function_section, chatbot])
            password.submit(fn = login, inputs = [username, password], outputs = [identity, hint, login_section, function_section, chatbot])
    # 功能区显示开关与功能区的互动
    def fn_area_visibility(a):
        ret = {}
        ret.update({area_basic_fn: gr.update(visible=("Quick Actions (Will automatically reset the conversation when you click the buttons)" in a))})
        ret.update({area_crazy_fn: gr.update(visible=("函数插件区" in a))})
        ret.update({area_input_primary: gr.update(visible=("底部输入区" not in a))})
        ret.update({area_input_secondary: gr.update(visible=("底部输入区" in a))})
        if "底部输入区" in a: ret.update({txt: gr.update(value="")})
        return ret
    checkboxes.select(fn_area_visibility, [checkboxes], [area_basic_fn, area_crazy_fn, area_input_primary, area_input_secondary, txt, txt2] )
    # 整理反复出现的控件句柄组合
    input_combo = [txt, txt2, top_p, temperature, chatbot, history, system_prompt]
    # 身份确认
    output_combo = [chatbot, history, status, identity]

    predict_args = dict(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True), gr.State(None), identity], outputs=output_combo)
    # 提交按钮、重置按钮
    cancel_handles.append(txt.submit(**predict_args))
    cancel_handles.append(txt2.submit(**predict_args))
    cancel_handles.append(submitBtn.click(**predict_args))
    cancel_handles.append(submitBtn2.click(**predict_args))
    resetBtn.click(lambda identity: ([], [], "Already Reset", identity), [identity], output_combo)
    # resetBtn2.click(lambda: ([], [], "Already Reset", identity.value), None, output_combo)
    # 基础功能区的回调函数注册
    for k in functional:
        click_handle = functional[k]["Button"].click(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True), gr.State(k), identity], outputs=output_combo)
        cancel_handles.append(click_handle)
    # 文件上传区，接收文件后与chatbot的互动
    file_upload.upload(on_file_uploaded, [file_upload, chatbot, txt], [chatbot, txt])
    # 函数插件-固定按钮区
    for k in crazy_fns:
        if not crazy_fns[k].get("AsButton", True): continue
        click_handle = crazy_fns[k]["Button"].click(ArgsGeneralWrapper(crazy_fns[k]["Function"]), [*input_combo, gr.State(PORT)], output_combo)
        click_handle.then(on_report_generated, [file_upload, chatbot], [file_upload, chatbot])
        cancel_handles.append(click_handle)
    # 函数插件-下拉菜单与随变按钮的互动
    def on_dropdown_changed(k):
        variant = crazy_fns[k]["Color"] if "Color" in crazy_fns[k] else "secondary"
        return {switchy_bt: gr.update(value=k, variant=variant)}
    dropdown.select(on_dropdown_changed, [dropdown], [switchy_bt] )
    # 随变按钮的回调函数注册
    def route(k, *args, **kwargs):
        if k in [r"打开插件列表", r"请先从插件列表中选择"]: return 
        yield from ArgsGeneralWrapper(crazy_fns[k]["Function"])(*args, **kwargs)
    click_handle = switchy_bt.click(route,[switchy_bt, *input_combo, gr.State(PORT)], output_combo)
    click_handle.then(on_report_generated, [file_upload, chatbot], [file_upload, chatbot])
    # def expand_file_area(file_upload, area_file_up):
    #     if len(file_upload)>0: return {area_file_up: gr.update(open=True)}
    # click_handle.then(expand_file_area, [file_upload, area_file_up], [area_file_up])
    cancel_handles.append(click_handle)
    # 终止按钮的回调函数注册
    # stopBtn.click(fn=None, inputs=None, outputs=None, cancels=cancel_handles)
    stopBtn2.click(fn=None, inputs=None, outputs=None, cancels=cancel_handles)
    
# gradio的inbrowser触发不太稳定，回滚代码到原始的浏览器打开函数
def auto_opentab_delay():
    import threading, webbrowser, time
    print(f"如果浏览器没有自动打开，请复制并转到以下URL：")
    print(f"\t（亮色主题）: http://localhost:{PORT}")
    print(f"\t（暗色主题）: http://localhost:{PORT}/?__dark-theme=true")
    def open(): 
        time.sleep(2)       # 打开浏览器
        webbrowser.open_new_tab(f"http://localhost:{PORT}/?__dark-theme=true")
    threading.Thread(target=open, name="open-browser", daemon=True).start()
    threading.Thread(target=auto_update, name="self-upgrade", daemon=True).start()


# auto_opentab_delay()

demo.queue(concurrency_count=CONCURRENT_COUNT).launch(server_name="0.0.0.0", share=True, server_port=PORT)
