-- 001_create_travel_plans_table.sql
-- 사용자별 여행 계획을 저장하기 위한 테이블 생성

-- 1. 여행 계획 테이블 생성
CREATE TABLE IF NOT EXISTS public.travel_plans (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL, -- Supabase Auth의 유저 ID와 연동
    title TEXT NOT NULL, -- 여행 계획 제목
    destination TEXT NOT NULL, -- 여행 목적지
    content_json JSONB NOT NULL, -- 전체 여행 설계 데이터 (에이전트 결과 등)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. 보안 정책(RLS) 설정: 자신의 데이터만 보고 수정할 수 있도록 함
ALTER TABLE public.travel_plans ENABLE ROW LEVEL SECURITY;

-- 조회: 내 데이터만 가능
CREATE POLICY "Users can view their own travel plans" 
ON public.travel_plans FOR SELECT 
USING (auth.uid() = user_id);

-- 삽입: 내 ID로만 가능
CREATE POLICY "Users can insert their own travel plans" 
ON public.travel_plans FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- 수정: 내 데이터만 가능
CREATE POLICY "Users can update their own travel plans" 
ON public.travel_plans FOR UPDATE 
USING (auth.uid() = user_id);

-- 삭제: 내 데이터만 가능
CREATE POLICY "Users can delete their own travel plans" 
ON public.travel_plans FOR DELETE 
USING (auth.uid() = user_id);
