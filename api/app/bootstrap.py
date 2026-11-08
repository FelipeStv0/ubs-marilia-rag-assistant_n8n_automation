from .collector import ingest_all

if __name__ == "__main__":
    import json
    print(json.dumps(ingest_all(), ensure_ascii=False, indent=2))
