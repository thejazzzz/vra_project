import chromadb

client = chromadb.HttpClient(host="localhost", port=8000)

collection = client.get_or_create_collection("test")

collection.add(
    documents=["hello world"],
    ids=["1"]
)

results = collection.query(query_texts=["hello"], n_results=1)
print(results)
