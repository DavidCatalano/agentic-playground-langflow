import argparse
import json
import os
import urllib.request
from pathlib import Path


def load_dotenv(filepath=".env"):
    for line in Path(filepath).read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

load_dotenv()

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = os.getenv("WEAVIATE_PORT", "8181")
BASE_URL = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"
SCHEMA_DIR = Path("config/weaviate")
SAMPLE_TAG = "sample"

def schema_exists(collection):
    try:
        with urllib.request.urlopen(f"{BASE_URL}/v1/schema") as response:
            schema = json.load(response)
            return any(cls["class"] == collection for cls in schema.get("classes", []))
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False

def add_class(collection_arg):
    # Accept with or without .json
    collection = collection_arg.replace(".json", "")
    filename = SCHEMA_DIR / f"{collection}.json"
    if not filename.exists():
        print(f"Schema file not found: {filename}")
        return

    if schema_exists(collection):
        print(f"Schema '{collection}' already exists. Skipping.")
        return

    try:
        with open(filename) as f:
            data = f.read()
        req = urllib.request.Request(f"{BASE_URL}/v1/schema", data=data.encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            print(f"Schema '{collection}' created: {response.status}")
    except Exception as e:
        print(f"Failed to add schema '{collection}': {e}")

def add_sample(collection):
    sample_globals = {}
    sample_file = Path(f"config/weaviate/{collection}_samples.py")
    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        return
    exec(sample_file.read_text(), sample_globals)
    samples = sample_globals.get(f"{collection.upper()}_SAMPLES")
    if not samples:
        print(f"Sample data variable '{collection.upper()}_SAMPLES' not found.")
        return

    name_to_uuid = {}

    # Insert all sample memories
    for mem in samples["memories"]:
        properties = {k: v for k, v in mem.items() if k not in ("name", "related_to")}
        tags = set(properties.get("tags", []))
        tags.add(SAMPLE_TAG)
        properties["tags"] = list(tags)
        obj = {
            "class": collection,
            "properties": properties
        }
        try:
            req = urllib.request.Request(f"{BASE_URL}/v1/objects",
                                         data=json.dumps(obj).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as res:
                result = json.load(res)
                obj_id = result.get("id")
                print(f"Inserted '{mem['name']}' as {obj_id}")
                name_to_uuid[mem["name"]] = obj_id
        except Exception as e:
            print(f"Failed to insert '{mem['name']}': {e}")

    # Update relationships using GET + PUT
    for source, targets in samples.get("relations", {}).items():
        if not targets:
            continue

        obj_id = name_to_uuid.get(source)
        if not obj_id:
            print(f"  ⚠️ Skipping '{source}' (not found)")
            continue

        # Step 1: GET the full object
        try:
            get_url = f"{BASE_URL}/v1/objects/{obj_id}"
            with urllib.request.urlopen(get_url) as res:
                obj_data = json.load(res)
        except Exception as e:
            print(f"  ❌ Failed to fetch object for '{source}': {e}")
            continue

        # Step 2: Modify relatedMemories
        beacon_refs = [{"beacon": f"weaviate://localhost/{collection}/{name_to_uuid[t]}"} for t in targets if t in name_to_uuid]
        obj_data["properties"]["relatedMemories"] = beacon_refs

        # Step 3: PUT the full object back
        try:
            put_url = f"{BASE_URL}/v1/objects/{obj_id}"
            req = urllib.request.Request(put_url,
                                         data=json.dumps(obj_data).encode("utf-8"),
                                         headers={"Content-Type": "application/json"},
                                         method="PUT")
            with urllib.request.urlopen(req) as res:
                print(f"Updated relations for '{source}'")
        except Exception as e:
            print(f"  ❌ Failed to update relations for '{source}': {e}")


def clear_sample(collection):
    gql_query = {
        "query": f"""
        {{
            Get {{
                {collection}(where: {{
                    path: ["tags"],
                    operator: ContainsAny,
                    valueText: ["{SAMPLE_TAG}"]
                }}) {{
                    _additional {{
                        id
                    }}
                }}
            }}
        }}
        """
    }

    try:
        req = urllib.request.Request(f"{BASE_URL}/v1/graphql",
                                     data=json.dumps(gql_query).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            data = json.load(res)
            results = data.get("data", {}).get("Get", {}).get(collection, [])
            ids = [obj["_additional"]["id"] for obj in results]

    except Exception as e:
        print(f"❌ Failed to fetch sample data: {e}")
        return

    if not ids:
        print(f"✅ No sample-tagged records found for '{collection}'")
        return

    print(f"🧹 Deleting {len(ids)} objects tagged as '{SAMPLE_TAG}'...")
    for obj_id in ids:
        try:
            del_req = urllib.request.Request(f"{BASE_URL}/v1/objects/{obj_id}", method="DELETE")
            with urllib.request.urlopen(del_req) as res:
                print(f"  ✔ Deleted object {obj_id}")
        except Exception as e:
            print(f"  ❌ Failed to delete object {obj_id}: {e}")


def clear_all(collection):
    gql_query = {
        "query": f"""
        {{
            Get {{
                {collection}(limit: 1000) {{
                    _additional {{
                        id
                    }}
                }}
            }}
        }}
        """
    }

    try:
        req = urllib.request.Request(f"{BASE_URL}/v1/graphql",
                                     data=json.dumps(gql_query).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            data = json.load(res)
            results = data.get("data", {}).get("Get", {}).get(collection, [])
            ids = [obj["_additional"]["id"] for obj in results]
    except Exception as e:
        print(f"❌ Failed to fetch objects in '{collection}': {e}")
        return

    if not ids:
        print(f"✅ No records found in '{collection}'")
        return

    print(f"🔥 Deleting all {len(ids)} records in collection '{collection}'...")
    for obj_id in ids:
        try:
            del_req = urllib.request.Request(f"{BASE_URL}/v1/objects/{obj_id}", method="DELETE")
            with urllib.request.urlopen(del_req) as res:
                print(f"  ✔ Deleted object {obj_id}")
        except Exception as e:
            print(f"  ❌ Failed to delete object {obj_id}: {e}")


def print_info():
    print("📦 Schema found on server:")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/v1/schema") as response:
            schema = json.load(response)
            for cls in schema.get("classes", []):
                print(f"  - {cls['class']}")
    except Exception as e:
        print(f"  Error fetching schema: {e}")

    print("📁 Schema files found in ./config/weaviate/:")
    for file in sorted(SCHEMA_DIR.glob("*.json")):
        print(f"  - {file.name}")

    print("🛠 Commands:")
    print("  --add-class <Collection>      Add schema from JSON (e.g. Memory_v1)")
    print("  --add-sample <Collection>     Add sample data from corresponding _samples.py")
    print("  --clear-sample <Collection>   Delete objects tagged as 'sample'")
    print("  --clear-all <Collection>      Delete all objects in collection")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--add-class", metavar="COLLECTION", help="Add schema class from JSON")
    parser.add_argument("--add-sample", metavar="COLLECTION", help="Add sample memories from a .py file")
    parser.add_argument("--clear-sample", metavar="COLLECTION", help="Delete all objects with sample tag")
    parser.add_argument("--clear-all", metavar="COLLECTION", help="Delete all objects in collection")

    args = parser.parse_args()
    if not any(vars(args).values()):
        print_info()
    if args.add_class:
        add_class(args.add_class)
    if args.add_sample:
        add_sample(args.add_sample)
    if args.clear_sample:
        clear_sample(args.clear_sample)
    if args.clear_all:
        clear_all(args.clear_all)

if __name__ == "__main__":
    main()
