# REQ-101 friction log

## Setup cost

Setup cost is recorded separately in `SETUP_COST.md` and excluded from this feature-cycle cost.

## Feature-cycle observations

| 단계 | 관찰 | 재작업 커밋 | 기준선 diff | 게이트 오탐 |
| --- | --- | --- | --- | --- |
| SRS/용어 등록 | REQ-101 요구사항과 노트 저장 관련 용어 3개를 추가했다. | 0 | 0 | 0 |
| handoff scaffold | 생성 직후 P0가 placeholder handoff를 정상 실패시켰다. | 0 | 0 | 0 |
| handoff 작성 | 보안 체크는 terminal allowlist 때문에 `점검 완료/영향 없음/확인 필요 없음`만 사용해야 했다. | 0 | 0 | 0 |
| 구현+테스트 | ai-daily 노트 저장 계약 구현, 신규 테스트 4개 추가, 전체 32개 테스트 통과. | 0 | 0 | 0 |
| REVIEW_LOG/릴리스 | REVIEW_LOG 수동 행 추가 및 RELEASE_CHECKLIST local-only 릴리스 게이트 작성. | 0 | 0 | 0 |
| final gate cleanup | 최종 리뷰에서 REVIEW_LOG placeholder row와 P0 false-pass gap을 발견해 G007로 수정했다. | 1 | 1 | 1 |

Current friction definition: rework commit OR baseline diff OR gate false-positive/false-negative. Current count after all rows: 1.