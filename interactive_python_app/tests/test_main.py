import unittest

from interactive_python_app.main import build_greeting, parse_domestic_gold_price


class GreetingTests(unittest.TestCase):
    def test_build_greeting_uses_name(self) -> None:
        self.assertEqual(
            build_greeting("Alice"),
            "你好，Alice！我们已经准备好开始写应用了。",
        )

    def test_build_greeting_falls_back_for_blank_name(self) -> None:
        self.assertEqual(
            build_greeting("   "),
            "你好，朋友！我们已经准备好开始写应用了。",
        )

    def test_parse_domestic_gold_price_prefers_afternoon_price(self) -> None:
        html = """
        <p>行情日期：2026-06-15</p>
        <span>上海金早盘价（元/克）</span>
        <span>935.20</span>
        <span>上海金午盘价（元/克）</span>
        <span>936.39</span>
        """

        price = parse_domestic_gold_price(html)

        self.assertEqual(price.name, "上海金午盘价")
        self.assertEqual(price.price, 936.39)
        self.assertEqual(price.date, "2026-06-15")


if __name__ == "__main__":
    unittest.main()
