-- 002_tighten_comments_ratings_rls.sql
-- Security Advisor "RLS Policy Always True" 경고 해소 (public.comments, public.ratings).
--
-- 배경: 000_integrated_schema_v1.sql 의 아래 정책들이 USING (true) / WITH CHECK (true)
-- 라서 과도하게 허용적(always true)으로 플래그됨.
--   - "Public read comments"  / "Public insert comments"
--   - "Public read ratings"   / "Public insert ratings"
--
-- 방침: 공개(익명 허용) 기능은 유지하되 정책을 명시화한다.
--   1) 역할을 anon, authenticated 로 한정 (기본 public 역할 적용 제거).
--   2) INSERT 는 user_id 가 NULL(익명)이거나 본인(auth.uid())일 때만 허용
--      → 순수 true 제거 + 로그인 사용자의 user_id 위조 방지.
--   3) SELECT 는 공개 게시판 특성상 전체 공개가 의도된 동작이므로 USING (true) 를
--      유지하되 역할만 한정한다.
--
-- 적용: Supabase 대시보드 SQL Editor 에서 실행하거나 supabase db push 로 반영.
-- 멱등성을 위해 DROP POLICY IF EXISTS 후 재생성한다.

-- RLS 가 켜져 있는지 보장 (이미 켜져 있으면 무시됨)
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ratings  ENABLE ROW LEVEL SECURITY;

-- 기존 정책을 이름과 무관하게 전부 제거한다.
-- (000 의 "Public ..." 이름이든, 대시보드에서 수동 생성된 다른 이름이든 모두 정리)
DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname, tablename
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename IN ('comments', 'ratings')
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', pol.policyname, pol.tablename);
    END LOOP;
END $$;

-- [comments] 공개 읽기 (역할 한정)
CREATE POLICY "comments_select_public" ON public.comments
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- [comments] 익명(user_id NULL) 또는 본인만 작성 가능
CREATE POLICY "comments_insert_anon_or_owner" ON public.comments
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (user_id IS NULL OR auth.uid() = user_id);

-- [ratings] 공개 읽기 (역할 한정)
CREATE POLICY "ratings_select_public" ON public.ratings
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- [ratings] 익명(user_id NULL) 또는 본인만 작성 가능
CREATE POLICY "ratings_insert_anon_or_owner" ON public.ratings
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (user_id IS NULL OR auth.uid() = user_id);

-- 적용 결과 확인용 (필요 시 별도로 실행):
-- SELECT tablename, policyname, cmd, roles, qual, with_check
--   FROM pg_policies
--  WHERE schemaname = 'public' AND tablename IN ('comments', 'ratings')
--  ORDER BY tablename, cmd;
