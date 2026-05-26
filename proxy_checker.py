import asyncio
import httpx
import os

# Source URLs
SOCKS4_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt"
SOCKS5_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"

# Target Filenames
SOCKS4_FILE = "socks4.txt"
SOCKS5_FILE = "socks5.txt"

# Relaxed timeout for free public proxies (8 seconds instead of 5)
TIMEOUT = 8.0 
TEST_URL = "https://httpbin.org/ip"

async def check_proxy(client: httpx.AsyncClient, proxy_url: str) -> str | None:
    """Tests if a proxy can successfully reach the internet."""
    try:
        # Explicitly pass proxy configuration via the proxy argument
        response = await client.get(TEST_URL, proxy=proxy_url, timeout=TIMEOUT)
        if response.status_code == 200:
            return proxy_url.split("//")[-1]
    except Exception:
        pass
    return None

async def process_protocol(url: str, protocol: str, output_file: str):
    print(f"--- Starting {protocol.upper()} Fetching ---")
    
    # Use a standard client to safely fetch the initial target files
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            res = await client.get(url)
            if res.status_code != 200:
                print(f"Error: HTTP status {res.status_code} while downloading source.")
                return
            
            raw_proxies = [p.strip() for p in res.text.splitlines() if p.strip()]
        except Exception as e:
            print(f"Network error while downloading list: {e}")
            return

    print(f"Found {len(raw_proxies)} raw proxies on Github source.")
    if not raw_proxies:
        print("Source list appears empty. Skipping validation.")
        return

    print(f"Validating concurrently (Timeout limit: {TIMEOUT}s)...")
    
    tasks = []
    # Force httpx to properly mount proxy extensions by using individual connections
    async with httpx.AsyncClient(verify=False) as client:
        for proxy in raw_proxies:
            proxy_url = f"{protocol}://{proxy}"
            tasks.append(check_proxy(client, proxy_url))
        
        results = await asyncio.gather(*tasks)
    
    working_proxies = [p for p in results if p is not None]
    print(f"Verification done. Live/working count: {len(working_proxies)}")
    
    # Save the file (even if empty, it ensures the script executes file changes)
    with open(output_file, "w") as f:
        for proxy in working_proxies:
            f.write(f"{proxy}\n")
    print(f"Saved working outputs into {output_file}.\n")

async def main():
    await process_protocol(SOCKS4_URL, "socks4", SOCKS4_FILE)
    await process_protocol(SOCKS5_URL, "socks5", SOCKS5_FILE)

if __name__ == "__main__":
    asyncio.run(main())
