"""
C2D2 Edge Server

Routes:
  /api/*  → FastAPI backend (uvicorn on port 8000)
  /*      → Next.js frontend (next on port 3000)

Usage (Docker / Azure App Service):
  python server.py
"""
import asyncio
import os
import subprocess
import sys
from aiohttp import web, ClientSession


BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000"))
EDGE_PORT = int(os.getenv("PORT", "8080"))

BACKEND_URL  = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"


async def proxy(target_base: str, request: web.Request) -> web.Response:
    url = f"{target_base}{request.path_qs}"
    async with ClientSession() as session:
        async with session.request(
            request.method,
            url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            data=await request.read(),
        ) as resp:
            body = await resp.read()
            return web.Response(
                status=resp.status,
                headers={k: v for k, v in resp.headers.items()
                         if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")},
                body=body,
            )


async def handle(request: web.Request) -> web.Response:
    if request.path.startswith("/api") or request.path == "/health":
        return await proxy(BACKEND_URL, request)
    return await proxy(FRONTEND_URL, request)


def start_servers():
    procs = []

    # Start FastAPI
    procs.append(subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "127.0.0.1",
        "--port", str(BACKEND_PORT),
    ]))

    # Start Next.js
    procs.append(subprocess.Popen(
        ["node", "frontend/.next/standalone/server.js"],
        env={**os.environ, "PORT": str(FRONTEND_PORT)},
    ))

    return procs


async def main():
    procs = start_servers()
    app = web.Application()
    app.router.add_route("*", "/{path_info:.*}", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", EDGE_PORT)
    await site.start()
    print(f"C2D2 edge server running on :{EDGE_PORT}")

    try:
        await asyncio.Event().wait()
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    asyncio.run(main())
