import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout
    if result.stderr:
        output += "\n" + result.stderr
    return f"$ {' '.join(command)}\n{output.strip()}\n\nexit code: {result.returncode}"


def render_terminal(text: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=18)
    padding = 28
    line_height = 24
    max_chars = 108
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(raw_line, max_chars, replace_whitespace=False) or [""])

    width = 1440
    height = max(520, padding * 2 + line_height * len(lines))
    image = Image.new("RGB", (width, height), "#101418")
    draw = ImageDraw.Draw(image)

    y = padding
    for line in lines:
        color = "#d6deeb"
        if line.startswith("$"):
            color = "#7ee787"
        elif "PASSED" in line or "[PASS]" in line or "READY" in line:
            color = "#8ddb8c"
        elif "FAILED" in line or "[FAIL]" in line:
            color = "#ff7b72"
        draw.text((padding, y), line, font=font, fill=color)
        y += line_height

    image.save(target)


if __name__ == "__main__":
    outputs = {
        ROOT / "screenshots" / "api_gateway.png": run(["curl", "-s", "http://localhost:8000/health"]),
        ROOT / "smoke_tests_results.png": run(["python3", "-m", "pytest", "smoke-tests/", "-v"]),
        ROOT / "production_readiness.png": run(["python3", "scripts/production_readiness_check.py"]),
    }
    for path, text in outputs.items():
        render_terminal(text, path)
        print(f"Wrote {path.relative_to(ROOT)}")
