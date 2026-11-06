# 宁德时代收盘图报备份

云环境 `codex` 对应 GitHub 仓库 `daiyin422860/codex` 的 `main` 分支。本任务备份位于 `automations/catl-close-report/`。

每个沪深交易日北京时间 15:40，生成宁德时代最近 10 个交易日的分钟成交量图，并按成交额与股数计算 10 日市场成交均价。

## 恢复

1. 在备份目录建立 Python 3.11+ 环境，安装依赖。Linux 安装 Noto Sans CJK 中文字体，macOS 可直接使用系统中文字体。
2. 如需补齐历史分钟数据，把有相应行情权限的 Tushare 凭据放在环境变量 `TUSHARE_TOKEN`，或项目根目录中本机的 `.env`。凭据由恢复者另行配置。
3. 在新环境先运行一次批量回填，再生成目标收盘日的首张图。把下面的示例日期替换为实际已收盘的交易日。
4. 在 Codex 中打开要接收报告的聊天，以 `schedule.toml` 的名称、北京时间、重复规则与提示词恢复本地 heartbeat。如果已存在同一任务，更新已有任务。任务的工作目录选择本目录；如备份被恢复到项目的子目录，将提示词中的工作目录改为该子目录的真实位置。
5. 以后每个交易日运行收盘脚本。日线、分钟缓存及图片写入 `research/宁德收盘图报/`。按日期保留分钟缓存即可滚动生成。

```sh
cd automations/catl-close-report
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/bootstrap_minutes.py --date 2026-11-06
.venv/bin/python scripts/catl_close_volume.py --date 2026-11-06
```

核对样例：2026-11-06 图的 10 个交易日从 2026-10-26 开始，10 日市场成交均价为 244.72 元/股。每行对应一天，开盘、最高、最低、收盘、涨跌幅和成交量使用该日不复权报价。腾讯近五日分时与本机分钟缓存可用于日常更新；历史缺口通过一次 Tushare 历史分钟请求和逐日日线核验补齐。限频时稍后重试；已有本机 Tushare 原始响应的，可在回填命令后加 `--minute-file 文件名.json`。缺失的分钟数据在图中单列说明。

本仓库存放调度设置、生成程序和恢复步骤。GitHub 上的这些文件是备份；实际投递由本机 Codex 任务执行。
