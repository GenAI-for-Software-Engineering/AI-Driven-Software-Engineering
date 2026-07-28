from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent  # Modern native agent harness

# Simple Tool with one parameter without args_schema
@tool()
def greet_user(name: str) -> str:
    """Greets the user by name."""
    return f"Hello, {name}!"


# Pydantic models for tool arguments
class ReverseStringArgs(BaseModel):
    text: str = Field(description="Text to be reversed")


# Tool with One Parameter using args_schema
@tool(args_schema=ReverseStringArgs)
def reverse_string(text: str) -> str:
    """Reverses the given string."""
    return text[::-1]


# Another Pydantic model for tool arguments
class ConcatenateStringsArgs(BaseModel):
    a: str = Field(description="First string")
    b: str = Field(description="Second string")


# Tool with Two Parameters using args_schema
@tool(args_schema=ConcatenateStringsArgs)
def concatenate_strings(a: str, b: str) -> str:
    """Concatenates two strings."""
    print("Executing tool with inputs - a:", a, "b:", b)
    return a + b


# Create tools using the @tool decorator
tools = [
    greet_user,
    reverse_string,
    concatenate_strings,
]

# Initialize a modern ChatAgent instance using the unified harness
# This internalizes state tracking and runtime loop execution
agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    system_prompt="You are a helpful assistant. Use your tools whenever appropriate.",
)

# Test the agent with sample queries
# The modern harness processes structured turns under the "messages" array
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
    
    # Extract the final AI generation cleanly from the response messages
    final_message = response["messages"][-1]
    print("Response:", final_message.content)
