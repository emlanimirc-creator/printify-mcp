import os
import json
import httpx
import uvicorn
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

# Initialize FastMCP Server
mcp = FastMCP("Printify")

BASE_URL = "https://api.printify.com/v1"
API_TOKEN = os.environ.get("PRINTIFY_API_TOKEN")

def get_headers() -> Dict[str, str]:
    if not API_TOKEN:
        raise ValueError("PRINTIFY_API_TOKEN environment variable is not set.")
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Printify-MCP-Server/1.0",
    }

# ==========================================
# 1. SHOPS
# ==========================================
@mcp.tool()
async def list_shops() -> str:
    """Retrieve all Printify shops connected to the account."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BASE_URL}/shops.json", headers=get_headers())
        res.raise_for_status()
        return json.dumps(res.json(), indent=2)

# ==========================================
# 2. CATALOG & BLUEPRINTS
# ==========================================
@mcp.tool()
async def list_blueprints() -> str:
    """List available product blueprints from the Printify catalog."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BASE_URL}/catalog/blueprints.json", headers=get_headers())
        res.raise_for_status()
        blueprints = [{"id": b["id"], "title": b["title"], "brand": b.get("brand")} for b in res.json()]
        return json.dumps(blueprints, indent=2)

@mcp.tool()
async def get_print_providers(blueprint_id: int) -> str:
    """Get print providers supporting a specific blueprint."""
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/catalog/blueprints/{blueprint_id}/print_providers.json"
        res = await client.get(url, headers=get_headers())
        res.raise_for_status()
        return json.dumps(res.json(), indent=2)

@mcp.tool()
async def get_blueprint_variants(blueprint_id: int, print_provider_id: int) -> str:
    """List available variants (sizes, colors, pricing) for a blueprint and print provider."""
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json"
        res = await client.get(url, headers=get_headers())
        res.raise_for_status()
        return json.dumps(res.json(), indent=2)

# ==========================================
# 3. UPLOADS / ARTWORK
# ==========================================
@mcp.tool()
async def upload_artwork_url(file_name: str, url: str) -> str:
    """Upload an artwork image to Printify from a public image URL."""
    payload = {"file_name": file_name, "url": url}
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{BASE_URL}/uploads/images.json", headers=get_headers(), json=payload)
        res.raise_for_status()
        data = res.json()
        return json.dumps({"image_id": data.get("id"), "file_name": data.get("file_name")}, indent=2)

# ==========================================
# 4. PRODUCTS
# ==========================================
@mcp.tool()
async def list_products(shop_id: int, limit: int = 10, page: int = 1) -> str:
    """List existing products inside a specific Printify shop."""
    params = {"limit": limit, "page": page}
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/shops/{shop_id}/products.json"
        res = await client.get(url, headers=get_headers(), params=params)
        res.raise_for_status()
        return json.dumps(res.json(), indent=2)

@mcp.tool()
async def create_product(
    shop_id: int,
    title: str,
    description: str,
    blueprint_id: int,
    print_provider_id: int,
    variants: List[Dict[str, Any]],
    print_areas: List[Dict[str, Any]],
) -> str:
    """Create a new product in a Printify shop."""
    payload = {
        "title": title,
        "description": description,
        "blueprint_id": blueprint_id,
        "print_provider_id": print_provider_id,
        "variants": variants,
        "print_areas": print_areas
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BASE_URL}/shops/{shop_id}/products.json"
        res = await client.post(url, headers=get_headers(), json=payload)
        res.raise_for_status()
        return json.dumps(res.json(), indent=2)

# Expose Starlette app
app = mcp.sse_app()

# Enable CORS for Gemini web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

async def root_health(request):
    return JSONResponse({"status": "ok", "mcp": "Printify", "sse_endpoint": "/sse"})

app.routes.append(Route("/", root_health))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
