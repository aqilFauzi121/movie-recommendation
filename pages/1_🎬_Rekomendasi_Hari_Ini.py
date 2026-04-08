"""
1_🎬_Rekomendasi_Hari_Ini.py — Halaman Rekomendasi Film Harian
====================================================
Menampilkan rekomendasi film harian dengan poster, detail, 
trailer, dan info streaming.
"""

import json
import html
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse
import streamlit as st
import db
import tmdb_api

# Zona waktu WIB (UTC+7)
_WIB = timezone(timedelta(hours=7))

# ============================================================================
# KONFIGURASI HALAMAN
# ============================================================================
st.set_page_config(
    page_title="Rekomendasi Hari Ini — One Day One Movie",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inisialisasi database
db.init_db()

# Auto-skip: film dari hari sebelumnya yang masih 'recommended' → 'skipped'
db.auto_skip_stale_recommendations()

# ============================================================================
# ATRIBUSI TMDB (Wajib sesuai Terms of Use)
# ============================================================================
with st.sidebar:
    st.image(
        "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg",
        width=180,
    )
    st.caption(
        "This product uses the TMDB API but is not endorsed or certified by TMDB."
    )
    st.caption(
        "Streaming data provided by [JustWatch](https://www.justwatch.com)."
    )
    st.markdown("---")

    # Countdown timer — sisa waktu sebelum reset tengah malam WIB
    now_wib = datetime.now(_WIB)
    midnight_wib = now_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    remaining = midnight_wib - now_wib
    hours_left = int(remaining.total_seconds() // 3600)
    mins_left = int((remaining.total_seconds() % 3600) // 60)
    st.info(f"⏰ Sisa waktu hari ini: **{hours_left} jam {mins_left} menit**")
    st.markdown("---")

# ============================================================================
# CUSTOM CSS
# ============================================================================
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    /* Hero header */
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #E50914 0%, #FF6B6B 50%, #FFA07A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        text-align: center;
        color: #8899AA;
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    
    /* Movie card */
    .movie-card {
        background: linear-gradient(145deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid rgba(229, 9, 20, 0.15);
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .movie-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FAFAFA;
        margin-bottom: 0.3rem;
    }
    .movie-year {
        font-size: 1.1rem;
        color: #8899AA;
        font-weight: 400;
    }
    .movie-rating {
        font-size: 1.4rem;
        font-weight: 700;
        color: #FFD700;
    }
    .genre-badge {
        display: inline-block;
        background: rgba(229, 9, 20, 0.15);
        color: #FF6B6B;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .overview-text {
        color: #C0C0C0;
        font-size: 0.95rem;
        line-height: 1.7;
        margin-top: 1rem;
    }
    .section-label {
        color: #8899AA;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 0.5rem;
    }
    
    /* Provider logo styling */
    .provider-logo {
        width: 48px;
        height: 48px;
        border-radius: 10px;
        margin-right: 8px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    /* Stats cards */
    .stat-card {
        background: linear-gradient(145deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid rgba(229, 9, 20, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 800;
        color: #E50914;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #8899AA;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Poster styling */
    .poster-container img {
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(229, 9, 20, 0.3);
    }
    
    /* Divider */
    .custom-divider {
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(229,9,20,0.3), transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================
st.markdown('<h1 class="hero-title">🎬 Rekomendasi Hari Ini</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Satu film berkualitas untuk menemanimu hari ini.</p>', unsafe_allow_html=True)

# ============================================================================
# STATISTIK RINGKAS
# ============================================================================
stats = db.get_stats()
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{stats['total']}</div>
        <div class="stat-label">Total Rekomendasi</div>
    </div>
    """, unsafe_allow_html=True)
with col_s2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{stats['watched']}</div>
        <div class="stat-label">Sudah Ditonton</div>
    </div>
    """, unsafe_allow_html=True)
with col_s3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number">{'⭐ ' + str(stats['avg_rating']) if stats['avg_rating'] else '—'}</div>
        <div class="stat-label">Rata-rata Rating</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ============================================================================
# FUNGSI HELPER
# ============================================================================
def _render_providers(providers_json_str: str) -> None:
    """Render informasi streaming provider dari JSON string."""
    providers: dict[str, Any] = {}
    try:
        loaded: Any = json.loads(providers_json_str) if isinstance(providers_json_str, str) else providers_json_str
        if isinstance(loaded, dict):
            providers = loaded
    except (json.JSONDecodeError, TypeError):
        providers = {}

    has_any: bool = False
    categories: list[tuple[str, str]] = [("flatrate", "🟢 Streaming"), ("rent", "🔵 Sewa"), ("buy", "🟡 Beli")]
    for category, label in categories:
        try:
            provider_list: Any = providers[category]  # type: ignore[index]
        except (KeyError, TypeError):
            continue
        has_any = True
        names: list[str] = [str(p.get("name", "")) for p in provider_list]
        logo_parts: list[str] = []
        for p in provider_list:
            logo: Any = p.get("logo_path")
            name: str = str(p.get("name", ""))
            safe_name = html.escape(name, quote=True)
            if isinstance(logo, str) and logo.startswith("https://"):
                safe_logo = html.escape(logo, quote=True)
                logo_parts.append(
                    f'<img class="provider-logo" src="{safe_logo}" title="{safe_name}" alt="{safe_name}">'
                )
        st.markdown(f"**{label}:**", unsafe_allow_html=True)
        logos_html: str = "".join(logo_parts)
        if logos_html:
            st.markdown(logos_html, unsafe_allow_html=True)
        else:
            st.caption(", ".join(names))

    if not has_any:
        st.caption("Belum tersedia di platform streaming Indonesia.")

    # Atribusi JustWatch (wajib sesuai ketentuan TMDB)
    st.caption("Data streaming oleh JustWatch")


def _is_safe_https_url(url: Any) -> bool:
    """Validasi URL agar hanya https dengan host valid yang boleh dirender."""
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


# ============================================================================
# FUNGSI DISPLAY FILM
# ============================================================================
def display_movie(movie: dict):
    """Render tampilan detail film dengan layout 2 kolom (poster + info)."""
    
    col_poster, col_info = st.columns([1, 2], gap="large")
    
    with col_poster:
        poster_path = movie.get("poster_path")
        if _is_safe_https_url(poster_path):
            st.image(str(poster_path), use_container_width=True)
        else:
            st.markdown("🎬 *Poster tidak tersedia*")
    
    with col_info:
        # Judul & Tahun
        year = movie.get("release_date", "")[:4] if movie.get("release_date") else "N/A"
        safe_title = html.escape(str(movie.get("title", "Unknown")), quote=True)
        safe_year = html.escape(str(year), quote=True)
        rating = float(movie.get("vote_average", 0) or 0)
        st.markdown(f'<div class="movie-title">{safe_title}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="movie-year">📅 {safe_year}</span> &nbsp;&nbsp; <span class="movie-rating">⭐ {rating:.1f}</span>',
            unsafe_allow_html=True,
        )
        
        # Genre badges
        genres = movie.get("genres", "")
        if genres:
            genre_html = "".join(
                f'<span class="genre-badge">{html.escape(g.strip(), quote=True)}</span>'
                for g in str(genres).split(",")
            )
            st.markdown(genre_html, unsafe_allow_html=True)
        
        # Sinopsis
        st.markdown(f'<p class="section-label">Sinopsis</p>', unsafe_allow_html=True)
        safe_overview = html.escape(str(movie.get("overview", "Tidak tersedia.")), quote=True)
        st.markdown(f'<p class="overview-text">{safe_overview}</p>', unsafe_allow_html=True)
    
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    
    # Trailer & Streaming info — full width
    col_t, col_w = st.columns(2)
    
    with col_t:
        st.markdown('<p class="section-label">🎥 Trailer</p>', unsafe_allow_html=True)
        trailer_url = movie.get("trailer_url", "")
        if _is_safe_https_url(trailer_url):
            st.link_button("▶️ Tonton Trailer di YouTube", str(trailer_url), type="primary")
        else:
            st.caption("Trailer tidak tersedia.")
    
    with col_w:
        st.markdown('<p class="section-label">📺 Tersedia di (Indonesia)</p>', unsafe_allow_html=True)
        providers_json_str: str = movie.get("providers_json", "{}")
        _render_providers(providers_json_str)


# ============================================================================
# LOGIKA UTAMA: REKOMENDASI HARI INI
# ============================================================================

# Cek apakah sudah ada rekomendasi hari ini di database
today_rec = db.get_today_recommendation()

if today_rec:
    st.success("🎯 Rekomendasi hari ini sudah tersedia!")
    display_movie(today_rec)
    
    # Tombol aksi
    col_a1, col_a2, col_a3 = st.columns([1, 1, 2])
    with col_a1:
        if st.button("🔄 Reroll", help="Ganti dengan film lain", use_container_width=True):
            try:
                # Tandai film saat ini sebagai 'rerolled' (blacklist permanen)
                db.mark_as_rerolled(today_rec["id"])
                
                # Cari film baru
                with st.spinner("Mencari film pengganti..."):
                    new_movie = tmdb_api.get_random_recommendation()
                    db.save_recommendation(new_movie)
                
                st.rerun()
            except Exception as e:
                st.error(f"Gagal reroll: {e}")
    
    with col_a2:
        if today_rec["status"] != "watched":
            if st.button("✅ Sudah Ditonton", use_container_width=True, type="primary"):
                db.mark_as_watched(today_rec["id"])
                st.rerun()
        else:
            st.markdown("✅ **Sudah ditonton!**")
else:
    # Belum ada rekomendasi hari ini
    st.markdown("---")
    
    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        st.markdown(
            """
            <div style="text-align: center; padding: 3rem 1rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">🍿</div>
                <h3 style="color: #FAFAFA; font-weight: 600;">Siap untuk film hari ini?</h3>
                <p style="color: #8899AA;">Tekan tombol di bawah untuk mendapatkan rekomendasi film berkualitas.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if st.button("🎲 Dapatkan Rekomendasi Hari Ini", use_container_width=True, type="primary"):
            try:
                with st.spinner("🔍 Mencari film terbaik untuk Anda..."):
                    movie = tmdb_api.get_random_recommendation()
                    db.save_recommendation(movie)
                st.rerun()
            except ValueError as e:
                st.error(f"⚠️ Konfigurasi Error: {e}")
            except ConnectionError as e:
                st.error(f"🌐 Koneksi Error: {e}")
            except RuntimeError as e:
                st.warning(f"🎬 {e}")
            except Exception as e:
                st.error(f"❌ Error tidak terduga: {e}")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption(
    "Dibuat dengan ❤️ menggunakan Streamlit & TMDB API. "
    "Data film dari [The Movie Database (TMDB)](https://www.themoviedb.org). "
    "Data streaming dari [JustWatch](https://www.justwatch.com)."
)
