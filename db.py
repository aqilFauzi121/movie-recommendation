"""
db.py — Modul Database SQLite untuk One Day One Movie
=====================================================
Mengelola penyimpanan riwayat rekomendasi film dan jurnal tontonan.
Menggunakan SQLite untuk efisiensi dan portabilitas (single-file database).
"""

from __future__ import annotations

import sqlite3
import json
from datetime import date, datetime
from typing import Optional
from pathlib import Path

# Path database: disimpan di direktori yang sama dengan skrip
DB_PATH = Path(__file__).parent / "movie_history.db"


def _get_connection() -> sqlite3.Connection:
    """Buat koneksi SQLite dengan row_factory agar hasil query bisa diakses via nama kolom."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging untuk performa lebih baik
    return conn


def init_db():
    """
    Inisialisasi tabel database jika belum ada.
    
    Tabel 'recommendations':
        Menyimpan setiap film yang pernah direkomendasikan oleh sistem.
        Status bisa: 'recommended', 'watched', atau 'skipped'.
    
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
                created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS journal (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id    INTEGER NOT NULL,
                rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                review      TEXT,
                watched_date TEXT NOT NULL DEFAULT (date('now', 'localtime')),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_rec_movie_id ON recommendations(movie_id);
            CREATE INDEX IF NOT EXISTS idx_rec_date ON recommendations(recommended_date);
            CREATE INDEX IF NOT EXISTS idx_journal_movie_id ON journal(movie_id);
        """)
        conn.commit()
    finally:
        conn.close()


def get_today_recommendation() -> Optional[dict]:
    """
    Cek apakah sudah ada rekomendasi untuk hari ini.
    Mengembalikan data film jika ada, None jika belum ada.
    Hanya mengembalikan film dengan status 'recommended' atau 'watched' (bukan 'skipped').
    """
    today = date.today().isoformat()
    conn = _get_connection()
    result: Optional[dict] = None
    try:
        row = conn.execute(
            """SELECT * FROM recommendations 
               WHERE recommended_date = ? AND status != 'skipped'
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
    
    Args:
        movie_data: Dict berisi data film dari TMDB API.
                    Keys: movie_id, title, poster_path, release_date, genres,
                          vote_average, overview, trailer_url, providers_json
    
    Returns:
        ID row yang baru diinsert.
    """
    today = date.today().isoformat()
    conn = _get_connection()
    row_id = 0
    try:
        cursor = conn.execute(
            """INSERT INTO recommendations 
               (movie_id, title, poster_path, release_date, genres, 
                vote_average, overview, trailer_url, providers_json, 
                recommended_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recommended')""",
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
            )
        )
        conn.commit()
        row_id = cursor.lastrowid or 0
    finally:
        conn.close()
    return row_id


def is_movie_seen(movie_id: int) -> bool:
    """
    Anti-duplikasi: cek apakah film dengan movie_id sudah pernah masuk ke database.
    Mengembalikan True jika film sudah pernah direkomendasikan/ditonton/diskip sebelumnya.
    """
    conn = _get_connection()
    seen = False
    try:
        row = conn.execute(
            "SELECT 1 FROM recommendations WHERE movie_id = ? LIMIT 1",
            (movie_id,)
        ).fetchone()
        seen = row is not None
    finally:
        conn.close()
    return seen


def mark_as_skipped(rec_id: int):
    """Tandai rekomendasi sebagai 'skipped' (di-reroll oleh user)."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE recommendations SET status = 'skipped' WHERE id = ?",
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
        status_filter: 'all', 'watched', 'skipped', atau 'recommended'
    
    Returns:
        List of dict berisi data setiap film.
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
    """
    conn = _get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM journal WHERE movie_id = ? LIMIT 1",
            (movie_id,)
        ).fetchone()
        
        if existing:
            conn.execute(
                """UPDATE journal 
                   SET rating = ?, review = ?, updated_at = datetime('now', 'localtime')
                   WHERE movie_id = ?""",
                (rating, review, movie_id)
            )
        else:
            conn.execute(
                """INSERT INTO journal (movie_id, rating, review)
                   VALUES (?, ?, ?)""",
                (movie_id, rating, review)
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
    stats: dict = {"total": 0, "watched": 0, "skipped": 0, "reviewed": 0, "avg_rating": 0}
    try:
        total = conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
        watched = conn.execute(
            "SELECT COUNT(*) FROM recommendations WHERE status = 'watched'"
        ).fetchone()[0]
        skipped = conn.execute(
            "SELECT COUNT(*) FROM recommendations WHERE status = 'skipped'"
        ).fetchone()[0]
        reviewed = conn.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
        avg_rating = conn.execute(
            "SELECT AVG(rating) FROM journal"
        ).fetchone()[0]
        
        stats = {
            "total": total,
            "watched": watched,
            "skipped": skipped,
            "reviewed": reviewed,
            "avg_rating": round(avg_rating, 1) if avg_rating else 0,
        }
    finally:
        conn.close()
    return stats
