#!/usr/bin/env python3
"""
🎴 TaijiOS TTS · 孔明亲口说话

首选: edge-tts (免费 · 微软 Edge 声音 · 无需 key)
备选: Doubao TTS (需 key · 更自然) — 可 future

安装:
    pip install edge-tts

用法:
    python tts.py --text "臣观天象, 卦显大畜之象"
    python tts.py --text "..." --voice zh-CN-YunjianNeural  # 男声
    python tts.py --text "..." --save out.mp3               # 不播, 只存
    echo "孔明评语" | python tts.py                         # 从 stdin 读

Voice 推荐:
    zh-CN-XiaoxiaoNeural  · 中文女声 (默认)
    zh-CN-YunjianNeural   · 中文男声 · 沉稳 (推荐孔明)
    zh-CN-YunxiNeural     · 中文男声 · 年轻
    zh-CN-YunyangNeural   · 中文男声 · 新闻播音员
"""
import sys, os, asyncio, tempfile, argparse, platform, subprocess, pathlib

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_VOICE = "zh-CN-YunjianNeural"  # 男声沉稳 · 孔明


async def _synth(text: str, voice: str, out_path: str):
    try:
        import edge_tts
    except ImportError:
        print("✗ edge-tts 未装. 跑: pip install edge-tts", file=sys.stderr)
        sys.exit(1)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def play(path: str):
    """跨平台播放 mp3."""
    system = platform.system()
    try:
        if system == "Windows":
            # winsound 只支持 wav · mp3 用 os.startfile 调默认播放器
            os.startfile(path)  # 非阻塞
        elif system == "Darwin":
            subprocess.run(["afplay", path], check=False)
        else:
            # Linux · try paplay / aplay / mpg123
            for cmd in ("mpg123", "paplay", "aplay"):
                if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                    subprocess.run([cmd, path], check=False)
                    return
            print(f"  (Linux 无播放器 · mp3 存在 {path} 手动开)", file=sys.stderr)
    except Exception as e:
        print(f"  (播放失败: {e} · mp3 存在 {path})", file=sys.stderr)


def speak(text: str, voice: str = DEFAULT_VOICE, save_to: str = None, do_play: bool = True) -> str:
    """主 API · 其他 python 代码 `from tts import speak` 用."""
    if not text.strip():
        return ""
    out = save_to or str(pathlib.Path(tempfile.gettempdir()) / f"taijios_tts_{os.getpid()}.mp3")
    asyncio.run(_synth(text, voice, out))
    if do_play:
        play(out)
    return out


def main():
    ap = argparse.ArgumentParser(description="TaijiOS TTS")
    ap.add_argument("--text", default=None, help="要说的话 (或从 stdin 读)")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="voice id (zh-CN-*)")
    ap.add_argument("--save", default=None, help="保存 mp3 到 path (不播)")
    ap.add_argument("--no-play", action="store_true", help="只合成不播")
    args = ap.parse_args()

    text = args.text
    if text is None:
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            print("✗ 需要 --text 或 stdin 输入", file=sys.stderr)
            sys.exit(1)

    do_play = not (args.save or args.no_play)
    out = speak(text, voice=args.voice, save_to=args.save, do_play=do_play)
    print(f"✓ mp3: {out}")


if __name__ == "__main__":
    main()
