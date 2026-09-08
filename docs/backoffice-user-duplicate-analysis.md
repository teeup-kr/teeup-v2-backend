# 백오피스 유저 목록 중복 출력 원인 분석

## 결론

- **DB/백엔드에서는 유저가 중복으로 반환되지 않습니다.**
- 실제로 등록된 API는 **한 개**이며 (`GET /api/v1/admin/users`), 쿼리도 단순 `User` 조회 + 페이지네이션이라 동일 유저가 두 번 나올 구조가 아닙니다.
- 따라서 **화면에서의 중복은 프론트엔드(백오피스 웹) 쪽 원인일 가능성이 큽니다.**

---

## 1. 백엔드 라우트 확인

- `main.py`에서는 `from routers import admin`으로 **패키지** `routers/admin/` 만 로드합니다.
- `routers/admin/__init__.py`에서 `users_router`만 포함하므로, **유저 목록 API는 다음 하나만** 등록됩니다.
  - `GET /api/v1/admin/users` → `routers/admin/users.py`의 `get_admin_users`
- 같은 경로의 다른 파일인 `routers/admin.py`에도 `GET /users`가 정의돼 있지만, 이 파일은 앱에 포함되지 않습니다 (패키지 `admin/`이 우선).  
  → **동일 경로가 두 번 등록돼서 중복 응답을 만드는 상황은 없음.**

---

## 2. 백엔드 쿼리 확인

`routers/admin/users.py`의 `get_admin_users`:

- `db.query(User).filter(...).order_by(...).offset(offset).limit(limit).all()` 로 **User 테이블만** 조회.
- 조인 없음 → 한 유저당 행이 한 번만 나옴.
- `user_responses`는 `for user in users`로 한 번씩만 append.

따라서 **같은 유저가 응답 배열에 두 번 들어가는 구조는 아님.**

---

## 3. 프론트엔드에서 확인할 것 (백오피스 웹)

DB/백엔드에 중복이 없다면, 아래를 순서대로 점검하는 것이 좋습니다.

1. **API를 두 번 호출하고 결과를 합치지 않는지**
   - 예: `fetch`를 두 번 호출하고 `setUsers([...prev, ...res.data])`처럼 이전 목록에 계속 이어붙이기.
   - 페이지네이션일 때: 새 페이지 요청 시 **기존 목록을 교체**하는지, **추가**하는지 확인.

2. **목록 상태를 한 번만 설정하는지**
   - 예: `useEffect` 안에서 `setUsers(data)`를 두 번 호출하거나,  
     의존성 배열 때문에 effect가 두 번 돌면서 이전 결과 + 새 결과가 합쳐지지 않는지.

3. **React 리스트 key**
   - `<tr key={user.id}>` 또는 `<div key={user.id}>` 처럼 **유저 고유 id**를 key로 쓰는지 확인.
   - `key={index}` 사용 시 정렬/필터 시 React가 잘못 매칭해 겉보기에 중복처럼 보일 수 있음.

4. **같은 목록을 두 군데서 그리지 않는지**
   - 예: 상단 요약 테이블 + 본문 테이블이 같은 `users`를 참조하는데, 한쪽은 필터/슬라이스 없이 전체를 두 번 렌더링하는 경우.

5. **React Strict Mode**
   - 개발 모드에서 Strict Mode면 일부 effect가 두 번 실행될 수 있음.  
     위 1, 2번과 결합되면 “같은 응답을 두 번 반영”해 중복처럼 보일 수 있음.

---

## 4. 백엔드에서 검증하고 싶을 때

API 응답에 실제로 중복이 없는지 확인하려면, `get_admin_users` 반환 직전에 아래처럼 로그를 넣어볼 수 있습니다.

```python
# routers/admin/users.py, return 직전
ids = [u.id for u in user_responses]
assert len(ids) == len(set(ids)), "duplicate user ids in response"
logger.info("get_admin_users count=%s ids=%s", len(ids), ids[:20])
```

- `assert`가 터지면 백엔드에서 중복이 나오는 것이고,  
- 한 번도 안 터지면 응답에는 중복이 없으므로 프론트엔드 원인으로 좁혀갈 수 있습니다.

---

## 5. 참고: 사용하지 않는 `routers/admin.py`

- `routers/admin.py`에는 `prefix="/admin"`과 `GET /users`가 있어, 패키지 `routers/admin/`과 경로가 겹칩니다.
- 현재는 패키지만 로드되므로 문제는 없지만, 나중에 이 파일을 라우터에 포함하면 **같은 엔드포인트가 두 번 등록**될 수 있습니다.
- 혼동을 줄이려면 `routers/admin.py`를 제거하거나, 백오피스용이 아니면 prefix/이름을 바꾸는 것이 좋습니다.
