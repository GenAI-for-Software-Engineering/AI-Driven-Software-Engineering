from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnablePassthrough
from langchain_openai import ChatOpenAI

# Load environment variables from .env
load_dotenv()

# Create a ChatOpenAI model
model = ChatOpenAI(model="gpt-4o")

# Define prompt templates for different feedback types
positive_feedback_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        ("human", "Generate a thank you note for this positive feedback: {feedback}."),
    ]
)

negative_feedback_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        ("human", "Generate a response addressing this negative feedback: {feedback}."),
    ]
)

neutral_feedback_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        ("human", "Generate a request for more details for this neutral feedback: {feedback}."),
    ]
)

escalate_feedback_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        ("human", "Generate a message to escalate this feedback to a human agent: {feedback}."),
    ]
)

# Define the feedback classification template
classification_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Output only the category name in lowercase: positive, negative, neutral, or escalate."),
        ("human", "Classify the sentiment of this feedback: {feedback}."),
    ]
)

# Define the runnable branches for handling feedback
# Now 'x' contains a dictionary: {"sentiment": ..., "feedback": ...}
branches = RunnableBranch(
    (
        lambda x: "positive" in x["sentiment"].lower(),
        positive_feedback_template | model | StrOutputParser()
    ),
    (
        lambda x: "negative" in x["sentiment"].lower(),
        negative_feedback_template | model | StrOutputParser()
    ),
    (
        lambda x: "neutral" in x["sentiment"].lower(),
        neutral_feedback_template | model | StrOutputParser()
    ),
    escalate_feedback_template | model | StrOutputParser()
)

# Create the classification chain
classification_chain = classification_template | model | StrOutputParser()

# Combine classification and response generation into one chain
# RunnablePassthrough() keeps the original data structure intact
chain = (
    {"sentiment": classification_chain, "feedback": RunnablePassthrough.assign()}
    | branches
)

# Run the chain with an example review
review = "The product is terrible. It broke after just one use and the quality is very poor."
result = chain.invoke({"feedback": review})

# Output the result
print(result)
