from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI

# Load environment variables from .env
load_dotenv()

# Create a ChatOpenAI model
model = ChatOpenAI(model="gpt-4o")

# Define prompt template
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an expert product reviewer."),
        ("human", "List the main features of the product {product_name}."),
    ]
)


# Define pros analysis step
def analyze_pros(features):
    pros_template = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an expert product reviewer."),
            (
                "human",
                "Given these features: {features}, list the pros of these features.",
            ),
        ]
    )
    return pros_template.format_prompt(features=features)


# Define cons analysis step
def analyze_cons(features):
    cons_template = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an expert product reviewer."),
            (
                "human",
                "Given these features: {features}, list the cons of these features.",
            ),
        ]
    )
    return cons_template.format_prompt(features=features)


# Combine pros and cons into a final review
# Notice the arguments match the keys from the RunnableParallel dictionary below
def combine_pros_cons(input_dict):
    return f"Pros:\n{input_dict['pros']}\n\nCons:\n{input_dict['cons']}"


# Clean branches: Removed redundant RunnableLambda wrappers
pros_branch_chain = analyze_pros | model | StrOutputParser()
cons_branch_chain = analyze_cons | model | StrOutputParser()

# Create the combined chain using LangChain Expression Language (LCEL)
# Note: A standard Python dict maps directly to RunnableParallel execution
chain = (
    prompt_template
    | model
    | StrOutputParser()
    | {"pros": pros_branch_chain, "cons": cons_branch_chain}
    | combine_pros_cons
)

# Run the chain
result = chain.invoke({"product_name": "MacBook Pro"})

# Output
print(result)
