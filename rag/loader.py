import re
from typing import List
from langchain_core.documents import Document

class ArticleMarkdownLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex to split by "#### [법률] 제N조(제목)" or similar
        articles = re.split(r'\n(####\s\[.*?\]\s제\d+조\(.*?\))', content)
        
        documents = []
        # The first element might be preamble or empty
        header = articles[0]
        
        for i in range(1, len(articles), 2):
            article_title = articles[i]
            article_body = articles[i+1] if i+1 < len(articles) else ""
            
            full_text = f"{article_title}\n{article_body.strip()}"
            
            # Extract metadata from filename or header if needed
            article_num_match = re.search(r'제(\d+)조', article_title)
            article_num = article_num_match.group(1) if article_num_match else None
            
            metadata = {
                "source": self.file_path,
                "article": article_title,
                "ArticleNumber": article_num
            }
            
            documents.append(Document(page_content=full_text, metadata=metadata))
            
        return documents
