"""Firestore 클라이언트 — SQLAlchemy engine/Session 대체. TECH 12-firestore-migration.md.

로컬/테스트는 `FIRESTORE_EMULATOR_HOST` 환경변수만 있으면 인증 없이 에뮬레이터로 붙는다
(google-cloud-firestore 가 이 변수를 자동 인식해 실제 GCP 대신 에뮬레이터로 리다이렉트).
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Callable, TypeVar

from google.api_core.exceptions import Aborted
from google.cloud import firestore
from google.oauth2 import service_account

from .config import settings

_client: firestore.Client | None = None
_T = TypeVar("_T")


def _load_credentials() -> service_account.Credentials | None:
    """Vercel 등 GCP 밖 환경 배포용. `GOOGLE_APPLICATION_CREDENTIALS_JSON`(서비스
    계정 키 JSON 전체를 값으로 담은 환경변수)이 있으면 그걸로 인증정보를 메모리에서
    바로 만든다. 없으면 None을 반환해 google-cloud-firestore 의 기본 인증 탐색
    (`GOOGLE_APPLICATION_CREDENTIALS` 파일 경로, GCE/Cloud Run 메타데이터 서버 등)에
    맡긴다. 12-firestore-migration.md § 9.
    """
    raw = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not raw:
        return None
    info = json.loads(raw)
    return service_account.Credentials.from_service_account_info(info)


def get_client() -> firestore.Client:
    global _client
    if _client is None:
        # pydantic-settings 는 .env 값을 os.environ 에 반영하지 않는다 — google-cloud-firestore
        # 는 FIRESTORE_EMULATOR_HOST 를 os.environ 에서 직접 읽으므로 여기서 명시적으로 넣어준다.
        if settings.firestore_emulator_host and "FIRESTORE_EMULATOR_HOST" not in os.environ:
            os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
        project = os.getenv("FIRESTORE_PROJECT_ID", settings.firebase_project_id)
        # 에뮬레이터 사용 시엔 인증정보 자체가 불필요 — 명시적으로 넘기면 오히려
        # 에뮬레이터 우회 동작과 충돌할 수 있어 이때는 None(=인증 없음)으로 둔다.
        credentials = None if os.environ.get("FIRESTORE_EMULATOR_HOST") else _load_credentials()
        _client = firestore.Client(project=project, credentials=credentials)
    return _client


def reset_client() -> None:
    """테스트 전용: 캐시된 클라이언트를 버린다(프로젝트ID/에뮬레이터 대상 전환 시 사용)."""
    global _client
    _client = None


# `number_sequences` 문서 하나(그룹×연도)를 여러 등록 요청이 동시에 두드리면, Firestore
# 클라이언트가 트랜잭션 내부적으로 재시도(`max_attempts`)해도 경합이 심하면 그마저 소진돼
# `Aborted`/`ValueError("Failed to commit transaction in N attempts")`가 올라온다(에뮬레이터
# 로 4~10 스레드 동시 채번 실측 시 재현됨, 12-firestore-migration.md § 5). 그래서 트랜잭션
# 최대 시도 횟수 위에 애플리케이션 레벨 재시도를 한 겹 더 둔다 — 지수 백오프 + 지터.
def run_transaction(
    client: firestore.Client,
    callback: Callable[[firestore.Transaction], _T],
    *,
    max_attempts: int = 15,
    outer_retries: int = 5,
) -> _T:
    """`callback(transaction)`을 트랜잭션 안에서 실행. 콜백은 순수해야 한다(부작용은
    `transaction.set/update/delete`로만 — 재시도 시 그대로 다시 호출되기 때문)."""
    wrapped = firestore.transactional(callback)
    last_exc: Exception | None = None
    for attempt in range(outer_retries):
        try:
            return wrapped(client.transaction(max_attempts=max_attempts))
        except (Aborted, ValueError) as exc:
            last_exc = exc
            time.sleep(0.05 * (2**attempt) + random.uniform(0, 0.05))
    assert last_exc is not None
    raise last_exc
