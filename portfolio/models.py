"""Modelo de posiciones, precios y rebalanceo de acciones."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from typing import Self


@dataclass(frozen=True, slots=True)
class PriceQuote:
    price: Decimal
    at: datetime


class Stock:
    """Activo identificado por ticker, con historial de cotizaciones."""

    def __init__(self, ticker: str) -> None:
        self._ticker = ticker.strip().upper()
        if not self._ticker:
            raise ValueError("El ticker no puede estar vacío")
        self._history: list[PriceQuote] = []

    @property
    def ticker(self) -> str:
        return self._ticker

    @property
    def price_history(self) -> tuple[PriceQuote, ...]:
        """Cotizaciones en orden de registro."""
        return tuple(self._history)

    def record_price(self, price: Decimal, at: datetime | None = None) -> None:
        if not price.is_finite() or price <= 0:
            raise ValueError("El precio debe ser positivo y finito")
        timestamp = datetime.now(UTC) if at is None else at
        if timestamp.utcoffset() is None:
            raise ValueError("La fecha debe incluir zona horaria")
        self._history.append(PriceQuote(price, timestamp.astimezone(UTC)))

    def current_price(self) -> Decimal:
        """Último precio por fecha. En un empate prevalece el último registro."""
        if not self._history:
            raise ValueError(f"{self.ticker} no tiene un precio registrado")
        return max(reversed(self._history), key=lambda quote: quote.at).price


@dataclass(frozen=True, slots=True)
class Position:
    stock: Stock
    shares: Fraction

    def __post_init__(self) -> None:
        if self.shares <= 0:
            raise ValueError("La cantidad de acciones debe ser positiva")

    @classmethod
    def buy(cls, stock: Stock, *, amount: Decimal) -> Self:
        """Simula una compra al precio vigente y guarda las unidades obtenidas."""
        if not amount.is_finite() or amount <= 0:
            raise ValueError("El monto debe ser positivo y finito")
        return cls(stock, Fraction(amount) / Fraction(stock.current_price()))


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class Order:
    ticker: str
    side: Side
    shares: Fraction
    amount: Fraction


@dataclass(frozen=True, slots=True)
class Portfolio:
    _positions: tuple[Position, ...]
    _target_weights: dict[str, Fraction]

    @classmethod
    def from_positions(cls, positions: Iterable[Position]) -> Self:
        """Fija la asignación objetivo a partir del valor inicial por ticker."""
        holdings: dict[str, Position] = {}
        for position in positions:
            ticker = position.stock.ticker
            previous = holdings.get(ticker)
            if previous is None:
                holdings[ticker] = position
                continue
            if previous.stock is not position.stock:
                raise ValueError(f"Usa un mismo Stock para las posiciones de {ticker}")
            holdings[ticker] = Position(position.stock, previous.shares + position.shares)

        snapshot = tuple(holdings.values())
        return cls(snapshot, cls._weights(cls._valuation(snapshot)))

    @property
    def target_weights(self) -> dict[str, Fraction]:
        """Devuelve una copia de la asignación fijada al crear el portafolio."""
        return self._target_weights.copy()

    def current_distribution(self) -> dict[str, Fraction]:
        return self._weights(self._valuation(self._positions))

    def rebalance(self) -> tuple[Order, ...]:
        """Calcula las operaciones a partir de una cotización por activo."""
        valuation = self._valuation(self._positions)
        total = sum((value for _, value in valuation.values()), start=Fraction(0))
        orders: list[Order] = []

        for ticker, (price, current_value) in valuation.items():
            # Apply the original weights to today's total value.
            target_value = total * self._target_weights[ticker]
            delta = target_value - current_value
            if delta == 0:
                continue
            side = Side.BUY if delta > 0 else Side.SELL
            orders.append(Order(ticker, side, abs(delta) / price, abs(delta)))

        return tuple(sorted(orders, key=lambda order: (order.side != Side.SELL, order.ticker)))

    @staticmethod
    def _valuation(
        positions: tuple[Position, ...],
    ) -> dict[str, tuple[Fraction, Fraction]]:
        valuation: dict[str, tuple[Fraction, Fraction]] = {}
        for position in positions:
            price = Fraction(position.stock.current_price())
            valuation[position.stock.ticker] = (price, position.shares * price)
        return valuation

    @staticmethod
    def _weights(
        valuation: dict[str, tuple[Fraction, Fraction]],
    ) -> dict[str, Fraction]:
        total = sum((value for _, value in valuation.values()), start=Fraction(0))
        return {ticker: value / total for ticker, (_, value) in valuation.items()}
