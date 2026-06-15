import unittest

from interactive_python_app.main import build_greeting


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


if __name__ == "__main__":
    unittest.main()
