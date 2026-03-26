"""
📓 Jurnal Tontonan — Halaman Riwayat & Review
==============================================
Halaman multi-page Streamlit untuk melihat riwayat film
dan menulis ulasan personal dengan rating bintang.
"""

import json
from datetime import datetime, timezone, timedelta
import streamlit as st
import db

# Zona waktu WIB (UTC+7)
_WIB = timezone(timedelta(hours=7))

st.set_page_config(
    page_title="Jurnal Tontonan — One Day One Movie",
    page_icon="📓",
    layout="wide",
    initial_sidebar_state="collapsed",
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
# CUSTOM CSS (sama dengan app.py untuk konsistensi)
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #E50914 0%, #FF6B6B 50%, #FFA07A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
    }
    .hero-subtitle {
        text-align: center;
        color: #8899AA;
        font-size: 1rem;
        font-weight: 300;
        margin-top: 0;
        margin-bottom: 2rem;
    }
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
    .movie-card-journal {
        background: linear-gradient(145deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid rgba(229, 9, 20, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .status-badge-watched {
        display: inline-block;
        background: rgba(34, 197, 94, 0.15);
        color: #22C55E;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-recommended {
        display: inline-block;
        background: rgba(59, 130, 246, 0.15);
        color: #3B82F6;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-skipped {
        display: inline-block;
        background: rgba(156, 163, 175, 0.15);
        color: #9CA3AF;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-rerolled {
        display: inline-block;
        background: rgba(249, 115, 22, 0.15);
        color: #F97316;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
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
st.markdown('<h1 class="hero-title">📓 Jurnal Tontonan</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Riwayat film dan ulasan personal Anda</p>', unsafe_allow_html=True)

# ============================================================================
# STATISTIK
# ============================================================================
stats = db.get_stats()

col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
with col_s1:
    st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["total"]}</div><div class="stat-label">Total</div></div>', unsafe_allow_html=True)
with col_s2:
    st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["watched"]}</div><div class="stat-label">Ditonton</div></div>', unsafe_allow_html=True)
with col_s3:
    st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["skipped"]}</div><div class="stat-label">Dilewati</div></div>', unsafe_allow_html=True)
with col_s4:
    st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["rerolled"]}</div><div class="stat-label">Reroll</div></div>', unsafe_allow_html=True)
with col_s5:
    avg = f'⭐ {stats["avg_rating"]}' if stats["avg_rating"] else "—"
    st.markdown(f'<div class="stat-card"><div class="stat-number">{avg}</div><div class="stat-label">Avg Rating</div></div>', unsafe_allow_html=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# ============================================================================
# FILTER
# ============================================================================
filter_options = {
    "🎬 Semua": "all",
    "✅ Ditonton": "watched",
    "📌 Direkomendasikan": "recommended",
    "⏭️ Dilewati": "skipped",
    "🔄 Rerolled": "rerolled",
}

selected_filter = st.radio(
    "Filter riwayat:",
    options=list(filter_options.keys()),
    horizontal=True,
    label_visibility="collapsed",
)

status_filter = filter_options[selected_filter]

# ============================================================================
# DAFTAR FILM
# ============================================================================
recommendations = db.get_all_recommendations(status_filter)

if not recommendations:
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
            <p style="color: #8899AA;">Belum ada riwayat film. 
            Dapatkan rekomendasi pertama di halaman utama!</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    for rec in recommendations:
        status = rec["status"]
        badge_class = f"status-badge-{status}"
        status_labels = {"watched": "✅ Ditonton", "recommended": "📌 Direkomendasikan", "skipped": "⏭️ Dilewati", "rerolled": "🔄 Rerolled"}
        status_label = status_labels.get(status, status.capitalize())
        
        # Judul expander dengan info ringkas
        year = rec.get("release_date", "")[:4] if rec.get("release_date") else ""
        expander_title = f"{rec['title']} ({year}) — ⭐ {rec.get('vote_average', 0):.1f}"
        
        with st.expander(expander_title, expanded=False):
            st.markdown(f'<span class="{badge_class}">{status_label}</span> &nbsp; 📅 Direkomendasikan: {rec["recommended_date"]}', unsafe_allow_html=True)
            
            col_p, col_d = st.columns([1, 3])
            
            with col_p:
                if rec.get("poster_path"):
                    st.image(rec["poster_path"], width=150)
            
            with col_d:
                # Genre
                genres = rec.get("genres", "")
                if genres:
                    st.markdown(f"**Genre:** {genres}")
                
                # Sinopsis
                overview = rec.get("overview", "")
                if overview:
                    st.markdown(f"*{overview[:300]}{'...' if len(overview) > 300 else ''}*")
                
                # Trailer
                trailer_url = rec.get("trailer_url", "")
                if trailer_url:
                    st.link_button("▶️ Trailer", trailer_url)
            
            st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
            
            # ============================================================
            # FORM JURNAL — Rating & Review
            # ============================================================
            st.markdown("**📝 Jurnal Pribadi**")
            
            # Ambil jurnal entry yang sudah ada (jika ada)
            journal_entry = db.get_journal_entry(rec["movie_id"])
            
            existing_rating = journal_entry["rating"] if journal_entry else 3
            existing_review = journal_entry["review"] if journal_entry else ""
            
            # Gunakan unique key per film agar widget tidak konflik
            unique_key = f"journal_{rec['id']}_{rec['movie_id']}"
            
            # Rating dengan emoji bintang
            star_options = {
                1: "⭐ (1/5) Buruk",
                2: "⭐⭐ (2/5) Kurang",
                3: "⭐⭐⭐ (3/5) Cukup",
                4: "⭐⭐⭐⭐ (4/5) Bagus",
                5: "⭐⭐⭐⭐⭐ (5/5) Luar Biasa",
            }
            
            rating = st.select_slider(
                "Rating Anda:",
                options=[1, 2, 3, 4, 5],
                value=existing_rating,
                format_func=lambda x: star_options[x],
                key=f"rating_{unique_key}",
            )
            
            review = st.text_area(
                "Ulasan singkat:",
                value=existing_review,
                placeholder="Tulis kesan Anda setelah menonton film ini...",
                key=f"review_{unique_key}",
                max_chars=500,
            )
            
            col_save, col_status = st.columns([1, 3])
            with col_save:
                if st.button("💾 Simpan Jurnal", key=f"save_{unique_key}", type="primary"):
                    db.save_journal_entry(rec["movie_id"], rating, review)
                    # Otomatis tandai sebagai 'watched' jika belum
                    if rec["status"] != "watched":
                        db.mark_as_watched(rec["id"])
                    st.success("Jurnal tersimpan! ✅")
                    st.rerun()
            
            with col_status:
                if journal_entry:
                    st.caption(f"Terakhir diupdate: {journal_entry.get('updated_at', 'N/A')}")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption(
    "Data film dari [TMDB](https://www.themoviedb.org). "
    "Data streaming dari [JustWatch](https://www.justwatch.com)."
)
