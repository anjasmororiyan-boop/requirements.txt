import streamlit as st
import pandas as pd

# --- KONFIGURASI ---
st.set_page_config(page_title="NutriCost Pro v9.0", layout="wide")

if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- NAVIGASI ---
nav = st.sidebar.radio("Navigasi", ["Data Master", "Upload Data", "Buat Resep (Menu Master)"])

# --- MODUL BUAT RESEP (LOGIKA BARU) ---
if nav == "Buat Resep (Menu Master)":
    st.title("🍳 Recipe Builder & Yield Calculation")
    
    if st.session_state.db_bahan.empty:
        st.warning("Database bahan kosong.")
    else:
        # STEP 1: INFORMASI UMUM
        with st.container():
            c1, c2 = st.columns(2)
            nama_resep = c1.text_input("Nama Menu / Resep", placeholder="Contoh: Nasi Ayam Bakar")
            komponen = c2.multiselect("Pilih Bahan Baku yang Digunakan", st.session_state.db_bahan['nama'].tolist())

        if komponen:
            st.markdown("---")
            st.subheader("📋 Rincian Komposisi Bahan")
            
            # STEP 2: TABEL RINCIAN BAHAN
            total_mentah = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'berat': 0.0}
            
            # Header Tabel
            h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
            h1.write("**Nama Bahan**")
            h2.write("**UOM**")
            h3.write("**Qty Input**")
            h4.write("**Berat (gr)**")

            for b in komponen:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                
                # Baris Input
                col_n, col_u, col_q, col_g = st.columns([3, 1, 1, 1])
                col_n.write(f"🔹 {b}")
                uom_val = row.get('uom', 'kg')
                col_u.write(uom_val)
                
                qty = col_q.number_input(f"Qty {b}", min_value=0.0, step=0.01, key=f"q_{b}", label_visibility="collapsed")
                
                # Hitung Berat Gramasi Mentah
                berat_dasar = float(row.get('berat', 1000))
                gramasi_mentah = qty * berat_dasar
                col_g.write(f"{gramasi_mentah:,.0f} gr")
                
                # Akumulasi Nutrisi Mentah (Berdasarkan BDD)
                ratio = (berat_dasar / 100) * (float(row.get('bdd', 100)) / 100)
                total_mentah['kal'] += float(row.get('kalori', 0)) * ratio * qty
                total_mentah['pro'] += float(row.get('protein', 0)) * ratio * qty
                total_mentah['lem'] += float(row.get('lemak', 0)) * ratio * qty
                total_mentah['kar'] += float(row.get('karbo', 0)) * ratio * qty
                total_mentah['cost'] += float(row.get('harga', 0)) * qty
                total_mentah['berat'] += gramasi_mentah

            st.markdown("---")
            
            # STEP 3: YIELD & HASIL JADI
            st.subheader("⚖️ Yield & Porsi")
            y1, y2, y3 = st.columns(3)
            
            y1.metric("Total Berat Mentah", f"{total_mentah['berat']:,.0f} gr")
            yield_jadi = y2.number_input("Berat Hasil Jadi (Matang) - Gram", min_value=1.0, value=total_mentah['berat'], help="Isi berat total masakan setelah matang")
            jumlah_porsi = y3.number_input("Jumlah Porsi per Masakan", min_value=1, value=1)

            # Kalkulasi Akhir
            berat_per_porsi = yield_jadi / jumlah_porsi
            cost_per_porsi = total_mentah['cost'] / jumlah_porsi
            
            st.info(f"💡 Hasil: 1 Porsi beratnya **{berat_per_porsi:,.0f} gr** dengan HPP **Rp {cost_per_porsi:,.0f}**")

            if st.button("💾 Simpan Menu ke Master Item"):
                res_menu = {
                    "nama": nama_resep,
                    "berat_porsi": berat_per_porsi,
                    "kal": total_mentah['kal'] / jumlah_porsi,
                    "pro": total_mentah['pro'] / jumlah_porsi,
                    "lem": total_mentah['lem'] / jumlah_porsi,
                    "kar": total_mentah['kar'] / jumlah_porsi,
                    "hpp": cost_per_porsi
                }
                st.session_state.db_menu.append(res_menu)
                st.success(f"Menu {nama_resep} berhasil disimpan!")

# --- MODUL LAIN (Data Master & Upload) Tetap Sama ---
