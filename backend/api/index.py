"""Vercel Python 런타임 진입점. `api/` 아래 파일에서 노출한 ASGI `app`을
Vercel이 자동으로 서버리스 함수로 인식한다. 실제 애플리케이션 정의는
`app/main.py`에 그대로 있고, 여기서는 재노출만 한다.

Vercel은 이 파일이 있는 디렉터리(`backend/api/`)만 실행 경로로 잡고 `backend/`
자체는 sys.path에 넣어주지 않는다 — `app` 패키지(`backend/app/`)를 못 찾고
모듈 임포트가 실패해 모든 요청이 FUNCTION_INVOCATION_FAILED로 떨어지는 원인이
됐다. 임포트 전에 상위 디렉터리를 직접 경로에 추가해 해결한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

__all__ = ["app"]
