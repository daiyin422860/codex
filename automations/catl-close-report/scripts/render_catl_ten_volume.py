"""Render the closing report: python scripts/render_catl_ten_volume.py INPUT_JSON OUTPUT_PNG."""

import argparse
from datetime import date
import json
import math
from pathlib import Path
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator

INK = "#1a3449"
BLUE = "#286387"
AMBER = "#c76e24"
MUTED = "#516678"
GRID = "#d9e3e9"
WEEKDAY = "一二三四五六日"


def load_font():
    # Explicit registration also works when Matplotlib's font cache is older than the OS.
    for path in (
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ):
        if Path(path).is_file():
            font_manager.fontManager.addfont(path)
            return font_manager.FontProperties(fname=path).get_name()
    for family in ("Noto Sans CJK SC", "Microsoft YaHei", "SimHei"):
        try:
            font_manager.findfont(family, fallback_to_default=False)
            return family
        except ValueError:
            continue
    raise RuntimeError("需要可用的中文字体，以正确显示图上的价格和指标名称。")


def coordinate(time):
    value = str(time).replace(":", "").zfill(4)
    hour, minute = int(value[:2]), int(value[2:])
    if minute > 59:
        raise ValueError(f"无法识别分钟时点 {time}")
    minute_of_day = hour * 60 + minute
    if 570 <= minute_of_day <= 690:
        return minute_of_day - 570
    if 780 <= minute_of_day <= 900:
        return minute_of_day - 780 + 121
    raise ValueError(f"分钟时点超出交易时段 {time}")


def minute_series(day):
    bars = day.get("bars") or []
    series = sorted((coordinate(bar["time"]), float(bar["hands"])) for bar in bars)
    if len({x for x, _ in series}) != len(series):
        raise ValueError(f"{day['date']} 同一分钟重复")
    if any(not math.isfinite(v) or v < 0 for _, v in series):
        raise ValueError(f"{day['date']} 有无效的分钟成交量")
    return series


def row_label(ax, day):
    trade_date = date.fromisoformat(day["date"])
    ax.text(0, 1.10, f"{trade_date:%m/%d}  周{WEEKDAY[trade_date.weekday()]}",
            transform=ax.transAxes, fontsize=12.3, color=INK, va="baseline")
    pct = float(day["pct"])
    color = "#b44335" if pct > 0 else "#197359" if pct < 0 else MUTED
    ax.text(.165, 1.10, f"{pct:+.2f}%", transform=ax.transAxes,
            fontsize=11.5, color=color, va="baseline")
    for x, label, field in ((.29, "开", "open"), (.44, "高", "high"),
                            (.59, "低", "low"), (.74, "收", "close")):
        ax.text(x, 1.10, f"{label}  {float(day[field]):.2f}", transform=ax.transAxes,
                fontsize=10.3, color=INK, va="baseline")
    ax.text(1, 1.10, f"{float(day['volume_hands']) / 10000:.2f} 万手",
            transform=ax.transAxes, ha="right", fontsize=10.4, color=MUTED, va="baseline")


def plot_day(ax, day, bars, ticks):
    ax.set_xlim(-1, 242)
    ax.set_ylim(0, ticks[-1] * 1.12)
    ax.set_yticks(ticks)
    ax.tick_params(length=0, pad=4, labelsize=9, colors=MUTED)
    ax.spines[["top", "left", "right"]].set_visible(False)
    ax.spines["bottom"].set_color("#bfcdd6")
    ax.grid(axis="y", color=GRID, lw=.66)
    row_label(ax, day)
    if not bars:
        ax.set_facecolor("#f7f9fa")
        ax.set_yticks([])
        ax.text(.5, .45, "当日完整分钟成交量待补", color=MUTED, fontsize=10,
                transform=ax.transAxes, ha="center", va="center")
        return
    ax.axvspan(120.5, 241.65, color="#f2f6f9", zorder=0)
    ax.axvline(120.5, color="#94a8b4", ls="--", lw=.75)
    xs, values = zip(*bars)
    ax.bar(xs, [v / 10000 for v in values], width=.87, color=BLUE, linewidth=0, zorder=2)
    peak_x, peak_hands = max(bars, key=lambda item: item[1])
    if peak_hands > 0:
        ax.bar(peak_x, peak_hands / 10000, width=.87, color=AMBER, linewidth=0, zorder=3)
        hm = next(str(b["time"]).replace(":", "").zfill(4) for b in day["bars"] if coordinate(b["time"]) == peak_x)
        before = peak_x > 195
        ax.annotate(f"{hm[:2]}:{hm[2:]}  {peak_hands/10000:.2f}",
                    (peak_x, peak_hands/10000), xytext=(-3 if before else 3, 1),
                    textcoords="offset points", ha="right" if before else "left",
                    color=AMBER, fontsize=7.5)
        pm = sum(v for x, v in bars if x > 120) / sum(values)
        ax.text(.55, .83, f"下午占 {pm:.1%}", color=MUTED, fontsize=8,
                transform=ax.transAxes)
    if len(bars) < 240:
        ax.text(.99, .88, f"仅有 {len(bars)} 个时点", color=MUTED, fontsize=8,
                transform=ax.transAxes, ha="right")


def render(payload, output):
    days = sorted(payload["days"], key=lambda d: d["date"])
    if len(days) != 10 or len({d["date"] for d in days}) != 10 or days[-1]["date"] != payload["asof"]:
        raise ValueError("图报必须含10个不同交易日，最后一天等于 asof。")
    series = [minute_series(day) for day in days]
    peak = max((v for bars in series for _, v in bars), default=0) / 10000
    ticks = MaxNLocator(nbins=3, steps=[1, 2, 2.5, 5, 10]).tick_values(0, peak or 1)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": load_font(), "font.size": 10, "axes.unicode_minus": False}):
        fig, axes = plt.subplots(10, 1, figsize=(11.4, 16.4), sharex=True, facecolor="white")
        fig.subplots_adjust(left=.068, right=.967, top=.881, bottom=.057, hspace=.70)
        fig.text(.068, .970, "宁德时代  |  十日分时成交量", fontsize=21, color=INK)
        fig.text(.068, .945, f"300750.SZ      {days[0]['date']}  至  {days[-1]['date']}      北京时间",
                 fontsize=11, color=MUTED)
        vwap = payload.get("vwap10")
        price = f"{float(vwap):.2f} 元/股" if vwap is not None and math.isfinite(float(vwap)) else "待核"
        fig.text(.967, .975, "10个交易日市场成交均价", ha="right", fontsize=11, color=MUTED)
        fig.text(.967, .945, price, ha="right", fontsize=21, color="#1c695c")
        fig.text(.068, .917, "纵轴：分钟成交量（万手）    ·    十天统一刻度    ·    橙色为当日最高量柱",
                 fontsize=10, color=MUTED)
        for ax, day, bars in zip(axes, days, series):
            plot_day(ax, day, bars, ticks)
        axes[-1].set_xticks([0, 30, 60, 90, 120.5, 151, 181, 211, 241],
                             ["09:30", "10:00", "10:30", "11:00", "11:30 / 13:00",
                              "13:30", "14:00", "14:30", "15:00"])
        fig.text(.068, .029, "分钟量按来源时点绘制，午休压缩。开盘竞价成交量随来源计入开盘或首分钟。",
                 fontsize=9, color=MUTED)
        fig.text(.068, .014, "市场成交均价 = 十日实际成交总额 ÷ 十日成交总股数。价格为人民币元，1手 = 100股。",
                 fontsize=9, color=MUTED)
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", dir=output.parent, delete=False) as tmp:
                temporary = Path(tmp.name)
            try:
                fig.savefig(temporary, dpi=160, facecolor="white", format="png")
                temporary.replace(output)
            finally:
                temporary.unlink(missing_ok=True)
        finally:
            plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成宁德时代最近10个交易日的分钟成交量图")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()
    render(json.loads(args.input_json.read_text(encoding="utf-8")), args.output_png)
