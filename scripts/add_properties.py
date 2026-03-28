#!/usr/bin/env python3
"""Add new properties to the Notion database for knowledge base features."""
from notion_api import NotionAPI


def main():
    api = NotionAPI()

    new_props = {
        "Research Line": {"select": {"options": [
            {"name": "Body Models"},
            {"name": "HPE→Mesh"},
            {"name": "Motion-Physics"},
            {"name": "Other"},
        ]}},
        "Builds On": {"relation": {
            "database_id": api.db_id,
            "type": "single_property",
            "single_property": {},
        }},
        "Evolution Note": {"rich_text": {}},
        "Followed": {"checkbox": {}},
        "Favorite": {"checkbox": {}},
    }

    result = api.update_database(new_props)
    props = result.get("properties", {})
    print("Database properties updated:")
    for name, prop in props.items():
        print(f"  {name}: {prop['type']}")


if __name__ == "__main__":
    main()
