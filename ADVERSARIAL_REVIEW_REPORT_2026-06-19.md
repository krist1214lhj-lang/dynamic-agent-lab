# 적대적 코드 검수 보고서 — dynamic-agent-lab

- 작성일: 2026-06-19
- 대상: `main` (검수 시점 HEAD `1e731c6`)
- 관점: 레드팀(적대적). "공격자가 이 시스템으로 무엇을 할 수 있는가"에 초점.
- 범위: 백엔드(`main.py`, `validators/`, `workflow_critic.py`, 에이전트), 프런트(`static/index.html`), 배포·시크릿 설정.
- **주의: 이 문서는 분석·보고만 한다. 코드는 수정하지 않았다.** 수정은 추후 별도 진행.

---

## 0. 한눈에 보기 (심각도 요약)

| # | 심각도 | 항목 | 위치 |
|---|--------|------|------|
| F-1 | **High** | 인증·레이트리밋 없는 `/run-workflow` → LLM/외부API **비용 증폭(denial-of-wallet)** | `main.py:229` |
| F-2 | **High(검증요)** | 테넌트 격리가 **Supabase RLS + anon키 종류에만** 의존(앱 레이어 방어 없음). prod anon키가 service_role이면 IDOR 부활 | `main.py:144`,`172`,`179` |
| F-3 | Med | PostgREST 쿼리스트링에 `plan_id` 직접 보간(파라미터 인젝션 스멜) | `main.py:92,97` |
| F-4 | Med | `load_dotenv(override=True)` + 에이전트별 `.env` 로딩 → 플랫폼 env를 파일이 덮어쓰는 역전 위험 | `main.py:24` |
| F-5 | Med | `**additional_conditions`가 `input_data`의 확정 키(destination/days 등)를 **덮어쓸 수 있음** | `main.py:248-253` |
| F-6 | Med | 읽기 경로가 비-연결 오류(401/403 등)를 **무음 `[]`**로 마스킹 | `main.py:80,84` |
| F-7 | Med | 동적 코드 실행(`exec_module`)으로 에이전트 로딩 — 현재 도달 불가하나 방어취약 | `main.py:222-227` |
| F-8 | Low-Med | 오류 detail에 내부 정보(연결오류·PostgREST 메시지) 표면화 | `main.py:38,51` |
| F-9 | Low-Med | LLM 비평 프롬프트 인젝션(영향은 본인 요청에 한정) | `workflow_critic.py:10-22` |
| F-10 | Low | CORS 미설정(현 구조상 영향 낮음), 회원검증 약함(EmailStr/비번정책 없음) | `main.py:108-109` |
| F-11 | Low | `run_workflow`가 동기(`def`) 블로킹 I/O — F-1과 결합 시 워커 고갈 가속 | `main.py:230` |

가장 시급: **F-1**(이번 세션에 prod `ANTHROPIC_API_KEY`가 활성화되며 실제 과금 표면이 됨)과 **F-2**(전체 데이터 격리의 단일 의존점).

---

## 1. High

### F-1. 인증 없는 `/run-workflow`·`/recommend` → 비용/자원 증폭 공격
**위치:** `main.py:229`(`run_workflow_endpoint`), `:297`(`recommend_endpoint`)
**관찰:**
- 두 엔드포인트 모두 **인증·레이트리밋·CAPTCHA·봇차단 없음**. 누구나 무제한 POST 가능.
- `/run-workflow` 1회가 유발하는 비용:
  1. 최대 9개 에이전트를 매번 `importlib`로 로드 + 실행(`main.py:262-271`).
  2. 각 에이전트가 외부 API(TourAPI/KMA/ODSay) 호출 → **등록된 서비스 키 쿼터 소모**(예: tour agent는 한 요청에 다수의 keyword/detailImage 호출, `travel_tour_agent/main.py:660-837`).
  3. `critique()`가 **Anthropic `claude-haiku-4-5` 실제 호출**(`workflow_critic.py:25-36`) → **요청당 실제 과금**.
**공격 시나리오:** 스크립트로 `/run-workflow`를 반복 호출 → (a) ANTHROPIC 청구액 급증(denial-of-wallet), (b) TourAPI/KMA/ODSay 일일 쿼터 소진(정상 사용자 서비스 마비), (c) Vercel 함수 동시성/실행시간 소진.
**왜 지금 중요한가:** 2026-06-19 세션에서 prod `ANTHROPIC_API_KEY`가 활성화됨. 이전에는 `rule_only`라 LLM 과금 표면이 없었으나, **이제는 무인증 엔드포인트가 직접 돈을 쓴다.**
**완화 방향(추후):** 최소 레이트리밋(IP/세션 기준), Vercel Firewall/BotID, `/run-workflow`에 경량 인증 또는 토큰버킷, LLM 호출에 일일 상한/캐시. 동기 블로킹(F-11)도 함께.

---

### F-2. 데이터 격리가 RLS + anon키 종류에만 의존 (앱 레이어 방어 부재)
**위치:** `main.py:144-154`(`_user_id_from_token`), `:172`,`:179`,`:188`,`:195`
**관찰:**
- 서버는 JWT **서명을 검증하지 않는다**. `_user_id_from_token`은 payload를 base64 디코드해 `sub`만 추출(주석: "유효성은 Supabase가 RLS에서 검증").
- 모든 plan 접근은 사용자 토큰을 PostgREST로 그대로 전달 → RLS(`auth.uid()=user_id`)가 실제 경계.
- 구조적으로 **위조 토큰은 DB에서 거부**되므로(서명 불일치 → `auth.uid()` null → RLS 차단) 현재는 안전.
**리스크:** 전체 테넌트 격리가 **단일 지점 두 개**에 100% 의존한다 — ① Supabase RLS 정책이 올바르게 켜져 있을 것, ② `SUPABASE_ANON_KEY`가 **publishable(anon) 키일 것**. 만약 prod env의 `SUPABASE_ANON_KEY`가 과거처럼 `service_role` 비밀키라면 **RLS가 전면 무력화되어 IDOR(C-1/C-2)가 부활**한다. 앱 레이어에는 이를 잡아줄 2차 방어가 없다.
**검증 필요(코드로 확인 불가):** prod `SUPABASE_ANON_KEY`가 anon/publishable인지 대시보드에서 확인. (메모상 2026-06-17에 publishable로 교체했다고 기록되나, 본 검수에서 키 종류를 직접 확인하지는 못함 — `vercel env ls`는 "Encrypted"만 표시.)
**완화 방향(추후):** 서버에서 JWT 서명 검증(Supabase JWKS) 추가해 2차 방어 확보, anon키 종류 모니터링, RLS 정책 회귀 테스트 유지.

---

## 2. Medium

### F-3. PostgREST 필터에 `plan_id` 직접 문자열 보간
**위치:** `main.py:92`(`patch`), `:97`(`delete`) — `f"{self.table_url}?id=eq.{plan_id}"`
**관찰:** `plan_id`(경로 파라미터)를 URL 인코딩 없이 쿼리스트링에 삽입. `&`·PostgREST 연산자가 섞이면 필터 조작 시도가 가능한 인젝션 스멜.
**영향:** UPDATE/DELETE는 RLS `USING (auth.uid()=user_id)`로 본인 행에 한정되므로 **현재 피해는 본인 데이터 범위로 제한**. 그래도 신뢰 못 할 입력을 쿼리에 직접 보간하는 패턴은 제거 권장.
**완화 방향:** 값 URL 인코딩 또는 PostgREST 파라미터 안전 처리.

### F-4. `load_dotenv(override=True)` — 플랫폼 env를 파일이 덮어씀
**위치:** `main.py:24`; 에이전트 `load_service_key`(`travel_tour_agent/main.py:183-210`)
**관찰:** `override=True`는 OS/플랫폼 환경변수보다 `.env` 파일 값을 우선시킨다(정상 우선순위의 역전). `conftest.py`도 "동적 로드 에이전트가 `load_dotenv(override=True)`로 키를 되살린다"는 부작용을 명시.
**리스크:** `.env`가 번들에 포함되는 일이 생기면(현재는 `.gitignore`로 차단됨) 플랫폼 시크릿을 파일이 덮어써 의도치 않은 키로 동작. 테스트에서 이미 한 번 발목을 잡은 패턴.
**완화 방향:** prod 경로에서는 `override=False` 또는 파일 로딩 비활성, 에이전트별 `.env` 의존 제거.

### F-5. `additional_conditions`가 확정 입력을 덮어쓸 수 있음
**위치:** `main.py:248-253` — `input_data = { ...확정키... , **payload.additional_conditions }`
**관찰:** 사용자 제공 `additional_conditions` dict가 **맨 뒤에 spread**되어 `destination`/`days`/`people`/`budget_level` 등 검증된 값을 덮어쓸 수 있다(예: `{"days": 100000}`).
**영향:** 대부분 본인 요청에만 영향이나, 비정상 `days` 등으로 에이전트 루프·자원 사용을 키워 F-1을 증폭할 수 있다.
**완화 방향:** 화이트리스트 키만 병합(themes/companions/priority 등)하거나 spread를 확정키 **앞**에 두기.

### F-6. 읽기 경로가 비-연결 오류를 무음 `[]`로 마스킹
**위치:** `main.py:80`(`select_all`), `:84`(`select_mine`) — `return resp.json() if resp.ok else []`
**관찰:** G3에서 쓰기 경로는 `_sb_raise_for_status`로 표준화했으나, 읽기는 여전히 비-ok 응답(401/403/5xx)을 빈 배열로 삼킨다. 사용자는 "데이터 없음"으로 오인.
**완화 방향:** 연결오류 외 PostgREST 에러도 표면화하거나 최소 로깅.

### F-7. 동적 코드 실행(`exec_module`)으로 에이전트 로딩
**위치:** `main.py:222-227`(`load_agent`), `:219`(`EXTERNAL_AGENT_LIBRARY = D:/AI_AGENT_LIBRARY`)
**관찰:** `agent.json`의 `entrypoint`를 읽어 `exec_module`. 에이전트 이름은 고정 `FEATURE_AGENT_MAP`에서만 오므로 **사용자 입력 경로 주입은 불가**. 하드코딩된 외부 경로는 Vercel에 존재하지 않아 prod에선 내부 에이전트만 로드.
**리스크:** 현재 도달 불가하나, 에이전트 디렉터리/`agent.json`에 쓰기 권한을 얻은 공격자에겐 즉시 RCE가 되는 구조. 방어취약(심층방어 관점) 기록.

---

## 3. Low ~ Low-Med

### F-8. 오류 detail에 내부 정보 표면화
`main.py:38`(`Supabase 연결 오류: {e}`), `:51`(PostgREST message 전달). 내부 URL/스키마 힌트가 클라이언트로 샐 수 있음. 사용자용 일반 메시지 + 서버 로깅 분리 권장.

### F-9. LLM 비평 프롬프트 인젝션
`workflow_critic.py:10-22`. `user_request` 등이 프롬프트에 포함. 다만 `_parse_critique`가 `valid_agents`만 수용하고 `PROTECTED_AGENTS`는 드롭 불가(`:48-49,61`)라 **영향은 공격자 본인 요청의 keep/drop 왜곡에 한정**. 교차사용자 영향 없음.

### F-10. CORS 미설정 / 회원검증 약함
- CORS 미들웨어 없음. 인증은 쿠키가 아닌 Bearer(JS)라 CSRF 표면은 작고, 상태변경 POST(`/comments` 등)는 원래 무인증이라 CORS 부재의 추가 피해는 낮음.
- `SignupRequest.email`이 `EmailStr`이 아닌 `str`, 비밀번호 정책 없음(`main.py:108-109`). Supabase 자체 최소정책에 의존.

### F-11. `run_workflow`가 동기 블로킹
`main.py:230` `def`(비-async)에서 최대 9개 순차 외부호출 + LLM 호출. 요청당 수 초 소요 가능 → F-1과 결합 시 서버리스 워커 고갈을 가속.

### 기타(비보안/정합성)
- `build_mock_tour_result`의 이미지가 `https://example.com/...` 더미(`travel_tour_agent/main.py:1014~`) — mock 모드에서 깨진 이미지.
- `/agent-library`·`/health`가 카운트 `10`을 하드코딩(`main.py:311,315`).
- 마이그레이션 `000_integrated_schema_v1.sql` 선두 `DROP TABLE IF EXISTS` — **재실행 시 데이터 소실** 위험(운영 DB에 무심코 적용 금지). comments/ratings엔 DELETE/UPDATE 정책 없음(공개 게시판 의도).

---

## 4. 잘 되어 있는 점 (적대적 관점에서도 합격)

- **테넌트 격리 동작 검증됨**: 사용자 토큰 포워딩 + RLS로 IDOR 차단(이전 세션 브라우저 E2E로 실증).
- **출력 이스케이프 일관**: `escapeHtml` 26곳, 댓글 렌더(`index.html:577`)에도 `user_name`/`content` 모두 적용 → 저장형 XSS 차단.
- **시크릿 위생 양호**: `.gitignore`가 `.env`·`.env.*`·`*.key`·`*.pem`·`.vercel` 차단, 추적되는 건 `.env.example`(플레이스홀더)뿐. 키가 git에 커밋된 적 없음.
- **그레이스풀 폴백**: 외부 API 실패 → mock, LLM 실패/키없음 → `rule_only`(`workflow_critic.py:59-60`). 가용성 양호.
- **회귀 테스트 자산**: 81개 통과. RLS/Supabase 예외/인증 502 등 보안 회귀 테스트 포함.
- **최근 강화**: G3 예외 표준화 + 본 세션 인증 502 표면화 + Pydantic v2 정리.

---

## 5. 추후 수정 권고 순서 (수정은 별도 진행)

1. **F-1**: `/run-workflow`·`/recommend` 레이트리밋/봇차단 + LLM 호출 상한·캐시 (지갑 고갈 차단). 최우선.
2. **F-2 검증**: prod `SUPABASE_ANON_KEY`가 publishable인지 즉시 확인. 이후 서버측 JWT 서명검증으로 2차 방어.
3. **F-5 / F-3**: 입력 화이트리스트 병합, PostgREST 값 인코딩.
4. **F-4 / F-6**: `override` 정책 정리, 읽기 오류 표면화.
5. F-8~F-11 및 정합성 항목은 후속 정리.

---

## 6. 검수가 확인하지 못한 것(코드 밖)

- prod `SUPABASE_ANON_KEY`의 실제 키 종류(anon vs service_role) — 대시보드 확인 필요(F-2 전제).
- Supabase 'Confirm email' ON 여부, 테스트 계정/잔존 댓글(`rls-regression`) 정리 여부 — anon키로 확인 불가.
- Vercel Firewall/BotID 등 플랫폼 레이어 보호 활성 여부.
