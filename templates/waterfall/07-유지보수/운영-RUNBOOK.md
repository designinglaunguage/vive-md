# 운영-RUNBOOK

> 모니터링, 장애 대응, 포스트모템을 하나로 통합한 운영 문서다. 별도 MONITORING, INCIDENT_RUNBOOK, POSTMORTEM 파일로 분리하지 않는다.

## 1. 무엇을 감시하나

| 감시 대상 | 지표/로그 | 정상 기준 | 알림 조건 | 확인 위치 |
| --- | --- | --- | --- | --- |
| [placeholder: 서비스/API/잡] | [placeholder: 지표명] | [placeholder: 정상 범위] | [placeholder: 임계값] | [placeholder: 대시보드/로그 경로] |
| [placeholder: 데이터/큐/외부연동] | [placeholder: 지표명] | [placeholder: 정상 범위] | [placeholder: 임계값] | [placeholder: 대시보드/로그 경로] |

## 2. 장애 나면 무엇을 하나

| 단계 | 조치 | 명령/위치 | 판단 기준 | 담당 |
| --- | --- | --- | --- | --- |
| 1. 감지 확인 | 알림이 실제 사용자 영향인지 확인한다. | `[placeholder: 확인 명령/URL]` | 영향 있음/없음 판단 | [placeholder] |
| 2. 완화 | 사용자 영향이 큰 기능을 우회하거나 이전 버전으로 되돌린다. | `[placeholder: 완화/롤백 명령]` | 오류율 또는 실패 건수 감소 | [placeholder] |
| 3. 원인 좁히기 | 최근 릴리스, 설정, 외부 의존성을 확인한다. | [placeholder: 로그/릴리스 링크] | 재현 조건 확인 | [placeholder] |
| 4. 복구 확인 | 핵심 스모크와 알림 상태를 확인한다. | `[placeholder: 스모크 명령]` | 정상 기준 복귀 | [placeholder] |
| 5. 공유 | 영향, 조치, 남은 위험을 공유한다. | [placeholder: 채널/문서] | 이해관계자 확인 | [placeholder] |

## 3. 끝나면 무엇을 기록하나

| 항목 | 내용 |
| --- | --- |
| 장애 ID | [INC-YYYYMMDD-000] |
| 발생/감지/복구 시각 | [placeholder: 시간대 포함] |
| 사용자 영향 | [placeholder: 영향 범위와 지속 시간] |
| 직접 원인 | [placeholder: 확인된 원인] |
| 기여 요인 | [placeholder: 감지/테스트/운영 공백] |
| 수행한 조치 | [placeholder: 명령, PR, 설정 변경 링크] |
| 재발 방지 | [placeholder: 담당자와 기한] |
| 관련 RELEASE_CHECKLIST | [placeholder: 경로 또는 해당 없음 사유] |
| 관련 REVIEW_LOG | [placeholder: 날짜/핸드오프 ID 또는 해당 없음 사유] |
