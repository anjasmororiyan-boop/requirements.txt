import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro", layout="wide")

# --- DATABASE STATE ---
# Inisialisasi database di session_state agar data tidak hilang saat refresh
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame([
        {"nama": "Dada Ayam", "kalori": 165, "protein": 31, "lemak": 3.6, "karbo": 0, "bdd": 100, "harga_per_kg": 55000},
        {"nama": "Beras Putih", "kalori": 130, "protein": 2.7, "lemak": 0.3, "karbo": 28, "bdd": 100, "harga_per_kg": 15000},
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v1.0")
nav = st.sidebar.radio("Menu Utama", ["Master Bahan Baku", "Master Item (Single Menu)", "Set Menu (Paket)", "Dashboard Analisis"])

# --- MODUL 1: MASTER BAHAN BAKU (IMPORT) ---
if nav == "Master Bahan Baku":
    st.title("📦 Management Bahan Baku")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Daftar Bahan Saat Ini")
        st.dataframe(st.session_state.db_bahan, use_container_width=True)
    
    with col2:
        st.subheader("📥 Import Bulk (CSV)")
        st.info("Format CSV: nama, kalori, protein, lemak, karbo, bdd, harga_per_kg")
        
        uploaded_file = st.file_uploader("Upload File CSV", type=["csv"])
        if uploaded_file:
            try:
                df_new = pd.read_csv(uploaded_file)
                if st.button("Konfirmasi Import"):
                    st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                    st.success("Data berhasil diperbarui!")
                    st.rerun()
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")

# --- MODUL 2: MASTER ITEM (SINGLE MENU) ---
elif nav == "Master Item (Single Menu)":
    st.title("🍳 Pembuatan Single Menu")
    
    # Form Pertama: Input Nama dan Pilih Bahan
    with st.form("form_awal"):
        nama_menu = st.text_input("Nama Menu (Item Master)")
        selected_bahan = st.multiselect("Pilih Bahan Baku", st.session_state.db_bahan['nama'].tolist())
        btn_lanjut = st.form_submit_button("Lanjut ke Detail Porsi")

    if selected_bahan:
        st.subheader(f"Detail Resep: {nama_menu}")
        total_nutrisi = {'kal': 0, 'pro': 0, 'lem': 0, 'kar': 0, 'cost': 0}
        
        # Form Kedua: Input Berat Porsi
        with st.form("form_porsi"):
            for b in selected_bahan:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                berat = st.number_input(f"Berat {b} (gram)", min_value=0.0, value=100.0, key=f"in_{b}")
                
                # Kalkulasi
                ratio = berat / 100
                bdd_factor = row['bdd'] / 100
                total_nutrisi['kal'] += row['kalori'] * ratio * bdd_factor
                total_nutrisi['pro'] += row['protein'] * ratio * bdd_factor
                total_nutrisi['lem'] += row['lemak'] * ratio * bdd_factor
                total_nutrisi['kar'] += row['karbo'] * ratio * bdd_factor
                total_nutrisi['cost'] += (berat / 1000) * row['harga_per_kg']
            
            btn_simpan = st.form_submit_button("Simpan ke Master Item")
            
            if btn_simpan:
                if not nama_menu:
                    st.error("Nama menu wajib diisi!")
                else:
                    entry = {
                        "nama_menu": nama_menu,
                        "total_kalori": round(total_nutrisi['kal'], 2),
                        "total_protein": round(total_nutrisi['pro'], 2),
                        "total_lemak": round(total_nutrisi['lem'], 2),
                        "total_karbo": round(total_nutrisi['kar'], 2),
                        "total_hpp": round(total_nutrisi['cost'], 2)
                    }
                    st.session_state.db_menu.append(entry)
                    st.success(f"Menu '{nama_menu}' berhasil disimpan!")

# --- MODUL 3: SET MENU (PAKET) ---
elif nav == "Set Menu (Paket)":
    st.title("🍱 Pembuatan Set Menu (Aggregator)")
    if not st.session_state.db_menu:
        st.warning("Belum ada data di Master Item. Buat menu satuan terlebih dahulu.")
    else:
        nama_set = st.text_input("Nama Paket (Contoh: Paket Hemat)")
        pilihan = st.multiselect("Ambil dari Master Item", [m['nama_menu'] for m in st.session_state.db_menu])
        
        if pilihan:
            res_set = {'kal': 0, 'pro': 0, 'lem': 0, 'kar': 0, 'hpp': 0}
            for p in pilihan:
                m_data = next(item for item in st.session_state.db_menu if item["nama_menu"] == p)
                res_set['kal'] += m_data['total_kalori']
                res_set['pro'] += m_data['total_protein']
                res_set['lem'] += m_data['total_lemak']
                res_set['kar'] += m_data['total_karbo']
                res_set['hpp'] += m_data['total_hpp']
            
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Kalori", f"{res_set['kal']:.2f} kkal")
            c2.metric("Total Protein", f"{res_set['pro']:.2f} g")
            c3.metric("Total HPP", f"Rp {res_set['hpp']:,.0f}")
            c4.metric("Harga Jual (FC 30%)", f"Rp {res_set['hpp']/0.3:,.0f}")
            
            fig = px.pie(values=[res_set['pro'], res_set['lem'], res_set['kar']], 
                         names=['Protein', 'Lemak', 'Karbo'], 
                         title=f"Analisis Gizi: {nama_set}")
            st.plotly_chart(fig)

# --- MODUL 4: DASHBOARD ANALISIS ---
elif nav == "Dashboard Analisis":
    st.title("📊 Ringkasan Master Item")
    if st.session_state.db_menu:
        df = pd.DataFrame(st.session_state.db_menu)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Data Master Item kosong.")
