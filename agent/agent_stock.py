
try:
    # load environment variables from .env file (requires `python-dotenv`)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool

import baostock as bs
import pandas as pd


@tool
def search_stock_data(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定股票在指定时间段内的历史K线数据。

    Args:
        code (str): 股票代码。
        start_date (str): 查询开始日期，格式为YYYY-MM-DD。
        end_date (str): 查询结束日期，格式为YYYY-MM-DD。

    Returns:
        pd.DataFrame: 包含股票历史K线数据的DataFrame，包含日期、开盘价、最高价、最低价、收盘价、成交量、成交额和复权因子等列。

    Raises:
        Exception: 如果查询出错，抛出异常，异常信息为错误信息。
    """
    bs_api = bs.login()
    rs = bs.query_history_k_data_plus(code,
        "date,code,open,high,low,close,volume,amount,adjustflag",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3")

    if rs.error_code != "0":
        print("error code: ", rs.error_code)
        bs_api.close()
        raise Exception(rs.error_msg)

    # 获取具体的信息
    result_list = []
    while (rs.error_code == '0') & rs.next():
        # 分页查询，将每页信息合并在一起
        result_list.append(rs.get_row_data())
    result = pd.DataFrame(result_list, columns=rs.fields)
    result['date'] = pd.to_datetime(result['date'])
    result['open'] = pd.to_numeric(result['open'])
    result['high'] = pd.to_numeric(result['high'])
    result['low'] = pd.to_numeric(result['low'])
    result['close'] = pd.to_numeric(result['close'])
    result['volume'] = pd.to_numeric(result['volume'])
    result['amount'] = pd.to_numeric(result['amount'])
    bs_api.close()
    return result


# Create the agent
model = init_chat_model("ernie-4.0-8k-latest", model_provider="openai")
agent = create_react_agent(
    model,
    [search_stock_data],
    checkpointer=MemorySaver()
)


from langchain_core.messages import HumanMessage, SystemMessage
config = {"configurable": {"thread_id": "abc123"}}
input_messages = [
    SystemMessage("你是桥水基金创始人, 瑞·达利欧。根据用户输入的股票数据, 就算sma和macd数据，结合交易量，预测未来股价走势"),
    HumanMessage("股票代号是: sz.000858"),
    HumanMessage("股票代号是: sz.000858. 上一次发生金叉是什么时候，并且当时的MACD值是多少, 当时买入以后最多持有21天的收益率是多少"),
    HumanMessage("计算每次发生金叉买入, 死叉的时候卖出，最多持有21天正收益的概率。"),
]

for step in agent.stream(
    {"messages": input_messages}, config, stream_mode="values"
):
    step["messages"][-1].pretty_print()
    
 
