from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest
from src.utils.alpaca_client import get_alpaca_credentials


def test_xsp_execution():
    key, secret = get_alpaca_credentials()
    if not key:
        print("No Alpaca credentials found.")
        return

    # Check if we are in paper mode
    trading_client = TradingClient(key, secret, paper=True)
    data_client = OptionHistoricalDataClient(key, secret)

    print("Fetching XSP option chain...")
    req = OptionChainRequest(underlying_symbol="SPX")
    try:
        chain = data_client.get_option_chain(req)
        print(f"Successfully fetched {len(chain)} SPX contracts.")
    except Exception as e:
        print(f"Failed to fetch SPX chain: {e}")
        return

    # To test execution routing, we need a valid OCC symbol.
    target_contract = None
    for contract, data in chain.items():
        if "P" in contract and contract.startswith("SPX"):
            target_contract = contract
            break

    if not target_contract:
        print("No suitable SPX put contract found in chain.")
        return

    print(f"Attempting to route a test buy order for 1 contract of {target_contract}...")

    # We will place a limit order at $0.01 so it doesn't actually fill,
    # but Alpaca will tell us if index options are restricted.
    order_req = LimitOrderRequest(
        symbol=target_contract,
        qty=1,
        side=OrderSide.BUY,
        type="limit",
        limit_price=0.01,
        time_in_force=TimeInForce.DAY
    )

    try:
        order = trading_client.submit_order(order_req)
        print(f"SUCCESS: Order submitted. ID: {order.id}, Status: {order.status}")

        print("Canceling the test order...")
        trading_client.cancel_order_by_id(order.id)
        print("Order canceled.")
    except Exception as e:
        print(f"ROUTING FAILED: Alpaca rejected the index option order. Error: {e}")

if __name__ == "__main__":
    test_xsp_execution()
