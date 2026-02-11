import re
import os

def debug_regex():
    filepath = r"d:\PhythonProject\LawProject\data\laws\근로기준법(시행령).md"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Test Split Regex
    split_pattern = r"(?=#### \[.*?\] 제\d+조|## |### )"
    blocks = re.split(split_pattern, content)
    print(f"Total Blocks: {len(blocks)}")
    
    checklist = []
    for i, block in enumerate(blocks[:20]):
        block = block.strip()
        if not block: continue
        
        print(f"Block {i} Start: {block[:50]}...")
        if "제" in block and "조" in block:
            lines = block.split("\n")
            header = lines[0]
            print(f"  Header: {header}")
            
            # Test Extract Regex
            num_match = re.search(r"제(\d+(?:의\d+)?)조", header)
            if num_match:
                print(f"  Found Num: {num_match.group(1)}")
                checklist.append(num_match.group(1))
            else:
                print(f"  NO MATCH for number in header")
                
    print(f"Total Extracted in sample: {len(checklist)}")

if __name__ == "__main__":
    debug_regex()
