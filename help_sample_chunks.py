from rag.retriever import LawRetriever
from dotenv import load_dotenv

load_dotenv()

def sample_chunks():
    retriever = LawRetriever()
    query = "임금체불"
    print(f"Sampling chunks for query: {query}")
    docs = retriever.retrieve(query, k=5)
    
    total_len = 0
    for i, doc in enumerate(docs):
        content = doc.page_content
        print(f"\n[Doc {i}] Length: {len(content)}")
        print(f"Metadata: {doc.metadata}")
        print(f"Content Sample: {content[:100]}...")
        total_len += len(content)
    
    print(f"\nTotal character count for 5 docs: {total_len}")
    print(f"Estimated token count (chars * 0.5): {int(total_len * 0.5)}")

if __name__ == "__main__":
    sample_chunks()
