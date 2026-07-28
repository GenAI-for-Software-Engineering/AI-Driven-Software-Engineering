import os
from dotenv import load_dotenv

# Modern hub client import
import langchain_classic as hub

# Modern core imports
from langchain_classic.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_core.prompts import MessagesPlaceholder
from langchain_openai import ChatOpenAI

# Memory has moved to langchain_community
from langchain_classic.memory import ConversationBufferMemory

# Load environment variables from .env file
load_dotenv()


# Define Tools
def get_current_time(*args, **kwargs):
    """Returns the current time in H:MM AM/PM format."""
    import datetime
    now = datetime.datetime.now()
    return now.strftime("%I:%M %p")


def search_wikipedia(query):
    """Searches Wikipedia and returns the summary of the first result."""
    from wikipedia import summary
    try:
        return summary(query, sentences=2)
    except:
        return "I couldn't find any information on that."


# Define the tools that the agent can use
tools = [
    Tool(
        name="Time",
        func=get_current_time,
        description="Useful for when you need to know the current time.",
    ),
    Tool(
        name="Wikipedia",
        func=search_wikipedia,
        description="Useful for when you need to know information about a topic.",
    ),
]

# Load the structured chat prompt from the official hub
base_prompt = hub.pull("hwchase17/structured-chat-agent")

# Modify the hub prompt to support chat history dynamically
# This injects a 'chat_history' placeholder right before the final human message turn
prompt = base_prompt.partial(
    chat_history=[]
)
if "chat_history" not in [v for v in prompt.input_variables]:
    # Ensure the prompt structural chain expects chat_history
    prompt.messages.insert(-1, MessagesPlaceholder(variable_name="chat_history"))

# Initialize ChatOpenAI model
llm = ChatOpenAI(model="gpt-4o")

# Create Conversation Buffer Memory
# The memory_key must match the MessagesPlaceholder variable name
memory = ConversationBufferMemory(
    memory_key="chat_history", 
    return_messages=True
)

# Seed the memory with your initial system context safely
initial_message = "You are an AI assistant that can provide helpful answers using available tools.\nIf you are unable to answer, you can use the following tools: Time and Wikipedia."
memory.chat_memory.add_message(SystemMessage(content=initial_message))

# Initialize the structured chat agent
agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)

# Initialize the executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    memory=memory,  # Executor automatically manages reading/writing history here
    handle_parsing_errors=True,
)

# Chat Loop to interact with the user
print("Start chatting with the AI! Type 'exit' to end the conversation.")
while True:
    user_input = input("\nUser: ")
    if user_input.lower() == "exit":
        break

    # REMOVED: manual memory.chat_memory.add_message(HumanMessage(...))
    # AgentExecutor handles adding the input to history automatically.
    
    # Invoke the agent executor
    response = agent_executor.invoke({"input": user_input})
    
    print("Bot:", response["output"])

    # AgentExecutor handles saving the output to history automatically.
