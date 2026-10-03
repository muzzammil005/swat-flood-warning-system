import json
import sys
from pathlib import Path

# Add backend/src to path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from interfaces.http.main import app

def export():
    schema = app.openapi()
    output_path = Path(__file__).parent.parent / "openapi.json"
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"OpenAPI schema exported to {output_path}")

if __name__ == "__main__":
    export()
