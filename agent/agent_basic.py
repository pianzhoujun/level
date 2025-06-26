import os
import openai

bce_api_key = 'bce-v3/ALTAK-oCA20JUsptfsWIeUXLOXb/0517ee71cc56fcc52636cbcc86750e6fa62e616b'

openai.api_key = os.environ.get('OPENAI_API_KEY')

# 工具函数：模拟一个天气查询
def get_weather(city):
    return f"当前 {city} 的天气是 25°C，晴朗。"

def ask_llm(content):
    import requests
    url = "https://qianfan.baidubce.com/v2/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bce_api_key}"
    }
    data = {
        "model": "ernie-3.5-8k",
        "messages": [{"role": "user", "content": content}]
    }
    response = requests.post(url=url, headers=headers, json=data)
    return response.json()

# Agent 主体
def simple_agent(user_input):
    # 调用 OpenAI 接口理解用户意图
    prompt = f"""
你是一个智能助手，帮用户完成任务。
用户输入："{user_input}"
请判断用户想做什么，并用函数调用方式回应。例如：
- 如果用户问天气，调用 get_weather(city)
如果不理解，就回答"我不理解"。

只输出函数调用或一句话答案。
"""

    response = ask_llm(prompt)
    print(response)
    answer = response['choices'][0]['message']['content'].strip()
    # 简单执行：如果是调用 get_weather
    if answer.startswith("get_weather("):
        city = answer[len("get_weather("):-1].strip("'\" ")
        return get_weather(city)
    else:
        return answer

# 测试
while True:
    user_input = input("你想问什么？")
    print("Agent:", simple_agent(user_input))
