try:
    # load environment variables from .env file (requires `python-dotenv`)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# import getpass
# import os
#os.environ["LANGSMITH_TRACING"] = "true"
#if "LANGSMITH_API_KEY" not in os.environ:
#    os.environ["LANGSMITH_API_KEY"] = getpass.getpass(
#        prompt="Enter your LangSmith API key (optional): "
#    )
#if "LANGSMITH_PROJECT" not in os.environ:
#    os.environ["LANGSMITH_PROJECT"] = getpass.getpass(
#        prompt='Enter your LangSmith Project Name (default = "default"): '
#    )
#    if not os.environ.get("LANGSMITH_PROJECT"):
#        os.environ["LANGSMITH_PROJECT"] = "default"
#
#if not os.environ.get("OPENAI_API_KEY"):
#  os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")
#

# @part 1. Basic Chat Model
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

model = init_chat_model("ernie-4.0-8k-latest", model_provider="openai")
if False:
    messages = [
        SystemMessage("Translate the following from English into Italian"),
        HumanMessage("hi!"),
    ] 
    res = model.invoke(messages)
    print(res)

# part 2. Prompt Template
from langchain_core.prompts import ChatPromptTemplate
if False:
    system_template = "Translate the following from English into {language}"
    prompt_template = ChatPromptTemplate.from_messages(
        [("system", system_template), ("user", "{text}")]
    )
    
    prompt = prompt_template.invoke({"language": "Italian", "text": "hi!"})
    print(prompt)
    print(model.invoke(prompt))

# @part 3. Document Loader. 
if False:
    from langchain_community.document_loaders import PyPDFLoader
    file_path = "/Users/wangguosheng01/workspace/3_document/04_IBS/论文/botsort-2206.14651v2.pdf"
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    print(len(docs))
    print(f"{docs[0].page_content[:200]}\n")
    print(docs[0].metadata)

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, add_start_index=True
    )
    all_splits = text_splitter.split_documents(docs)
    len(all_splits)

    from langchain_community.embeddings import QianfanEmbeddingsEndpoint

# @part 4. end to end agent.
# Import relevant functionality
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Create the agent
memory = MemorySaver()
search = TavilySearch(max_results=2)
# search_results = search.invoke("What is the weather in SF")
# print(f"Search results: {search_results}\n")
tools = [search]

## @basic agent 
if False:
    agent_executor = create_react_agent(model, tools, checkpointer=memory)
    
    # Use the agent
    config = {"configurable": {"thread_id": "abc123"}}
    input_message = {
        "role": "user",
        "content": "Hi, I'm Bob and I life in SF.",
    }
    for step in agent_executor.stream(
        {"messages": [input_message]}, config, stream_mode="values"
    ):
        step["messages"][-1].pretty_print()
    
    
    input_message = {
        "role": "user",
        "content": "What's the weather where I live?",
    }
    for step in agent_executor.stream(
        {"messages": [input_message]}, config, stream_mode="values"
    ):
        step["messages"][-1].pretty_print()

## @add tool to model
if False:
    model_with_tools = model.bind_tools(tools)
    query = "Search for the weather in SF"
    # query = "Hi"
    response = model_with_tools.invoke([{"role": "user", "content": query}])

    print(f"Message content: {response.text()}\n")
    print(f"Tool calls: {response.tool_calls}")


agent_executor = create_react_agent(model, tools)

# agent_executor.get_graph().draw_mermaid_png(max_retries=5, retry_delay=2.0)
print(agent_executor.get_graph().draw_ascii())


input_message = {"role": "user", "content": "Hi!"}
for step in agent_executor.stream({"messages": [input_message]}, stream_mode="values"):
   step["messages"][-1].pretty_print()

input_message = {"role": "user", "content": "Search for the weather in SF"}
for step in agent_executor.stream({"messages": [input_message]}, stream_mode="values"):
   step["messages"][-1].pretty_print()
