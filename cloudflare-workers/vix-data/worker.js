/**
 * VIX Data Worker
 * Fetches real-time VIX data and provides entry signal based on LL-321 rules
 *
 * Entry Rules (from LL-321):
 * - VIX < 15: WAIT (premiums thin)
 * - VIX 15-20 + IV Rank < 30%: WAIT
 * - VIX 15-20 + IV Rank > 50%: ENTER
 * - VIX 20-25: OPTIMAL zone
 * - VIX > 30: CAUTION (may whipsaw)
 */

export default {
  async fetch(request, env) {
    // Handle CORS
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    try {
      // Fetch VIX from Yahoo Finance API (free, no auth needed)
      const vixResponse = await fetch(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d",
        {
          headers: {
            "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)",
          },
        },
      );

      if (!vixResponse.ok) {
        throw new Error(`Yahoo Finance API error: ${vixResponse.status}`);
      }

      const data = await vixResponse.json();
      const result = data.chart?.result?.[0];

      if (!result) {
        throw new Error("No VIX data returned");
      }

      const meta = result.meta;
      const quote = result.indicators?.quote?.[0];

      const currentVix =
        meta.regularMarketPrice || quote?.close?.[quote.close.length - 1];
      const previousClose = meta.chartPreviousClose || meta.previousClose;
      const change = currentVix - previousClose;
      const changePercent = (change / previousClose) * 100;

      // Determine entry signal based on LL-321 rules
      let signal, reason;

      if (currentVix < 15) {
        signal = "WAIT";
        reason = "VIX < 15: Premiums too thin for profitable iron condors";
      } else if (currentVix >= 15 && currentVix < 20) {
        signal = "CAUTION";
        reason = "VIX 15-20: Check IV Rank. Enter only if IV Rank > 50%";
      } else if (currentVix >= 20 && currentVix <= 25) {
        signal = "OPTIMAL";
        reason = "VIX 20-25: OPTIMAL entry zone for iron condors";
      } else if (currentVix > 25 && currentVix <= 30) {
        signal = "ELEVATED";
        reason = "VIX 25-30: Good premiums but increased volatility risk";
      } else {
        signal = "EXTREME";
        reason = "VIX > 30: CAUTION - Market stress, may whipsaw";
      }

      const response = {
        vix: {
          current: parseFloat(currentVix.toFixed(2)),
          previousClose: parseFloat(previousClose.toFixed(2)),
          change: parseFloat(change.toFixed(2)),
          changePercent: parseFloat(changePercent.toFixed(2)),
        },
        signal,
        reason,
        timestamp: new Date().toISOString(),
        source: "Yahoo Finance",
      };

      return new Response(JSON.stringify(response, null, 2), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=60", // Cache for 1 minute
        },
      });
    } catch (error) {
      return new Response(
        JSON.stringify({
          error: error.message,
          timestamp: new Date().toISOString(),
        }),
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        },
      );
    }
  },

  // Scheduled handler - can be set up to run every hour
  async scheduled(event, env, ctx) {
    // Could store VIX history in KV or D1 for trend analysis
    console.log("Scheduled VIX check at:", new Date().toISOString());
  },
};
