-- ============================================================================
-- SQL DDL untuk Supabase — One Day One Movie
-- ============================================================================
-- Jalankan script ini di Supabase SQL Editor:
-- Dashboard > SQL Editor > New Query > Paste > Run
-- ============================================================================

-- Tabel: recommendations
-- Menyimpan setiap film yang pernah direkomendasikan oleh sistem.
-- Status: 'recommended', 'watched', 'rerolled', 'skipped'
CREATE TABLE IF NOT EXISTS recommendations (
    id               BIGSERIAL PRIMARY KEY,
    movie_id         INTEGER NOT NULL,
    title            TEXT NOT NULL,
    poster_path      TEXT,
    release_date     TEXT,
    genres           TEXT,
    vote_average     REAL,
    overview         TEXT,
    trailer_url      TEXT,
    providers_json   TEXT,
    recommended_date TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'recommended',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabel: journal
-- Menyimpan ulasan personal (rating & review) untuk film yang sudah ditonton.
CREATE TABLE IF NOT EXISTS journal (
    id           BIGSERIAL PRIMARY KEY,
    movie_id     INTEGER NOT NULL,
    rating       INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review       TEXT,
    watched_date TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indeks untuk performa query
CREATE INDEX IF NOT EXISTS idx_rec_movie_id ON recommendations(movie_id);
CREATE INDEX IF NOT EXISTS idx_rec_date ON recommendations(recommended_date);
CREATE INDEX IF NOT EXISTS idx_rec_status ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_journal_movie_id ON journal(movie_id);

-- ============================================================================
-- KEAMANAN: Aktifkan RLS + batasi akses public
-- ============================================================================
-- Default aman untuk deployment publik:
-- 1) RLS aktif pada semua tabel yang diekspos PostgREST
-- 2) Role anon/authenticated tidak diberi akses langsung ke tabel ini
-- 3) Akses penuh hanya untuk service_role (server-side secret)
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON recommendations FROM anon, authenticated;
REVOKE ALL ON journal FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;

DROP POLICY IF EXISTS recommendations_service_role_all ON recommendations;
DROP POLICY IF EXISTS journal_service_role_all ON journal;

CREATE POLICY recommendations_service_role_all
ON recommendations
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY journal_service_role_all
ON journal
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

GRANT ALL ON recommendations TO service_role;
GRANT ALL ON journal TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
