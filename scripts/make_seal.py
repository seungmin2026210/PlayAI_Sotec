"""임시 직인(도장) PNG 생성 — 실제 직인이 준비되기 전까지 쓰는 자리표시.

    py -3 scripts/make_seal.py          # backend/app/assets/sotec-seal.png 생성

실제 직인이 오면 이 스크립트로 만든 파일을 **같은 경로에 덮어쓰기만** 하면 된다.
크기가 달라도 출력물에서는 config.SEAL_MM(한 변 mm)로 정규화되므로 정사각 PNG면 된다.
문구/색/크기를 바꾸려면 아래 상수만 고친다. Pillow 필요(backend/.venv).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TEXT = "SOTEC"
SUBTEXT = "대표이사"
COLOR = (200, 16, 46, 210)          # 인주 빨강 + 약간 투명(찍힌 느낌)
PX = 600                             # 출력 PNG 한 변(px). 클수록 축소 시 선명.
OUT = Path(__file__).resolve().parent.parent / "backend" / "app" / "assets" / "sotec-seal.png"


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("malgunbd.ttf", "malgun.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def main() -> None:
    img = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad, ring = PX * 0.06, max(6, PX // 60)

    d.ellipse([pad, pad, PX - pad, PX - pad], outline=COLOR, width=ring)
    d.ellipse([pad * 2.1, pad * 2.1, PX - pad * 2.1, PX - pad * 2.1], outline=COLOR, width=max(3, ring // 2))

    big = _font(int(PX * 0.19))
    d.text((PX / 2, PX * 0.44), TEXT, font=big, fill=COLOR, anchor="mm")
    small = _font(int(PX * 0.11))
    d.text((PX / 2, PX * 0.68), SUBTEXT, font=small, fill=COLOR, anchor="mm")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT}  ({PX}x{PX})")


if __name__ == "__main__":
    main()
