from rag.retriever import LawRetriever
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

def verify():
    print("Initializing Retriever...")
    retriever = LawRetriever(persist_directory="data/chroma", collection_name="statutes")
    # Test Query: Money + Bullying
    custom_query = "돈도 못받았는데 상사가 날괴롭혀"
    print(f"Query: {custom_query}")
    
    print("Retrieving Grouped Results...")
    grouped_results = retriever.retrieve_grouped(custom_query, k_per_cat=3, top_k_cats=3)
    
    if not grouped_results:
        print("FAILED: No grouped results found.")
    else:
        print(f"SUCCESS: Found {len(grouped_results)} categories.")
        for cat_name, docs in grouped_results.items():
            print(f"\n--- Category: {cat_name} ---")
            for i, doc in enumerate(docs):
                art_num = doc.metadata.get('ArticleNumber', 'Unknown')
                print(f"[{i+1}] {doc.metadata.get('Article', 'Unknown')} (Art {art_num})")

if __name__ == "__main__":
    verify()
