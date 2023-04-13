# 借鉴了 https://github.com/GaiZhenbiao/ChuanhuChatGPT 项目

"""
    该文件中主要包含三个函数

    不具备多线程能力的函数：
    1. predict: 正常对话时使用，具备完备的交互功能，不可多线程

    具备多线程调用能力的函数
    2. predict_no_ui：高级实验性功能模块调用，不会实时显示在界面上，参数简单，可以多线程并行，方便实现复杂的功能逻辑
    3. predict_no_ui_long_connection：在实验过程中发现调用predict_no_ui处理长文档时，和openai的连接容易断掉，这个函数用stream的方式解决这个问题，同样支持多线程
"""

import json
import time
import gradio as gr
import logging
import traceback
import requests
import importlib
import datetime, os

# config_private.py放自己的秘密如API和代理网址
# 读取时首先看是否存在私密的config_private配置文件（不受git管控），如果有，则覆盖原config文件
from toolbox import get_conf
proxies, API_URL, API_KEY, TIMEOUT_SECONDS, MAX_RETRY, LLM_MODEL = \
    get_conf('proxies', 'API_URL', 'API_KEY', 'TIMEOUT_SECONDS', 'MAX_RETRY', 'LLM_MODEL')

timeout_bot_msg = '[Local Message] Request timeout. Network error. Please check proxy settings in config.py.' + \
                  '网络错误，检查代理服务器是否可用，以及代理设置的格式是否正确，格式须是[协议]://[地址]:[端口]，缺一不可。'

def get_full_error(chunk, stream_response):
    """
        获取完整的从Openai返回的报错
    """
    while True:
        try:
            chunk += next(stream_response)
        except:
            break
    return chunk

def predict_no_ui(inputs, top_p, temperature, history=[], sys_prompt=""):
    """
        发送至chatGPT，等待回复，一次性完成，不显示中间过程。
        predict函数的简化版。
        用于payload比较大的情况，或者用于实现多线、带嵌套的复杂功能。

        inputs 是本次问询的输入
        top_p, temperature是chatGPT的内部调优参数
        history 是之前的对话列表
        （注意无论是inputs还是history，内容太长了都会触发token数量溢出的错误，然后raise ConnectionAbortedError）
    """
    headers, payload = generate_payload(inputs, top_p, temperature, history, system_prompt=sys_prompt, stream=False)

    retry = 0
    while True:
        try:
            # make a POST request to the API endpoint, stream=False
            response = requests.post(API_URL, headers=headers, proxies=proxies,
                                    json=payload, stream=False, timeout=TIMEOUT_SECONDS*2); break
        except requests.exceptions.ReadTimeout as e:
            retry += 1
            traceback.print_exc()
            if retry > MAX_RETRY: raise TimeoutError
            if MAX_RETRY!=0: print(f'请求超时，正在重试 ({retry}/{MAX_RETRY}) ……')

    try:
        result = json.loads(response.text)["choices"][0]["message"]["content"]
        return result
    except Exception as e:
        if "choices" not in response.text: print(response.text)
        raise ConnectionAbortedError("Json解析不合常规，可能是文本过长" + response.text)


def predict_no_ui_long_connection(inputs, top_p, temperature, history=[], sys_prompt="", observe_window=None):
    """
        发送至chatGPT，等待回复，一次性完成，不显示中间过程。但内部用stream的方法避免中途网线被掐。
        inputs：
            是本次问询的输入
        sys_prompt:
            系统静默prompt
        top_p, temperature：
            chatGPT的内部调优参数
        history：
            是之前的对话列表
        observe_window = None：
            用于负责跨越线程传递已经输出的部分，大部分时候仅仅为了fancy的视觉效果，留空即可。observe_window[0]：观测窗。observe_window[1]：看门狗
    """
    watch_dog_patience = 5 # 看门狗的耐心, 设置5秒即可
    headers, payload = generate_payload(inputs, top_p, temperature, history, system_prompt=sys_prompt, stream=True)
    retry = 0
    while True:
        try:
            # make a POST request to the API endpoint, stream=False
            response = requests.post(API_URL, headers=headers, proxies=proxies,
                                    json=payload, stream=True, timeout=TIMEOUT_SECONDS); break
        except requests.exceptions.ReadTimeout as e:
            retry += 1
            traceback.print_exc()
            if retry > MAX_RETRY: raise TimeoutError
            if MAX_RETRY!=0: print(f'请求超时，正在重试 ({retry}/{MAX_RETRY}) ……')

    stream_response =  response.iter_lines()
    result = ''
    while True:
        try: chunk = next(stream_response).decode()
        except StopIteration: 
            break
        except requests.exceptions.ConnectionError:
            chunk = next(stream_response).decode() # 失败了，重试一次？再失败就没办法了。
        if len(chunk)==0: continue
        if not chunk.startswith('data:'): 
            error_msg = get_full_error(chunk.encode('utf8'), stream_response).decode()
            if "reduce the length" in error_msg:
                raise ConnectionAbortedError("OpenAI拒绝了请求:" + error_msg)
            else:
                raise RuntimeError("OpenAI拒绝了请求：" + error_msg)
        json_data = json.loads(chunk.lstrip('data:'))['choices'][0]
        delta = json_data["delta"]
        if len(delta) == 0: break
        if "role" in delta: continue
        if "content" in delta: 
            result += delta["content"]
            print(delta["content"], end='')
            if observe_window is not None: 
                # 观测窗，把已经获取的数据显示出去
                if len(observe_window) >= 1: observe_window[0] += delta["content"]
                # 看门狗，如果超过期限没有喂狗，则终止
                if len(observe_window) >= 2:  
                    if (time.time()-observe_window[1]) > watch_dog_patience:
                        raise RuntimeError("程序终止。")
        else: raise RuntimeError("意外Json结构："+delta)
    if json_data['finish_reason'] == 'length':
        raise ConnectionAbortedError("正常结束，但显示Token不足，导致输出不完整，请削减单次输入的文本量。")
    return result

def calculate_cost(identity = "anonymous"):
    with open("total.txt", "r") as f:
        total = float(f.read())
    total_cost = 0.0
    user_cost = 0.0
    with open("bill.txt", "r") as f:
        for line in f.readlines():
            try:
                prompt_tokens, completion_tokens, _, username = line.strip().split(",")
            except:
                prompt_tokens, completion_tokens, _ = line.strip().split(",")
                username = "ids"
            total_cost += int(prompt_tokens) * 0.03 * 0.001 + int(completion_tokens) * 0.06 * 0.001
            if username.replace(" ","").lower() == identity.lower():
                    user_cost += int(prompt_tokens) * 0.03 * 0.001 + int(completion_tokens) * 0.06 * 0.001
    remaining = total - total_cost
    print(f"total: {total}, total_cost: {total_cost}, remaining: {remaining}, user_cost: {user_cost}")
    return total, total_cost, remaining, user_cost

def predict(inputs, top_p, temperature, chatbot=[], history=[], system_prompt='', 
            stream = True, additional_fn=None, identity = ["anonymous"]):
    """
        发送至chatGPT，流式获取输出。
        用于基础的对话功能。
        inputs 是本次问询的输入
        top_p, temperature是chatGPT的内部调优参数
        history 是之前的对话列表（注意无论是inputs还是history，内容太长了都会触发token数量溢出的错误）
        chatbot 为WebUI中显示的对话列表，修改它，然后yeild出去，可以直接修改对话界面内容
        additional_fn代表点击的哪个按钮，按钮见functional.py
    """
    if len(chatbot) >= 1 and chatbot[0][1].find("Hello, I am a GPT-4 model. I can answer your questions") != -1:
        chatbot.pop(0) # 去掉初始的欢迎语

    print(identity)
    
    if identity == "anonymous":
        print("Invalid identity")
        yield chatbot, history, "Sorry, the password is wrong.", identity
        return            
        
    

    total, total_cost, remaining, user_cost = calculate_cost(identity)
    if remaining < 0.01:
        chatbot[-1] = ((chatbot[-1][0], "Sorry, our balance is not enough this month, the service will be suspended."))
        yield chatbot, history, "Not enough balance, the service will be suspended."
        return

    if len(history) // 2 >= 5:
        if inputs.find("I am Naibo: ") == -1:
            print("I'm not Naibo:")
            chatbot[-1] = ((chatbot[-1][0], "Sorry, the service is suspended because the number of communication rounds exceeds the limit, please reset the conversation and start a new session."))
            yield chatbot, history, "The service is suspended because the number of communication rounds exceeds the limit.", identity
            return
        else:
            print("I'm Naibo:")
            inputs = inputs.replace("I am Naibo: ", "")

    if additional_fn is not None:
        import core_functional
        importlib.reload(core_functional)    # 热更新prompt
        core_functional = core_functional.get_core_functions()
        if "PreProcess" in core_functional[additional_fn]: inputs = core_functional[additional_fn]["PreProcess"](inputs)  # 获取预处理函数（如果有的话）
        inputs = core_functional[additional_fn]["Prefix"] + inputs + core_functional[additional_fn]["Suffix"]
        chatbot = [] # clear before use
        history = [] # clear before use


    if stream:
        raw_input = inputs
        logging.info(f'[raw_input] {raw_input}')
        chatbot.append((inputs, "Waiting for OpenAI's response, please wait. Maybe you should wait for 1 minute or more when the response is long, so don't close this window."))
        yield chatbot, history, "Waiting...", identity

    headers, payload = generate_payload(inputs, top_p, temperature, history, system_prompt, stream=False, identity=identity)
    history.append(inputs); history.append(" ")

    retry = 0

    
    while True:
        try:
            # make a POST request to the API endpoint, stream=True
            response = requests.post(API_URL, headers=headers, proxies=proxies,
                                    json=payload, stream=True, timeout=TIMEOUT_SECONDS);
            # print(response.text)
            filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f') + '_response_'+identity+'.json'
            with open("logs/" + filename, 'w') as f:
                f.write(response.text)
            break
        except:
            retry += 1
            chatbot[-1] = ((chatbot[-1][0], timeout_bot_msg))
            retry_msg = f"，正在重试 ({retry}/{MAX_RETRY}) ……" if MAX_RETRY > 0 else ""
            yield chatbot, history, "请求超时"+retry_msg, identity
            if retry > MAX_RETRY: raise TimeoutError

    


    try:
        gpt_replying_buffer = json.loads(response.text)['choices'][0]['message']["content"]
        usage = json.loads(response.text)["usage"]["prompt_tokens"] * 0.03 * 0.001 + json.loads(response.text)["usage"]["completion_tokens"] * 0.06 * 0.001
        # gpt_replying_buffer +=  "\n\n-------\n\n" + f"This time of conversation you spend {usage:.7f} US Dollars, please note。\n\n-------"
        history[-1] = gpt_replying_buffer
        prompt_tokens = json.loads(response.text)["usage"]["prompt_tokens"]
        completion_tokens = json.loads(response.text)["usage"]["completion_tokens"]

        hint = ""
        multi_round = ""
        with open("bill.txt", "a") as f:
            time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S-%f')
            f.write(f"{prompt_tokens}, {completion_tokens}, {time_now}, {identity} \n")
        total, total_cost, remaining, user_cost = calculate_cost(identity)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')} : {identity}'s Response : {gpt_replying_buffer} \n")
        with open("infos/" + "plain_text_" + today + ".txt", 'a') as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')} : {identity}'s Response : {gpt_replying_buffer} \n")
            
        if len(history) // 2 > 1:
            multi_round = " **including your pervious "+ str(len(history) // 2 - 1) +" round(s) of questions and answers**"
        hint += " \n Here is the detail of usage for this time of conversation:  \n\n  1. You send " + str(prompt_tokens) + f" prompt tokens (your input to ChatGPT, 0.03 USD/1K tokens)"+ multi_round + f", which cost {float(prompt_tokens) * 0.03 * 0.001: .5f} USD.  \n   2. You receive " + str(completion_tokens) + f" completion tokens (output from ChatGPT, 0.06 USD/1K tokens), which cost  {float(completion_tokens) * 0.06 * 0.001:.5f} USD. \n\n  You should note that as long as the conversation content is not cleared, the previous questions and answers will be used as input for the next API call, resulting in increased cost with more rounds of conversation. Therefore, ** please try to avoid generating multiple rounds of conversation.** If you have a new question, please ** click the reset button first ** to start a new conversation. \n\n However, you don't need to artificially click the reset button before you use the buttons in the ** Quick Actions ** area, such as English Academic Writing Improvement, we will automatically reset the conversation every time you click them."

        chatbot[-1] = (history[-2], history[-1])
        chatbot.append((f"This time you spend **${usage:.5f}**,  you have used **${user_cost:.4f}** in total, the remaining credit for whole IDS: **${remaining:.4f}/${total},** please note.", hint))
        # chatbot.append(("", hint))
        if len(history) // 2 >= 3:
            chatbot.append((f"This is already your {len(history) // 2}-th round of conversation, ** too many rounds will bring huge cost, ** please note.", "** You cannot ask questions for more than 5 rounds. ** If you want to start a new conversation, please ** click the reset button ** to start a new conversation. Most of cases, we don't need to generate multiple rounds of conversation, such as English Academic Writing Improvement, because we don't need the previous conversation context when we want to rephrase a new sentences."))
    except:
        chatbot[-1] = ((chatbot[-1][0], "Error, please retry:" + json.loads(response.text)['error']["message"]))

    yield chatbot, history, None, identity
    is_head_of_the_stream = True
    
    stream = False # 不再使用数据流
    if stream:
        stream_response =  response.iter_lines()
        while True:
            chunk = next(stream_response)
            # print(chunk.decode()[6:])
            if is_head_of_the_stream:
                # 数据流的第一帧不携带content
                is_head_of_the_stream = False; continue
            
            if chunk:
                try:
                    # print(chunk.decode())
                    if len(json.loads(chunk.decode()[6:])['choices'][0]["delta"]) == 0:
                        # 判定为数据流的结束，gpt_replying_buffer也写完了
                        logging.info(f'[response] {gpt_replying_buffer}')
                        break
                    # 处理数据流的主体
                    chunkjson = json.loads(chunk.decode()[6:])
                    # print("chunkjson:", chunkjson)
                    status_text = f"finish_reason: {chunkjson['choices'][0]['finish_reason']}"
                    # 如果这里抛出异常，一般是文本过长，详情见get_full_error的输出
                    gpt_replying_buffer = gpt_replying_buffer + json.loads(chunk.decode()[6:])['choices'][0]["delta"]["content"]
                    history[-1] = gpt_replying_buffer
                    chatbot[-1] = (history[-2], history[-1])
                    yield chatbot, history, status_text, identity

                except Exception as e:
                    traceback.print_exc()
                    yield chatbot, history, "Json解析不合常规", identity
                    chunk = get_full_error(chunk, stream_response)
                    error_msg = chunk.decode()
                    if "reduce the length" in error_msg:
                        chatbot[-1] = (chatbot[-1][0], "[Local Message] Reduce the length. 本次输入过长，或历史数据过长. 历史缓存数据现已释放，您可以请再次尝试.")
                        history = []    # 清除历史
                    elif "Incorrect API key" in error_msg:
                        chatbot[-1] = (chatbot[-1][0], "[Local Message] Incorrect API key. OpenAI以提供了不正确的API_KEY为由，拒绝服务.")
                    elif "exceeded your current quota" in error_msg:
                        chatbot[-1] = (chatbot[-1][0], "[Local Message] You exceeded your current quota. OpenAI以账户额度不足为由，拒绝服务.")
                    else:
                        from toolbox import regular_txt_to_markdown
                        tb_str = '```\n' + traceback.format_exc() + '```'
                        chatbot[-1] = (chatbot[-1][0], f"[Local Message] 异常 \n\n{tb_str} \n\n{regular_txt_to_markdown(chunk.decode()[4:])}")
                    yield chatbot, history, "Json异常" + error_msg, identity
                    return

def generate_payload(inputs, top_p, temperature, history, system_prompt, stream, identity):
    """
        整合所有信息，选择LLM模型，生成http请求，为发送请求做准备
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    conversation_cnt = len(history) // 2

    messages = [{"role": "system", "content": system_prompt}]
    if conversation_cnt:
        for index in range(0, 2*conversation_cnt, 2):
            what_i_have_asked = {}
            what_i_have_asked["role"] = "user"
            what_i_have_asked["content"] = history[index]
            what_gpt_answer = {}
            what_gpt_answer["role"] = "assistant"
            what_gpt_answer["content"] = history[index+1]
            if what_i_have_asked["content"] != "":
                if what_gpt_answer["content"] == "": continue
                if what_gpt_answer["content"] == timeout_bot_msg: continue
                messages.append(what_i_have_asked)
                messages.append(what_gpt_answer)
            else:
                messages[-1]['content'] = what_gpt_answer['content']

    what_i_ask_now = {}
    what_i_ask_now["role"] = "user"
    what_i_ask_now["content"] = inputs
    messages.append(what_i_ask_now)

    payload = {
        "model": LLM_MODEL,
        "messages": messages, 
        "temperature": temperature,  # 1.0,
        "top_p": top_p,  # 1.0,
        "n": 1,
        "stream": stream,
        "presence_penalty": 0,
        "frequency_penalty": 0,
    }
    
    print(f" {datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')} : {identity} {LLM_MODEL} : {conversation_cnt} : {inputs}")
    # print(payload)
    filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f') + '_query_'+identity+'.json'
    if not os.path.exists("logs"):
        os.mkdir("logs")
    if not os.path.exists("infos"):
        os.mkdir("infos")
    with open("logs/" + filename, 'w') as f:
        json.dump(payload, f)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    with open("infos/" + "plain_text_" + today + ".txt", 'a') as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')}: {identity} : {LLM_MODEL} : {conversation_cnt} : {inputs}\n")

    return headers,payload


