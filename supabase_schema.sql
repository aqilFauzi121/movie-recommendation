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
-- Row Level Security (RLS) — PENTING!
-- ============================================================================
-- Untuk aplikasi sederhana (single-user), kita DISABLE RLS
-- agar Supabase anon key bisa mengakses data tanpa autentikasi.
-- Jika Anda menambahkan multi-user di masa depan, aktifkan kembali RLS.
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal ENABLE ROW LEVEL SECURITY;

-- Policy: izinkan semua operasi untuk anon key
CREATE POLICY "Allow all for anon" ON recommendations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON journal FOR ALL USING (true) WITH CHECK (true);
