"""
News Catalyst Strategy.

Active window : 24/7 (window = None)
Signal cap    : unlimited

Purpose:
  Surface significant news that could move the underlying and flag it
  as a potential trade catalyst — even if no technical setup exists yet.
  A high-conviction news event can front-run the technical setup and put
  the system on alert before the breakout candle prints.

Monitored catalyst types (TSLA-specific + general):
  - Delivery / production reports (monthly)
  - Elon Musk announcements (X posts, interviews, earnings calls)
  - FSD / Autopilot regulatory decisions (NHTSA, NTSB)
  - Analyst rating changes (upgrade, downgrade, price target revision)
  - Index inclusion / exclusion events
  - Macro catalysts that move growth/tech (FOMC, CPI, NFP)
  - Competitor earnings (GM, RIVN, NIO) that shift EV sentiment
  - Battery / supply chain news

Signal rules:
  - Direction: aligned with the news sentiment (bullish/bearish)
  - No bar data required — news alone can trigger a signal
  - Confidence graded by source credibility and relevance
  - Signal expires: 2 hours for intraday news, EOD for pre-market catalysts

Inputs needed:
  - News feed in EvalContext.news (populated by News/Review Agent)
  - Sentiment scoring (simple keyword model or LLM scoring)
  - Source whitelist (Reuters, Bloomberg, SEC filing, earnings call)

Note on current state:
  EvalContext.news is always [] until the News Agent is built.
  This strategy will silently return None until the feed is wired up.
"""

from typing import Optional

from .base import BaseStrategy, EvalContext, SignalOutput

_BULLISH_KEYWORDS = [
    "record deliveries", "beat estimates", "upgrade", "buy", "outperform",
    "fsd approval", "full self-driving", "autonomous", "strong demand",
]
_BEARISH_KEYWORDS = [
    "recall", "investigation", "downgrade", "sell", "underperform",
    "miss estimates", "production cut", "layoffs", "lawsuit",
]


class NewsCatalystStrategy(BaseStrategy):
    name        = "NewsCatalyst"
    max_signals = None   # unlimited — news doesn't have a daily cap
    window      = None   # 24/7

    def update(self, context: EvalContext) -> Optional[SignalOutput]:
        if not context.news:
            return None   # feed not yet wired — silent until News Agent is built

        raise NotImplementedError(
            "NewsCatalystStrategy not yet implemented. "
            "Feed is now wired (context.news is non-empty) — implement: "
            "sentiment scoring, source credibility weighting, "
            "duplicate suppression, signal expiry logic."
        )

    def reset_session(self) -> None:
        super().reset_session()
