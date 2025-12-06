import os
import requests
import sys

def ingest_folder(folder_path, api_url="http://localhost:8005/ingest"):
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    print(f"Scanning folder: {folder_path}")
    
    files_to_ingest = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # Filter out hidden files
            if file.startswith('.'):
                continue
            files_to_ingest.append(os.path.join(root, file))

    print(f"Found {len(files_to_ingest)} files.")

    for file_path in files_to_ingest:
        print(f"Ingesting: {file_path}...")
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(api_url, files={'file': f})
                
            if response.status_code == 200:
                print(f"✅ Success: {file_path}")
            else:
                print(f"❌ Failed: {file_path} - {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error ingesting {file_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_folder.py <folder_path>")
        sys.exit(1)
    
    folder = sys.argv[1]
    ingest_folder(folder)
