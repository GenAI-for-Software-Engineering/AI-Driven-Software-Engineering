import os
import chromadb
from dotenv import load_dotenv

# Modern helper chain imports
from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# Modern core imports
import langchain_classic as hub
from langchain_chroma import Chroma
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Load environment variables from .env file
load_dotenv()

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(current_dir, "..", "..", "4_rag", "db")
persistent_directory = os.path.join(db_dir, "chroma_db_with_metadata")

# Check if the Chroma vector store already exists
if not os.path.exists(persistent_directory):
    raise FileNotFoundError(
        f"The directory {persistent_directory} does not exist. Please check the path."
    )

# Define the embedding model
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize modern Chroma persistent client to connect to your existing DB
persistent_client = chromadb.PersistentClient(path=persistent_directory)

# Load the existing vector store with the embedding function
db = Chroma(
    client=persistent_client,
    embedding_function=embeddings
)

# Create a retriever for querying the vector store
retriever = db.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3},
)

# Create a ChatOpenAI model
llm = ChatOpenAI(model="gpt-4o")

# Contextualize question prompt
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, just "
    "reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Create a history-aware retriever
history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)

# Answer question prompt
qa_system_prompt = (
    "You are an assistant for question-answering tasks. Use "
    "the following pieces of retrieved context to answer the "
    "question. If you don't know the answer, just say that you "
    "don't know. Use three sentences maximum and keep the answer "
    "concise."
    "\n\n"
    "{context}"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Create a chain to combine documents for question answering
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

# Create a retrieval chain that combines the history-aware retriever and the question answering chain
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)


# Define Tool
# We scope the lambda to forward the current runtime session context correctly
def answer_question_tool(tool_input: str) -> str:
    # Resolves internal history directly from our loop state tracking variable
    result = rag_chain.invoke({"input": tool_input, "chat_history": chat_history})
    return result["answer"]

tools = [
    Tool(
        name="Answer_Question", # ReAct names should avoid space characters for syntax stability
        func=answer_question_tool,
        description="useful for when you need to answer questions about the context documents",
    )
]

# Pull a modern chat-ready ReAct prompt that supports historical messages
react_chat_prompt = hub.pull("hwchase17/react-chat")

# Create the ReAct Agent
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=react_chat_prompt,
)

# Initialize Agent Executor
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    handle_parsing_errors=True, 
    verbose=True,
)

# Chat loop variables
chat_history = []
print("Start chatting with the AI! Type 'exit' to end the conversation.")

while True:
    query = input("\nYou: ")
    if query.lower() == "exit":
        break
        
    # Execute the conversational agent
    response = agent_executor.invoke(
        {
            "input": query, 
            "chat_history": chat_history
        }
    )
    
    print(f"AI: {response['output']}")

    # Update history with clean context pairs
    chat_history.append(HumanMessage(content=query))
    chat_history.append(AIMessage(content=response["output"]))
