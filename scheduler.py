import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windowsターミナルの文字化け対策
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parent

SCRIPTS = [
    "fetch.py",
    "compare.py",
    "generate_html.py",
]


def run_script(script_name: str) -> bool:
    """
    指定したPythonファイルを実行する。

    成功した場合:
        True

    失敗した場合:
        False
    """
    script_path = PROJECT_DIR / script_name

    if not script_path.exists():
        print()
        print("=" * 80)
        print("ファイルが見つかりません")
        print("=" * 80)
        print(f"対象ファイル: {script_path}")
        print("=" * 80)
        return False

    print()
    print("=" * 80)
    print(f"{script_name} を実行します")
    print("=" * 80)

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
            ],
            cwd=PROJECT_DIR,
            check=False,
        )

    except OSError as error:
        print()
        print("=" * 80)
        print(f"{script_name} の起動に失敗しました")
        print("=" * 80)
        print(error)
        print("=" * 80)
        return False

    if result.returncode != 0:
        print()
        print("=" * 80)
        print(f"{script_name} でエラーが発生しました")
        print("=" * 80)
        print(f"終了コード: {result.returncode}")
        print("=" * 80)
        return False

    print()
    print(f"{script_name} が正常に完了しました。")

    return True


def main() -> None:
    """価格取得からHTML生成までを順番に実行する。"""
    started_at = datetime.now()

    print()
    print("=" * 80)
    print("楽天価格ランキング更新処理を開始します")
    print("=" * 80)
    print(
        "開始日時:",
        started_at.strftime("%Y年%m月%d日 %H:%M:%S")
    )
    print(f"プロジェクト: {PROJECT_DIR}")
    print("=" * 80)

    completed_scripts: list[str] = []

    for script_name in SCRIPTS:
        success = run_script(script_name)

        if not success:
            finished_at = datetime.now()
            elapsed = finished_at - started_at

            print()
            print("=" * 80)
            print("更新処理を中断しました")
            print("=" * 80)
            print(f"失敗した処理: {script_name}")
            print(
                "完了済み処理:",
                ", ".join(completed_scripts)
                if completed_scripts
                else "なし"
            )
            print(
                "終了日時:",
                finished_at.strftime(
                    "%Y年%m月%d日 %H:%M:%S"
                )
            )
            print(
                f"実行時間: "
                f"{elapsed.total_seconds():.1f}秒"
            )
            print("=" * 80)

            sys.exit(1)

        completed_scripts.append(script_name)

    finished_at = datetime.now()
    elapsed = finished_at - started_at

    ranking_html_path = (
        PROJECT_DIR
        / "output"
        / "ranking.html"
    )

    print()
    print("=" * 80)
    print("楽天価格ランキング更新処理が完了しました")
    print("=" * 80)
    print(
        "終了日時:",
        finished_at.strftime("%Y年%m月%d日 %H:%M:%S")
    )
    print(
        f"実行時間: "
        f"{elapsed.total_seconds():.1f}秒"
    )
    print(
        "実行した処理:",
        " → ".join(completed_scripts)
    )
    print(f"HTML出力先: {ranking_html_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()