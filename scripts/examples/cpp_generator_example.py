"""Example of a script with options: asks the loaded model to write a C++ file into another folder.

AI Harness reads the argparse options below and shows them as a form (with your last values remembered).
Files written to --out-dir are listed after the run.
"""
import argparse
from pathlib import Path

from openai import OpenAI

ap = argparse.ArgumentParser()
ap.add_argument("task", help="What the C++ program should do")
ap.add_argument("--out-dir", type=Path, default=Path("~/AIHarness/generated"), help="Folder for the generated file")
ap.add_argument("--workers", type=int, default=1, help="Parallel requests to the model")
ap.add_argument("--max-tokens", type=int, default=2048, help="Max tokens per response")
ap.add_argument("--style", choices=["modern", "c-like"], default="modern")
ap.add_argument("--verbose", action="store_true")
args = ap.parse_args()

out = args.out_dir.expanduser()
out.mkdir(parents=True, exist_ok=True)
client = OpenAI()
model = client.models.list().data[0].id
if args.verbose:
    print(f"model={model} workers={args.workers}")
resp = client.chat.completions.create(
    model=model, max_tokens=args.max_tokens,
    messages=[{"role": "user", "content": f"Write a single {args.style} C++ file that does: {args.task}. Output only code."}],
)
code = resp.choices[0].message.content.strip().removeprefix("```cpp").removesuffix("```").strip()
(out / "main.cpp").write_text(code + "\n")
print(f"Wrote {out / 'main.cpp'}")
