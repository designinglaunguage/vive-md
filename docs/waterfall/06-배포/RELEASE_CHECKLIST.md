# RELEASE_CHECKLIST

> REQ-101 local-only release gate. 외부 Kimi/news generation 검증은 범위 밖이며, 노트 저장 로컬 계약만 릴리스 증거로 삼는다.

## 1. 릴리스 식별

| 항목 | 내용 |
| --- | --- |
| 릴리스 ID | REL-20260705-REQ101 |
| 핸드오프 ID | CODING_HANDOFF-REQ-101 |
| 요구사항 ID | REQ-101 |
| 게이트 상태 | 완료 |
| 작성일 | 2026-07-05 |

## 2. 테스트 통과 증거

| 검증 명령 | 실행 일시 | 결과 | 증거 링크/로그 |
| --- | --- | --- | --- |
| `python3 -m unittest discover -s tests` | 2026-07-05 | 통과 | `artifacts/g007-test-report.json`; `artifacts/req101-final-verification.json` |
| `python3 -m compileall scripts` | 2026-07-05 | 통과 | `artifacts/g007-test-report.json`; `artifacts/req101-final-verification.json` |
| `python3 -m py_compile scripts/ai-news-collector/ai-daily.py` | 2026-07-05 | 통과 | `artifacts/g007-test-report.json`; `artifacts/req101-final-verification.json` |
| `python3 scripts/p0_check.py --project-root docs/waterfall --stage handoff` | 2026-07-05 | 통과 | `artifacts/req101-p0-handoff-pass.json` |
| `python3 scripts/p0_check.py --project-root docs/waterfall --stage all` | 2026-07-05 | 통과 | `artifacts/req101-final-p0-all.json`; `artifacts/req101-final-verification.json` |

## 3. REVIEW_LOG 참조

| 핸드오프 ID | REVIEW_LOG 항목 날짜 | 리뷰어 | 판정 |
| --- | --- | --- | --- |
| CODING_HANDOFF-REQ-101 | 2026-07-05 | GJC final cleanup/QA lanes | 통과 |

## 4. 롤백 절차

| 롤백 항목 | 롤백 명령 또는 절차 | 롤백 검증 명령 | 책임자 |
| --- | --- | --- | --- |
| 코드 변경 | `[REQ-101]` 커밋들을 되돌린다. | `python3 -m unittest discover -s tests` | GJC |
| 설정 변경 | config.ini [저장] notes_dir 추가를 되돌린다. | `python3 -m py_compile scripts/ai-news-collector/ai-daily.py` | GJC |
| 로컬 노트 산출물 | 생성된 `docs/news/ai-notes` 파일은 부가 산출물이므로 필요 시 삭제한다. | `python3 -m unittest discover -s tests` | GJC |

## 5. 릴리스 후 확인 항목

| 확인 항목 | 확인 방법 | 기대 결과 | 확인 결과 |
| --- | --- | --- | --- |
| --no-notes 계약 | `tests/test_ai_daily_notes.py` main wiring test | 저장 호출 0회 | 통과 |
| 경로 실패 계약 | `tests/test_ai_daily_notes.py` OSError test | WARNING 후 None | 통과 |
| 외부 의존 제외 | RELEASE_CHECKLIST 범위 확인 | Kimi/news e2e 미요구 | 통과 |

## 6. 최종 게이트

- [x] 모든 검증 명령이 통과했다.
- [x] REVIEW_LOG에 같은 핸드오프 ID의 통과 항목이 있다.
- [x] 롤백 명령과 롤백 검증 명령이 비어 있지 않다.
- [x] 릴리스 후 확인 항목의 기대 결과와 확인 방법이 비어 있지 않다.
- [x] `게이트 상태`를 `완료`로 갱신했다.
