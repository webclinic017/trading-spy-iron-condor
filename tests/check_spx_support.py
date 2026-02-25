from src.utils.alpaca_client import get_alpaca_credentials
from alpaca.data.requests import OptionChainRequest
from alpaca.data.historical.option import OptionHistoricalDataClient

key, secret = get_alpaca_credentials()
if not key:
    print("No Alpaca keys found")
    exit(1)

client = OptionHistoricalDataClient(key, secret)

def check_symbol(sym):
    try:
        req = OptionChainRequest(underlying_symbol=sym)
        res = client.get_option_chain(req)
        print(f"{sym} chain retrieved, {len(res)} contracts")
    except Exception as e:
        print(f"Data fetch error for {sym}: {e}")

check_symbol("SPY")
check_symbol("XSP")
check_symbol("SPX")
check_symbol("SPXW")
