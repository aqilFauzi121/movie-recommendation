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
-- KEAMANAN: Nonaktifkan RLS (aplikasi personal single-user)
-- ============================================================================
-- Untuk personal use, RLS di-disable agar anon key bisa akses langsung.
-- Jika menambahkan multi-user di masa depan, AKTIFKAN kembali RLS + buat policies.
ALTER TABLE recommendations DISABLE ROW LEVEL SECURITY;
ALTER TABLE journal DISABLE ROW LEVEL SECURITY;

-- Berikan akses penuh
GRANT ALL ON recommendations TO anon, authenticated;
GRANT ALL ON journal TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
