"""
Quick connection test for all Polymarket APIs.
Run from your terminal: python test_connection.py
"""
import os
import sys

def test_gamma_api():
    """Test 1: Gamma API (no auth needed)"""
    print("\n=== TEST 1: Gamma API (public, no auth) ===")
    try:
        import httpx
        resp = httpx.get("https://gamma-api.polymarket.com/markets?limit=2&active=true")
        resp.raise_for_status()
        markets = resp.json()
        print(f"  OK — fetched {len(markets)} markets")
        if markets:
            print(f"  Sample: {markets[0].get('question', 'N/A')[:80]}")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

def test_polygon_rpc():
    """Test 2: Polygon RPC (no auth needed)"""
    print("\n=== TEST 2: Polygon RPC (Web3 connection) ===")
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider("https://1rpc.io/matic"))
        block = w3.eth.block_number
        print(f"  OK — connected, latest block: {block}")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

def test_env_vars():
    """Test 3: Check env vars exist"""
    print("\n=== TEST 3: Environment Variables ===")
    pk = os.getenv("POLYGON_WALLET_PRIVATE_KEY")
    ant = os.getenv("ANTHROPIC_API_KEY")
    tav = os.getenv("TAVILY_API_KEY")
    ok = True
    if pk:
        print(f"  POLYGON_WALLET_PRIVATE_KEY: present ({pk[:6]}...{pk[-4:]})")
    else:
        print("  POLYGON_WALLET_PRIVATE_KEY: MISSING")
        ok = False
    if ant:
        print(f"  ANTHROPIC_API_KEY: present ({ant[:8]}...{ant[-4:]})")
    else:
        print("  ANTHROPIC_API_KEY: MISSING")
        ok = False
    if tav:
        print(f"  TAVILY_API_KEY: present ({tav[:8]}...{tav[-4:]})")
    else:
        print("  TAVILY_API_KEY: MISSING")
        ok = False
    return ok

def test_wallet_address():
    """Test 4: Derive wallet address from private key"""
    print("\n=== TEST 4: Wallet Address Derivation ===")
    try:
        from web3 import Web3
        pk = os.getenv("POLYGON_WALLET_PRIVATE_KEY")
        if not pk:
            print("  SKIP — no private key")
            return False
        w3 = Web3()
        account = w3.eth.account.from_key(pk)
        print(f"  OK — wallet address: {account.address}")

        # Check USDC balance on Polygon
        w3_poly = Web3(Web3.HTTPProvider("https://1rpc.io/matic"))
        balance_wei = w3_poly.eth.get_balance(account.address)
        balance_matic = w3_poly.from_wei(balance_wei, 'ether')
        print(f"  MATIC balance: {balance_matic}")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

def test_clob_auth():
    """Test 5: CLOB API authentication (the real test)"""
    print("\n=== TEST 5: Polymarket CLOB Auth ===")
    try:
        pk = os.getenv("POLYGON_WALLET_PRIVATE_KEY")
        if not pk:
            print("  SKIP — no private key")
            return False
        from py_clob_client.client import ClobClient
        client = ClobClient(
            "https://clob.polymarket.com",
            key=pk,
            chain_id=137
        )
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        print(f"  OK — CLOB API authenticated")
        print(f"  API key: {creds.api_key[:8]}...")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

def test_anthropic():
    """Test 6: Anthropic API connection"""
    print("\n=== TEST 6: Anthropic API ===")
    try:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            print("  SKIP — no ANTHROPIC_API_KEY")
            return False
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage
        llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
        result = llm.invoke([HumanMessage(content="Reply with exactly: CONNECTION_OK")])
        print(f"  OK — claude-sonnet-4-6 responded: {result.content.strip()[:50]}")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

def test_tavily():
    """Test 7: Tavily web search"""
    print("\n=== TEST 7: Tavily Web Search ===")
    try:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            print("  SKIP — no TAVILY_API_KEY")
            return False
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        result = client.search("Polymarket prediction markets", max_results=2)
        results_list = result.get("results", [])
        print(f"  OK — got {len(results_list)} results")
        if results_list:
            print(f"  Sample: {results_list[0].get('title', 'N/A')[:80]}")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Cognitive Trading Agent — Connection Tests")
    print("=" * 50)

    results = {}
    results["Gamma API"] = test_gamma_api()
    results["Polygon RPC"] = test_polygon_rpc()
    results["Env Vars"] = test_env_vars()
    results["Wallet"] = test_wallet_address()
    results["CLOB Auth"] = test_clob_auth()
    results["Anthropic"] = test_anthropic()
    results["Tavily"] = test_tavily()

    print("\n" + "=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {status} — {name}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  {passed}/{total} tests passed")