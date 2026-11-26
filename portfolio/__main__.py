"""Ejemplo de compra, cambio de precios y rebalanceo."""

from datetime import UTC, datetime
from decimal import Decimal

from .models import Portfolio, Position, Side, Stock


def main() -> None:
    initial = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 2, 1, tzinfo=UTC)
    meta, apple = Stock("META"), Stock("AAPL")
    for stock in (meta, apple):
        stock.record_price(Decimal("100"), initial)

    portfolio = Portfolio.from_positions([
        Position.buy(meta, amount=Decimal("400")),
        Position.buy(apple, amount=Decimal("600")),
    ])

    meta.record_price(Decimal("120"), later)
    apple.record_price(Decimal("80"), later)

    current = portfolio.current_distribution()
    for ticker, target in portfolio.target_weights.items():
        print(f"{ticker}  Objetivo {target:.0%}  Actual {current[ticker]:.0%}")

    for order in portfolio.rebalance():
        action = "Vender" if order.side == Side.SELL else "Comprar"
        print(f"{action} {order.shares:.1f} {order.ticker} por ${order.amount:.2f}")


if __name__ == "__main__":
    main()
