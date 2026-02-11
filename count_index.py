import json
import os

try:
    with open('judgment/legal_index.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    categories = data.get('categories', [])
    print(f"Total Categories: {len(categories)}")
    
    unique_articles = set()
    for cat in categories:
        core = cat.get('core_articles', [])
        penalty = cat.get('penalty_articles', [])
        for a in core + penalty:
            unique_articles.add(f"{a['num']}_{a['type']}")
            
    print(f"Total Unique Mapped Articles: {len(unique_articles)}")
    
except Exception as e:
    print(f"Error: {e}")
