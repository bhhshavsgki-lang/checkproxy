#!/usr/bin/env python3
"""
Proxy Validator Script for Android-compatible proxies
Tests SOCKS4/5 proxies and validates connectivity
"""

import asyncio
import socket
import time
import os
from urllib.parse import urlparse
import sys

try:
    import aiohttp
    import socks
    from aiohttp_socks import SocksConnector
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp-socks", "pysocks"])
    import aiohttp
    import socks
    from aiohttp_socks import SocksConnector

SOCKS5_FILE = "proxies/protocols/socks5/data.txt"
SOCKS4_FILE = "proxies/protocols/socks4/data.txt"
VALIDATED_DIR = "proxies/validated"
OUTPUT_SOCKS5 = f"{VALIDATED_DIR}/socks5_working.txt"
OUTPUT_SOCKS4 = f"{VALIDATED_DIR}/socks4_working.txt"

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 10
TOTAL_TIMEOUT = 15

TEST_URLS = [
    "http://httpbin.org/ip",
    "http://icanhazip.com",
]

class ProxyValidator:
    def __init__(self):
        self.working_proxies = {'socks5': [], 'socks4': []}
        self.tested_count = {'socks5': 0, 'socks4': 0}
        self.failed_count = {'socks5': 0, 'socks4': 0}

    def parse_proxy_url(self, proxy_string):
        """Parse proxy URL"""
        try:
            parsed = urlparse(proxy_string)
            protocol = parsed.scheme.lower()
            host = parsed.hostname
            port = parsed.port
            
            if not host or not port:
                return None
            
            try:
                socket.inet_aton(host)
            except socket.error:
                return None
            
            if not (1 <= port <= 65535):
                return None
            
            return {
                'protocol': protocol,
                'host': host,
                'port': port,
                'url': proxy_string
            }
        except:
            return None

    async def test_proxy_connection(self, proxy_info):
        """Test proxy connection"""
        if not proxy_info:
            return False
        
        try:
            connector = SocksConnector.from_url(proxy_info['url'])
            async with aiohttp.ClientSession(connector=connector) as session:
                for test_url in TEST_URLS:
                    try:
                        async with session.get(
                            test_url,
                            timeout=aiohttp.ClientTimeout(total=TOTAL_TIMEOUT),
                            allow_redirects=True
                        ) as response:
                            if response.status == 200:
                                return True
                    except:
                        continue
            return False
        except:
            return False

    async def validate_proxy(self, proxy_string):
        """Validate a single proxy"""
        proxy_info = self.parse_proxy_url(proxy_string.strip())
        
        if not proxy_info:
            return False
        
        protocol = proxy_info['protocol']
        self.tested_count[protocol] += 1
        
        is_working = await self.test_proxy_connection(proxy_info)
        
        if is_working:
            self.working_proxies[protocol].append(proxy_string.strip())
            return True
        else:
            self.failed_count[protocol] += 1
            return False

    async def validate_file(self, filepath, protocol):
        """Validate all proxies in a file"""
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filepath}")
            return
        
        print(f"\n📝 Testing {protocol.upper()} proxies...")
        
        with open(filepath, 'r') as f:
            proxies = f.readlines()
        
        print(f"   Found {len(proxies)} proxies")
        
        semaphore = asyncio.Semaphore(5)
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                return await self.validate_proxy(proxy)
        
        tasks = [test_with_semaphore(proxy) for proxy in proxies]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        total = self.tested_count[protocol]
        working = len(self.working_proxies[protocol])
        failed = self.failed_count[protocol]
        
        print(f"   Tested: {total} | Working: {working} | Failed: {failed}")
        if total > 0:
            print(f"   Success Rate: {(working / total * 100):.1f}%")

    def save_working_proxies(self):
        """Save working proxies"""
        os.makedirs(VALIDATED_DIR, exist_ok=True)
        
        if self.working_proxies['socks5']:
            with open(OUTPUT_SOCKS5, 'w') as f:
                for i, proxy in enumerate(self.working_proxies['socks5'], 1):
                    f.write(f"{i}| {proxy}\n")
            print(f"\n✨ Saved {len(self.working_proxies['socks5'])} SOCKS5 proxies")
        
        if self.working_proxies['socks4']:
            with open(OUTPUT_SOCKS4, 'w') as f:
                for i, proxy in enumerate(self.working_proxies['socks4'], 1):
                    f.write(f"{i}| {proxy}\n")
            print(f"✨ Saved {len(self.working_proxies['socks4'])} SOCKS4 proxies")
        
        summary_file = f"{VALIDATED_DIR}/validation_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("PROXY VALIDATION SUMMARY\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            f.write("SOCKS5:\n")
            f.write(f"  Tested: {self.tested_count['socks5']}\n")
            f.write(f"  Working: {len(self.working_proxies['socks5'])}\n")
            f.write(f"  Failed: {self.failed_count['socks5']}\n")
            if self.tested_count['socks5'] > 0:
                f.write(f"  Rate: {(len(self.working_proxies['socks5']) / self.tested_count['socks5'] * 100):.1f}%\n")
            f.write("\nSOCKS4:\n")
            f.write(f"  Tested: {self.tested_count['socks4']}\n")
            f.write(f"  Working: {len(self.working_proxies['socks4'])}\n")
            f.write(f"  Failed: {self.failed_count['socks4']}\n")
            if self.tested_count['socks4'] > 0:
                f.write(f"  Rate: {(len(self.working_proxies['socks4']) / self.tested_count['socks4'] * 100):.1f}%\n")
            f.write("\nAndroid Compatible Apps:\n")
            f.write("  - ProxyDroid (SOCKS4/5 direct)\n")
            f.write("  - Psiphon (custom proxy)\n")
            f.write("  - HTTP Injector (SOCKS support)\n")
            f.write("  - Shadowsocks Android (SOCKS5)\n")
            f.write("  - Termux + socat\n")

    async def run(self):
        """Main validation"""
        print("🚀 Starting Proxy Validation...")
        print("=" * 50)
        
        start_time = time.time()
        
        await self.validate_file(SOCKS5_FILE, 'socks5')
        await self.validate_file(SOCKS4_FILE, 'socks4')
        
        self.save_working_proxies()
        
        elapsed = time.time() - start_time
        print("\n" + "=" * 50)
        print(f"✅ Complete in {elapsed:.1f}s")

def main():
    validator = ProxyValidator()
    try:
        asyncio.run(validator.run())
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
