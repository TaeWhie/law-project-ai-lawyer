import os
import zipfile
import shutil
import json

def zip_project(output_filename="law_project.zip"):
    # Files/Directories to exclude
    EXCLUDE_DIRS = {
        "venv", 
        "__pycache__", 
        ".git", 
        ".idea", 
        ".vscode",
        "chroma", 
        "wandb"
    }
    
    EXCLUDE_EXTENSIONS = {
        ".pyc", 
        ".pyd", 
        ".log", 
        ".ds_store"
    }
    
    EXCLUDE_FILES = {
        "law_project.zip", 
        ".env",
        "generate_colab_zip.py" 
    }

    project_root = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Zipping project from: {project_root}")
    print(f"Creating {output_filename}...")

    # Mapping for non-ASCII filenames to avoid zip encoding issues on Linux
    filename_mapping = {}

    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            if "chroma" in os.path.split(root):
                 continue

            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                
                _, ext = os.path.splitext(file)
                if ext.lower() in EXCLUDE_EXTENSIONS:
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_root)
                
                # Check for non-ASCII characters in filename
                try:
                    arcname.encode('ascii')
                except UnicodeEncodeError:
                    # Rename in zip to a safe name
                    # e.g. data/laws/근로기준법.md -> data/laws/law_data_1.md
                    safe_name = f"renamed_file_{len(filename_mapping)}{ext}"
                    safe_arcname = os.path.join(os.path.dirname(arcname), safe_name)
                    
                    # Store mapping: safe_arcname -> original encoded name (for reference/restoration if needed)
                    # But for now, we just want it to work. 
                    # Actually, better strategy: 
                    # Since ingest.py relies on filenames for metadata (e.g. "시행령"), 
                    # we must preserve the *meaning* or handle it in ingest.py.
                    # 
                    # Let's try to just ADD the file with the original name but ensure we don't mess up encoding.
                    # Python's zipfile handles utf-8 well usually, but Windows might be using cp949.
                    
                    # Force arcname to be unicode (it is by default in Py3), but let's be explicit
                    pass

                print(f"Adding: {arcname}")
                zipf.write(file_path, arcname)

    print(f"Successfully created {output_filename}")

    # [Automation] Copy to Google Drive if available
    # Check for G: drive (Google Drive for Desktop)
    if os.path.exists("G:/"):
        # Try Korean path first, then English
        possible_paths = ["G:/내 드라이브/LawProject", "G:/My Drive/LawProject"]
        drive_path = None
        
        for path in possible_paths:
            # Check if parent directory exists (e.g. G:/내 드라이브)
            parent = os.path.dirname(path)
            if os.path.exists(parent):
                drive_path = path
                break
        
        if drive_path:
            if not os.path.exists(drive_path):
                try:
                    os.makedirs(drive_path, exist_ok=True)
                    print(f"Created Google Drive folder: {drive_path}")
                except Exception as e:
                    print(f"Could not create folder on Google Drive: {e}")
                    drive_path = None

            if drive_path:
                try:
                    dest_file = os.path.join(drive_path, output_filename)
                    print(f"Copying to Google Drive: {dest_file}...")
                    shutil.copy2(output_filename, dest_file)
                    print("✅ Zip Upload to Google Drive complete!")

                    # Also copy the Notebook
                    notebook_filename = "LawProject_Colab.ipynb"
                    if os.path.exists(notebook_filename):
                         dest_nb = os.path.join(drive_path, notebook_filename)
                         print(f"Copying Notebook to Google Drive: {dest_nb}...")
                         shutil.copy2(notebook_filename, dest_nb)
                         print("✅ Notebook update complete!")

                except Exception as e:
                    print(f"❌ Failed to copy to Google Drive: {e}")
        else:
            print("Google Drive root found, but could not determine 'My Drive' path.")

if __name__ == "__main__":
    zip_project()
