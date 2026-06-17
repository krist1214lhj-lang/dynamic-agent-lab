-- 000_integrated_schema_v1.sql
-- 여행 계획, 댓글, 평가 시스템을 아우르는 통합 데이터베이스 스키마

-- 1. 기존 테이블 정리 (필요시)
DROP TABLE IF EXISTS public.travel_plans;
DROP TABLE IF EXISTS public.comments;
DROP TABLE IF EXISTS public.ratings;

-- 2. 여행 계획 테이블 (개인용)
CREATE TABLE public.travel_plans (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL, -- Supabase Auth 유저 연동
    title TEXT NOT NULL,
    destination TEXT NOT NULL,
    content_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. 커뮤니티 댓글 테이블 (공용)
CREATE TABLE public.comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID, -- 회원인 경우 저장 (익명 가능)
    user_name TEXT DEFAULT '익명' NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. 웹 서비스 평가 테이블 (공용)
CREATE TABLE public.ratings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID, -- 회원인 경우 저장
    score INTEGER CHECK (score >= 1 AND score <= 5) NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. 보안 정책 (RLS) 설정
ALTER TABLE public.travel_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ratings ENABLE ROW LEVEL SECURITY;

-- [Travel Plans] 내 데이터만 접근 가능
CREATE POLICY "Private plans" ON public.travel_plans FOR ALL USING (auth.uid() = user_id);

-- [Comments] 누구나 읽기 가능, 누구나 작성 가능 (익명 지원)
CREATE POLICY "Public read comments" ON public.comments FOR SELECT USING (true);
CREATE POLICY "Public insert comments" ON public.comments FOR INSERT WITH CHECK (true);

-- [Ratings] 누구나 읽기 가능, 누구나 작성 가능
CREATE POLICY "Public read ratings" ON public.ratings FOR SELECT USING (true);
CREATE POLICY "Public insert ratings" ON public.ratings FOR INSERT WITH CHECK (true);

-- 6. 인덱스 설정 (조회 성능 최적화)
CREATE INDEX idx_travel_plans_user_id ON public.travel_plans(user_id);
CREATE INDEX idx_comments_created_at ON public.comments(created_at DESC);
