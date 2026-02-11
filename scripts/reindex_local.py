
import os
import shutil
from app.indexer import LegalIndexer

# Force Local Configuration
os.environ["LLM_TYPE"] = "ollama"
os.environ["EMBEDDING_TYPE"] = "ollama"
os.environ["OLLAMA_MODEL_NAME"] = "qwen2.5"
os.environ["OLLAMA_EMBED_MODEL"] = "nomic-embed-text"

def reindex_local():
    print("--- Switching to Local Embeddings (Ollama: nomic-embed-text) ---")
    
    # 1. Clear existing ChromaDB (OpenAI vectors are incompatible)
    chroma_path = "data/chroma"
    if os.path.exists(chroma_path):
        print(f"Removing old VectorStore at {chroma_path}...")
        shutil.rmtree(chroma_path)
    
    # 2. Also clear version file to force re-processing
    version_path = "judgment/law_versions.json"
    if os.path.exists(version_path):
        os.remove(version_path)

    # 3. Run Indexer
    print("Starting re-indexing...")
    try:
        indexer = LegalIndexer()
        indexer.run()
        print("\n[SUCCESS] Local Indexing Complete!")
        print("You can now run 'python test_local_qwen.py' without mocking.")
    except Exception as e:
        print(f"\n[ERROR] Indexing failed: {e}")
        print("Make sure you have pulled the embedding model: 'ollama pull nomic-embed-text'")

if __name__ == "__main__":
    reindex_local()
