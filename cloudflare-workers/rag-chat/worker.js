/**
 * RAG Chat Cloudflare Worker
 * Proxies requests to Claude API with embedded trading lessons context
 * Supports conversation history for follow-up questions
 */

const LESSONS_CONTEXT = `You are a trading knowledge assistant for Igor's AI Trading System. Answer questions using ONLY the lessons below. If the answer isn't in the lessons, say "I don't have a lesson about that."

KEY LESSONS:

LL-323: Iron Condor Management (71,417 trade study) - January 31, 2026
- Close at 50% profit for 85% win rate
- 7 DTE mandatory close (not expiration)
- 16-delta setup optimal
- VIX > 20 significantly outperforms

LL-322: XSP vs SPY Tax Optimization - January 31, 2026
- SPY: 100% short-term gains, wash sale rules apply
- XSP: 60/40 tax treatment (Section 1256), cash settled
- At $72K profit: XSP saves ~$6,480/year
- Use SPY for paper, switch to XSP live at >$25K profit

LL-321: VIX Entry Rules - January 31, 2026
- VIX < 15: WAIT (premiums thin)
- VIX 15-20 + IV Rank < 30%: WAIT
- VIX 15-20 + IV Rank > 50%: ENTER
- VIX 20-25: OPTIMAL zone
- VIX > 30: CAUTION (may whipsaw)

LL-320: North Star - January 30, 2026
- Goal: $6,000/month after-tax = financial independence
- Timeline: By Nov 14, 2029 (age 50)
- Path: $100K -> $600K via iron condors
- Monthly target: 8% returns (conservative iron condor avg)

LL-319: CTO Crisis Failure - January 30, 2026
- Lost 86% of $30K account in 8 days
- Root cause: Dismissed CEO warnings, didn't query RAG
- Never claim success without verification evidence
- Must validate 80%+ win rate before live trading

LL-324: Claude Date Hallucination - February 1, 2026
- Claude wrote "Super Bowl weekend" on Feb 1 when Super Bowl is Feb 8
- Must verify dates with web search before publishing
- Never assume calendar knowledge is correct

LL-325: CTO Lied About Secret Upload - February 1, 2026
- Claimed success uploading empty API key
- Must test endpoints after claiming success
- Verification protocol violated

LL-318: Async Hooks Performance - January 27, 2026
- Use async: true for non-blocking hooks
- Reduced startup by 15-20 seconds

LL-300: Vertex AI Cost Explosion - February 1, 2026
- GCP bill hit $98 vs $20 budget
- Too many automated RAG calls
- Solution: Disabled auto Vertex AI, use local files

LL-268: Iron Condor Win Rate Research - January 21, 2026
- 15-delta = 86% probability of profit
- Close at 50% OR 7 DTE (whichever first)
- Risk/reward ~1.5:1
- Better than credit spreads: profit from BOTH sides

LL-282: Position Accumulation Bug - January 22, 2026
- Bug allowed 10+ positions when limit was 2
- Root cause: Counted SHARES not CONTRACTS
- Lost $1,472 in paper account
- Fix: Circuit breaker checks contract count

LL-230: Trade Data Architecture - January 15, 2026
- CANONICAL source: data/system_state.json -> trade_history
- Cloud Run has NO local files - fetch via GitHub API
- Deprecated: trades_*.json files

STRATEGY SUMMARY:
- Ticker: SPY ONLY (best liquidity, tightest spreads)
- Structure: Iron condors, 15-20 delta, $5-wide wings
- DTE: 30-45 days, close at 7 DTE or 50% profit
- Position size: Max 5% ($5,000 risk)
- Stop-loss: 200% of credit received
- Monthly target: 3-4 trades x $150-250 avg
`;

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    try {
      const { message, history } = await request.json();

      if (!message || typeof message !== "string") {
        return new Response(JSON.stringify({ error: "Message required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      // Build messages array with history for context
      const messages = [];

      // Add conversation history if provided (last 10 messages max)
      if (Array.isArray(history)) {
        const recentHistory = history.slice(-10);
        for (const msg of recentHistory) {
          if (msg.role && msg.content) {
            messages.push({ role: msg.role, content: msg.content });
          }
        }
      }

      // Add current message
      messages.push({ role: "user", content: message });

      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: "claude-3-5-haiku-20241022",
          max_tokens: 1024,
          system: LESSONS_CONTEXT,
          messages: messages,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        console.error("Claude API error:", error);
        return new Response(JSON.stringify({ error: "API error" }), {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        });
      }

      const data = await response.json();
      const reply = data.content[0]?.text || "No response";

      return new Response(JSON.stringify({ reply }), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (error) {
      console.error("Worker error:", error);
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }
  },
};
