import os
from typing import Type
from pydantic import BaseModel, Field  # Native Pydantic v2 setup
from dotenv import load_dotenv
from langchain_core.tools import BaseTool, ArgsSchema
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent  # Modern native agent harness

load_dotenv()

# Pydantic models for tool arguments (Updated to Pydantic v2)
class SimpleSearchInput(BaseModel):
    query: str = Field(description="should be a search query")


class MultiplyNumbersArgs(BaseModel):
    x: float = Field(description="First number to multiply")
    y: float = Field(description="Second number to multiply")


# Custom tool with only custom input
class SimpleSearchTool(BaseTool):
    # Ensure fields map accurately under Pydantic v2 inheritance constraints
    name: str = "simple_search"
    description: str = "useful for when you need to answer questions about current events"
    args_schema: ArgsSchema | None = SimpleSearchInput

    def _run(self, query: str) -> str:
        """Use the tool."""
        from tavily import TavilyClient

        api_key = os.getenv("TAVILY_API_KEY")
        client = TavilyClient(api_key=api_key)
        results = client.search(query=query)
        return f"Search results for: {query}\n\n\n{results}\n"


# Custom tool with custom input and output
class MultiplyNumbersTool(BaseTool):
    name: str = "multiply_numbers"
    description: str = "useful for multiplying two numbers"
    args_schema: ArgsSchema | None = MultiplyNumbersArgs

    def _run(self, x: float, y: float) -> str:
        """Use the tool."""
        result = x * y
        return f"The product of {x} and {y} is {result}"


# Create tools using the Pydantic subclass approach
tools = [
    SimpleSearchTool(),
    MultiplyNumbersTool(),
]

# Initialize a modern ChatAgent instance using the unified harness
agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    system_prompt="You are a helpful assistant. Use your tools whenever appropriate.",
)

# Test the agent with sample queries
queries = [
    "Search for Apple Intelligence",
    "Multiply 10 and 20"
]

for query in queries:
    print(f"\n--- Executing Query: '{query}' ---")
    response = agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    
    # Extract response blocks cleanly from the final execution turn
    final_message = response["messages"][-1]
    print("Response:", final_message.content)
