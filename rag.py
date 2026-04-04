import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

PDF_PATH = "data/sample.pdf"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "rag_collection"

def build_rag_pipeline(pdf_path: str = PDF_PATH):
    # Error Handling: Check if file exists to prevent crashing later without an explicit message
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Missing PDF Error: Cannot find the PDF file at path: {pdf_path}")
        
    print(f"Loading PDF from {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    print("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunk(s).")
    
    print("Initializing local embeddings (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print("Storing chunks and embeddings locally in ChromaDB...")
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_PATH
    )
    
    # Just to be 100% sure we're strictly enforcing local DB layout.
    assert os.path.exists(CHROMA_PATH), "Error: ChromaDB directory was not created!"
    print("Vector database successfully created and saved.")

def retrieve_context(query: str) -> list[str]:
    """
    Retrieves the top 3 most relevant textual context chunks from ChromaDB for a given query.
    """
    if not os.path.exists(CHROMA_PATH):
        raise FileNotFoundError(f"Missing ChromaDB Path: DB not found at {CHROMA_PATH}")
        
    # Re-initialize the same embedding protocol
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Load existing DB without recreating it
    db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH
    )
    
    results = db.similarity_search(query, k=3)
    
    # Only return page content strings, not full Document metadata objects
    return [doc.page_content for doc in results]

if __name__ == "__main__":
    # Ensure DB exists before trying to query
    if not os.path.exists(CHROMA_PATH):
        build_rag_pipeline()
    
    # Test our query execution
    print("Retrieving context for 'Python'...")
    chunks = retrieve_context("Python")
    if not chunks:
        print("No chunks returned.")
    else:
        print(f"Found {len(chunks)} chunk(s):")
        for idx, chunk in enumerate(chunks):
            print(f"Chunk {idx+1}:\n{chunk}\n")
