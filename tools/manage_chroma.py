
import sys
import os
import shutil
import logging
from typing import Optional

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from chromadb import PersistentClient
except ImportError:
    print("Error: chromadb is not installed. Run 'pip install chromadb' first.")
    sys.exit(1)

STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chroma_storage")

COLLECTION_NAME = "vra_data"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_client():
    if not os.path.exists(STORAGE_PATH):
        logger.warning(f"Storage path {STORAGE_PATH} does not exist.")
        return None
    return PersistentClient(path=STORAGE_PATH)

def view_contents() -> None:
    client = get_client()
    if not client:
        return

    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        print(f"\n--- ChromaDB Contents ({COLLECTION_NAME}) ---")
        print(f"Total Documents: {count}")
        
        if count > 0:
            peek = collection.peek(limit=5)
            print("\nLatest 5 Entries:")
            ids = peek['ids']
            metadatas = peek['metadatas']
            documents = peek['documents']
            
            for i in range(len(ids)):
                print(f"[{i+1}] ID: {ids[i]}")
                print(f"    Meta: {metadatas[i]}")
                
                doc_val = documents[i]
                if doc_val is None or not isinstance(doc_val, str):
                    safe_doc = str(doc_val) if doc_val is not None else ""
                else:
                    safe_doc = doc_val
                    
                print(f"    Doc: {safe_doc[:100]}...") # Truncate doc
                print("-" * 40)
        else:
            print("Collection is empty.")

    except Exception as e:
        print(f"Error accessing collection: {e}")

def reset_db():
    print(f"\nWARNING: This will permanently delete the '{STORAGE_PATH}' directory.")
    confirm = input("Type 'DELETE' to confirm: ")
    
    if confirm == "DELETE":
        try:
            if os.path.exists(STORAGE_PATH):
                shutil.rmtree(STORAGE_PATH)
                print(f"✅ Deleted {STORAGE_PATH}. Database has been reset.")
                print("Run the application again to re-initialize an empty DB.")
            else:
                print("Default storage path does not exist. Nothing to delete.")
        except Exception as e:
            print(f"❌ Error deleting persistence directory: {e}")
            print("You may need to stop the running uvicorn server first to release file locks.")
    else:
        print("Reset cancelled.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/manage_chroma.py [view|reset]")
        sys.exit(0)

    command = sys.argv[1].lower()
    
    if command == "view":
        view_contents()
    elif command == "reset":
        reset_db()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python tools/manage_chroma.py [view|reset]")
