---
description: "이모지와 컨벤셔널 커밋 메시지로 잘 포맷된 커밋을 생성합니다"
allowed-tools:
  [
    "Bash(git add:*)",
    "Bash(git status:*)",
    "Bash(git commit:*)",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git branch:*)",
    "Bash(git switch:*)",
  ]
---

# Claude 명령어: Commit

이모지와 컨벤셔널 커밋 메시지로 잘 포맷된 커밋을 생성합니다.

## 사용법

```
/commit
```

## 프로세스

1. 현재 브랜치 확인 (`git branch --show-current`)
   - main/master이고 변경이 hotfix(🚑️, 긴급 수정)가 아니면 → 커밋 전에 새 브랜치 생성·전환 (`git switch -c`)
     - 이름 규칙은 `/git:branch`와 동일: `<프리픽스>/<kebab-case-설명>` (예: `feature/user-search`, `fix/login-error`)
     - 프리픽스는 커밋 타입에서 유도: feat→`feature/`, fix→`fix/`, refactor→`refactor/`, docs→`docs/`, test→`test/`, 그 외(chore/style/perf 등)→`chore/`
   - hotfix이거나 이미 작업 브랜치에 있으면 브랜치 생성 없이 진행
2. 스테이지된 파일 확인, 스테이지된 파일이 있으면 해당 파일만 커밋
3. 여러 논리적 변경사항에 대한 diff 분석
4. 필요시 분할 제안
5. 이모지 컨벤셔널 포맷으로 커밋 생성

## 커밋 포맷

`<이모지> <타입>: <설명>`

**타입:**

- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서화
- `style`: 포맷팅
- `refactor`: 코드 리팩토링
- `perf`: 성능 개선
- `test`: 테스트
- `chore`: 빌드/도구

**규칙:**

- 명령형 어조 ("추가" not "추가됨")
- 첫 줄 72자 미만
- 원자적 커밋 (단일 목적)
- 관련 없는 변경사항 분할

## 이모지 맵

✨ feat | 🐛 fix | 📝 docs | 💄 style | ♻️ refactor | ⚡ perf | ✅ test | 🔧 chore | 🚀 ci | 🚨 warnings | 🔒️ security | 🚚 move | 🏗️ architecture | ➕ add-dep | ➖ remove-dep | 🌱 seed | 🧑‍💻 dx | 🏷️ types | 👔 business | 🚸 ux | 🩹 minor-fix | 🥅 errors | 🔥 remove | 🎨 structure | 🚑️ hotfix | 🎉 init | 🔖 release | 🚧 wip | 💚 ci-fix | 📌 pin-deps | 👷 ci-build | 📈 analytics | ✏️ typos | ⏪️ revert | 📄 license | 💥 breaking | 🍱 assets | ♿️ accessibility | 💡 comments | 🗃️ db | 🔊 logs | 🔇 remove-logs | 🙈 gitignore | 📸 snapshots | ⚗️ experiment | 🚩 flags | 💫 animations | ⚰️ dead-code | 🦺 validation | ✈️ offline

## 분할 기준

다른 관심사 | 혼합된 타입 | 파일 패턴 | 큰 변경사항

## 참고사항

- main/master에서 hotfix가 아닌 커밋 시 브랜치를 먼저 생성함
- 스테이지된 파일이 있으면 해당 파일만 커밋
- 분할 제안을 위한 diff 분석
- **커밋에 Claude 서명 절대 추가하지 않음**
