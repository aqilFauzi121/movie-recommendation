"""
app.py — Landing Page "One Day One Movie"
====================================================
Halaman panduan dan beranda untuk aplikasi One Day One Movie.
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
import db

# Zona waktu WIB (UTC+7)
_WIB = timezone(timedelta(hours=7))

# ============================================================================
# KONFIGURASI HALAMAN
# ============================================================================
st.set_page_config(
    page_title="Beranda — One Day One Movie",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inisialisasi database
db.init_db()

# Auto-skip: film dari hari sebelumnya yang masih 'recommended' → 'skipped'
db.auto_skip_stale_recommendations()

# ============================================================================
# SIDEBAR
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
        font-size: 1.2rem;
        font-weight: 300;
        margin-top: 0.5rem;
        margin-bottom: 3rem;
    }
    
    /* Guide cards */
    .guide-card {
        background: linear-gradient(145deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid rgba(229, 9, 20, 0.15);
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    .guide-card h3 {
        color: #FAFAFA;
        margin-top: 0;
        font-weight: 700;
        font-size: 1.4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .guide-card p, .guide-card li {
        color: #C0C0C0;
        font-size: 1rem;
        line-height: 1.7;
    }
    .guide-card li {
        margin-bottom: 0.5rem;
    }
    .guide-card strong {
        color: #FF6B6B;
    }
    
    /* Custom info box for auto-skip */
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# KONTEN LANDING PAGE
# ============================================================================
st.markdown('<h1 class="hero-title">🎬 Selamat Datang di One Day One Movie!</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Satu hari, satu tantangan, satu film berkualitas untuk mengeksplorasi dunia sinema!</p>', unsafe_allow_html=True)

st.markdown("""
<div class="guide-card">
    <h3>📌 Alur Kerja</h3>
    <ol>
        <li>Buka menu <strong>Rekomendasi Hari Ini</strong> di sidebar sebelah kiri.</li>
        <li>Klik tombol <strong>Dapatkan Rekomendasi Hari Ini</strong> untuk mendapatkan 1 film pilihan secara acak.</li>
        <li>Tonton film tersebut di platform streaming yang tersedia.</li>
    </ol>
</div>

<div class="guide-card">
    <h3>🔘 Tombol & Fitur</h3>
    <ul>
        <li><strong>🔄 Reroll:</strong> Gunakan tombol ini jika kamu <em>sudah pernah menonton</em> film yang direkomendasikan dan ingin menggantinya dengan film lain. Film yang di-reroll tidak akan direkomendasikan lagi di masa depan.</li>
        <li><strong>✅ Sudah Ditonton:</strong> Klik tombol ini setelah kamu selesai menonton rekomen hari ini. Film akan otomatis masuk ke <strong>Jurnal Tontonan</strong>.</li>
        <li><strong>📓 Jurnal Tontonan:</strong> Tempat kamu melihat riwayat film yang sudah lewat. Di sana kamu bisa memberikan <strong>Rating (Bintang)</strong> dan menuliskan <strong>Review/Ulasan</strong> singkat untuk film yang sudah ditonton.</li>
    </ul>
</div>

<div class="guide-card">
    <h3>⚙️ Sistem Auto-Skip (Lewati Otomatis)</h3>
    <p>Jika kamu mendapatkan rekomendasi untuk hari ini, namun kamu membiarkannya (tidak menekan 'Sudah Ditonton' atau 'Reroll') hingga lewat target waktu (tengah malam WIB), maka sistem akan secara otomatis menandainya sebagai <strong>Dilewati (Skipped)</strong>.</p>
    <div class="info-box">
        <strong>Penting:</strong> Film yang berstatus <em>Skipped</em> akan masuk ke Jurnal Tontonan sebagai riwayat lewat saja, namun <strong>tidak di-blacklist</strong>. Artinya, film tersebut punya kemungkinan untuk direkomendasikan kembali kepadamu di suatu hari nanti!
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.info("👈 Silakan klik menu **Rekomendasi Hari Ini** di sidebar sebelah kiri untuk mulai!", icon="🚀")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption(
    "Dibuat dengan ❤️ menggunakan Streamlit & TMDB API. "
    "Data film dari [The Movie Database (TMDB)](https://www.themoviedb.org). "
    "Data streaming dari [JustWatch](https://www.justwatch.com)."
)
