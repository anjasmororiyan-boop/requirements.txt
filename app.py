import streamlit as st
import pandas as pd

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v5.5", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame()

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR ---
st.sidebar.title("NutriCost Pro v5.5")
nav = st.sidebar.radio("Menu Utama", ["Master & Edit Bahan", "Master Item (Single Menu)", "Set Menu (Paket)"])

# --- MODUL 1: MASTER & EDIT BAHAN ---
if nav == "Master & Edit Bahan":
    st.title("📂 Database Management (Fix File Error)")
    
    with st.expander("📥 Import Data Baru (CSV/Excel)"):
        uploaded_file = st.file_uploader("Upload file template Anda", type=["csv", "xlsx"])
        if uploaded_file:
            try:
                # Membaca file
                if uploaded_file.name.endswith('.csv'):
                    df_new = pd.read_csv(uploaded_file)
                else:
                    df_new = pd.read_excel(uploaded_file)
                
                # --- PROSES PEMBERSIHAN KOLOM (MANDATORY) ---
                # 1. Hapus spasi di awal/akhir nama kolom & buat huruf kecil
                df_new.columns = df_new.columns.str.strip().str.lower()
                # 2. Hapus karakter pindah baris (\n) jika ada di nama kolom
                df_new.columns = df_new.columns.str.replace('\n', ' ', regex=True)
                
                # --- MAPPING KOLOM OTOMATIS ---
                # Memastikan kolom penting ada, jika tidak ada dibuatkan default 0
                essential_cols = {
                    "nama": "Unknown Item",
                    "kalori": 0, "protein": 0, "lemak": 0, "karbo": 0, "bdd": 100,
                    "satuan_beli_uom": "Kg",
                    "berat_bersih_per_uom_gr": 1000,
                    "harga_beli_per_uom": 0
                }
                
                for col, default_val in essential_cols.items():
                    if col not in df_new.columns:
                        df_new[col] = default_val
                
                # Bersihkan isi data (NaN jadi 0, hapus spasi di nama bahan)
                df_new['nama'] = df_new['nama'].astype(str).str.replace('\n', ' ', regex=True).str.strip()
                df_new = df_new.fillna(0)

                if st.button("🚀 Sinkronkan Data"):
                    st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                    st.success("Data berhasil dibersihkan dan disinkronkan!")
                    st.rerun()
            except Exception as e:
                st.error(f"Gagal memproses file: {e}")

    # --- TABEL EDITABLE ---
    if not st.session_state.db_bahan.empty:
        st.subheader("📝 Edit & Lengkapi Data")
        edited_df = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan"):
            st.session_state.db_bahan = edited_df.fillna(0)
            st.success("Data Tersimpan!")
    else:
        st.info("Upload file CSV/Excel untuk mengisi database.")

# --- MODUL 2: MASTER ITEM (SINGLE MENU) ---
elif nav == "Master Item (Single Menu)":
    st.title("🍳 Pembuatan Single Menu")
    if st.session_state.db_bahan.empty:
        st.warning("Database Kosong.")
    else:
        with st.form("form_item"):
            nama_m = st.text_input("Nama Item Master (Menu)")
            pilih_b = st.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())
            st.form_submit_button("Lanjut")
            
        if pilih_b:
            total = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0}
            with st.form("form_porsi"):
                for b in pilih_b:
                    # Ambil row secara aman
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    uom = row.get('satuan_beli_uom', 'unit')
                    qty = st.number_input(f"Jumlah {b} ({uom})", min_value=0.0, step=0.01, key=f"key_{b}")
                    
                    # Kalkulasi
                    try:
                        berat_dasar = float(row.get('berat_bersih_per_uom_gr', 1000))
                        bdd_fac = float(row.get('bdd', 100)) / 100
                        # Nutrisi per 100g ke total berat beli
                        ratio = (berat_dasar / 100) * bdd_fac
                        
                        total['kal'] += float(row.get('kalori', 0)) * ratio * qty
                        total['pro'] += float(row.get('protein', 0)) * ratio * qty
                        total['lem'] += float(row.get('lemak', 0)) * ratio * qty
                        total['kar'] += float(row.get('karbo', 0)) * ratio * qty
                        total['cost'] += float(row.get('harga_beli_per_uom', 0)) * qty
                    except:
                        pass
                
                if st.form_submit_button("Simpan Menu"):
                    st.session_state.db_menu.append({"nama_menu": nama_m, "total_kalori": total['kal'], "total_hpp": total['cost']})
                    st.success(f"Menu {nama_m} Tersimpan!")

# --- MODUL 3: SET MENU ---
elif nav == "Set Menu (Paket)":
    st.title("🍱 Gabungkan Menu Menjadi Paket")
    if not st.session_state.db_menu:
        st.info("Buat Item Master (Single Menu) terlebih dahulu.")
    else:
        nama_p = st.text_input("Nama Paket")
        pilih_item = st.multiselect("Pilih Menu Satuan", [m['nama_menu'] for m in st.session_state.db_menu])
        
        if pilih_item:
            tot = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0}
            for pi in pilih_item:
                dm = next(item for item in st.session_state.db_menu if item["nama_menu"] == pi)
                tot['k'] += dm['total_kalori']; tot['p'] += dm['total_protein']
                tot['l'] += dm['total_lemak']; tot['ka'] += dm['total_karbo']
                tot['h'] += dm['total_hpp']
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Energi", f"{tot['k']:.0f} kkal")
            c2.metric("Total HPP", f"Rp {tot['h']:,.0f}")
            c3.metric("Harga Jual (FC 30%)", f"Rp {tot['h']/0.3:,.0f}")

# --- MODUL 4: DASHBOARD ---
elif nav == "Dashboard":
    st.title("📊 Analisis Data")
    if st.session_state.db_menu:
        st.table(pd.DataFrame(st.session_state.db_menu))
    else:
        st.info("Belum ada data menu untuk dianalisis.")
