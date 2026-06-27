"""
Risk Engine — the only agent with veto power over every trade.

Design intent: this is deterministic code, not an LLM judgment call.
Every other agent's output passes through here before it can become
a real order. No agent (including future "self-learning" components)
is allowed to modify the values in risk_config.py at runtime.

This module owns:
  - per-trade position sizing
  - daily loss circuit breaker
  - max trades per day
  - consecutive-loss cooldown
  - max concurrent positions
  - dual exit trigger checks (premium stop + time-based force close)

It does NOT own:
  - signal generation (signal_agent.py)
  - strike selection (strategist, not yet built)
  - order submission (execution_agent.py)
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional

from config import risk_config as cfg

try:
    from utils.agent_brain import AgentBrain as _AgentBrain
    _brain = _AgentBrain("VAULT", "#c02a44")
except Exception:
    _brain = None


@dataclass
class Trade:
    entry_time: datetime
    direction: str          # "long" or "short"
    entry_premium: float
    quantity: int
    dollar_risk: float
    exit_time: Optional[datetime] = None
    exit_premium: Optional[float] = None
    pnl: Optional[float] = None
    exit_reason: Optional[str] = None  # "stop", "target", "time_force_close", "manual"


@dataclass
class SessionState:
    date: str
    starting_balance: float
    current_balance: float
    trades: list = field(default_factory=list)
    consecutive_losses: int = 0
    halted: bool = False
    halt_reason: Optional[str] = None

    @property
    def trades_opened_today(self) -> int:
        return len(self.trades)

    @property
    def daily_pnl(self) -> float:
        return sum(t.pnl for t in self.trades if t.pnl is not None)

    @property
    def open_positions(self) -> list:
        return [t for t in self.trades if t.exit_time is None]


class RiskEngine:
    def __init__(self, starting_balance: float = cfg.STARTING_BALANCE):
        self.session = SessionState(
            date=datetime.now().strftime("%Y-%m-%d"),
            starting_balance=starting_balance,
            current_balance=starting_balance,
        )

    # ------------------------------------------------------------------
    # Pre-trade checks
    # ------------------------------------------------------------------

    def evaluate(self, direction: str, entry_premium: float) -> dict:
        """
        Called by the strategist/execution layer before any order is sent.
        Returns approved/rejected + sizing, never just a boolean.
        """
        reasons = []

        if self.session.halted:
            return self._reject(self.session.halt_reason or "session halted")

        if self.session.trades_opened_today >= cfg.MAX_TRADES_PER_DAY:
            self._halt("max trades per day reached")
            return self._reject("max trades per day reached")

        if self.session.consecutive_losses >= cfg.CONSECUTIVE_LOSS_COOLDOWN:
            return self._reject(
                f"cooldown active after {self.session.consecutive_losses} consecutive losses"
            )

        if len(self.session.open_positions) >= cfg.MAX_CONCURRENT_POSITIONS:
            return self._reject("max concurrent positions reached")

        daily_loss_limit = self.session.starting_balance * cfg.DAILY_MAX_LOSS_PCT
        if self.session.daily_pnl <= -daily_loss_limit:
            self._halt("daily max loss circuit breaker hit")
            if _brain:
                try:
                    _brain.suggest(
                        title="Circuit breaker hit — daily loss limit reached",
                        reasoning=(
                            f"Daily P&L hit the {cfg.DAILY_MAX_LOSS_PCT * 100:.1f}% max loss "
                            "threshold. Session halted. Review entry criteria before tomorrow."
                        ),
                        category="Risk",
                        priority=8,
                        flags=["critical", "time_sensitive"],
                    )
                except Exception:
                    pass
            return self._reject("daily max loss circuit breaker hit")

        dollar_risk = self.session.current_balance * cfg.PER_TRADE_RISK_PCT
        if entry_premium <= 0:
            return self._reject("invalid entry premium")

        # Quantity sized so that a full premium-stop loss equals dollar_risk.
        # loss_per_contract_if_stopped = entry_premium * 100 * PREMIUM_STOP_PCT
        loss_per_contract = entry_premium * 100 * cfg.PREMIUM_STOP_PCT
        quantity = int(dollar_risk // loss_per_contract) if loss_per_contract > 0 else 0

        if quantity < 1:
            return self._reject("position size rounds to 0 contracts at current risk cap")

        return {
            "approved": True,
            "direction": direction,
            "quantity": quantity,
            "dollar_risk": round(dollar_risk, 2),
            "entry_premium": entry_premium,
            "stop_premium": round(entry_premium * (1 - cfg.PREMIUM_STOP_PCT), 4)
            if direction == "long"
            else round(entry_premium * (1 + cfg.PREMIUM_STOP_PCT), 4),
            "reasons": reasons,
        }

    def _reject(self, reason: str) -> dict:
        return {"approved": False, "reason": reason}

    def _halt(self, reason: str):
        self.session.halted = True
        self.session.halt_reason = reason

    # ------------------------------------------------------------------
    # Exit trigger checks — called continuously while a position is open
    # ------------------------------------------------------------------

    def check_force_close(self, now: datetime) -> bool:
        """
        Time-based hard exit, independent of price. Returns True if
        every open position should be flattened right now regardless
        of P&L. This is what prevents 'ran it to end of day'.
        """
        market_close = time(16, 0)
        minutes_to_close = (
            datetime.combine(now.date(), market_close) - now
        ).total_seconds() / 60
        return minutes_to_close <= cfg.FORCE_CLOSE_MINUTES_BEFORE_CLOSE

    def check_premium_stop(self, trade: Trade, current_premium: float) -> bool:
        if trade.direction == "long":
            return current_premium <= trade.entry_premium * (1 - cfg.PREMIUM_STOP_PCT)
        else:
            return current_premium >= trade.entry_premium * (1 + cfg.PREMIUM_STOP_PCT)

    # ------------------------------------------------------------------
    # Post-trade bookkeeping
    # ------------------------------------------------------------------

    def record_open(self, trade: Trade):
        self.session.trades.append(trade)

    def record_close(self, trade: Trade, exit_premium: float, exit_reason: str):
        trade.exit_time = datetime.now()
        trade.exit_premium = exit_premium
        trade.exit_reason = exit_reason
        if trade.direction == "long":
            trade.pnl = (exit_premium - trade.entry_premium) * 100 * trade.quantity
        else:
            trade.pnl = (trade.entry_premium - exit_premium) * 100 * trade.quantity

        self.session.current_balance += trade.pnl

        if trade.pnl < 0:
            self.session.consecutive_losses += 1
        else:
            self.session.consecutive_losses = 0

        # Suggest on consecutive loss pattern (2+ losses)
        if self.session.consecutive_losses >= 2 and _brain:
            try:
                _brain.suggest(
                    title=f"Consecutive loss pattern — {self.session.consecutive_losses} in a row",
                    reasoning=(
                        f"VAULT recorded {self.session.consecutive_losses} consecutive losses "
                        "this session. Cooldown may engage soon. Review setup quality."
                    ),
                    category="Trading",
                    priority=7,
                    flags=["time_sensitive"],
                )
            except Exception:
                pass

        daily_loss_limit = self.session.starting_balance * cfg.DAILY_MAX_LOSS_PCT
        if self.session.daily_pnl <= -daily_loss_limit:
            self._halt("daily max loss circuit breaker hit")
