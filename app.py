import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v9.0", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v9.0")
nav = st.sidebar.radio("Navigasi", [
    "1. Data Master & Edit", 
    "2. Upload Database Baru", 
    "3. Buat Resep (Recipe Engineering)",
    "4. Set Menu (Paket)"
])

# --- MODUL 1: DATA MASTER (Melihat 1500+ Item) ---
if nav == "1. Data Master & Edit":
    st.title("📂 Database Bahan Baku")
    if st.session_state.db_bahan.empty:
        st.info("Database kosong. Silakan ke menu Upload.")
    else:
        search = st.text_input("🔍 Cari Bahan (Contoh: Beras, Ayam...)")
        df_display = st.session_state.db_bahan
        if search:
            df_display = df_display[df_display['nama'].str.contains(search, case=False)]

        edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan"):
            st.session_state.db_bahan = edited_df.fillna(0)
            st.success("Perubahan tersimpan!")

# --- MODUL 2: UPLOAD (Fitur yang Anda tanyakan - TETAP ADA) ---
elif nav == "2. Upload Database Baru":
    st.title("📥 Upload Master Data (CSV/Excel)")
    uploaded_file = st.file_uploader("Pilih file template Anda", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                # Deteksi separator otomatis untuk file titik koma Anda
                df_new = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_new = pd.read_excel(uploaded_file)

            # Normalisasi kolom
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping)

            # Pastikan kolom wajib ada
            cols = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
            for c in cols:
                if c not in df_new.columns:
                    df_new[c] = 0 if c != "uom" else "kg"
            
            df_new = df_new[cols].fillna(0)

            if st.button("🚀 Konfirmasi & Masukkan ke Database"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data berhasil di-upload!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (LOGIKA BARU DENGAN TABEL & YIELD) ---
elif nav == "3. Buat Resep (Recipe Engineering)":
    st.title("🍳 Recipe Builder & Yield Calculation")
    
    if st.session_state.db_bahan.empty:
        st.warning("Database bahan kosong. Upload data terlebih dahulu.")
    else:
        with st.container():
            c1, c2 = st.columns(2)
            nama_resep = c1.text_input("Nama Menu / Resep", placeholder="Contoh: Nasi Goreng Spesial")
            pilih_b = c2.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())

        if pilih_b:
            st.markdown("### 📋 Rincian Komposisi Bahan")
            total_data = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'berat_mentah': 0.0}
            
            # Header Tabel Rincian
            h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
            h1.write("**Nama Bahan**")
            h2.write("**UOM**")
            h3.write("**Qty Input**")
            h4.write("**Gramasi**")

            for b in pilih_b:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                col_n, col_u, col_q, col_g = st.columns([3, 1, 1, 1])
                
                col_n.write(f"🔹 {b}")
                uom_label = row.get('uom', 'kg')
                col_u.write(uom_label)
                
                qty = col_q.number_input(f"Qty {b}", min_value=0.0, step=0.01, key=f"rec_{b}", label_visibility="collapsed")
                
                # Hitung berat mentah
                berat_uom = float(row.get('berat', 1000))
                gram_mentah = qty * berat_uom
                col_g.write(f"{gram_mentah:,.0f} gr")
                
                # Kalkulasi Nutrisi & Cost
                ratio = (berat_uom / 100) * (float(row.get('bdd', 100)) / 100)
                total_data['kal'] += float(row.get('kalori', 0)) * ratio * qty
                total_data['pro'] += float(row.get('protein', 0)) * ratio * qty
                total_data['lem'] += float(row.get('lemak', 0)) * ratio * qty
                total_data['kar'] += float(row.get('karbo', 0)) * ratio * qty
                total_data['cost'] += float(row.get('harga', 0)) * qty
                total_data['berat_mentah'] += gram_mentah

            st.divider()
            st.subheader("⚖️ Yield & Porsi Akhir")
            y1, y2, y3 = st.columns(3)
            
            y1.metric("Total Berat Mentah", f"{total_data['berat_mentah']:,.0f} gr")
            # User input berat matang (Yield)
            berat_matang = y2.number_input("Berat Hasil Jadi (Matang) - gr", min_value=1.0, value=total_data['berat_mentah'])
            jumlah_porsi = y3.number_input("Jumlah Porsi (Yield Portions)", min_value=1, value=1)

            # Hasil Per Porsi
            cost_porsi = total_data['cost'] / jumlah_porsi
            berat_porsi = berat_matang / jumlah_porsi

            st.success(f"**Ringkasan:** 1 Porsi = {berat_porsi:,.0f} gr | HPP = Rp {cost_porsi:,.0f}")

            if st.button("💾 Simpan Resep ke Master Item"):
                st.session_state.db_menu.append({
                    "nama": nama_resep,
                    "kal": total_data['kal'] / jumlah_porsi,
                    "pro": total_data['pro'] / jumlah_porsi,
                    "lem": total_data['lem'] / jumlah_porsi,
                    "kar": total_data['kar'] / jumlah_porsi,
                    "hpp": cost_porsi,
                    "berat_porsi": berat_porsi
                })
                st.success(f"Resep {nama_resep} Berhasil Disimpan!")

# --- MODUL 4: SET MENU (PAKET) ---
elif nav == "4. Set Menu (Paket)":
    st.title("🍱 Set Menu / Paket")
    # (Logika paket tetap sama...)
