# Sample Payloads

`run_single_test_profile.py`는 POST/PUT/PATCH 라우트 호출 시 아래 우선순위로 body를 구성합니다.

1. `sample/routes/<route_key>.json`
2. `sample/schemas/<module>.<SchemaName>.json`
3. 스키마 annotation 기반 자동 생성 fallback

## Route 샘플 키 규칙

`route_key = safe("{method.lower()} {normalized_path}")`

예시:

- `[POST] /meetings/{meeting_id}/settlement/rounding`
  - `sample/routes/post_meetings_meeting_id_settlement_rounding.json`

## 실행

```bash
.venv/bin/python scripts/loadtest/run_single_test_profile.py
```

## 메모

- `schemas` 폴더의 파일은 현재 `main.py` 라우트 바디 스키마 기준으로 생성된 기본 샘플입니다.
- `dict` 기반 라우터처럼 스키마로 고정되지 않은 payload는 추측 필드 주입 없이, 실제 라우터 코드에서 참조하는 키만 `routes` 파일에 명시합니다.
