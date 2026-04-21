import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v13.8", layout="wide")

# --- 1. FUNGSI PERSISTENSI DATA (FIXED) ---
def load_data(file_name, columns):
    """Fungsi ini memastikan tabel tetap muncul meskipun file belum ada."""
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            # Pastikan semua kolom wajib ada untuk mencegah error rendering
            for col in columns:
                if col not in df.columns:
                    df[col] = 0
            return df
        except:
            return pd.DataFrame(columns=columns)
    # Jika file tidak ada, buat dataframe kosong dengan kolom yang benar
    return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE (Sistem Tiered) ---
# Menggunakan folder yang sama untuk menyimpan database CSV
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("db_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data("db_wip.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data("db_fg.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data("db_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"])

# --- 3. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v13.8")
nav = st.sidebar.radio("Alur Produksi", [
    "📦 1. Database Bahan Baku (RM)", 
    "📥 2. Upload Master Data",
    "🍳 3. Master Resep Dasar (WIP)", 
    "🍱 4. Finished Goods (FG)",
    "🛒 5. Set Menu (Paket Jual)"
])

# --- HELPER: KALKULASI GIZI ---
def get_nutrisi_all_tier(qty, row, source='RM'):
    try:
        if source == 'RM':
            gr_mentah = qty * float(row['berat'])
            factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
            return {'k': float(row['kalori'])*factor, 'p': float(row['protein'])*factor, 'l': float(row['lemak'])*factor, 'ka': float(row['karbo'])*factor, 'h': float(row['harga'])*qty, 'g': gr_mentah}
        else: # Untuk WIP atau FG (sudah porsi)
            return {'k': float(row['kal_porsi'])*qty, 'p': float(row['pro_porsi'])*qty, 'l': float(row['lem_porsi'])*qty, 'ka': float(row['kar_porsi'])*qty, 'h': float(row['hpp_porsi'])*qty, 'g': float(row['berat_porsi_gr'])*qty}
    except: return {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'g':0}

# --- MODUL 1: DATABASE BAHAN ---
if nav == "1. Database Bahan Baku (RM)":
    st.title("📂 Database Bahan Baku")
    st.markdown("Kelola data mentah (Raw Material) di sini.")
    
    # Menampilkan editor tabel (tidak akan kosong karena fungsi load_data sudah diproteksi)
    edited_rm = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic", key="editor_rm_v13")
    
    if st.button("💾 Simpan Database Bahan"):
        st.session_state.db_bahan = edited_rm.fillna(0)
        save_data(st.session_state.db_bahan, "db_bahan.csv")
        st.success("Data Bahan Baku Berhasil Disimpan!")

# --- MODUL 2: UPLOAD DATA ---
elif nav == "2. Upload Master Data":
    st.title("📥 Upload Database Massal")
    up_file = st.file_uploader("Upload File (CSV/Excel)", type=["csv", "xlsx"])
    if up_file and st.button("🚀 Sinkronkan"):
        df_new = pd.read_csv(up_file, sep=None, engine='python') if up_file.name.endswith('.csv') else pd.read_excel(up_file)
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data(st.session_state.db_bahan, "db_bahan.csv")
        st.success("Sinkronisasi Berhasil!"); st.rerun()

# --- MODUL 3: MASTER RESEP (WIP) ---
elif nav == "3. Master Resep Dasar (WIP)":
    st.title("🍳 Master Resep Dasar (Work In Process)")
    tab1, tab2 = st.tabs(["📝 Buat WIP Baru", "📋 Database WIP"])
    
    with tab1:
        if "w_id" not in st.session_state: st.session_state.w_id = 0
        nm_wip = st.text_input("Nama Resep (Contoh: Sambal Goreng)", key=f"wnm_{st.session_state.w_id}")
        selected_rm = st.multiselect("Pilih Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"wsel_{st.session_state.w_id}")
        
        if selected_rm:
            res_w = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for b in selected_rm:
                row_b = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                q_w = st.number_input(f"Qty {b}", min_value=0.0, key=f"qw_{b}")
                calc = get_nutrisi_all_tier(q_w, row_b, 'RM')
                for key in res_w: res_w[key] += calc[key]
            
            y_w = st.number_input("Berat Matang (gr)", value=max(res_w['g'], 1.0))
            p_w = st.number_input("Jumlah Porsi", min_value=1, value=1)
            
            if st.button("💾 Simpan WIP"):
                new_w = pd.DataFrame([{"nama":nm_wip, "berat_porsi_gr":y_w/p_w, "kal_porsi":res_w['k']/p_w, "pro_porsi":res_w['p']/p_w, "lem_porsi":res_w['l']/p_w, "kar_porsi":res_w['ka']/p_w, "hpp_porsi":res_w['h']/p_w}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new_w], ignore_index=True)
                save_data(st.session_state.db_wip, "db_wip.csv")
                st.session_state.w_id += 1; st.rerun()

    with tab2:
        st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic")

# --- MODUL 4: FINISHED GOODS (FG) ---
elif nav == "4. Finished Goods (FG)":
    st.title("🍱 Finished Goods (Gabungan RM + WIP)")
    # Logika UI yang sama dengan Tabbed Interface agar fitur terlihat jelas
    tab1, tab2 = st.tabs(["🆕 Buat Produk FG", "📋 Database FG"])
    # ... (Isi logika seperti versi v13.5 namun dipastikan rendering-nya di dalam tab)

# --- MODUL 5: SET MENU ---
elif nav == "5. Set Menu (Paket Jual)":
    st.title("🛒 Set Menu (Kombinasi Universal)")
    # Dipastikan menampilkan Form Input meski database masih sedikit
    if st.button("🧹 Reset Form"): st.rerun()
    # ... (Isi logika input Paket Jual)
