
import os
from typing import List, Optional, Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain.tools import tool


class QianfanChatModel(BaseChatModel):
    def __init__(self, model_url: str, api_key: str, **kwargs):
        super().__init__()
        self._api_key = api_key 
        self._model_url = model_url

    @property
    def _llm_type(self) -> str:
        return "qianfan-chat"

    def _generate(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        qianfan_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                qianfan_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                qianfan_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                qianfan_messages.append({"role": "assistant", "content": msg.content})
            else:
                raise ValueError(f"Unsupported message type: {msg}")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "ernie-3.5-8k",
            "messages": qianfan_messages       
        }
        import requests
        response = requests.post(self._model_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        print(result)
        text = result['choices'][0]['message']['content'].strip()

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )


# 一个查询天气的简单函数
@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气"""
    return f"{city} 当前天气是 25°C，晴朗。"

# 创建 Tool 列表
tools = [get_weather]

model_url = "https://qianfan.baidubce.com/v2/chat/completions"
bce_api_key = os.environ['QIANFAN_API_KEY']

# 创建 LLM 对象（使用 gpt-3.5）
chat_model =QianfanChatModel(api_key=bce_api_key, model_url=model_url)

messages = [
    SystemMessage("Translate the following from English into Chinese"),
    HumanMessage("hi!"),
]

answer = chat_model.invoke(messages)
print(answer)
