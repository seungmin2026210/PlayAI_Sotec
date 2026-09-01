-- 테스트용 DB 추가 생성 (메인 DB 'quote' 는 compose 가 생성)
SELECT 'CREATE DATABASE quote_test OWNER quote'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'quote_test')\gexec
