from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool, Tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent  # Modern native agent harness

# Functions for the tools
def greet_user(name: str) -> str:
    """Greets the user by name."""
    return f"Hello, {name}!"


def reverse_string(text: str) -> str:
    """Reverses the given string."""
    return text[::-1]


def concatenate_strings(a: str, b: str) -> str:
    """Concatenates two strings."""
    return a + b


# Native Pydantic v2 model for complex tool arguments
class ConcatenateStringsArgs(BaseModel):
    a: str = Field(description="First string")
    b: str = Field(description="Second string")


# Define tools using standard constructors
tools = [
    Tool(
        name="GreetUser",
        func=greet_user,
        description="Greets the user by name.",
    ),
    Tool(
        name="ReverseString",
        func=reverse_string,
        description="Reverses the given string.",
    ),
    StructuredTool.from_function(
        func=concatenate_strings,
        name="ConcatenateStrings",
        description="Concatenates two strings.",
        args_schema=ConcatenateStringsArgs,
    ),
]

# Initialize ChatOpenAI using the modern connection string pattern 
# or by passing an initialized chat model directly
agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    system_prompt="You are a helpful assistant. Use your tools whenever appropriate.",
)

# Test the agent with sample queries
# The modern harness expects the conversation history under the "messages" key
queries = [
    "Greet Alice",
    "Reverse the string 'hello'",
    "Concatenate 'hello' and 'world'"
]

for query in queries:
    print(f"\n--- Executing Query: '{query}' ---")
    response = agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    
    # Extract response blocks from the final message turn cleanly
    final_message = response["messages"][-1]
    print("Response:", final_message.content)
