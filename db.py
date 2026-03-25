"""
db.py — Modul Database SQLite untuk One Day One Movie
=====================================================
Mengelola penyimpanan riwayat rekomendasi film dan jurnal tontonan.
Menggunakan SQLite untuk efisiensi dan portabilitas (single-file database).

STATUS FILM:
  - 'recommended'  : Sedang ditampilkan hari ini, belum ditonton
  - 'watched'      : Sudah ditonton (BLACKLIST permanen)
  - 'rerolled'     : Di-reroll manual oleh user (BLACKLIST permanen)
  - 'skipped'      : Auto-skip karena lupa/tidak ditonton (BOLEH muncul lagi)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

# ============================================================================
# ZONA WAKTU INDONESIA (WIB = UTC+7)
# ============================================================================
# Semua pengambilan waktu harus melalui fungsi ini agar konsisten,
# baik di server lokal maupun di Streamlit Cloud (yang menggunakan UTC).
WIB = timezone(timedelta(hours=7))


def _today_wib() -> str:
    """Ambil tanggal hari ini dalam zona waktu WIB (Asia/Jakarta), format ISO."""
    return datetime.now(WIB).strftime("%Y-%m-%d")


def _now_wib() -> str:
    """Ambil datetime saat ini dalam zona waktu WIB, format ISO."""
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")


# Path database: disimpan di direktori yang sama dengan skrip
DB_PATH = Path(__file__).parent / "movie_history.db"


def _get_connection() -> sqlite3.Connection:
    """Buat koneksi SQLite dengan row_factory agar hasil query bisa diakses via nama kolom."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """
    Inisialisasi tabel database jika belum ada.

    Tabel 'recommendations':
        Menyimpan setiap film yang pernah direkomendasikan oleh sistem.
        Status: 'recommended', 'watched', 'rerolled', atau 'skipped'.

    Tabel 'journal':
        Menyimpan ulasan personal (rating & review) untuk film yang sudah ditonton.
    """
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id        INTEGER NOT NULL,
                title           TEXT NOT NULL,
                poster_path     TEXT,
                release_date    TEXT,
                genres          TEXT,
                vote_average    REAL,
                overview        TEXT,
                trailer_url     TEXT,
                providers_json  TEXT,
                recommended_date TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'recommended',
                created_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id    INTEGER NOT NULL,
                rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                review      TEXT,
                watched_date TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_rec_movie_id ON recommendations(movie_id);
            CREATE INDEX IF NOT EXISTS idx_rec_date ON recommendations(recommended_date);
            CREATE INDEX IF NOT EXISTS idx_journal_movie_id ON journal(movie_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# AUTO-SKIP: Film dari hari sebelumnya yang masih "recommended" → "skipped"
# ============================================================================
def auto_skip_stale_recommendations():
    """
    Dijalankan setiap kali app dimuat untuk hari baru.
    Mengubah status film dari tanggal sebelumnya yang masih 'recommended'
    menjadi 'skipped' secara otomatis.

    Logika: Jika user lupa menekan tombol dan hari berganti,
    film tersebut dianggap "dilewati" (skipped) bukan "rerolled".
    Film 'skipped' BOLEH direkomendasikan lagi di masa depan.
    """
    today = _today_wib()
    conn = _get_connection()
    try:
        conn.execute(
            """UPDATE recommendations
               SET status = 'skipped'
               WHERE status = 'recommended' AND recommended_date < ?""",
            (today,)
        )
        conn.commit()
    finally:
        conn.close()


def get_today_recommendation() -> Optional[dict]:
    """
    Cek apakah sudah ada rekomendasi untuk hari ini.
    Mengembalikan data film jika ada, None jika belum ada.
    Hanya mengembalikan film dengan status 'recommended' atau 'watched'
    (bukan 'skipped' atau 'rerolled').
    """
    today = _today_wib()
    conn = _get_connection()
    result: Optional[dict] = None
    try:
        row = conn.execute(
            """SELECT * FROM recommendations
               WHERE recommended_date = ? AND status IN ('recommended', 'watched')
               ORDER BY id DESC LIMIT 1""",
            (today,)
        ).fetchone()
        result = dict(row) if row else None
    finally:
        conn.close()
    return result


def save_recommendation(movie_data: dict) -> int:
    """
    Simpan rekomendasi film baru ke database.
    Jika film ini pernah di-'skipped' sebelumnya, update record lama
    menjadi 'recommended' dengan tanggal hari ini (mencegah duplikat movie_id).

    Returns:
        ID row yang diinsert/diupdate.
    """
    today = _today_wib()
    now = _now_wib()
    conn = _get_connection()
    row_id = 0
    try:
        # Cek apakah film ini pernah di-skip sebelumnya
        existing = conn.execute(
            "SELECT id FROM recommendations WHERE movie_id = ? AND status = 'skipped' LIMIT 1",
            (movie_data["movie_id"],)
        ).fetchone()

        if existing:
            # Re-rekomendasi film skipped: update row lama
            conn.execute(
                """UPDATE recommendations
                   SET title = ?, poster_path = ?, release_date = ?, genres = ?,
                       vote_average = ?, overview = ?, trailer_url = ?,
                       providers_json = ?, recommended_date = ?, status = 'recommended'
                   WHERE id = ?""",
                (
                    movie_data["title"],
                    movie_data.get("poster_path", ""),
                    movie_data.get("release_date", ""),
                    movie_data.get("genres", ""),
                    movie_data.get("vote_average", 0),
                    movie_data.get("overview", ""),
                    movie_data.get("trailer_url", ""),
                    movie_data.get("providers_json", "{}"),
                    today,
                    existing["id"],
                )
            )
            row_id = existing["id"]
        else:
            # Film baru: insert row baru
            cursor = conn.execute(
                """INSERT INTO recommendations
                   (movie_id, title, poster_path, release_date, genres,
                    vote_average, overview, trailer_url, providers_json,
                    recommended_date, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recommended', ?)""",
                (
                    movie_data["movie_id"],
                    movie_data["title"],
                    movie_data.get("poster_path", ""),
                    movie_data.get("release_date", ""),
                    movie_data.get("genres", ""),
                    movie_data.get("vote_average", 0),
                    movie_data.get("overview", ""),
                    movie_data.get("trailer_url", ""),
                    movie_data.get("providers_json", "{}"),
                    today,
                    now,
                )
            )
            row_id = cursor.lastrowid or 0
        conn.commit()
    finally:
        conn.close()
    return row_id


def is_movie_blacklisted(movie_id: int) -> bool:
    """
    Cek apakah film masuk blacklist (tidak boleh direkomendasikan lagi).

    ATURAN BLACKLIST:
      - 'watched'  → BLACKLIST (sudah ditonton, tidak perlu lagi)
      - 'rerolled' → BLACKLIST (user sengaja tolak, jangan tampilkan lagi)
      - 'skipped'  → TIDAK blacklist (boleh muncul lagi di masa depan)
      - 'recommended' → TIDAK blacklist (sedang aktif hari ini)
    """
    conn = _get_connection()
    blacklisted = False
    try:
        row = conn.execute(
            "SELECT 1 FROM recommendations WHERE movie_id = ? AND status IN ('watched', 'rerolled') LIMIT 1",
            (movie_id,)
        ).fetchone()
        blacklisted = row is not None
    finally:
        conn.close()
    return blacklisted


def mark_as_rerolled(rec_id: int):
    """Tandai rekomendasi sebagai 'rerolled' (user sengaja tolak via tombol Reroll)."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE recommendations SET status = 'rerolled' WHERE id = ?",
            (rec_id,)
        )
        conn.commit()
    finally:
        conn.close()


def mark_as_watched(rec_id: int):
    """Tandai rekomendasi sebagai 'watched' (sudah ditonton oleh user)."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE recommendations SET status = 'watched' WHERE id = ?",
            (rec_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_recommendations(status_filter: str = "all") -> list[dict]:
    """
    Ambil semua riwayat rekomendasi untuk halaman jurnal.

    Args:
        status_filter: 'all', 'watched', 'skipped', 'rerolled', atau 'recommended'
    """
    conn = _get_connection()
    result: list[dict] = []
    try:
        if status_filter == "all":
            rows = conn.execute(
                "SELECT * FROM recommendations ORDER BY recommended_date DESC, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM recommendations WHERE status = ? ORDER BY recommended_date DESC, id DESC",
                (status_filter,)
            ).fetchall()
        result = [dict(r) for r in rows]
    finally:
        conn.close()
    return result


def save_journal_entry(movie_id: int, rating: int, review: str):
    """
    Simpan atau update jurnal tontonan untuk sebuah film.
    Jika sudah ada entry untuk movie_id ini, update saja.
    Menggunakan WIB untuk timestamp.
    """
    now = _now_wib()
    today = _today_wib()
    conn = _get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM journal WHERE movie_id = ? LIMIT 1",
            (movie_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE journal
                   SET rating = ?, review = ?, updated_at = ?
                   WHERE movie_id = ?""",
                (rating, review, now, movie_id)
            )
        else:
            conn.execute(
                """INSERT INTO journal (movie_id, rating, review, watched_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (movie_id, rating, review, today, now, now)
            )
        conn.commit()
    finally:
        conn.close()


def get_journal_entry(movie_id: int) -> Optional[dict]:
    """Ambil jurnal entry untuk sebuah film, jika ada."""
    conn = _get_connection()
    result: Optional[dict] = None
    try:
        row = conn.execute(
            "SELECT * FROM journal WHERE movie_id = ? LIMIT 1",
            (movie_id,)
        ).fetchone()
        result = dict(row) if row else None
    finally:
        conn.close()
    return result


def get_stats() -> dict:
    """Ambil statistik ringkasan untuk dashboard jurnal."""
    conn = _get_connection()
    stats: dict = {"total": 0, "watched": 0, "skipped": 0, "rerolled": 0, "reviewed": 0, "avg_rating": 0}
    try:
        total = conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
        watched = conn.execute(
            "SELECT COUNT(*) FROM recommendations WHERE status = 'watched'"
        ).fetchone()[0]
        skipped = conn.execute(
            "SELECT COUNT(*) FROM recommendations WHERE status = 'skipped'"
        ).fetchone()[0]
        rerolled = conn.execute(
            "SELECT COUNT(*) FROM recommendations WHERE status = 'rerolled'"
        ).fetchone()[0]
        reviewed = conn.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
        avg_rating = conn.execute(
            "SELECT AVG(rating) FROM journal"
        ).fetchone()[0]

        stats = {
            "total": total,
            "watched": watched,
            "skipped": skipped,
            "rerolled": rerolled,
            "reviewed": reviewed,
            "avg_rating": round(avg_rating, 1) if avg_rating else 0,
        }
    finally:
        conn.close()
    return stats
