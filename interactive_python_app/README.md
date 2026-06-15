# Interactive Python App

一个用于交互开发应用的 Python 项目骨架。

## 运行

```bash
cd /Users/nuaa1001/Documents/编程/interactive_python_app
PYTHONPATH=src python3 -m interactive_python_app.main
```

## 可选：创建虚拟环境

```bash
cd /Users/nuaa1001/Documents/编程/interactive_python_app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
interactive-app
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
