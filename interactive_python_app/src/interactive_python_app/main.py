from __future__ import annotations


def build_greeting(name: str) -> str:
    clean_name = name.strip() or "朋友"
    return f"你好，{clean_name}！我们已经准备好开始写应用了。"


def run_app() -> None:
    print("Interactive Python App")
    print("输入你的名字开始，输入 q 退出。")

    while True:
        name = input("> ").strip()
        if name.lower() in {"q", "quit", "exit"}:
            print("下次继续。")
            return

        print(build_greeting(name))


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
