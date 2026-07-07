# RELEASE_CHECKLIST

> 기능 단위 릴리스 게이트다. 이 체크리스트가 완료되고 REVIEW_LOG에 해당 핸드오프 ID가 1개 이상 있어야 릴리스한다.

## 1. 릴리스 식별

| 항목 | 내용 |
| --- | --- |
| 릴리스 ID | [REL-YYYYMMDD-000] |
| 핸드오프 ID | [CODING_HANDOFF-REQ-000] |
| 요구사항 ID | [REQ-000] |
| 게이트 상태 | [미완료/완료] |
| 작성일 | [YYYY-MM-DD] |

## 2. 테스트 통과 증거

| 검증 명령 | 실행 일시 | 결과 | 증거 링크/로그 |
| --- | --- | --- | --- |
| `[placeholder: handoff의 검증 명령]` | [YYYY-MM-DD HH:MM] | [통과/실패] | [placeholder: 로그 경로] |

## 3. REVIEW_LOG 참조

| 핸드오프 ID | REVIEW_LOG 항목 날짜 | 리뷰어 | 판정 |
| --- | --- | --- | --- |
| [CODING_HANDOFF-REQ-000] | [YYYY-MM-DD] | [placeholder: 리뷰어] | [통과/수정 필요/차단] |

## 4. 롤백 절차

| 롤백 항목 | 롤백 명령 또는 절차 | 롤백 검증 명령 | 책임자 |
| --- | --- | --- | --- |
| 코드 변경 | `[placeholder: revert/cherry-pick/배포 되돌리기 명령]` | `[placeholder: 롤백 후 검증 명령]` | [placeholder: 이름] |
| 데이터/마이그레이션 | [placeholder: 해당 없음이면 이유 포함] | `[placeholder: 검증 명령 또는 해당 없음]` | [placeholder: 이름] |
| 설정/의존성 | [placeholder: 해당 없음이면 이유 포함] | `[placeholder: 검증 명령 또는 해당 없음]` | [placeholder: 이름] |

## 5. 릴리스 후 확인 항목

| 확인 항목 | 확인 방법 | 기대 결과 | 확인 결과 |
| --- | --- | --- | --- |
| 핵심 기능 스모크 | [placeholder: 실행 방법] | [placeholder: 기대 결과] | [대기/통과/실패] |
| 로그/알림 | [placeholder: 확인 위치] | 오류 알림 없음 | [대기/통과/실패] |
| 롤백 준비 | [placeholder: 담당자와 명령 확인] | 즉시 실행 가능 | [대기/통과/실패] |

## 6. 최종 게이트

- [ ] 모든 검증 명령이 통과했다.
- [ ] REVIEW_LOG에 같은 핸드오프 ID의 통과 또는 결함 처리 완료 항목이 있다.
- [ ] 롤백 명령과 롤백 검증 명령이 비어 있지 않다.
- [ ] 릴리스 후 확인 항목의 기대 결과와 확인 방법이 비어 있지 않다.
- [ ] `게이트 상태`를 `완료`로 갱신했다.
