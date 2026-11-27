from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
import unittest

from portfolio import Order, Portfolio, Position, PriceQuote, Side, Stock


INITIAL = datetime(2026, 1, 1, tzinfo=UTC)
LATER = datetime(2026, 2, 1, tzinfo=UTC)


def priced_stock(ticker: str, price: str = "100") -> Stock:
    stock = Stock(ticker)
    stock.record_price(Decimal(price), INITIAL)
    return stock


class StockTests(unittest.TestCase):
    def test_price_history_uses_latest_timestamp(self) -> None:
        stock = Stock(" meta ")
        stock.record_price(Decimal("120"), LATER)
        stock.record_price(Decimal("100"), INITIAL)
        self.assertEqual(stock.ticker, "META")
        self.assertEqual(stock.current_price(), Decimal("120"))
        self.assertEqual(
            stock.price_history,
            (PriceQuote(Decimal("120"), LATER), PriceQuote(Decimal("100"), INITIAL)),
        )
        stock.record_price(Decimal("125"), LATER)
        self.assertEqual(stock.current_price(), Decimal("125"))

    def test_records_utc_when_timestamp_is_omitted(self) -> None:
        stock = Stock("META")
        stock.record_price(Decimal("100"))
        self.assertIs(stock.price_history[0].at.tzinfo, UTC)

    def test_missing_price_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "META"):
            Stock("META").current_price()

    def test_rejects_invalid_prices(self) -> None:
        stock = Stock("META")
        for invalid in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(price=invalid), self.assertRaises(ValueError):
                stock.record_price(Decimal(invalid), INITIAL)
        self.assertEqual(stock.price_history, ())

    def test_rejects_timestamp_without_timezone(self) -> None:
        stock = Stock("META")
        with self.assertRaises(ValueError):
            stock.record_price(Decimal("100"), INITIAL.replace(tzinfo=None))


class PositionTests(unittest.TestCase):
    def test_buy_preserves_exact_fractional_units_after_price_change(self) -> None:
        stock = priced_stock("META", "3")
        position = Position.buy(stock, amount=Decimal("100"))
        stock.record_price(Decimal("6"), LATER)
        self.assertEqual(position.shares, Fraction(100, 3))

    def test_buy_rejects_invalid_amounts(self) -> None:
        stock = priced_stock("META")
        for invalid in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(amount=invalid), self.assertRaises(ValueError):
                Position.buy(stock, amount=Decimal(invalid))

    def test_position_rejects_zero_shares(self) -> None:
        with self.assertRaises(ValueError):
            Position(priced_stock("META"), Fraction(0))


class PortfolioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.meta = priced_stock("META")
        self.apple = priced_stock("AAPL")
        self.positions = (
            Position.buy(self.meta, amount=Decimal("400")),
            Position.buy(self.apple, amount=Decimal("600")),
        )
        self.portfolio = Portfolio.from_positions(self.positions)

    def test_initial_weights_are_inferred_and_rebalance_is_empty(self) -> None:
        expected = {"META": Fraction(2, 5), "AAPL": Fraction(3, 5)}
        self.assertEqual(self.portfolio.target_weights, expected)
        self.assertEqual(self.portfolio.current_distribution(), expected)
        self.assertEqual(self.portfolio.rebalance(), ())

    def test_prices_change_distribution_and_rebalance_moves_exact_amount(self) -> None:
        self.meta.record_price(Decimal("120"), LATER)
        self.apple.record_price(Decimal("80"), LATER)

        self.assertEqual(
            self.portfolio.current_distribution(),
            {"META": Fraction(1, 2), "AAPL": Fraction(1, 2)},
        )
        orders = (
            Order("META", Side.SELL, Fraction(4, 5), Fraction(96)),
            Order("AAPL", Side.BUY, Fraction(6, 5), Fraction(96)),
        )
        self.assertEqual(self.portfolio.rebalance(), orders)
        self.assertEqual(self.portfolio.rebalance(), orders)
        self.assertEqual(self.portfolio.target_weights["META"], Fraction(2, 5))
        self.assertEqual([position.shares for position in self.positions], [4, 6])

    def test_target_weights_use_market_value_when_portfolio_is_created(self) -> None:
        self.meta.record_price(Decimal("200"), LATER)
        portfolio = Portfolio.from_positions(self.positions)
        self.assertEqual(portfolio.target_weights, {"META": Fraction(4, 7), "AAPL": Fraction(3, 7)})

    def test_merges_multiple_purchases_of_the_same_stock(self) -> None:
        portfolio = Portfolio.from_positions([
            Position.buy(self.meta, amount=Decimal("200")),
            Position.buy(self.meta, amount=Decimal("200")),
            self.positions[1],
        ])
        self.assertEqual(portfolio.target_weights, self.portfolio.target_weights)

    def test_rejects_two_price_histories_for_same_ticker(self) -> None:
        other_meta = Position.buy(priced_stock("meta"), amount=Decimal("100"))
        with self.assertRaisesRegex(ValueError, "META"):
            Portfolio.from_positions([self.positions[0], other_meta])

    def test_periodic_weights_do_not_create_spurious_orders(self) -> None:
        a = Position.buy(self.meta, amount=Decimal("100"))
        b = Position.buy(self.apple, amount=Decimal("200"))
        portfolio = Portfolio.from_positions([a, b])
        self.meta.record_price(Decimal("200"), LATER)
        self.apple.record_price(Decimal("200"), LATER)
        self.assertEqual(portfolio.target_weights["META"], Fraction(1, 3))
        self.assertEqual(portfolio.rebalance(), ())

    def test_allocation_read_is_a_copy(self) -> None:
        self.portfolio.target_weights.clear()
        self.assertEqual(self.portfolio.target_weights["META"], Fraction(2, 5))

    def test_empty_portfolio(self) -> None:
        portfolio = Portfolio.from_positions([])
        self.assertEqual(portfolio.target_weights, {})
        self.assertEqual(portfolio.current_distribution(), {})
        self.assertEqual(portfolio.rebalance(), ())
