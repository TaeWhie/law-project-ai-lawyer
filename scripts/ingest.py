import os
from rag.loader import ArticleMarkdownLoader
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

def ingest_statutes():
    persist_directory = "data/chroma"
    law_dir = "data/laws"
    
    if not os.path.exists(law_dir):
        print(f"Directory {law_dir} not found.")
        return

    from app.llm_factory import LLMFactory
    embed_type = os.getenv("EMBEDDING_TYPE", os.getenv("LLM_TYPE", "openai"))
    print(f"Initializing Embeddings: {embed_type}...")
    embeddings = LLMFactory.create_embeddings(embed_type)
    
    # Initialize or load Chroma
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="statutes"
    )

    batch_docs = []
    batch_size = 50  # Save every 50 chunks
    count = 0

    files = [f for f in os.listdir(law_dir) if f.endswith(".md")]
    total_files = len(files)
    print(f"Found {total_files} documents to ingest.")

    for i, filename in enumerate(files):
        try:
            file_path = os.path.join(law_dir, filename)
            loader = ArticleMarkdownLoader(file_path)
            docs = loader.load()
            
            # Add metadata about the law type (Law, Decree, Rule)
            for doc in docs:
                if "시행령" in filename:
                    doc.metadata["tier"] = "decree"
                elif "시행규칙" in filename:
                    doc.metadata["tier"] = "rule"
                else:
                    doc.metadata["tier"] = "law"
                doc.metadata["law_name"] = filename.replace(".md", "")
            
            batch_docs.extend(docs)
            count += 1
            
            # Incremental Save
            if len(batch_docs) >= batch_size:
                print(f"[{count}/{total_files}] Saving batch of {len(batch_docs)} chunks...")
                vectorstore.add_documents(batch_docs)
                batch_docs = []
            elif count % 10 == 0:
                print(f"[{count}/{total_files}] Processing... ({len(batch_docs)} buffered)")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Save remaining
    if batch_docs:
        print(f"[{count}/{total_files}] Saving final batch of {len(batch_docs)} chunks...")
        vectorstore.add_documents(batch_docs)
    
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_statutes()
