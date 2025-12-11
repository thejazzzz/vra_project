# File: test/chroma_inspector.py

import os
os.environ["CHROMA_DISABLE_EMBEDDING_FUNCTIONS"] = "1"
import json
import chromadb

def connect():
    server = os.getenv("CHROMA_SERVER", "").strip()

    if server:
        # Remote HTTP mode (your Docker Chroma)
        from urllib.parse import urlparse
        parsed = urlparse(server)
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid CHROMA_SERVER URL: {server}")
        port = parsed.port or 8000
        print(f"[INFO] Connecting to remote Chroma at {host}:{port}")
        client = chromadb.HttpClient(
            host=host,
            port=port,
            ssl=(parsed.scheme == "https")
        )
    else:
        # Local persistent mode fallback
        print("[INFO] Connecting to local PersistentClient")
        client = chromadb.PersistentClient(path="./chroma_storage")

    return client


def inspect_collection(col):
    print("\n===========================")
    print(f" Collection: {col.name}")
    print("===========================\n")

    try:
        count = col.count()
        print(f"[INFO] Total items: {count}")

        if count == 0:
            print("[INFO] Collection is empty.")
            return

        # fetch all data
        data = col.get(include=["documents", "metadatas", "embeddings"])

        ids = data.get("ids", [])
        docs = data.get("documents", [])
        metas = data.get("metadatas", [])
        embeddings = data.get("embeddings", [])

        print(f"[INFO] Loaded {len(ids)} embeddings.")

        if ids:
            print("ID:", ids[0])
            if docs and docs[0]:
                print("Document:", str(docs[0])[:200], "...")   # show first 200 chars
            if metas and len(metas) > 0:
                print("Metadata:", metas[0])
            if embeddings and len(embeddings) > 0 and embeddings[0]:
                print("Embedding length:", len(embeddings[0]))            
                

        print("\n--- FULL LIST OF IDS ---")
        print(json.dumps(ids, indent=2))

    except Exception as e:
        print("[ERROR] Failed to inspect collection:", e)


def main():
    client = connect()

    # list all collections
    print("\n[INFO] Available collections:")
    cols = client.list_collections()
    for c in cols:
        print(" -", c.name)

    # inspect the one your code always uses
    print("\n[INFO] Inspecting collection 'vra_data'")
    col = client.get_collection("vra_data")

    inspect_collection(col)


if __name__ == "__main__":
    main()
