"""
db.py — Modul Database Supabase untuk One Day One Movie
=======================================================
Mengelola penyimpanan riwayat rekomendasi film dan jurnal tontonan
menggunakan Supabase (PostgreSQL) untuk persistensi data di cloud.

STATUS FILM:
  - 'recommended'  : Sedang ditampilkan hari ini, belum ditonton
  - 'watched'      : Sudah ditonton (BLACKLIST permanen)
  - 'rerolled'     : Di-reroll manual oleh user (BLACKLIST permanen)
  - 'skipped'      : Auto-skip karena lupa/tidak ditonton (BOLEH muncul lagi)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import streamlit as st
from supabase import create_client, Client

# ============================================================================
# ZONA WAKTU INDONESIA (WIB = UTC+7)
# ============================================================================
WIB = timezone(timedelta(hours=7))


def _today_wib() -> str:
    """Ambil tanggal hari ini dalam zona waktu WIB (Asia/Jakarta), format ISO."""
    return datetime.now(WIB).strftime("%Y-%m-%d")


def _now_wib() -> str:
    """Ambil datetime saat ini dalam zona waktu WIB, format ISO."""
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# KONEKSI SUPABASE
# ============================================================================
@st.cache_resource
def _get_client() -> Client:
    """
    Buat koneksi Supabase client (singleton, di-cache oleh Streamlit).
    Membaca URL dan Key dari st.secrets.
    """
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def init_db():
    """
    Inisialisasi koneksi database.
    Tabel dibuat via SQL Editor di dashboard Supabase (lihat supabase_schema.sql).
    Fungsi ini hanya memastikan koneksi siap.
    """
    _get_client()


# ============================================================================
# AUTO-SKIP: Film dari hari sebelumnya yang masih "recommended" → "skipped"
# ============================================================================
def auto_skip_stale_recommendations():
    """
    Dijalankan setiap kali app dimuat untuk hari baru.
    Mengubah status film dari tanggal sebelumnya yang masih 'recommended'
    menjadi 'skipped' secara otomatis.
    """
    today = _today_wib()
    client = _get_client()
    try:
        # Pertama cek apakah ada row yang perlu di-update
        stale = client.table("recommendations") \
            .select("id") \
            .eq("status", "recommended") \
            .lt("recommended_date", today) \
            .execute()

        if stale.data:
            for row in stale.data:
                client.table("recommendations") \
                    .update({"status": "skipped"}) \
                    .eq("id", row["id"]) \
                    .execute()
    except Exception:
        # Graceful fallback: jika tabel belum ada atau query gagal
        pass


def get_today_recommendation() -> Optional[dict]:
    """
    Cek apakah sudah ada rekomendasi untuk hari ini.
    Hanya mengembalikan film dengan status 'recommended' atau 'watched'.
    """
    today = _today_wib()
    client = _get_client()
    response = client.table("recommendations") \
        .select("*") \
        .eq("recommended_date", today) \
        .in_("status", ["recommended", "watched"]) \
        .order("id", desc=True) \
        .limit(1) \
        .execute()

    if response.data:
        return response.data[0]
    return None


def save_recommendation(movie_data: dict) -> int:
    """
    Simpan rekomendasi film baru ke database.
    Jika film ini pernah di-'skipped' sebelumnya, update record lama
    (mencegah duplikat movie_id).
    """
    today = _today_wib()
    now = _now_wib()
    client = _get_client()

    # Cek apakah film ini pernah di-skip sebelumnya
    existing = client.table("recommendations") \
        .select("id") \
        .eq("movie_id", movie_data["movie_id"]) \
        .eq("status", "skipped") \
        .limit(1) \
        .execute()

    if existing.data:
        # Re-rekomendasi film skipped: update row lama
        rec_id = existing.data[0]["id"]
        client.table("recommendations") \
            .update({
                "title": movie_data["title"],
                "poster_path": movie_data.get("poster_path", ""),
                "release_date": movie_data.get("release_date", ""),
                "genres": movie_data.get("genres", ""),
                "vote_average": movie_data.get("vote_average", 0),
                "overview": movie_data.get("overview", ""),
                "trailer_url": movie_data.get("trailer_url", ""),
                "providers_json": movie_data.get("providers_json", "{}"),
                "recommended_date": today,
                "status": "recommended",
            }) \
            .eq("id", rec_id) \
            .execute()
        return rec_id
    else:
        # Film baru: insert row baru
        response = client.table("recommendations") \
            .insert({
                "movie_id": movie_data["movie_id"],
                "title": movie_data["title"],
                "poster_path": movie_data.get("poster_path", ""),
                "release_date": movie_data.get("release_date", ""),
                "genres": movie_data.get("genres", ""),
                "vote_average": movie_data.get("vote_average", 0),
                "overview": movie_data.get("overview", ""),
                "trailer_url": movie_data.get("trailer_url", ""),
                "providers_json": movie_data.get("providers_json", "{}"),
                "recommended_date": today,
                "status": "recommended",
                "created_at": now,
            }) \
            .execute()
        if response.data:
            return response.data[0]["id"]
        return 0


def is_movie_blacklisted(movie_id: int) -> bool:
    """
    Cek apakah film masuk blacklist (tidak boleh direkomendasikan lagi).

    ATURAN BLACKLIST:
      - 'watched'  → BLACKLIST
      - 'rerolled' → BLACKLIST
      - 'skipped'  → TIDAK blacklist (boleh muncul lagi)
    """
    client = _get_client()
    response = client.table("recommendations") \
        .select("id") \
        .eq("movie_id", movie_id) \
        .in_("status", ["watched", "rerolled"]) \
        .limit(1) \
        .execute()
    return len(response.data) > 0


def mark_as_rerolled(rec_id: int):
    """Tandai rekomendasi sebagai 'rerolled' (blacklist permanen)."""
    client = _get_client()
    client.table("recommendations") \
        .update({"status": "rerolled"}) \
        .eq("id", rec_id) \
        .execute()


def mark_as_watched(rec_id: int):
    """Tandai rekomendasi sebagai 'watched'."""
    client = _get_client()
    client.table("recommendations") \
        .update({"status": "watched"}) \
        .eq("id", rec_id) \
        .execute()


def get_all_recommendations(status_filter: str = "all") -> list[dict]:
    """
    Ambil semua riwayat rekomendasi untuk halaman jurnal.

    Args:
        status_filter: 'all', 'watched', 'skipped', 'rerolled', atau 'recommended'
    """
    client = _get_client()
    query = client.table("recommendations").select("*")

    if status_filter != "all":
        query = query.eq("status", status_filter)

    response = query.order("recommended_date", desc=True) \
        .order("id", desc=True) \
        .execute()

    return response.data if response.data else []


def save_journal_entry(movie_id: int, rating: int, review: str):
    """
    Simpan atau update jurnal tontonan untuk sebuah film.
    Jika sudah ada entry untuk movie_id ini, update saja.
    """
    now = _now_wib()
    today = _today_wib()
    client = _get_client()

    existing = client.table("journal") \
        .select("id") \
        .eq("movie_id", movie_id) \
        .limit(1) \
        .execute()

    if existing.data:
        client.table("journal") \
            .update({
                "rating": rating,
                "review": review,
                "updated_at": now,
            }) \
            .eq("movie_id", movie_id) \
            .execute()
    else:
        client.table("journal") \
            .insert({
                "movie_id": movie_id,
                "rating": rating,
                "review": review,
                "watched_date": today,
                "created_at": now,
                "updated_at": now,
            }) \
            .execute()


def get_journal_entry(movie_id: int) -> Optional[dict]:
    """Ambil jurnal entry untuk sebuah film, jika ada."""
    client = _get_client()
    response = client.table("journal") \
        .select("*") \
        .eq("movie_id", movie_id) \
        .limit(1) \
        .execute()

    if response.data:
        return response.data[0]
    return None


def get_stats() -> dict:
    """Ambil statistik ringkasan untuk dashboard jurnal."""
    client = _get_client()

    total_resp = client.table("recommendations").select("id", count="exact").execute()
    watched_resp = client.table("recommendations").select("id", count="exact").eq("status", "watched").execute()
    skipped_resp = client.table("recommendations").select("id", count="exact").eq("status", "skipped").execute()
    rerolled_resp = client.table("recommendations").select("id", count="exact").eq("status", "rerolled").execute()
    reviewed_resp = client.table("journal").select("id", count="exact").execute()
    avg_resp = client.table("journal").select("rating").execute()

    # Hitung rata-rata rating manual
    avg_rating = 0
    if avg_resp.data:
        ratings = [r["rating"] for r in avg_resp.data]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "total": total_resp.count or 0,
        "watched": watched_resp.count or 0,
        "skipped": skipped_resp.count or 0,
        "rerolled": rerolled_resp.count or 0,
        "reviewed": reviewed_resp.count or 0,
        "avg_rating": avg_rating,
    }
