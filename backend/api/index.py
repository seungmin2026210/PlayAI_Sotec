"""Vercel Python 런타임 진입점. `api/` 아래 파일에서 노출한 ASGI `app`을
Vercel이 자동으로 서버리스 함수로 인식한다. 실제 애플리케이션 정의는
`app/main.py`에 그대로 있고, 여기서는 재노출만 한다.
"""

from app.main import app

__all__ = ["app"]
