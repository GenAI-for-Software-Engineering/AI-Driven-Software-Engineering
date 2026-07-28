# LangChain Crash Course

Welcome to the LangChain Crash Course repository. This project contains hands-on Python examples for learning LangChain from the ground up, including chat models, prompt templates, chains, retrieval-augmented generation (RAG), and agents.

## What You Will Learn

By working through this repository, you will learn how to:

- interact with large language models such as OpenAI, Anthropic, and Google Gemini
- build and customize prompt templates
- compose multi-step workflows with chains
- implement RAG pipelines over local documents and web content
- create agents and connect them to tools

## Course Outline

1. Setup Environment
2. Chat Models
3. Prompt Templates
4. Chains
5. RAG (Retrieval-Augmented Generation)
6. Agents & Tools

## Prerequisites

Before you begin, make sure you have:

- Python 3.10 or 3.11
- Poetry installed on your system
- API keys for the services you want to use, such as OpenAI, Anthropic, Google, Firecrawl, and Tavily

## Installation

1. Clone the repository:

   ```bash
   git clone <your-repo-url>
   cd langchain-crash-course
   ```

2. Install the project dependencies:

   ```bash
   poetry install --no-root
   ```

3. Create your environment file:

   ```bash
   cp .env.example .env
   ```

   Then update the values in `.env` with your own API keys.

4. Activate the Poetry environment:

   ```bash
   poetry shell
   ```

5. Run an example:

   ```bash
   poetry run python 1_chat_models/1_chat_model_basic.py
   ```

## Repository Structure

### 1. Chat Models

- `1_chat_model_basic.py`
- `2_chat_model_basic_conversation.py`
- `3_chat_model_alternatives.py`
- `4_chat_model_conversation_with_user.py`
- `5_chat_model_save_message_history_firebase.py`

Learn how to connect to chat models and manage conversations.

### 2. Prompt Templates

- `1_prompt_template_basic.py`
- `2_prompt_template_with_chat_model.py`

Understand how to structure reusable prompts for LLM applications.

### 3. Chains

- `1_chains_basics.py`
- `2_chains_under_the_hood.py`
- `3_chains_extended.py`
- `4_chains_parallel.py`
- `5_chains_branching.py`

Explore how LangChain chains combine prompts, models, and logic into workflows.

### 4. RAG (Retrieval-Augmented Generation)

- `1a_rag_basics.py`
- `1b_rag_basics.py`
- `2a_rag_basics_metadata.py`
- `2b_rag_basics_metadata.py`
- `3_rag_text_splitting_deep_dive.py`
- `4_rag_embedding_deep_dive.py`
- `5_rag_retriever_deep_dive.py`
- `6_rag_one_off_question.py`
- `7_rag_conversational.py`
- `8_rag_web_scrape_basic.py`
- `8_rag_web_scrape_firecrawl.py`

See how documents, embeddings, and vector stores are used to build question-answering systems.

### 5. Agents & Tools

- `1_agent_and_tools_basics.py`
- `agent_deep_dive/`
  - `1_agent_react_chat.py`
  - `2_agent_react_docstore.py`
- `tools_deep_dive/`
  - `1_tool_constructor.py`
  - `2_tool_decorator.py`
  - `3_tool_base_tool.py`

Learn how agents reason over tools and external capabilities.

## Environment Variables

The repository includes an `.env.example` file with commonly used keys:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `FIRECRAWL_API_KEY`
- `TAVILY_API_KEY`

Copy it to `.env` and fill in the values you need.

## How to Use This Repository

1. Follow the course modules in order.
2. Run the example scripts locally to see the concepts in action.
3. Experiment by changing prompts, models, and documents.
4. Join the community or open an issue if you get stuck.

## FAQ

### What is LangChain?

LangChain is a framework for building applications that use large language models in structured, production-friendly ways.

### How do I set up my environment?

Install the dependencies with Poetry, copy `.env.example` to `.env`, and add your API keys before running the scripts.

### Why are some examples missing API keys?

Some examples require specific providers or tools. If a provider is not needed for a particular script, you can leave that key empty.

### Can I contribute?

Yes. Contributions are welcome. Please open an issue or submit a pull request with your changes.



