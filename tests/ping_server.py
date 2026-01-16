
import urllib.request
import sys

URL = "http://localhost:7000/docs"

try:
    with urllib.request.urlopen(URL, timeout=2) as response:
        print(f"Server is UP. Status Code: {response.getcode()}")
except Exception as e:
    print(f"Server is DOWN. Error: {e}")
    sys.exit(1)
