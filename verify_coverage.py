import re
import os
import json

def get_articles_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    articles = set()
    matches = re.findall(r"####\s*\[.*?\]\s*(제\d+(?:의\d+)?조)", content)
    for m in matches:
        num = m.strip()
        articles.add(num)
    return articles

def verify():
    # 1. Expected Articles
    expected = {
        "법": get_articles_from_file(r"d:\PhythonProject\LawProject\data\laws\근로기준법(법률).md"),
        "령": get_articles_from_file(r"d:\PhythonProject\LawProject\data\laws\근로기준법(시행령).md"),
        "규": get_articles_from_file(r"d:\PhythonProject\LawProject\data\laws\근로기준법(시행규칙).md")
    }
    
    print(f"Expected Counts: Act={len(expected['법'])}, Decree={len(expected['령'])}, Rule={len(expected['규'])}")
    
    # 2. Actual Mapped Articles
    actual = {"법": set(), "령": set(), "규": set()}
    
    try:
        with open(r"judgment/legal_index.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        def add_article_to_actual(article_data):
            t = article_data['type']
            n = article_data['num']
            # Normalize type
            if t in ["법", "법률"]: k = "법"
            elif t in ["령", "시행령"]: k = "령"
            elif t in ["규", "시행규칙"]: k = "규"
            else: k = "기타"
            
            # Normalize number (sometimes just number, sometimes "제N조")
            if not n.startswith("제"): n = f"제{n}조"
            if "조" not in n: n = f"{n}조"
            
            if k in actual:
                actual[k].add(n)

        for cat in data['categories']:
            # Process core_articles
            for art in cat.get('core_articles', []):
                add_article_to_actual(art)
                # Check sub_articles within core_articles
                if "sub_articles" in art:
                    for sub in art["sub_articles"]:
                        add_article_to_actual(sub)
            
            # Process penalty_articles
            for art in cat.get('penalty_articles', []):
                add_article_to_actual(art)
                # Check sub_articles within penalty_articles (if applicable, though less common)
                if "sub_articles" in art:
                    for sub in art["sub_articles"]:
                        add_article_to_actual(sub)

            # Process orphan_articles
            if "orphan_articles" in cat:
                for art in cat["orphan_articles"]:
                    add_article_to_actual(art)
                    # Check sub_articles within orphan_articles (if applicable)
                    if "sub_articles" in art:
                        for sub in art["sub_articles"]:
                            add_article_to_actual(sub)
                    
        print(f"Actual Counts:   Act={len(actual['법'])}, Decree={len(actual['령'])}, Rule={len(actual['규'])}")
        
        # 3. Gap Analysis
        print("\n--- Missing Articles ---")
        for k in ["법", "령", "규"]:
            missing = expected[k] - actual[k]
            if missing:
                print(f"[{k}] Missing {len(missing)} articles: {sorted(list(missing))[:10]} ...")
            else:
                print(f"[{k}] 100% Covered!")
                
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify()
