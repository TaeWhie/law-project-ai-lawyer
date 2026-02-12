from rag.retriever import LawRetriever
import os
from dotenv import load_dotenv

load_dotenv()

def verify():
    try:
        print("Initializing LawRetriever...")
        retriever = LawRetriever()
        
        query = "돈을 못받았어"
        print(f"Searching for: {query}")
        
        results = retriever.retrieve(query, k=6)
        print(f"Retrieved {len(results)} results.")
        
        target_articles = ['36', '43', '37', '109']
        found_articles = []
        
        for i, doc in enumerate(results):
            law_name = doc.metadata.get('law_name', 'Unknown')
            # In loader.py we now set 'ArticleNumber'
            art_num = doc.metadata.get('ArticleNumber', 'Unknown')
            article_header = doc.metadata.get('article', 'Unknown')
            
            print(f"[{i+1}] {law_name} - {article_header}")
            
            if art_num in target_articles:
                found_articles.append(art_num)
        
        found_set = set(found_articles)
        missing = [a for a in target_articles if a not in found_set]
        
        if not missing:
            print("\n✅ Verification Success: All target articles (36, 43, 37, 109) were found!")
        else:
            print(f"\n❌ Verification Failed: Missing articles: {missing}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
