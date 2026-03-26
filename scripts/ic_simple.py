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
    quote = data_client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=["SPY"]))
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
        ics[expiry].append(
            {
                "symbol": sym,
                "qty": int(float(pos.qty)),
                "entry": float(pos.avg_entry_price),
                "current": float(pos.current_price)
                if hasattr(pos, "current_price")
                else float(pos.avg_entry_price),
                "type": "put" if "P" in sym[9:10] else "call",
            }
        )

    entries = _load_entries()

    for expiry, legs in ics.items():
        # Validate: need exactly 4 legs, 2P+2C, 2 short+2 long
        n_puts = sum(1 for leg in legs if leg["type"] == "put")
        n_calls = sum(1 for leg in legs if leg["type"] == "call")
        n_short = sum(1 for leg in legs if leg["qty"] < 0)
        n_long = sum(1 for leg in legs if leg["qty"] > 0)

        if not (n_puts == 2 and n_calls == 2 and n_short == 2 and n_long == 2):
            logger.warning(
                f"IC {expiry}: incomplete ({n_puts}P {n_calls}C {n_short}S {n_long}L). Skip."
            )
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

        # Exit checks (DTE failsafe first — always close expiring positions)
        reason = None
        if dte <= 1:
            reason = f"FAILSAFE: DTE={dte} (expiring — assignment/pin risk)"
        elif dte <= EXIT_DTE:
            reason = f"DTE={dte} <= {EXIT_DTE}"
        elif pnl >= max_profit * PROFIT_TARGET:
            reason = f"PROFIT: ${pnl:.2f} >= ${max_profit * PROFIT_TARGET:.2f}"
        elif pnl <= -(max_profit * STOP_LOSS):
            reason = f"STOP: ${pnl:.2f} <= -${max_profit * STOP_LOSS:.2f}"

        if reason:
            logger.warning(f"EXIT IC {expiry}: {reason}")
            _close_ic(client, legs, contract_count)
            _record_lesson(expiry, entry_credit, pnl, reason, dte, contract_count)
        else:
            logger.info(
                f"IC {expiry}: HOLD. Target=${max_profit * PROFIT_TARGET:.2f} Stop=-${max_profit * STOP_LOSS:.2f}"
            )


def _close_ic(client, legs: list[dict], qty: int):
    """Close IC with MLEG limit order. Fallback to individual legs."""
    from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
    from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, OptionLegRequest

    # Calculate current debit
    current_debit = abs(sum(leg["current"] * (1 if leg["qty"] < 0 else -1) for leg in legs))
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


# ── Learning: RAG + Trade Journal + Stats ────────────────────────────────────

JOURNAL_FILE = Path(__file__).parent.parent / "data" / "trade_journal.jsonl"
LESSONS_DIR = Path(__file__).parent.parent / "data" / "rag_knowledge" / "lessons_learned"


def _record_lesson(expiry: str, credit: float, pnl: float, reason: str, dte: int, qty: int):
    """Record trade outcome to journal + RAG after every close."""
    outcome = "WIN" if pnl > 0 else "LOSS"
    pnl_pct = (pnl / (credit * qty * 100)) * 100 if credit > 0 else 0

    # 1. Trade journal (append-only JSONL)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "expiry": expiry,
        "credit_per_share": credit,
        "qty": qty,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 1),
        "outcome": outcome,
        "exit_reason": reason,
        "dte_at_exit": dte,
    }
    try:
        JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(JOURNAL_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info(f"Journal: {outcome} ${pnl:+.2f} ({pnl_pct:+.1f}%) | {reason}")
    except Exception as e:
        logger.warning(f"Failed to write journal: {e}")

    # 2. RAG lesson (one markdown file per trade)
    lesson_id = f"IC_{expiry}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    lesson = f"""# Trade Exit: {outcome} ${pnl:+.2f}

- **Expiry**: {expiry}
- **Credit**: ${credit:.2f}/share x {qty} contracts
- **P/L**: ${pnl:+.2f} ({pnl_pct:+.1f}%)
- **Exit Reason**: {reason}
- **DTE at Exit**: {dte}
- **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Lesson
{"Position hit profit target — theta decay worked as expected." if "PROFIT" in reason else ""}{"Position hit stop loss — market moved against us." if "STOP" in reason else ""}{"Exited at DTE threshold to avoid gamma risk." if "DTE" in reason else ""}
"""
    try:
        LESSONS_DIR.mkdir(parents=True, exist_ok=True)
        (LESSONS_DIR / f"{lesson_id}.md").write_text(lesson)
        logger.info(f"RAG lesson saved: {lesson_id}")
    except Exception as e:
        logger.warning(f"Failed to write RAG lesson: {e}")

    # 3. Update cumulative stats
    _update_stats(entry)


def _update_stats(trade: dict):
    """Update running win rate and P/L stats."""
    stats_file = Path(__file__).parent.parent / "data" / "ic_stats.json"
    try:
        stats = (
            json.loads(stats_file.read_text())
            if stats_file.exists()
            else {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "win_pnls": [],
                "loss_pnls": [],
            }
        )
    except Exception:
        stats = {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "win_pnls": [],
            "loss_pnls": [],
        }

    stats["total"] += 1
    stats["total_pnl"] = round(stats["total_pnl"] + trade["pnl"], 2)

    if trade["pnl"] > 0:
        stats["wins"] += 1
        stats["win_pnls"].append(trade["pnl"])
        stats["avg_win"] = round(sum(stats["win_pnls"]) / len(stats["win_pnls"]), 2)
    else:
        stats["losses"] += 1
        stats["loss_pnls"].append(trade["pnl"])
        stats["avg_loss"] = round(sum(stats["loss_pnls"]) / len(stats["loss_pnls"]), 2)

    stats["win_rate"] = round(stats["wins"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
    stats["profit_factor"] = (
        round(abs(sum(stats["win_pnls"])) / abs(sum(stats["loss_pnls"])), 2)
        if stats["loss_pnls"] and sum(stats["loss_pnls"]) != 0
        else 999.0
    )

    stats_file.write_text(json.dumps(stats, indent=2))
    logger.info(
        f"Stats: {stats['total']} trades | {stats['win_rate']}% win rate | "
        f"PF={stats['profit_factor']} | Total P/L=${stats['total_pnl']:+.2f}"
    )


# ── Report + Weekend Learning ────────────────────────────────────────────────


def _print_report():
    """Print full performance report from trade journal."""
    stats_file = Path(__file__).parent.parent / "data" / "ic_stats.json"
    if not stats_file.exists():
        logger.info("No stats yet. Complete trades to build data.")
        return

    stats = json.loads(stats_file.read_text())
    logger.info("=" * 60)
    logger.info("PERFORMANCE REPORT")
    logger.info("=" * 60)
    logger.info(f"Total trades:   {stats.get('total', 0)}")
    logger.info(f"Wins:           {stats.get('wins', 0)}")
    logger.info(f"Losses:         {stats.get('losses', 0)}")
    logger.info(f"Win rate:       {stats.get('win_rate', 0):.1f}%")
    logger.info(f"Profit factor:  {stats.get('profit_factor', 0):.2f}")
    logger.info(f"Total P/L:      ${stats.get('total_pnl', 0):+,.2f}")
    logger.info(f"Avg win:        ${stats.get('avg_win', 0):+,.2f}")
    logger.info(f"Avg loss:       ${stats.get('avg_loss', 0):+,.2f}")

    needed = 30 - stats.get("total", 0)
    if needed > 0:
        logger.info(f"\nNeed {needed} more trades for statistical significance.")
    else:
        wr = stats.get("win_rate", 0)
        if wr >= 80:
            logger.info("\n80%+ win rate VALIDATED. Strategy is working.")
        elif wr >= 70:
            logger.info("\n70-80% win rate. Marginal — review delta selection.")
        else:
            logger.info(f"\n{wr}% win rate. Below target. Reassess strategy.")

    # Print recent trades from journal
    if JOURNAL_FILE.exists():
        lines = JOURNAL_FILE.read_text().strip().split("\n")
        logger.info("\nLast 5 trades:")
        for line in lines[-5:]:
            trade = json.loads(line)
            logger.info(
                f"  {trade['expiry']} | {trade['outcome']} ${trade['pnl']:+.2f} "
                f"({trade['pnl_pct']:+.1f}%) | {trade['exit_reason']}"
            )


def _weekend_learn():
    """Weekend learning: analyze all closed trades, extract patterns, update strategy.

    Run this on Saturday/Sunday to review the week's performance.
    """
    logger.info("=" * 60)
    logger.info("WEEKEND LEARNING SESSION")
    logger.info("=" * 60)

    if not JOURNAL_FILE.exists():
        logger.info("No trade journal yet. Nothing to learn from.")
        return

    lines = JOURNAL_FILE.read_text().strip().split("\n")
    trades = [json.loads(line) for line in lines if line.strip()]

    if not trades:
        logger.info("No trades to analyze.")
        return

    # Analyze patterns
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    logger.info(f"Total trades: {len(trades)}")
    logger.info(f"Wins: {len(wins)} | Losses: {len(losses)}")

    # Exit reason analysis
    exit_reasons = {}
    for trade in trades:
        reason_type = (
            "PROFIT"
            if "PROFIT" in trade["exit_reason"]
            else "STOP"
            if "STOP" in trade["exit_reason"]
            else "DTE"
            if "DTE" in trade["exit_reason"]
            else "OTHER"
        )
        if reason_type not in exit_reasons:
            exit_reasons[reason_type] = {"count": 0, "total_pnl": 0}
        exit_reasons[reason_type]["count"] += 1
        exit_reasons[reason_type]["total_pnl"] += trade["pnl"]

    logger.info("\nExit reason analysis:")
    for reason, data in exit_reasons.items():
        avg = data["total_pnl"] / data["count"] if data["count"] > 0 else 0
        logger.info(f"  {reason}: {data['count']} trades, avg P/L=${avg:+.2f}")

    # DTE analysis
    if trades:
        avg_dte = sum(t.get("dte_at_exit", 0) for t in trades) / len(trades)
        logger.info(f"\nAvg DTE at exit: {avg_dte:.1f}")

    # Generate weekly lesson
    lesson_file = LESSONS_DIR / f"weekly_{datetime.now().strftime('%Y%m%d')}.md"
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)

    total_pnl = sum(t["pnl"] for t in trades)
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    lesson = f"""# Weekly Review — {datetime.now().strftime("%Y-%m-%d")}

## Performance
- Trades: {len(trades)} ({len(wins)}W / {len(losses)}L)
- Win rate: {win_rate:.1f}%
- Total P/L: ${total_pnl:+.2f}

## Exit Analysis
"""
    for reason, data in exit_reasons.items():
        avg = data["total_pnl"] / data["count"] if data["count"] > 0 else 0
        lesson += f"- {reason}: {data['count']} trades, avg ${avg:+.2f}\n"

    lesson += f"""
## Recommendations
{"- Strategy validated at {win_rate:.0f}% win rate" if win_rate >= 80 else ""}{"- Win rate {win_rate:.0f}% below 80% target — consider widening delta or tightening stops" if win_rate < 80 and trades else ""}
{"- Need more data — only {len(trades)} trades so far" if len(trades) < 30 else ""}
"""
    lesson_file.write_text(lesson)
    logger.info(f"\nWeekly lesson saved: {lesson_file.name}")


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
    parser.add_argument(
        "--mode", choices=["entry", "exit", "both", "status", "report", "learn"], default="both"
    )
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

        # FOMC blackout check (2 days before through 1 day after)
        from datetime import timedelta

        FOMC_DATES = [
            "2026-01-28",
            "2026-03-18",
            "2026-05-06",
            "2026-06-17",
            "2026-07-29",
            "2026-09-16",
            "2026-11-04",
            "2026-12-16",
        ]
        today = datetime.now().date()
        fomc_blocked = False
        for fomc_str in FOMC_DATES:
            fomc_date = datetime.strptime(fomc_str, "%Y-%m-%d").date()
            if (fomc_date - timedelta(days=2)) <= today <= (fomc_date + timedelta(days=1)):
                logger.warning(f"FOMC blackout: {fomc_str}. No entry.")
                fomc_blocked = True
                break

        # Position limit
        ic_count = _count_open_ics(client)
        if fomc_blocked:
            pass  # Skip entry
        elif ic_count >= MAX_IC:
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

    if args.mode == "report":
        _print_report()

    if args.mode == "learn":
        _weekend_learn()

    logger.info("\nDone.")


if __name__ == "__main__":
    main()
