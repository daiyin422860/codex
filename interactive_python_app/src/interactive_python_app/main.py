from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DomesticGoldPrice:
    name: str
    price: float
    date: str | None


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def build_greeting(name: str) -> str:
    clean_name = name.strip() or "朋友"
    return f"你好，{clean_name}！我们已经准备好开始写应用了。"


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_gold_price() -> float:
    load_env_file()
    api_key = os.environ.get("TWELVE_DATA_API_KEY") or os.environ.get("GOLD_API_KEY")
    if not api_key:
        raise RuntimeError("请先在 .env 里设置 TWELVE_DATA_API_KEY。")

    params = urlencode({
        "symbol": "XAU/USD",
        "apikey": api_key,
    })
    url = f"https://api.twelvedata.com/price?{params}"

    with urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    if "price" not in data:
        raise RuntimeError(f"接口返回异常: {data}")

    return float(data["price"])


def parse_domestic_gold_price(html: str) -> DomesticGoldPrice:
    parser = TextExtractor()
    parser.feed(html)

    date = None
    for part in parser.parts:
        if "行情日期" in part:
            date = part.split("：", 1)[-1].strip()
            break

    for name in ("上海金午盘价", "上海金早盘价"):
        price = find_price_after_label(parser.parts, name)
        if price is not None:
            return DomesticGoldPrice(name=name, price=price, date=date)

    raise RuntimeError("没有在上海黄金交易所页面找到上海金价格。")


def find_price_after_label(parts: list[str], label: str) -> float | None:
    for index, part in enumerate(parts):
        if label not in part:
            continue

        price = parse_first_number(part.split(label, 1)[-1])
        if price is not None:
            return price

        for candidate in parts[index + 1:index + 8]:
            price = parse_first_number(candidate)
            if price is not None:
                return price

    return None


def parse_first_number(text: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if match is None:
        return None

    return float(match.group(0))


def get_domestic_gold_price() -> DomesticGoldPrice:
    request = Request("https://www.sge.com.cn/", headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request, timeout=10) as response:
        html = response.read().decode("utf-8")

    return parse_domestic_gold_price(html)


def main() -> None:
    try:
        price = get_gold_price()
    except (RuntimeError, URLError) as error:
        print(f"国际金价查询失败: {error}")
    else:
        print(f"国际金价 XAU/USD: ${price:,.2f} / 盎司")

    try:
        domestic_price = get_domestic_gold_price()
    except (RuntimeError, URLError) as error:
        print(f"国内金价查询失败: {error}")
        return

    date_text = f"（{domestic_price.date}）" if domestic_price.date else ""
    print(f"国内金价 {domestic_price.name}{date_text}: ¥{domestic_price.price:,.2f} / 克")


if __name__ == "__main__":
    main()
