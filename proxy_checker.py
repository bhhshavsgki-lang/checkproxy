import asyncio
import httpx
import os

# Source URLs
SOCKS4_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt"
SOCKS5_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"

# Target Filenames
SOCKS4_FILE = "socks4.txt"
SOCKS5_FILE = "socks5.txt"

# Android devices often drops bad connections quickly, 
# so we use a strict timeout to ensure only fast, highly stable proxies are kept.
TIMEOUT = 5.0 
TEST_URL = "https://httpbin.org/ip"

async def check_proxy(client: httpx.AsyncClient, proxy_url: str) -> str | None:
    """Tests if a proxy can successfully reach the internet within the timeout."""
    try:
        # Format: httpx expects socks5://username:password@host:port or socks5://host:port
        response = await client.get(TEST_URL, proxy=proxy_url, timeout=TIMEOUT)
        if response.status_code == 200:
            # Extract just the host:port string to save
            return proxy_url.split("//")[-1]
    except Exception:
        pass
    return None

async def process_protocol(url: str, protocol: str, output_file: str):
    print(f"Fetching {protocol.upper()} proxy list...")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url)
            if res.status_code != 200:
                print(f"Failed to fetch {protocol} list.")
                return
            
            # Clean up the downloaded list
            raw_proxies = [p.strip() for p in res.text.splitlines() if p.strip()]
        except Exception as e:
            print(f"Error fetching list: {e}")
            return

    print(f"Found {len(raw_proxies)} {protocol.upper()} proxies. Starting validation...")
    
    # Configure an HTTPX client tailored for proxy cycling
    # We create tasks to check them concurrently
    tasks = []
    async with httpx.AsyncClient() as client:
        for proxy in raw_proxies:
            proxy_url = f"{protocol}://{proxy}"
            tasks.append(check_proxy(client, proxy_url))
        
        results = await asyncio.gather(*tasks)
    
    # Filter out None values (failed proxies)
    working_proxies = [p for p in results if p is not None]
    
    print(f"Validation complete. Working {protocol.upper()} proxies: {len(working_proxies)}")
    
    # Save the working ones to the file
    with open(output_file, "w") as f:
        for proxy in working_proxies:
            f.write(f"{proxy}\n")

async def main():
    # Process both SOCKS4 and SOCKS5 lists
    await process_protocol(SOCKS4_URL, "socks4", SOCKS4_FILE)
    await process_protocol(SOCKS5_URL, "socks5", SOCKS5_FILE)

if __name__ == "__main__":
    asyncio.run(main())
