from rag.retriever import LawRetriever
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

def verify():
    print("Initializing Retriever...")
    retriever = LawRetriever(persist_directory="data/chroma", collection_name="statutes")
    
    query = "돈도 못받았는데 상사가 날괴롭혀"
    print(f"Query: {query}")
    
    print("Retrieving Top 3...")
    # Initialize connection
    retriever = LawRetriever(persist_directory="data/chroma", collection_name="statutes")
    
    # Check logical flow
    print("----- DEBUG: Checking Category Selection -----")
    # This calls the internal method directly to see what categories are picked
    # We must mock the retrieval internal logic or just call _get_relevant_article_numbers directly
    # But wait, verify_recommendation calls .retrieve. 
    # Let's call .retrieve but also inspect the internal method if possible.
    # Actually, retrieve calls _get_relevant_article_numbers internally and prints DEBUG logs.
    
    results = retriever.retrieve(query, k=3, use_llm_rerank=True)

    
    if not results:
        print("FAILED: No results found.")
    else:
        print(f"SUCCESS: Found {len(results)} articles.")
        for i, doc in enumerate(results):
            art_num = doc.metadata.get('ArticleNumber', 'Unknown')
            print(f"[{i+1}] {doc.metadata.get('Article', 'Unknown')} (Article {art_num})")
            
            # Warn if Article 68 appears
            if str(art_num) == "68":
                print("WARNING: Article 68 (Minors) is present! Filtering failed.")

if __name__ == "__main__":
    verify()
