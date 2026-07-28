import os
import chromadb
from dotenv import load_dotenv

# Modern package for text splitting
from langchain_text_splitters import CharacterTextSplitter 
from langchain_community.document_loaders import FireCrawlLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Load environment variables from .env
load_dotenv()

# Define the persistent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(current_dir, "db")
persistent_directory = os.path.join(db_dir, "chroma_db_firecrawl")


def create_vector_store(persistent_client):
    """Crawl the website, split the content, create embeddings, and persist the vector store."""
    # Define the Firecrawl API key
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY environment variable not set")

    # Step 1: Crawl the website using FireCrawlLoader
    print("Begin crawling the website...")
    loader = FireCrawlLoader(
        api_key=api_key, url="https://apple.com", mode="scrape")
    docs = loader.load()
    print("Finished crawling the website.")

    # Convert metadata values to strings if they are lists
    for doc in docs:
        for key, value in doc.metadata.items():
            if isinstance(value, list):
                doc.metadata[key] = ", ".join(map(str, value))

    # Step 2: Split the crawled content into chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    split_docs = text_splitter.split_documents(docs)

    # Display information about the split documents
    print("\n--- Document Chunks Information ---")
    print(f"Number of document chunks: {len(split_docs)}")
    if split_docs:
        print(f"Sample chunk:\n{split_docs[0].page_content}\n")

    # Step 3: Create embeddings for the document chunks
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Step 4: Create and persist the vector store with the embeddings via client
    print(f"\n--- Creating vector store in {persistent_directory} ---")
    Chroma.from_documents(
        documents=split_docs, 
        embedding=embeddings, 
        client=persistent_client
    )
    print(f"--- Finished creating vector store in {persistent_directory} ---")


# Initialize a modern Chroma persistent client 
chroma_client = chromadb.PersistentClient(path=persistent_directory)

# Check if the Chroma vector store already exists
if not os.path.exists(persistent_directory):
    create_vector_store(chroma_client)
else:
    print(f"Vector store {persistent_directory} already exists. No need to initialize.")

# Load the vector store with the embeddings using the shared persistent client
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
db = Chroma(
    client=chroma_client,
    embedding_function=embeddings
)


# Step 5: Query the vector store
def query_vector_store(query):
    """Query the vector store with the specified question."""
    # Create a retriever for querying the vector store
    retriever = db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )

    # Retrieve relevant documents based on the query
    relevant_docs = retriever.invoke(query)

    # Display the relevant results with metadata
    print("\n--- Relevant Documents ---")
    for i, doc in enumerate(relevant_docs, 1):
        print(f"Document {i}:\n{doc.page_content}\n")
        if doc.metadata:
            print(f"Source: {doc.metadata.get('source', 'Unknown')}\n")


# Define the user's question
query = "Apple Intelligence?"

# Query the vector store with the user's question
query_vector_store(query)
