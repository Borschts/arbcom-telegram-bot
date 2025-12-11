import asyncio
import httpx
import socket
import sys
import certifi
import ssl

URL = "https://api.telegram.org"

async def test_connection():
    print(f"Testing connection to {URL}...")
    print(f"Python version: {sys.version}")
    print(f"httpx version: {httpx.__version__}")
    print(f"certifi where: {certifi.where()}")
    
    # DNS Resolution
    try:
        hostname = "api.telegram.org"
        ip = socket.gethostbyname(hostname)
        print(f"DNS Resolution for {hostname}: {ip}")
    except Exception as e:
        print(f"DNS Resolution FAILED: {e}")

    # SSL Context
    try:
        ctx = ssl.create_default_context()
        print(f"Default SSL Context: {ctx.verify_mode}")
    except Exception as e:
        print(f"SSL Context Creation FAILED: {e}")

    # Async Request
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{URL}/bot8574806079:AAG03WruUKfddvXgd9-rtyAbPCkf7RgHgXM/getMe", timeout=10)
            print(f"Async Request Status: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Async Request FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
