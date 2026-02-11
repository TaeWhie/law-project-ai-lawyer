import os
import re
import json
import random
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.llm_factory import LLMFactory
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

class LegalIndexer:
    def __init__(self, target_law_name: str = "근로기준법", data_path: str = "data/laws", output_path: str = None, persist_directory: str = "data/chroma", unified_mode: bool = True):
        """Initialize LegalIndexer.
        
        Args:
            target_law_name: Name of the law to index (e.g., '근로기준법')
            data_path: Directory containing law markdown files
            output_path: Output JSON file path. If None and unified_mode=True, defaults to 'judgment/legal_index.json'
            persist_directory: ChromaDB directory
            unified_mode: If True, creates/updates unified index with all laws. If False, creates separate file per law.
        """
        self.target_law_name = target_law_name
        self.data_path = data_path
        self.unified_mode = unified_mode
        
        if output_path:
            self.output_path = output_path
        else:
            # Default: unified index for all laws
            self.output_path = "judgment/legal_index.json" if unified_mode else f"judgment/legal_index_{target_law_name}.json"
        
        self.persist_directory = persist_directory
        self.version_path = "judgment/law_versions.json"
        
        # Determine embedding type from env (similar to LLM_TYPE)
        # Default to openai if not set, but user can set LLM_TYPE=ollama to trigger local embeddings if desired
        # Or better, use a specific EMBEDDING_TYPE env var, defaulting to LLM_TYPE
        embed_type = os.getenv("EMBEDDING_TYPE", os.getenv("LLM_TYPE", "openai"))
        self.embeddings = LLMFactory.create_embeddings(embed_type)
        
        self.llm = LLMFactory.create_llm(os.getenv("LLM_TYPE", "openai"))

    def run(self):
        print(f"--- Starting Legal Indexing and Version Check from {self.data_path} ---")
        
        # 1. Check for updates and ingest to Chroma
        updated_files = self._get_updated_files()
        if updated_files:
            print(f"New or updated files detected: {updated_files}")
            self._ingest_to_chroma(updated_files)
            self._update_version_index(updated_files)
        else:
            print("No updates detected in legal documents.")
        
        # 2. Re-generate legal index if any updates occurred or index missing
        if updated_files or not os.path.exists(self.output_path):
            self.generate_and_save()
        
        print("--- Legal Sync Complete ---")

    def _get_updated_files(self) -> List[str]:
        versions = {}
        if os.path.exists(self.version_path):
            try:
                with open(self.version_path, "r", encoding="utf-8") as f:
                    versions = json.load(f)
            except: versions = {}
        
        updated = []
        if not os.path.exists(self.data_path):
            return []

        for filename in os.listdir(self.data_path):
            if filename.endswith(".md"):
                filepath = os.path.join(self.data_path, filename)
                # Use modification time as the sole version key
                mtime = os.path.getmtime(filepath)
                current_ver = str(int(mtime))
                
                if filename not in versions or versions[filename] != current_ver:
                    updated.append(filename)
        return updated

    def _update_version_index(self, updated_files: List[str]):
        versions = {}
        if os.path.exists(self.version_path):
            try:
                with open(self.version_path, "r", encoding="utf-8") as f:
                    versions = json.load(f)
            except: versions = {}
        
        for filename in updated_files:
            filepath = os.path.join(self.data_path, filename)
            # Consistently use mtime as the unique version key
            versions[filename] = str(int(os.path.getmtime(filepath)))
            
        with open(self.version_path, "w", encoding="utf-8") as f:
            json.dump(versions, f, ensure_ascii=False, indent=4)

    def _generate_legal_index(self):
        """Generate index for a single law (target_law_name).
        Returns the index structure (does NOT save to file).
        """
        print(f"Starting 2-Stage Zero-Loss Indexing for {self.target_law_name}...")
        
        # Stage 1: Base Index (Act Only)
        print(f"Stage 1: Base Generation ({self.target_law_name} Act)...")
        base_index = self._stage1_base_generation()
        
        # Stage 2: Augmentation (Decree & Rules)
        print("Stage 2: Augmentation (Enforcement Decree)...")
        index_with_decree = self._stage2_augmentation(base_index, "시행령", "령")
        
        print("Stage 2: Augmentation (Enforcement Rules)...")
        final_index = self._stage2_augmentation(index_with_decree, "시행규칙", "규")
        
        # Stage 3: Penalty Distribution
        print("Stage 3: Penalty Distribution...")
        final_index = self._distribute_penalties(final_index)
        
        print(f"Indexing complete for {self.target_law_name}.")
        return final_index
    
    def generate_and_save(self):
        """Generate index and save to file.
        
        If unified_mode=True, loads existing unified index, updates/adds the law, and saves.
        If unified_mode=False, saves law index to separate file.
        """
        law_index = self._generate_legal_index()
        
        if self.unified_mode:
            # Load existing unified index or create new
            if os.path.exists(self.output_path):
                print(f"Loading existing unified index from {self.output_path}...")
                with open(self.output_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                
                # Check if it's already in unified format (has "laws" key)
                if "laws" in existing_data:
                    unified_index = existing_data
                else:
                    # Old format: migrate to unified structure
                    print("⚠️  Detected old format. Migrating to unified structure...")
                    # Assume the file contains a single law index (근로기준법 by default)
                    # Try to detect law name from categories if possible, otherwise use default
                    old_law_name = "근로기준법"  # Default assumption
                    unified_index = {
                        "version": "2.0",
                        "last_updated": "",
                        "laws": {
                            old_law_name: existing_data
                        }
                    }
                    print(f"✅ Migrated old index as '{old_law_name}'")
            else:
                print("Creating new unified index...")
                unified_index = {
                    "version": "2.0",
                    "last_updated": "",
                    "laws": {}
                }
            
            # Update/add the law
            unified_index["laws"][self.target_law_name] = law_index
            
            # Update timestamp
            from datetime import datetime
            unified_index["last_updated"] = datetime.now().isoformat()
            
            # Save unified index
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(unified_index, f, ensure_ascii=False, indent=2)
            print(f"✅ Unified index updated: {self.target_law_name} added to {self.output_path}")
        else:
            # Single law mode: save to separate file
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(law_index, f, ensure_ascii=False, indent=4)
            print(f"✅ Single law index saved to {self.output_path}")

    def _load_text_for_type(self, target_ltype, target_short, override_list=None, full_text=False):
        text_content = ""
        checklist = []
        
        print(f"DEBUG: Loading text for {target_ltype} (type={target_short}, full={full_text})")
        for filename in sorted(os.listdir(self.data_path)):
            # Filter by target_law_name AND ltype
            if filename.endswith(".md") and self.target_law_name in filename and f"({target_ltype})" in filename:
                filepath = os.path.join(self.data_path, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Use a robust split pattern
                    blocks = re.split(r"(?=#### \[.*?\] 제\d+조|## |### )", content)
                    text_content += f"\n=== [{target_ltype} 원본 조문 목록 시작] ===\n"
                    
                    for block in blocks:
                        block = block.strip()
                        if not block: continue
                        
                        lines = block.split("\n")
                        header = lines[0]
                        
                        # Prioritize finding article numbers
                        num_match = re.search(r"제(\d+(?:의\d+)?)조", header)
                        
                        if num_match:
                            num = num_match.group(1)
                            # If override_list is provided, filter
                            if override_list and not any(str(i["num"]) == num for i in override_list):
                                # print(f"DEBUG: Skipping {target_short} {num} (not in override_list)")
                                continue # Skip this article
                                
                            # It is an article -> Add to checklist and text
                            text_content += f"{header} ({target_ltype})\n"
                            
                            if not override_list: # Only add to checklist if not overriding (or handling override logic specificly)
                                checklist.append({"num": num, "type": target_short})
                            
                            if full_text:
                                # Add ALL lines
                                for bline in lines[1:]:
                                    text_content += f"{bline}\n"
                            else:
                                # Add some body context (up to 4 lines)
                                body_lines = [l.strip() for l in lines[1:5] if l.strip()]
                                for bline in body_lines:
                                    text_content += f"{bline[:100]}\n"
                        elif block.startswith("#"):
                             # Structural header without article number -> just add to text context
                             text_content += f"{header}\n"
        
        print(f"DEBUG: Loaded {len(checklist)} {target_short} articles from {len(text_content)} chars")
        return text_content, checklist

    def _stage1_base_generation(self):
        all_text, checklist = self._load_text_for_type("법률", "법")
        checklist_text = ", ".join([f"{a['num']}" for a in checklist])
        
        prompt = ChatPromptTemplate.from_template("""{target_law_name}(법률)의 모든 조항을 분석하여 법률 지식 지도의 '기본 골격(Categories)'을 작성하라.

 [작성 규칙]
  1. **[Zero-Loss 원칙]**: 아래 [매핑 대상 조문]의 모든 조항이 빠짐없이 카테고리에 포함되어야 한다.
  2. **[카테고리 구조]**: 법의 1장~12장 구조를 반영하여 최소 14개 이상의 대분류를 생성하라.
  3. **[Core Mapping]**: 각 카테고리의 `core_articles`에는 해당되는 법률 조항 번호를 `{{"num":"번호","type":"법"}}` 형태로 매핑하라.
  4. **[부칙 제외]**: 부칙(附則) 조문은 카테고리에 포함하지 마라. 본문(제1조~제147조) 조항만 매핑하라.
  5. **[출력 제한]**: 오직 JSON 데이터만 출력하라.

 [매핑 대상 조문]
 {checklist_text}

 [참고 문서]
 {all_text}

  [응답 형식]
 {{
  "categories": [
   {{
    "key": "cat_code",
    "korean": "카테고리명",
    "description": "설명",
    "start_num": 1,
    "end_num": 10,
    "search_keywords": ["키워드"]
   }}
  ]
 }}
 """)
        chain = prompt | self.llm
        response = chain.invoke({
            "target_law_name": self.target_law_name,
            "all_text": all_text[:90000], 
            "checklist_text": checklist_text
        })
        base_index = self._parse_json_response(response.content)

        # --- Post-process: Populate core_articles based on ranges ---
        print("DEBUG: Populating core_articles based on extracted ranges...")
        # 1. Load actual Act articles
        _, act_checklist = self._load_text_for_type("법률", "법", full_text=False)
        
        # 2. Assign to categories
        for cat in base_index.get("categories", []):
            cat["core_articles"] = [] # Initialize
            cat["penalty_articles"] = []
            cat["orphan_articles"] = []
            
            # Ensure metadata
            if "key" not in cat: cat["key"] = f"cat_{random.randint(1000,9999)}"
            
            start = int(cat.get("start_num", 0))
            end = int(cat.get("end_num", 9999))
            
            for item in act_checklist:
                # Handle "10의2" -> 10
                art_main_num = int(re.sub(r"\D.*", "", str(item["num"])))
                
                if start <= art_main_num <= end:
                    # Check for duplicates in this category
                    if any(existing["num"] == str(item["num"]) for existing in cat["core_articles"]):
                        continue

                    # Create Article Object
                    art_obj = {
                        "num": str(item["num"]),
                        "type": "법",
                        "sub_articles": []
                    }
                    cat["core_articles"].append(art_obj)
        
        # --- Stage 1.5: Verify and Correct Act Coverage ---
        # (With this logic, coverage should be good if ranges are correct. 
        # But we keep correction logic for safety, mainly checking if any article was missed due to range gaps)
        
        # Recalculate mapped_nums
        mapped_nums = set()
        if "categories" in base_index:
            for cat in base_index["categories"]:
                for art in cat["core_articles"]:
                     mapped_nums.add(str(art["num"]))

        missing_items = [item for item in checklist if str(item["num"]) not in mapped_nums]
        
        if missing_items:
            print(f"DEBUG: Detected {len(missing_items)} missing Act articles. Applying Stage 1.5 Correction...")
            # Use stage 2 LLM fallback (Categorization) directly for Acts, not augmentation (Hierarchical Mapping)
            # 1. Load text for missing items
            missing_text, _ = self._load_text_for_type("법률", "법", override_list=missing_items, full_text=True)
            # 2. Call fallback
            base_index = self._stage2_llm_fallback(base_index, "법률", "법", missing_items, missing_text)
            print("DEBUG: Stage 1.5 Correction Complete.")
        else:
            print("DEBUG: Act Coverage is 100%.")

        return base_index

    def _stage2_augmentation(self, current_index, ltype, short_type, checklist_override=None):
        """
        Relational Augmentation Strategy (Hierarchical):
        1. Extract explicit references to 'Act (법)' articles from the text.
        2. If a Decree/Rule article cites 'Act Article X', add it to 'Act Article X's 'sub_articles' list.
        3. Support multiple references (add to all referenced Act parents).
        4. If no explicit reference is found, fallback to LLM semantic mapping (add to Category's orphan_articles or core_articles).
        """
        if checklist_override:
            all_text, checklist = self._load_text_for_type(ltype, short_type, override_list=checklist_override, full_text=True)
        else:
            all_text, checklist = self._load_text_for_type(ltype, short_type, full_text=True)
            
        print(f"DEBUG: Starting Relational Augmentation for {ltype} ({len(checklist)} articles)")
        
        # 0. Ensure all Act articles have 'sub_articles' field
        # This is a good place to lazily init it if missing
        count_init = 0
        for cat in current_index["categories"]:
            if "orphan_articles" not in cat: cat["orphan_articles"] = []
            for art in cat.get("core_articles", []):
                if art["type"] == "법" and "sub_articles" not in art:
                    art["sub_articles"] = []
                    count_init += 1
        # print(f"DEBUG: Initialized 'sub_articles' for {count_init} Act articles.")

        # 1. Build a map of "Act Article Number" -> "Category Key"
        act_to_cat = {}
        for cat in current_index["categories"]:
            for art in cat.get("core_articles", []):
                if art["type"] == "법":
                    act_to_cat[str(art["num"])] = cat["key"]
        
        # 2. Process each article in checklist
        semantic_fallback_list = []
        
        article_texts = self._split_text_by_article(all_text, ltype)
        
        for item in checklist:
            art_num = str(item["num"])
            # Find text for this article
            art_text = article_texts.get(art_num, "")
            
            # Extract references to Act (법 제OO조)
            # Strategy:
            # 1. Find all "XYZ법 제OO조" or "법 제OO조"
            # 2. If it specifies a law name that is NOT the target law (and NOT "법"), ignore it.
            # 3. If it is "법 제OO조" or "{target_law} 제OO조", accept it.
            
            # This regex captures (LawName, ArticleNum)
            # Matches: "근로기준법 제2조", "남녀고용평등법 제3조", "법 제5조"
            matches = re.findall(r"([가-힣]+법)?\s*제\s*(\d+(?:의\d+)?)조", art_text)
            
            valid_refs = []
            for law_name, ref_num in matches:
                law_name = law_name.strip()
                # If law_name exists and is NOT "법" and NOT target_law_name (approx match), it's external.
                # Note: "법" is usually empty in capture group 1 if regex is (Law)? because "법" is not captured by [가-힣]+법 if it is just "법"
                # Let's adjust regex to be safer.
                
            # Better Regex: Capture optional Law Name preceding "제OO조"
            # We look for (Any Word ending in 법)? (Space)* 제 (Num) 조
            # But we need to be careful about not capturing "법" as the law name if it's just "법 제"
            
            # Simple approach: Check the full match string
            raw_refs = re.finditer(r"([가-힣\s]*?)(법|령|규칙)?\s*제\s*(\d+(?:의\d+)?)조", art_text)
            
            refs = []
            for m in raw_refs:
                prefix = m.group(1).strip() # e.g., "근로기준", "고용보험", or empty
                suffix = m.group(2) # e.g., "법", "령", "규칙"
                ref_num = m.group(3)
                
                # We only care if it targets the ACT (법)
                if suffix != "법" and suffix is not None:
                    continue # It's citing a Decree or Rule, ignore for now (or handle differently)
                
                # If prefix exists, check if it is explicitly OTHER law
                full_law_name = f"{prefix}{suffix}" if suffix else prefix
                
                # Logic:
                # 1. If prefix is empty -> It implies "This Law" (법 제OO조) -> MATCH
                # 2. If prefix is "근로기준" (Target Law) -> MATCH
                # 3. If prefix is "고용보험" (Other Law) -> SKIP
                
                is_target = False
                if not prefix:
                     is_target = True
                elif self.target_law_name.replace("법", "") in prefix: # e.g., "근로기준" in "근로기준"
                     is_target = True
                
                if is_target:
                    refs.append(ref_num)
                    
            if refs:
                # Deduplicate refs
                refs = list(set(refs))
                for ref_num in refs:
                    target_cat_key = act_to_cat.get(ref_num)
                    if target_cat_key:
                        # Add to the specific Act article's hierarchy
                        success = self._add_to_hierarchy(current_index, target_cat_key, ref_num, art_num, short_type)
                        if success:
                            mapped = True
                            # print(f"  [Relational] {short_type} {art_num} -> Cat {target_cat_key} > Law {ref_num}")
            
            if not mapped:
                semantic_fallback_list.append(item)
        
        print(f"DEBUG: Relational Mapping Complete. {len(checklist) - len(semantic_fallback_list)} mapped, {len(semantic_fallback_list)} fallback to LLM.")
        
        # 3. LLM Fallback for remaining items
        if semantic_fallback_list:
            current_index = self._stage2_llm_fallback(current_index, ltype, short_type, semantic_fallback_list, all_text)
            
        return current_index

    def _distribute_penalties(self, current_index):
        """
        Parses Chapter 12 (Penalty) and distributes penalty articles to relevant categories.
        """
        print("DEBUG: Distributing Penalties...")
        # Load Penalty Chapter (Chapter 12, Articles 107~116)
        # We load from Act text.
        all_text, _ = self._load_text_for_type("법률", "법", full_text=True)
        
        # Build Act->Cat map
        act_to_cat = {}
        for cat in current_index["categories"]:
            for art in cat.get("core_articles", []):
                if art["type"] == "법":
                    act_to_cat[str(art["num"])] = cat["key"]

        # Parse penalty articles
        # Penalty articles: 107, 109, 110, 111, 112, 113, 114, 115, 116 (approx)
        # Pattern: "제OO조를 위반한 자"
        
        # Isolate penalty articles from text
        penalty_articles = []
        # Use robust regex matching any header level
        blocks = re.split(r"(?=#{2,6} \[.*?\] 제\d+조)", all_text)
        
        for block in blocks:
            header_match = re.search(r"제(\d+(?:의\d+)?)조", block.split("\n")[0])
            if header_match:
                art_num = header_match.group(1)
                # Check if it's a penalty article (usually 107~) or check content
                # Simple heuristic: Article number >= 107
                try:
                    num_val = int(re.sub(r"\D", "", art_num.split("의")[0]))
                    if num_val >= 107:
                         penalty_articles.append((art_num, block))
                except: pass

        count = 0
        for p_num, p_text in penalty_articles:
            # Extract violated articles: "제OO조, 제OO조...를 위반한 자"
            violated_refs = re.findall(r"제(\d+(?:의\d+)?)조", p_text)
            # Filter out self-reference or irrelevant ones if needed, but usually these are targets.
            # Remove p_num itself if captured
            violated_refs = [r for r in violated_refs if r != p_num]
            
            for v_ref in violated_refs:
                target_cat_key = act_to_cat.get(v_ref)
                if target_cat_key:
                    # Add to penalty_articles list of that category
                    self._add_penalty_to_category(current_index, target_cat_key, p_num, "법")
                    # print(f"  [Penalty] Law {p_num} -> Cat {target_cat_key} (Targets Law {v_ref})")
                    count += 1
        print(f"DEBUG: Distributed {count} penalty mappings.")
        return current_index

    def _add_to_hierarchy(self, index, cat_key, parent_act_num, child_num, child_type):
        """
        Adds a child article (Decree/Rule) to the 'sub_articles' list of a specific Act article.
        """
        for cat in index["categories"]:
            if cat["key"] == cat_key:
                for art in cat["core_articles"]:
                    if art["type"] == "법" and str(art["num"]) == str(parent_act_num):
                        # Found the parent Act article
                        if "sub_articles" not in art: art["sub_articles"] = []
                        
                        # Check existance
                        exists = any(sub["num"] == child_num and sub["type"] == child_type for sub in art["sub_articles"])
                        if not exists:
                            art["sub_articles"].append({"num": child_num, "type": child_type})
                        return True
        return False

    def _add_to_category(self, index, cat_key, num, type_short):
        """
        Legacy/Fallback: Adds to category. 
        If 'Act', add to core_articles (with sub_articles).
        If 'Decree/Rule', add to orphan_articles.
        """
        target_list = "core_articles" if type_short == "법" else "orphan_articles"
        
        for cat in index["categories"]:
            if cat["key"] == cat_key:
                if target_list not in cat: cat[target_list] = []
                
                exists = any(a["num"] == num and a["type"] == type_short for a in cat[target_list])
                if not exists:
                    new_art = {"num": num, "type": type_short}
                    if type_short == "법":
                         new_art["sub_articles"] = []
                    cat[target_list].append(new_art)
                return

    def _add_penalty_to_category(self, index, cat_key, num, type_short):
        for cat in index["categories"]:
            if cat["key"] == cat_key:
                # Ensure penalty_articles list exists
                if "penalty_articles" not in cat: cat["penalty_articles"] = []
                exists = any(a["num"] == num and a["type"] == type_short for a in cat["penalty_articles"])
                if not exists:
                    cat["penalty_articles"].append({"num": num, "type": type_short})
                return

    def _split_text_by_article(self, text, ltype):
        """Map article number to its text content"""
        mapping = {}
        
        # Use simple pattern first to see if it splits
        blocks = re.split(r"(?=#{2,6} \[.*?\] 제\d+조)", text)
        
        for block in blocks:
            # The header might differ slightly due to the appended (type)
            # Try matching '제OO조' in the first line
            first_line = block.strip().split("\n")[0]
            match = re.search(r"제(\d+(?:의\d+)?)조", first_line)
            if match:
                mapping[match.group(1)] = block
                    
        return mapping

    def _stage2_llm_fallback(self, current_index, ltype, short_type, checklist, all_text):
        print(f"DEBUG: LLM Fallback for {len(checklist)} items...")
        
        checklist_text = ", ".join([f"{a['num']}" for a in checklist])
        categories_summary = "\n".join([f"- {c['key']}: {c['korean']} ({c['description']})" for c in current_index['categories']])
        
        prompt = ChatPromptTemplate.from_template("""기존 법률 지식 지도에 '{ltype}' 조항들을 추가 매핑하려 한다.
 아래 '{ltype}'의 각 조항 내용을 분석하여, 가장 적절한 '기존 카테고리(Category Key)'에 배정하라.
 (이미 명시적 참조가 있는 조항들은 처리되었으며, 남은 조항들이다.)

 [작성 규칙]
  1. **[Zero-Loss 원칙]**: 아래 [매핑 대상 조문]의 모든 조항을 하나도 빠짐없이 매핑해야 한다.
  2. **[기존 카테고리 활용]**: 새로운 카테고리를 만들지 말고, 제공된 [기존 카테고리 목록] 중 가장 연관성 높은 곳을 찾아라.
  3. **[출력 제한]**: 오직 JSON 리스트만 출력하라.

 [기존 카테고리 목록]
 {categories_summary}

 [매핑 대상 조문 ({ltype})]
 {checklist_text}

 [문서 내용]
 {all_text}

 [응답 형식]
 [
  {{ "num": "1", "target_key": "cat_code_A" }},
  {{ "num": "2", "target_key": "cat_code_B" }}
 ]
 """)
        chain = prompt | self.llm
        print(f"DEBUG: Invoking LLM for {ltype} augmentation...")
        response = chain.invoke({
            "ltype": ltype,
            "all_text": all_text[:90000], 
            "checklist_text": checklist_text,
            "categories_summary": categories_summary
        })
        
        try:
            mapping_list = self._parse_json_response(response.content)
            print(f"DEBUG: LLM returned {len(mapping_list)} mappings")
        except Exception as e:
            print(f"DEBUG: JSON Parse Error: {e}")
            return current_index
        
        for item in mapping_list:
            self._add_to_category(current_index, item.get("target_key"), item.get("num"), short_type)
        
        return current_index

    def _parse_json_response(self, content):
        content = content.strip().replace("```json", "").replace("```", "")
        # Remove comments (// ...)
        content = re.sub(r"//.*", "", content)
        
        start = content.find("[") if content.strip().startswith("[") else content.find("{")
        end = content.rfind("]") if content.strip().endswith("]") else content.rfind("}")
        
        if start != -1 and end != -1:
            content = content[start:end+1]
            
        # Fix Trailing Commas: , } -> } and , ] -> ]
        content = re.sub(r",\s*([\]}])", r"\1", content)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON Parse Error: {e}. Content snippet: {content[:100]}...")
            # Fallback: Try to use ast.literal_eval for single quote JSONs or some python dicts
            import ast
            try:
                return ast.literal_eval(content)
            except:
                raise e

    def _ingest_to_chroma(self, files: List[str]):
        headers_to_split_on = [
            ("#", "Title"),
            ("##", "Chapter"),
            ("###", "Section"),
            ("####", "Article"),
        ]
        text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        
        all_docs = []
        for filename in files:
            filepath = os.path.join(self.data_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                docs = text_splitter.split_text(content)
                for doc in docs:
                    doc.metadata["source"] = filename
                    # Prepend headers to content for better searchability of specific articles
                    header_vals = [doc.metadata.get(h) for h in ["Chapter", "Section", "Article"] if doc.metadata.get(h)]
                    if header_vals:
                        header_prefix = " > ".join(header_vals)
                        doc.page_content = f"[{header_prefix}]\n{doc.page_content}"
                    
                    if "Article" in doc.metadata:
                        # Capture branch articles like 제76조의2 -> 76의2
                        num_match = re.search(r"제(\d+)(?:조(?:의(\d+))?)?", doc.metadata["Article"])
                        if num_match:
                            main_num = num_match.group(1)
                            branch_num = num_match.group(2)
                            doc.metadata["ArticleNumber"] = f"{main_num}의{branch_num}" if branch_num else main_num
                all_docs.extend(docs)
        
        if all_docs:
            print(f"Incrementally ingesting {len(all_docs)} chunks into Chroma...")
            Chroma.from_documents(
                documents=all_docs,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_name="statutes"
            )
            print("Incremental Ingestion complete.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    indexer = LegalIndexer()
    indexer.generate_and_save()

