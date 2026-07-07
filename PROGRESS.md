# PROGRESS

## 2026-07-07

- Fable 고도화본 `/home/juns/tmp/vive-md`의 워터폴 템플릿, `docs/waterfall` 증거 문서, CLI/검증 스크립트, 테스트를 C 경로 작업본에 반영했다.
- `templates/waterfall/00-기획/1.아이디어 프로토타입 .md` 파일명 끝 공백을 제거해 `1.아이디어 프로토타입.md`로 정리했다.
- `README.md`, `DOCUMENTATION_INDEX.md`, `CLAUDE.md`, `templates/waterfall/CLAUDE.md`에 새 워터폴 문서 목록을 연결했다.
- 커밋 전 리뷰에서 발견한 누락/깨진 요소를 정리했다. `scripts/ai-news-collector/config.ini`의 `[저장] notes_dir` 기본값, 누락된 `artifacts/` 증거 파일, 생성 handoff 상대 링크, `vive-md` 실행 파일 모드, 문서 깨진 링크를 고쳤다.
- 검증 결과:
  - `python3 scripts/check_coding_handoff.py --self-test` 통과
  - `python3 scripts/p0_check.py --project-root docs/waterfall --stage all` 통과
  - `python3 -m unittest discover -s tests` 통과, 37 tests
  - 루트/워터폴 주요 문서 상대 링크 확인 통과
  - `python3 -m compileall scripts` 통과
- 남은 위험:
  - 작업 전부터 있던 미추적 파일 `assets/logo.png`, `seo-guide.md`, `templates/waterfall/00-기획/(선택)사업아이디어 추출.md`, `templates/waterfall/00-기획/2.제품의사결정체크리스트.md`, `templates/waterfall/07-유지보수/변경이력.md`는 사용자 작업으로 보고 보존했다.
  - `vive-md` CLI 래퍼는 새 테스트 실행에 필요해 함께 추가했다.
