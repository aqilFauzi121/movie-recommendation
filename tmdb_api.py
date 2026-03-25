"""
tmdb_api.py — Wrapper TMDB API untuk One Day One Movie
======================================================
Mengambil data film dari The Movie Database (TMDB) API v3.
Termasuk filter kualitas, anti-duplikasi, trailer YouTube, dan info streaming.
"""

from __future__ import annotations

import json
import os
import random
from typing import Optional

import requests
import streamlit as st
from dotenv import load_dotenv

import db

# ============================================================================
# KONFIGURASI CACHING
# ============================================================================
# Streamlit me-rerun seluruh skrip setiap ada interaksi UI.
# @st.cache_data mencegah pemanggilan API berulang untuk data yang sama.
# TTL (Time to Live) mengatur berapa lama cache valid sebelum di-refresh.
_TTL_SHORT = 3600       # 1 jam — untuk request API umum
_TTL_MEDIUM = 43200     # 12 jam — untuk data yang jarang berubah (genre list, total pages)
_TTL_LONG = 86400       # 24 jam — untuk data statis (trailer, watch providers)

# ============================================================================
# LOAD API KEY
# ============================================================================
# Prioritas: st.secrets (Streamlit Cloud) > .env (lokal)
# Di Streamlit Cloud, key dimasukkan via Secrets Management.
# Di lokal, key bisa dari .streamlit/secrets.toml ATAU .env file.
load_dotenv()

def _get_api_key() -> str:
    """Ambil TMDB API Key dari st.secrets (Cloud) atau .env (lokal)."""
    try:
        return st.secrets["TMDB_API_KEY"]
    except (KeyError, FileNotFoundError):
        key = os.getenv("TMDB_API_KEY", "")
        return key if key else ""

TMDB_API_KEY = _get_api_key()

# ============================================================================
# KONFIGURASI FILTER KUALITAS
# ============================================================================
# Nilai minimum rating (vote_average) agar film dianggap berkualitas.
MIN_RATING = 6.0

# Jumlah minimum vote agar rating film dianggap reliabel/populer.
# 10000 vote memastikan film sudah cukup banyak ditonton secara global.
MIN_VOTE_COUNT = 10000

# Genre ID Horror di TMDB = 27.
# Film horror di-exclude secara permanen dari hasil pencarian.
EXCLUDED_GENRE_IDS = "27"

# Base URL TMDB API v3
BASE_URL = "https://api.themoviedb.org/3"

# Base URL untuk gambar poster TMDB (ukuran w500)
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Maksimum percobaan untuk mencari film yang belum pernah direkomendasikan
MAX_RETRY = 20


@st.cache_data(ttl=_TTL_SHORT, show_spinner=False)
def _make_request(endpoint: str, _params_json: str = "{}") -> Optional[dict]:
    """Cached version — params diterima sebagai JSON string agar hashable oleh Streamlit."""
    params: Optional[dict] = json.loads(_params_json) if _params_json != "{}" else None

    if not TMDB_API_KEY:
        raise ValueError(
            "TMDB_API_KEY belum diset! "
            "Buat file .env dan isi: TMDB_API_KEY=your_key_here"
        )
    
    url = f"{BASE_URL}{endpoint}"
    default_params = {"api_key": TMDB_API_KEY}
    if params:
        default_params.update(params)
    
    try:
        response = requests.get(url, params=default_params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ConnectionError("Request ke TMDB API timeout. Cek koneksi internet Anda.")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError("API Key TMDB tidak valid! Cek kembali TMDB_API_KEY Anda.")
        raise ConnectionError(f"TMDB API error: {e}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Gagal menghubungi TMDB API: {e}")


@st.cache_data(ttl=_TTL_MEDIUM, show_spinner=False)
def get_total_pages() -> int:
    """
    Ambil total halaman yang tersedia dari TMDB Discover API dengan filter kualitas.
    
    Filter yang digunakan:
    - vote_average >= MIN_RATING (6.0): hanya film dengan rating baik
    - vote_count >= MIN_VOTE_COUNT (10000): hanya film yang sudah banyak di-vote
    - without_genres = 27: excludes Horror
    
    TMDB membatasi akses hingga halaman 500, jadi kita cap di angka itu.
    """
    data = _make_request("/discover/movie", json.dumps({
        "vote_average.gte": MIN_RATING,
        "vote_count.gte": MIN_VOTE_COUNT,
        "without_genres": EXCLUDED_GENRE_IDS,
        "sort_by": "popularity.desc",
        "page": 1,
    }))
    
    if not data:
        return 1
    
    # TMDB API membatasi akses hingga halaman 500
    total = data.get("total_pages", 1)
    return min(total, 500)


@st.cache_data(ttl=_TTL_LONG, show_spinner=False)
def get_movie_trailer(movie_id: int) -> Optional[str]:
    """
    Ambil URL trailer YouTube untuk sebuah film.
    
    Mencari video bertipe 'Trailer' dari sumber 'YouTube'.
    Jika tidak ada trailer, coba ambil video tipe 'Teaser'.
    
    Returns:
        URL YouTube lengkap, atau None jika tidak ditemukan.
    """
    data = _make_request(f"/movie/{movie_id}/videos", json.dumps({"language": "en-US"}))
    if not data:
        return None
    
    videos = data.get("results", [])
    
    # Prioritas: Official Trailer > Trailer > Teaser
    for video_type in ["Trailer", "Teaser"]:
        for video in videos:
            if video.get("type") == video_type and video.get("site") == "YouTube":
                return f"https://www.youtube.com/watch?v={video['key']}"
    
    return None


@st.cache_data(ttl=_TTL_LONG, show_spinner=False)
def get_watch_providers(movie_id: int) -> dict:
    """
    Ambil informasi 'Where to Watch' menggunakan data JustWatch via TMDB API.
    
    Fokus pada region ID (Indonesia).
    
    Returns:
        Dict dengan keys 'flatrate' (langganan), 'rent' (sewa), 'buy' (beli).
        Setiap value adalah list of dict: {name, logo_path}.
        Mengembalikan dict kosong jika tidak tersedia di Indonesia.
    """
    data = _make_request(f"/movie/{movie_id}/watch/providers")
    if not data:
        return {}
    
    results = data.get("results", {})
    
    # Ambil data untuk Indonesia (region code: ID)
    id_data = results.get("ID", {})
    
    if not id_data:
        return {}
    
    providers = {}
    for category in ["flatrate", "rent", "buy"]:
        if category in id_data:
            providers[category] = [
                {
                    "name": p.get("provider_name", "Unknown"),
                    "logo_path": f"{POSTER_BASE_URL}{p['logo_path']}" if p.get("logo_path") else None,
                }
                for p in id_data[category]
            ]
    
    return providers


def _get_genre_names(genre_ids: list[int], genre_map: dict) -> str:
    """Konversi list genre ID menjadi string nama genre yang dipisah koma."""
    names = [genre_map.get(gid, "") for gid in genre_ids]
    return ", ".join(n for n in names if n)


def get_random_recommendation() -> dict:
    """
    Engine utama: ambil satu rekomendasi film acak yang belum pernah direkomendasikan.
    
    Alur:
    1. Ambil daftar genre dari TMDB untuk mapping ID → nama
    2. Hitung total halaman yang tersedia (dengan filter kualitas)
    3. Pilih halaman acak → pilih film acak dari halaman itu
    4. Cek anti-duplikasi via db.is_movie_seen()
    5. Jika sudah pernah, ulangi (maks MAX_RETRY kali)
    6. Ambil trailer dan info streaming
    7. Return dict lengkap siap ditampilkan
    
    Returns:
        Dict berisi: movie_id, title, poster_path, release_date, genres,
                     vote_average, overview, trailer_url, providers_json
    
    Raises:
        RuntimeError: Jika gagal menemukan film unik setelah MAX_RETRY percobaan.
    """
    # Step 1: Ambil mapping genre ID → nama genre
    genre_data = _make_request("/genre/movie/list", json.dumps({"language": "id-ID"}))
    genre_map = {}
    if genre_data:
        genre_map = {g["id"]: g["name"] for g in genre_data.get("genres", [])}
    
    # Step 2: Hitung total halaman
    total_pages = get_total_pages()
    
    # Step 3-5: Cari film unik (belum pernah direkomendasikan)
    for attempt in range(MAX_RETRY):
        # Pilih halaman acak
        random_page = random.randint(1, total_pages)
        
        # Request ke Discover API dengan filter kualitas
        data = _make_request("/discover/movie", json.dumps({
            "vote_average.gte": MIN_RATING,
            "vote_count.gte": MIN_VOTE_COUNT,
            "without_genres": EXCLUDED_GENRE_IDS,
            "sort_by": "popularity.desc",
            "page": random_page,
            "language": "id-ID",
        }))
        
        if not data or not data.get("results"):
            continue
        
        movies = data["results"]
        random.shuffle(movies)
        
        for movie in movies:
            movie_id = movie["id"]
            
            # Anti-duplikasi: skip jika sudah pernah direkomendasikan
            if db.is_movie_seen(movie_id):
                continue
            
            # Step 6: Ambil data tambahan (trailer & streaming)
            trailer_url = get_movie_trailer(movie_id) or ""
            providers = get_watch_providers(movie_id)
            
            # Step 7: Susun dict hasil
            return {
                "movie_id": movie_id,
                "title": movie.get("title", "Unknown"),
                "poster_path": (
                    f"{POSTER_BASE_URL}{movie['poster_path']}" 
                    if movie.get("poster_path") else ""
                ),
                "release_date": movie.get("release_date", ""),
                "genres": _get_genre_names(movie.get("genre_ids", []), genre_map),
                "vote_average": movie.get("vote_average", 0),
                "overview": movie.get("overview", "Sinopsis tidak tersedia."),
                "trailer_url": trailer_url,
                "providers_json": json.dumps(providers),
            }
    
    raise RuntimeError(
        f"Gagal menemukan film unik setelah {MAX_RETRY} percobaan. "
        "Kemungkinan semua film populer sudah pernah direkomendasikan!"
    )
