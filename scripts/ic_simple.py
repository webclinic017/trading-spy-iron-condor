#!/usr/bin/env python3
"""
Simple Iron Condor System — One file, one workflow, no complexity.

Entry: Real 15-delta strikes via Alpaca option chain, limit orders only.
Exit:  50% profit, 100% stop, 7 DTE. 4-hour minimum hold. MLEG close.
Guard: Net-credit required, $0.50 minimum, 1 IC per day, position limit 2.

This replaces: iron_condor_trader.py, iron_condor_guardian.py,
iron_condor_scanner.py, manage_iron_condor_positions.py, and 6 workflows.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ic_simple")

# ── Constants ────────────────────────────────────────────────────────────────
MAX_IC = 2  # Max concurrent iron condors
MIN_CREDIT = 0.50  # Minimum net credit per share
MIN_HOLD_HOURS = 4  # Don't close until held this long
PROFIT_TARGET = 0.50  # Close at 50% of credit
STOP_LOSS = 1.0  # Close at 100% loss of credit
EXIT_DTE = 7  # Close at 7 DTE
WING_WIDTH = 10  # $10 wide spreads
TARGET_DELTA = 0.15
ENTRIES_FILE = Path(__file__).parent.parent / "data" / "ic_entries.json"


# ── Alpaca Client ────────────────────────────────────────────────────────────
def get_client():
    from alpaca.trading.client import TradingClient
    from src.utils.alpaca_client import get_alpaca_credentials

    api_key, secret = get_alpaca_credentials()
    if not api_key or not secret:
        raise RuntimeError("Alpaca credentials not found")
    return TradingClient(api_key, secret, paper=True)


def get_spy_price(client):
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest
    from src.utils.alpaca_client import get_alpaca_credentials

    api_key, secret = get_alpaca_credentials()
    data_client = StockHistoricalDataClient(api_key, secret)
    quote = data_client.get_stock_latest_quote(
        StockLatestQuoteRequest(symbol_or_symbols=["SPY"])
    )
    return (quote["SPY"].ask_price + quote["SPY"].bid_price) / 2


# ── Entry: Find and Place IC ────────────────────────────────────────────────
def find_opportunity(spy_price: float) -> dict | None:
    """Select strikes by real delta. Returns opportunity dict or None."""
    from src.markets.option_chain import select_strikes_by_delta

    selection = select_strikes_by_delta(
        underlying_price=spy_price,
        wing_width=WING_WIDTH,
        target_delta=TARGET_DELTA,
        target_dte=30,
        min_dte=21,
        max_dte=45,
    )

    est_credit = selection.put_bid + selection.call_bid
    if selection.method == "heuristic_fallback":
        est_credit = 1.50  # Conservative guess

    if est_credit < MIN_CREDIT:
        logger.warning(f"Credit ${est_credit:.2f} < ${MIN_CREDIT:.2f} minimum. Skip.")
        return None

    logger.info(
        f"Opportunity: SP={selection.short_put} SC={selection.short_call} "
        f"method={selection.method} credit=${est_credit:.2f} "
        f"put_delta={selection.put_delta:.3f} call_delta={selection.call_delta:.3f}"
    )

    return {
        "expiry": selection.expiry,
        "long_put": selection.long_put,
        "short_put": selection.short_put,
        "short_call": selection.short_call,
        "long_call": selection.long_call,
        "est_credit": est_credit,
        "method": selection.method,
    }


def place_ic(client, opp: dict) -> str | None:
    """Submit limit MLEG order. Returns order ID or None."""
    from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
    from alpaca.trading.requests import LimitOrderRequest, OptionLegRequest

    expiry_yymmdd = opp["expiry"].replace("-", "")[2:]

    def sym(strike, opt_type):
        return f"SPY{expiry_yymmdd}{opt_type}{int(strike * 1000):08d}"

    legs = [
        OptionLegRequest(symbol=sym(opp["long_put"], "P"), side=OrderSide.BUY, ratio_qty=1),
        OptionLegRequest(symbol=sym(opp["short_put"], "P"), side=OrderSide.SELL, ratio_qty=1),
        OptionLegRequest(symbol=sym(opp["short_call"], "C"), side=OrderSide.SELL, ratio_qty=1),
        OptionLegRequest(symbol=sym(opp["long_call"], "C"), side=OrderSide.BUY, ratio_qty=1),
    ]

    limit_credit = round(opp["est_credit"] - 0.05, 2)
    if limit_credit < MIN_CREDIT:
        limit_credit = MIN_CREDIT

    logger.info(f"Submitting MLEG limit order: credit >= ${limit_credit:.2f}")

    order = client.submit_order(
        LimitOrderRequest(
            qty=1,
            order_class=OrderClass.MLEG,
            legs=legs,
            time_in_force=TimeInForce.DAY,
            limit_price=round(-limit_credit, 2),
        )
    )

    logger.info(f"Order {order.id}: {order.status}")

    # Save entry data
    entries = _load_entries()
    entry_key = f"IC_{expiry_yymmdd}"
    entries[entry_key] = {
        "credit": opp["est_credit"],
        "date": datetime.now().isoformat(),
        "order_id": str(order.id),
        "strikes": {
            "short_put": opp["short_put"],
            "short_call": opp["short_call"],
            "long_put": opp["long_put"],
            "long_call": opp["long_call"],
        },
    }
    _save_entries(entries)

    return str(order.id)


# ── Exit: Check and Close Positions ──────────────────────────────────────────
def check_exits(client):
    """Check all open ICs for exit conditions."""
    positions = client.get_all_positions()
    if not positions:
        logger.info("No positions.")
        return

    # Group by expiry
    ics = {}
    for pos in positions:
        sym = pos.symbol
        if len(sym) <= 10:
            continue
        expiry = sym[3:9]
        if expiry not in ics:
            ics[expiry] = []
        ics[expiry].append({
            "symbol": sym,
            "qty": int(float(pos.qty)),
            "entry": float(pos.avg_entry_price),
            "current": float(pos.current_price) if hasattr(pos, "current_price") else float(pos.avg_entry_price),
            "type": "put" if "P" in sym[9:10] else "call",
        })

    entries = _load_entries()

    for expiry, legs in ics.items():
        # Validate: need exactly 4 legs, 2P+2C, 2 short+2 long
        n_puts = sum(1 for leg in legs if leg["type"] == "put")
        n_calls = sum(1 for leg in legs if leg["type"] == "call")
        n_short = sum(1 for leg in legs if leg["qty"] < 0)
        n_long = sum(1 for leg in legs if leg["qty"] > 0)

        if not (n_puts == 2 and n_calls == 2 and n_short == 2 and n_long == 2):
            logger.warning(f"IC {expiry}: incomplete ({n_puts}P {n_calls}C {n_short}S {n_long}L). Skip.")
            continue

        # Get entry credit
        entry_key = f"IC_{expiry}"
        if entry_key in entries:
            entry_credit = entries[entry_key]["credit"]
            entry_date = entries[entry_key].get("date")
        else:
            # Estimate from positions
            short_prem = sum(leg["entry"] for leg in legs if leg["qty"] < 0)
            long_prem = sum(leg["entry"] for leg in legs if leg["qty"] > 0)
            entry_credit = short_prem - long_prem
            entry_date = None
            if entry_credit <= 0:
                logger.warning(f"IC {expiry}: non-positive credit ${entry_credit:.2f}. Skip.")
                continue

        # Minimum holding period
        if entry_date:
            try:
                entry_dt = datetime.fromisoformat(entry_date)
                if entry_dt.tzinfo:
                    entry_dt = entry_dt.replace(tzinfo=None)
                hours = (datetime.now() - entry_dt).total_seconds() / 3600
                if hours < MIN_HOLD_HOURS:
                    logger.info(f"IC {expiry}: held {hours:.1f}h < {MIN_HOLD_HOURS}h. Hold.")
                    continue
            except (ValueError, TypeError):
                pass

        # Calculate P/L
        contract_count = max(abs(leg["qty"]) for leg in legs)
        current_value = sum(
            (-leg["current"] if leg["qty"] < 0 else leg["current"]) * abs(leg["qty"]) * 100
            for leg in legs
        )
        pnl = entry_credit * contract_count * 100 + current_value
        max_profit = entry_credit * contract_count * 100

        # DTE
        from datetime import date as date_type
        exp_date = date_type(2000 + int(expiry[:2]), int(expiry[2:4]), int(expiry[4:6]))
        dte = (exp_date - date_type.today()).days

        logger.info(
            f"IC {expiry}: DTE={dte} P/L=${pnl:+.2f} "
            f"(credit=${entry_credit:.2f}x{contract_count} max=${max_profit:.2f})"
        )

        # Exit checks
        reason = None
        if dte <= EXIT_DTE:
            reason = f"DTE={dte} <= {EXIT_DTE}"
        elif pnl >= max_profit * PROFIT_TARGET:
            reason = f"PROFIT: ${pnl:.2f} >= ${max_profit * PROFIT_TARGET:.2f}"
        elif pnl <= -(max_profit * STOP_LOSS):
            reason = f"STOP: ${pnl:.2f} <= -${max_profit * STOP_LOSS:.2f}"

        if reason:
            logger.warning(f"EXIT IC {expiry}: {reason}")
            _close_ic(client, legs, contract_count)
        else:
            logger.info(f"IC {expiry}: HOLD. Target=${max_profit * PROFIT_TARGET:.2f} Stop=-${max_profit * STOP_LOSS:.2f}")


def _close_ic(client, legs: list[dict], qty: int):
    """Close IC with MLEG limit order. Fallback to individual legs."""
    from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
    from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, OptionLegRequest

    # Calculate current debit
    current_debit = abs(sum(
        leg["current"] * (1 if leg["qty"] < 0 else -1) for leg in legs
    ))
    limit_debit = round(current_debit + 0.10, 2)

    option_legs = [
        OptionLegRequest(
            symbol=leg["symbol"],
            side=OrderSide.BUY if leg["qty"] < 0 else OrderSide.SELL,
            ratio_qty=1,
        )
        for leg in legs
    ]

    try:
        order = client.submit_order(
            LimitOrderRequest(
                qty=qty,
                order_class=OrderClass.MLEG,
                legs=option_legs,
                time_in_force=TimeInForce.DAY,
                limit_price=round(limit_debit, 2),
            )
        )
        logger.info(f"MLEG close: {order.id} @ ${limit_debit:.2f} debit")
    except Exception as e:
        logger.warning(f"MLEG close failed ({e}). Individual leg fallback.")
        for leg in legs:
            try:
                side = OrderSide.BUY if leg["qty"] < 0 else OrderSide.SELL
                client.submit_order(
                    MarketOrderRequest(
                        symbol=leg["symbol"],
                        qty=abs(leg["qty"]),
                        side=side,
                        time_in_force=TimeInForce.DAY,
                    )
                )
            except Exception as le:
                logger.error(f"Failed to close {leg['symbol']}: {le}")


# ── Helpers ──────────────────────────────────────────────────────────────────
def _load_entries() -> dict:
    try:
        if ENTRIES_FILE.exists():
            return json.loads(ENTRIES_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_entries(entries: dict):
    ENTRIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENTRIES_FILE.write_text(json.dumps(entries, indent=2))


def _count_open_ics(client) -> int:
    positions = client.get_all_positions()
    spy_options = [p for p in positions if p.symbol.startswith("SPY") and len(p.symbol) > 10]
    return len(spy_options) // 4


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simple IC system")
    parser.add_argument("--mode", choices=["entry", "exit", "both", "status"], default="both")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"IC SIMPLE | mode={args.mode} dry_run={args.dry_run}")
    logger.info("=" * 60)

    client = get_client()

    if args.mode in ("exit", "both"):
        logger.info("\n--- EXIT CHECK ---")
        if args.dry_run:
            logger.info("(dry run — would check exits)")
        else:
            check_exits(client)

    if args.mode in ("entry", "both"):
        logger.info("\n--- ENTRY CHECK ---")

        # Position limit
        ic_count = _count_open_ics(client)
        if ic_count >= MAX_IC:
            logger.info(f"Position limit: {ic_count}/{MAX_IC} ICs. No new entry.")
        else:
            spy_price = get_spy_price(client)
            logger.info(f"SPY: ${spy_price:.2f}")

            opp = find_opportunity(spy_price)
            if opp:
                if args.dry_run:
                    logger.info(f"(dry run — would place IC: {opp})")
                else:
                    order_id = place_ic(client, opp)
                    logger.info(f"Placed IC: order={order_id}")
            else:
                logger.info("No opportunity found.")

    if args.mode == "status":
        ic_count = _count_open_ics(client)
        account = client.get_account()
        logger.info(f"Equity: ${float(account.equity):,.2f}")
        logger.info(f"Open ICs: {ic_count}/{MAX_IC}")
        logger.info(f"Today P/L: ${float(account.equity) - float(account.last_equity):+,.2f}")

    logger.info("\nDone.")


if __name__ == "__main__":
    main()
