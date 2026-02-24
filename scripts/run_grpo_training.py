import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.ml.grpo_trade_learner import get_optimal_trade_params, train_grpo_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    Execute the GRPO Self-Training Loop.
    1. Load trade history from system_state.json
    2. Train the policy network on wins/losses
    3. Output optimized trade parameters for the next session
    """
    print("🚀 Starting GRPO Self-Training Loop...")

    # Train the model
    try:
        result = await train_grpo_model()

        if "error" in result:
            print(f"⚠️ Training skipped: {result['error']}")
        else:
            summary = result.get("learning_summary", {})
            print(f"✅ Training Complete on {summary.get('total_trades', 0)} trades.")
            print(f"   Win Rate: {summary.get('win_rate', 0):.1%}")
            print(f"   Profit Factor: {summary.get('profit_factor', 0):.2f}")

            # Save the optimal parameters for the orchestrator
            params = get_optimal_trade_params()
            print("\n🧠 OPTIMAL PARAMETERS FOR NEXT SESSION:")
            print(f"   Delta: {params.delta:.3f}")
            print(f"   DTE: {params.dte}")
            print(f"   Entry Hour: {params.entry_hour:.2f}")
            print(f"   Exit Profit: {params.exit_profit_pct:.0%}")
            print(f"   Confidence: {params.confidence:.1%}")

    except Exception as e:
        logger.error(f"Critical error in training loop: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
