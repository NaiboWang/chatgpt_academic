import os; os.environ['no_proxy'] = '*' # 避免代理网络产生意外污染
import gradio as gr
from request_llm.bridge_chatgpt import predict
from toolbox import format_io, find_free_port, on_file_uploaded, on_report_generated, ArgsGeneralWrapper, DummyWith
from functools import wraps, lru_cache
import importlib

@lru_cache(maxsize=128)
def read_single_conf_with_lru_cache(arg):
    try:
        r = getattr(importlib.import_module('config_private_naibo'), arg)
    except:
        r = getattr(importlib.import_module('config'), arg)
    # 在读取API_KEY时，检查一下是不是忘了改config
    if arg == 'API_KEY':
        # 正确的 API_KEY 是 "sk-" + 48 位大小写字母数字的组合
        API_MATCH = re.match(r"sk-[a-zA-Z0-9]{48}$", r)
        if API_MATCH:
            print(f"[API_KEY] 您的 API_KEY 是: {r[:15]}*** API_KEY 导入成功")
        else:
            assert False, "正确的 API_KEY 是 'sk-' + '48 位大小写字母数字' 的组合，请在config文件中修改API密钥, 添加海外代理之后再运行。" + \
                "（如果您刚更新过代码，请确保旧版config_private文件中没有遗留任何新增键值）"
    if arg == 'proxies':
        if r is None:
            print('[PROXY] 网络代理状态：未配置。无代理状态下很可能无法访问。建议：检查USE_PROXY选项是否修改。')
        else:
            print('[PROXY] 网络代理状态：已配置。配置信息如下：', r)
            assert isinstance(r, dict), 'proxies格式错误，请注意proxies选项的格式，不要遗漏括号。'
    return r


def get_conf(*args):
    # 建议您复制一个config_private.py放自己的秘密, 如API和代理网址, 避免不小心传github被别人看到
    res = []
    for arg in args:
        r = read_single_conf_with_lru_cache(arg)
        res.append(r)
    return res

# 建议您复制一个config_private.py放自己的秘密, 如API和代理网址, 避免不小心传github被别人看到
proxies, WEB_PORT, LLM_MODEL, CONCURRENT_COUNT, AUTHENTICATION, CHATBOT_HEIGHT, LAYOUT = \
    get_conf('proxies', 'WEB_PORT', 'LLM_MODEL', 'CONCURRENT_COUNT', 'AUTHENTICATION', 'CHATBOT_HEIGHT', 'LAYOUT')

# 如果WEB_PORT是-1, 则随机选取WEB端口
PORT = find_free_port() if WEB_PORT <= 0 else WEB_PORT
if not AUTHENTICATION: AUTHENTICATION = None

from check_proxy import get_current_version
initial_prompt = "Serve me as a writing and programming assistant."
# title_html = f"<h1 align=\"center\">ChatGPT Academic For IDS students and staffs</h1><p style='text-align: center'>Dark theme is not friendly for display, so if you are in dark mode, we suggest you change to <a href='/?__dark-theme=false'>Light Theme</a>.</p>"
title_html = f"<h1 align=\"center\">ChatGPT Academic For Naibo Wang</h1>"
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

# 高级函数插件
from crazy_functional import get_crazy_functions
crazy_fns = get_crazy_functions()

# 处理markdown文本格式的转变
gr.Chatbot.postprocess = format_io

# 做一些外观色彩上的调整
from theme_naibo import adjust_theme, advanced_css
set_theme = adjust_theme()

# 代理与自动更新
from check_proxy import check_proxy, auto_update
proxy_info = check_proxy(proxies)

gr_L1 = lambda: gr.Row().style()
gr_L2 = lambda scale: gr.Column(scale=scale)
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

with gr.Blocks(title="ChatGPT Academic", theme=set_theme, analytics_enabled=False, css=advanced_css) as demo:
    gr.HTML(title_html)
    demo.load(__js = js)
    with gr_L1():
        with gr_L2(scale=2):
            chatbot = gr.Chatbot()
            chatbot.style(height=CHATBOT_HEIGHT)
            history = gr.State([])
        with gr_L2(scale=1):
            with gr.Accordion("Input Section", open=True) as area_input_primary:
                with gr.Row():
                    txt = gr.Textbox(show_label=False, placeholder="Input question here.").style(container=False)
                with gr.Row():
                    submitBtn = gr.Button("提交/Submit", variant="primary")
                with gr.Row():
                    resetBtn = gr.Button("重置/Reset", variant="secondary");
                    # stopBtn = gr.Button("停止/Stop", variant="secondary"); stopBtn.style(size="sm")
                with gr.Row():
                    status = gr.Markdown(f"Tip: Press Enter to submit, press Shift+Enter to start a new line. Current model: {LLM_MODEL} \n {proxy_info}")
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
                    submitBtn2 = gr.Button("提交/Submit", variant="primary")
                with gr.Row():
                    resetBtn2 = gr.Button("重置/Reset", variant="secondary"); resetBtn.style(size="sm")
                    stopBtn2 = gr.Button("停止/Stop", variant="secondary");
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
    output_combo = [chatbot, history, status]
    predict_args = dict(fn=ArgsGeneralWrapper(predict), inputs=input_combo, outputs=output_combo)
    # 提交按钮、重置按钮
    cancel_handles.append(txt.submit(**predict_args))
    cancel_handles.append(txt2.submit(**predict_args))
    cancel_handles.append(submitBtn.click(**predict_args))
    cancel_handles.append(submitBtn2.click(**predict_args))
    resetBtn.click(lambda: ([], [], "Already Reset"), None, output_combo)
    resetBtn2.click(lambda: ([], [], "Already Reset"), None, output_combo)
    # 基础功能区的回调函数注册
    for k in functional:
        click_handle = functional[k]["Button"].click(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True), gr.State(k)], outputs=output_combo)
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

demo.queue(concurrency_count=CONCURRENT_COUNT).launch(server_name="0.0.0.0", share=True, server_port=PORT, auth=AUTHENTICATION)
