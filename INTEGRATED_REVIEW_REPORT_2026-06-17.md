# 통합 리뷰 보고서 (Gemini 리뷰 + 보안/연결 점검 교차검증)

작성일: 2026-06-17 · 대상: `main` 작업트리 현재 상태 · 방식: 정적 분석, 무수정

> ⚠️ **검토 기준 차이**: `GEMINI_CLI_REVIEW_REPORT.md`는 `2 files / +343 / -285` 시점 스냅샷이고,
> 현재 작업트리는 `+347 / -264`로 그 이후 또 변경되었습니다(세션 중 `static/index.html` 560여 줄 → 441줄).
> 그래서 Gemini 지적 중 일부는 이미 수정되었거나 부분만 유효합니다. 아래는 전부 현재 코드로 재확인한 결과입니다.

---

## 0. 프로젝트 연결 현황 (요약)

| 영역 | 내용 |
|------|------|
| 프로젝트 | dynamic-agent-lab (앱명 `ONE'S OWN AI Travel Lab`), FastAPI 여행설계 웹앱 |
| GitHub | `https://github.com/krist1214lhj-lang/dynamic-agent-lab.git` (HTTPS, branch `main`) |
| Vercel | `vercel.json` → `@vercel/python`, 엔트리 `api/index.py` → `from main import app`, 배포주소 `https://dynamic-agent-lab.vercel.app` |
| Supabase | Direct REST API 방식(`main.py`의 자체 `SupabaseClient`), 테이블 `travel_plans`(RLS 정책 작성됨)/`comments`/`ratings` |
| 외부 API | 기상청 KMA(`KMA_SERVICE_KEY`), TourAPI(`TOUR_API_SERVICE_KEY`), ODsay(`ODSAY_API_KEY`) — 키 없으면 mock_fallback |
| 내부 에이전트 | `agents/` 10개 (`travel_*`), 외부 폴백 `D:/AI_AGENT_LIBRARY` |
| 미커밋 변경 | `main.py`, `static/index.html` (2 files, +347 / -264) |

---

## 1. Gemini 지적 재검증 결과

| # | Gemini 지적 | 현재 코드 검증 | 판정 |
|---|------------|---------------|------|
| G1 | `destination` 선택해도 agent 미실행 | `base_order`에 `travel_destination_agent` 없음(main.py:164), 기본 features에도 `destination` 없음(:161) | ✅ 여전히 유효 (High) |
| G2 | `/feature-map`에 `feature_count` 누락 | `def feat(): return {"features": FEATURE_AGENT_MAP}` (:205) — 없음 | ✅ 여전히 유효 (Med) |
| G3 | Supabase 예외 미처리 | `insert`/`delete`는 `ConnectionError` 미포착, 실패 시 `{}` 반환(무음 실패) | ✅ 여전히 유효 (Med) |
| G4 | 보관함 CRUD 축소 (서버 PATCH 제거 등) | 서버 `@app.patch`는 현재 존재(:111) → 복구됨. 단 프런트엔드 제목수정/비로그인 로컬저장/로그인 시 마이그레이션은 여전히 없음 | ⚠️ 부분 유효 (백엔드 OK, 프런트 회귀 잔존) |
| G5 | 프런트 `innerHTML` XSS | `${r.summary}`,`${res.summary}`,`${res.total}`, recommendations `${t}`, 저장플랜 `${p.title}`(:390) escape 없음. 교통/댓글/circle title은 escape됨 → 불일치 | ✅ 여전히 유효 (Med→High, X-1 참고) |
| G6 | 교통카드 CSS `flex-wrap:gap:20px` 오타 | 현재 `flex-wrap:wrap; gap:20px`(:353) — 오타 없음 | ✔️ 이미 수정됨 (해결) |

---

## 2. 보안/연결 점검 결과 (현재도 유효 재확인)

| ID | 내용 | 현재 검증 | 심각도 |
|----|------|----------|--------|
| C-1 | **IDOR** — `user_id`를 클라이언트 쿼리로 신뢰, 토큰 검증 없음 | index.html:384 `user_id=${currentUser.id}` 그대로, main.py:103~122 토큰 미검증 | 🔴 Critical |
| C-2 | `SUPABASE_ANON_KEY`에 **service_role 비밀키**(`sb_secret_`) → RLS 무력화 | 변동 없음(서버 전용·미노출은 양호) | 🔴 Critical |
| M-1 | `SUPABASE_URL`이 `http://` (HTTPS 아님) | 변동 없음 | 🟡 Medium |
| M-2 | `comments`/`ratings` 마이그레이션·권한 없음(공개 read/write) | 변동 없음 | 🟡 Medium |
| L-1 | `ratings.json` 고아 파일(평점은 Supabase로 이동) | 변동 없음 | 🟢 Low |
| L-2 | KMA·TOUR 서비스키 동일 값(64자) | 변동 없음 | 🟢 Low |
| L-3 | GitHub 소유자 `krist1214lhj-lang` vs 로컬 git user `krist1214lhj` 네임스페이스 불일치 | 변동 없음 | 🟢 Low |
| L-4 | `EXTERNAL_AGENT_LIBRARY = D:/AI_AGENT_LIBRARY` 하드코딩 | 변동 없음 | 🟢 Low |

> 참고: `.env`의 `SUPABASE_URL` 값 앞 공백은 python-dotenv가 자동 제거하므로 문제 아님(검증 완료).

---

## 3. 교차로 드러난 복합 위험

### X-1. 저장형(Stored) XSS × RLS 부재 = 실제 공격 성립
G5(저장플랜 `title`·`summary` escape 없음) + C-2(RLS 무력) + C-1(타인 데이터 쓰기 가능)이 결합.
공격자가 `/api/plans`에 임의 `user_id`로 악성 `<script>` 제목 저장(C-1) → 피해자 보관함 조회 시
`${p.title}`가 escape 없이 `innerHTML` 삽입(G5) → 스크립트 실행. RLS가 살아있었다면 차단됐을 경로가 C-2로 열림.
→ G5는 단독 Medium이지만 C-1·C-2와 합치면 실효 High.

### X-2. 무음 실패 + 예외 전파 (G3 보강)
`insert()`가 실패해도 `{}` 반환 → 프런트는 "저장됨"으로 인지하나 실제 미저장(데이터 유실).
반대로 `ConnectionError`는 그대로 500 전파. 둘 다 사용자에게 정확한 신호를 주지 못함.

---

## 4. 통합 우선순위 (권고 — 적용은 별도 지시 시)

| 순위 | 항목 | 근거 |
|------|------|------|
| 1 | **G1** destination 라우팅 복구 | 기능 즉시 깨짐 + 스모크 테스트 실패. 1곳 수정 |
| 2 | **C-1+C-2** 토큰 기반 인증 + 키 분리(secret→publishable) | IDOR·RLS 무력화 동시 해결, X-1 차단 |
| 3 | **G5** 모든 서버/사용자 출력 `escapeHtml` 일관 적용 | X-1 2차 방어선 |
| 4 | **M-1** `https` | 1줄, 무위험 |
| 5 | **G2** `feature_count` 복구 / **G3** 예외 표준화 | API 계약·안정성 |
| 6 | **G4(프런트)** 제목수정/로컬저장 회귀가 의도인지 확정 | 제품 결정 필요 |
| 7 | **M-2 / L-1~4** 마이그레이션·정리 | 위생 |

---

## 5. 양호 확인 (회귀 아님)
- G6 CSS 오타: 이미 수정됨.
- 서버 `PATCH /api/plans` 엔드포인트: 존재(Gemini 시점엔 없었음).
- `.env`·비밀키 git 미커밋, 프런트 키 미노출, `travel_plans` RLS 정책 자체는 정상 작성(키 문제로 미적용일 뿐).

---

## 6. 인증/권한 수정안 설계 (방식 B 권장, 미적용 초안)

목표 흐름:
```
[브라우저] access_token(JWT) ──Bearer 헤더──> [FastAPI] ──사용자 JWT 그대로 전달──> [Supabase REST]
                                  ▲ 토큰=신원              ▲ RLS(auth.uid()=user_id) 자동 적용
```

- `.env`: `SUPABASE_URL`을 `https://`로, `SUPABASE_ANON_KEY`를 publishable 키로 교체. secret 키는 필요 시 `SUPABASE_SERVICE_KEY`로 분리.
- `main.py`: 테이블 메서드가 요청자 `access_token`을 받아 그 토큰으로 PostgREST 호출(RLS 적용). 엔드포인트는 `user_id` 쿼리 대신 `Authorization` 헤더 신뢰, user_id는 토큰에서 도출.
- `static/index.html`: 로그인 시 `data.access_token` 저장, `/api/plans` 호출에 `Authorization: Bearer` 헤더 추가, `user_id` 쿼리 제거.
- `comments`/`ratings`: `supabase/migrations/002_*.sql` 신규 생성으로 테이블·RLS 정책 정의.

---

## 결론
Gemini 리뷰의 핵심 기능 회귀(G1 destination, G2 feature_count, G3 예외, G5 XSS)는 현재도 유효하나,
G6은 해결되었고 G4는 백엔드만 복구된 상태. 여기에 보안 점검(C-1 IDOR, C-2 secret키/RLS)이 더해지면
단독 Medium이던 G5 XSS가 실제 공격 가능한 High(X-1)로 격상. 따라서 **G1(기능) → C-1·C-2(인증) → G5(XSS)** 순서 최우선 권고.

> 본 보고서 작성 및 점검 과정에서 어떤 소스 파일도 수정하지 않았습니다.
