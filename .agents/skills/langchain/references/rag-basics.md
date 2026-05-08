---
name: rag-basics
description: LangChain RAG (Retrieval Augmented Generation) basics for knowledge-based QA
---

# RAG Basics

> RAG (Retrieval Augmented Generation) combines LLMs with external knowledge retrieval for accurate, up-to-date answers.

**Official Docs**: https://docs.langchain.com/oss/python/langchain/rag

## Core Concept

RAG workflow:
1. **Index**: Process and store documents in a vector database
2. **Retrieve**: Find relevant documents for a query
3. **Generate**: Use retrieved context to generate accurate answers

## Basic RAG Pipeline

### Simple RAG

```python
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

loader = TextLoader("documents/knowledge.txt")
documents = loader.load()

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(texts, embeddings)

retriever = vectorstore.as_retriever()

llm = ChatOpenAI(model="gpt-4")

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever
)

result = qa.run("What is the main topic?")
```

## Document Loading

### Text Files

```python
from langchain_community.document_loaders import TextLoader

loader = TextLoader("file.txt")
documents = loader.load()
```

### PDF Files

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("document.pdf")
pages = loader.load()
```

### Web Pages

```python
from langchain_community.document_loaders import WebBaseLoader

loader = WebBaseLoader("https://example.com")
documents = loader.load()
```

### Multiple Files

```python
from langchain_community.document_loaders import DirectoryLoader

loader = DirectoryLoader("./documents", glob="**/*.txt")
documents = loader.load()
```

## Text Splitting

### Character Text Splitter

```python
from langchain.text_splitter import CharacterTextSplitter

text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)

texts = text_splitter.split_text(text)
```

### Recursive Character Text Splitter

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

texts = text_splitter.split_documents(documents)
```

### Code Splitter

```python
from langchain.text_splitter import PythonCodeTextSplitter

text_splitter = PythonCodeTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
```

## Embeddings

### OpenAI Embeddings

```python
from langchain_community.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()

text_embedding = embeddings.embed_query("Hello world")
doc_embeddings = embeddings.embed_documents(["Hello", "World"])
```

### HuggingFace Embeddings

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

## Vector Stores

### Chroma

```python
from langchain_community.vectorstores import Chroma

vectorstore = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

vectorstore.persist()
```

### FAISS

```python
from langchain_community.vectorstores import FAISS

vectorstore = FAISS.from_documents(texts, embeddings)
vectorstore.save_local("faiss_index")
```

### Pinecone

```python
from langchain_community.vectorstores import Pinecone
import pinecone

pinecone.init(api_key="your-key", environment="us-west1-gcp")

vectorstore = Pinecone.from_documents(
    texts,
    embeddings,
    index_name="my-index"
)
```

## Retrieval

### Similarity Search

```python
docs = vectorstore.similarity_search("query", k=4)
```

### Similarity Search with Scores

```python
docs_and_scores = vectorstore.similarity_search_with_score("query", k=4)

for doc, score in docs_and_scores:
    print(f"Score: {score}, Content: {doc.page_content}")
```

### Maximum Marginal Relevance

```python
docs = vectorstore.max_marginal_relevance_search(
    "query",
    k=4,
    fetch_k=20,
    lambda_mult=0.5
)
```

## Retrieval Strategies

### Basic Retriever

```python
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)
```

### Similarity Score Threshold

```python
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.8, "k": 4}
)
```

### Multi-Query Retriever

```python
from langchain.retrievers.multi_query import MultiQueryRetriever

retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(),
    llm=ChatOpenAI(model="gpt-4")
)

docs = retriever.get_relevant_documents("query")
```

## RAG Chains

### Basic RAG Chain

```python
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

result = qa({"query": "What is the topic?"})
print(result["result"])
print(result["source_documents"])
```

### Conversational RAG

```python
from langchain.chains import ConversationalRetrievalChain

qa = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory
)

result = qa({"question": "What is the topic?"})
```

### Custom RAG Prompt

```python
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

prompt_template = """
Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {question}
Answer:
"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    chain_type_kwargs={"prompt": PROMPT}
)
```

## Best Practices

1. **Chunk Size**: Use 500-1000 tokens for most use cases
2. **Overlap**: Use 10-20% overlap to maintain context
3. **Metadata**: Include metadata for filtering
4. **Hybrid Search**: Combine keyword and semantic search
5. **Re-ranking**: Re-rank results for better relevance

## Common Patterns

### RAG with Metadata Filtering

```python
retriever = vectorstore.as_retriever(
    search_kwargs={
        "k": 4,
        "filter": {"source": "documentation"}
    }
)
```

### RAG with Citations

```python
from langchain.chains import RetrievalQA

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

result = qa({"query": "What is the topic?"})

answer = result["result"]
sources = result["source_documents"]

print(f"Answer: {answer}")
print("\nSources:")
for i, doc in enumerate(sources, 1):
    print(f"{i}. {doc.metadata.get('source', 'Unknown')}")
```

### RAG with Streaming

```python
from langchain.chains import RetrievalQA

qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4", streaming=True),
    chain_type="stuff",
    retriever=retriever
)

for chunk in qa.stream({"query": "What is the topic?"}):
    print(chunk, end="", flush=True)
```
