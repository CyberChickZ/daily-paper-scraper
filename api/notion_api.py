"""Shared Notion API helper using requests (avoids notion-client SSL issues on Python 3.14)."""
import time
import json
import requests
try:
    import yaml
except ImportError:
    yaml = None  # Not needed in Vercel (env vars used directly)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _load_dotenv(path=".env"):
    """Load .env file into os.environ."""
    import os
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


class NotionAPI:
    def __init__(self, token=None, config_path="config.yaml"):
        import os
        _load_dotenv()  # Load .env if exists
        _load_dotenv(os.path.join(os.path.dirname(config_path), ".env"))
        if token is None:
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
            token = os.environ.get("NOTION_TOKEN") or cfg["notion"].get("token") or ""
            self.db_id = os.environ.get("NOTION_DATABASE_ID") or cfg["notion"].get("database_id") or ""
        else:
            self.db_id = os.environ.get("NOTION_DATABASE_ID", "")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self._last_call = 0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < 0.35:
            time.sleep(0.35 - elapsed)
        self._last_call = time.time()

    def _request(self, method, path, body=None, retries=5):
        for attempt in range(retries):
            self._throttle()
            url = f"{NOTION_API}/{path}"
            try:
                resp = requests.request(method, url, headers=self.headers, json=body, timeout=30)
                if resp.status_code in (429, 502, 503):
                    wait = 2 ** attempt
                    print(f"  HTTP {resp.status_code}, retry {attempt+1}/{retries} in {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    print(f"  {type(e).__name__}, retry {attempt+1}/{retries} in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        raise Exception(f"Max retries exceeded for {method} {path}")

    # Database operations
    def get_database(self, db_id=None):
        return self._request("GET", f"databases/{db_id or self.db_id}")

    def update_database(self, properties, db_id=None):
        return self._request("PATCH", f"databases/{db_id or self.db_id}", {"properties": properties})

    def query_database(self, db_id=None, filter=None, sorts=None):
        """Query all pages in a database (auto-paginates)."""
        pages = []
        cursor = None
        while True:
            body = {"page_size": 100}
            if filter:
                body["filter"] = filter
            if sorts:
                body["sorts"] = sorts
            if cursor:
                body["start_cursor"] = cursor
            resp = self._request("POST", f"databases/{db_id or self.db_id}/query", body)
            pages.extend(resp["results"])
            if not resp.get("has_more"):
                break
            cursor = resp["next_cursor"]
        return pages

    # Page operations
    def create_page(self, properties, db_id=None, children=None):
        body = {"parent": {"database_id": db_id or self.db_id}, "properties": properties}
        if children:
            body["children"] = children[:100]  # API limit
        return self._request("POST", "pages", body)

    def update_page(self, page_id, properties):
        return self._request("PATCH", f"pages/{page_id}", {"properties": properties})

    def archive_page(self, page_id):
        return self._request("PATCH", f"pages/{page_id}", {"archived": True})

    # Block operations
    def append_blocks(self, block_id, children):
        """Append children blocks to a page/block (batches of 100)."""
        results = []
        for i in range(0, len(children), 100):
            batch = children[i:i+100]
            resp = self._request("PATCH", f"blocks/{block_id}/children", {"children": batch})
            results.extend(resp.get("results", []))
        return results

    def create_subpage(self, parent_page_id, title, children=None):
        """Create a page under another page (not a database)."""
        body = {
            "parent": {"page_id": parent_page_id},
            "properties": {"title": [{"text": {"content": title}}]},
        }
        if children:
            body["children"] = children[:100]
        return self._request("POST", "pages", body)

    # Helpers
    @staticmethod
    def rich_text(text, bold=False, limit=2000):
        chunks = []
        for i in range(0, len(text), limit):
            chunk = {"type": "text", "text": {"content": text[i:i+limit]}}
            if bold:
                chunk["annotations"] = {"bold": True}
            chunks.append(chunk)
        return chunks or [{"type": "text", "text": {"content": ""}}]

    @staticmethod
    def heading(level, text):
        key = f"heading_{level}"
        return {"type": key, key: {"rich_text": [{"type": "text", "text": {"content": text}}]}}

    @staticmethod
    def paragraph(text, bold=False):
        rt = NotionAPI.rich_text(text, bold=bold)
        return {"type": "paragraph", "paragraph": {"rich_text": rt}}

    @staticmethod
    def toggle(title, children=None):
        block = {
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": title}}],
            }
        }
        if children:
            block["toggle"]["children"] = children
        return block

    @staticmethod
    def callout(text, emoji="💡"):
        return {
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "icon": {"type": "emoji", "emoji": emoji},
            }
        }

    @staticmethod
    def bullet(text, bold_prefix=None):
        rt = []
        if bold_prefix:
            rt.append({"type": "text", "text": {"content": bold_prefix}, "annotations": {"bold": True}})
            rt.append({"type": "text", "text": {"content": text}})
        else:
            rt.append({"type": "text", "text": {"content": text}})
        return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt}}

    @staticmethod
    def divider():
        return {"type": "divider", "divider": {}}
