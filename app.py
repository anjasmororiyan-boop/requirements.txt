import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v7.5", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v7.5")
nav = st.sidebar.radio("Navigasi", ["Data Master & Edit", "Upload Database Baru", "Buat Menu Satuan", "Set Menu (Paket)"])

# --- MODUL 1: DATA MASTER & EDIT ---
if nav == "Data Master & Edit":
    st.title("📂 Database Bahan Baku")
    if st.session_state.db_bahan.empty:
        st.info("Database masih kosong. Silakan ke menu 'Upload Database Baru'.")
    else:
        search = st.text_input("🔍 Cari Bahan...")
        df_display = st.session_state.db_bahan
        if search:
            df_display = df_display[df_display['nama'].str.contains(search, case=False)]

        st.subheader("Edit Data Langsung")
        edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 Simpan Perubahan"):
            st.session_state.db_bahan = edited_df.fillna(0)
            st.success("Perubahan disimpan!")

# --- MODUL 2: UPLOAD DATABASE (FITUR UTAMA) ---
elif nav == "Upload Database Baru":
    st.title("📥 Upload Master Data")
    st.write("Gunakan menu ini untuk mengunggah file `Template_Master_NutriCost_V2.csv` Anda.")
    
    uploaded_file = st.file_uploader("Pilih file CSV atau Excel", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            # Membaca file dengan deteksi separator otomatis (penting untuk file Anda)
            if uploaded_file.name.endswith('.csv'):
                df_new = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_new = pd.read_excel(uploaded_file)

            # --- PEMBERSIHAN DATA ---
            # 1. Bersihkan nama kolom (kecilkan, hapus spasi, hapus \n)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            
            # 2. Mapping kolom jika nama berbeda (uom vs satuan_beli_uom, dll)
            mapping = {
                'satuan_beli_uom': 'uom',
                'berat_bersih_per_uom_gr': 'berat',
                'harga_beli_per_uom': 'harga'
            }
            df_new = df_new.rename(columns=mapping)

            # 3. Bersihkan isi kolom 'nama' dari karakter pindah baris
            df_new['nama'] = df_new['nama'].astype(str).str.replace('\n', ' ').str.strip()
            
            # 4. Pastikan kolom wajib ada
            required = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
            for col in required:
                if col not in df_new.columns:
                    df_new[col] = 0 if col != "uom" else "kg"
            
            df_new = df_new[required].fillna(0)

            st.subheader("Preview Data Terdeteksi")
            st.dataframe(df_new.head())

            if st.button("🚀 Konfirmasi & Sinkronkan"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success(f"Berhasil mengunggah {len(df_new)} bahan!")
                st.rerun()

        except Exception as e:
            st.error(f"Gagal memproses file: {e}")

# --- MODUL 3: BUAT MENU SATUAN ---
elif nav == "Buat Menu Satuan":
    st.title("🍳 Pembuatan Master Item (Menu)")
    if st.session_state.db_bahan.empty:
        st.warning("Database kosong.")
    else:
        with st.form("form_item"):
            nama_m = st.text_input("Nama Menu Baru")
            pilih_b = st.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())
            st.form_submit_button("Lanjut")
        
        if pilih_b:
            total = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0}
            with st.form("form_porsi"):
                for b in pilih_b:
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    qty = st.number_input(f"Jumlah {b} ({row['uom']})", min_value=0.0, step=0.01, key=f"q_{b}")
                    
                    # Kalkulasi
                    ratio = (row['berat'] / 100) * (row['bdd'] / 100)
                    total['kal'] += row['kalori'] * ratio * qty
                    total['pro'] += row['protein'] * ratio * qty
                    total['lem'] += row['lemak'] * ratio * qty
                    total['kar'] += row['karbo'] * ratio * qty
                    total['cost'] += row['harga'] * qty
                
                if st.form_submit_button("Simpan Menu"):
                    st.session_state.db_menu.append({
                        "nama": nama_m, "kal": total['kal'], "pro": total['pro'], 
                        "lem": total['lem'], "kar": total['kar'], "hpp": total['cost']
                    })
                    st.success(f"Menu '{nama_m}' tersimpan!")

# --- MODUL 4: SET MENU ---
elif nav == "Set Menu (Paket)":
    st.title("🍱 Set Menu (Paket)")
    if not st.session_state.db_menu:
        st.info("Buat menu satuan dulu.")
    else:
        nama_p = st.text_input("Nama Paket")
        pilih_item = st.multiselect("Pilih Menu Satuan", [m['nama'] for m in st.session_state.db_menu])
        if pilih_item:
            res = {'k': 0, 'p': 0, 'l': 0, 'ka': 0, 'h': 0}
            for pi in pilih_item:
                dm = next(item for item in st.session_state.db_menu if item["nama"] == pi)
                res['k'] += dm['kal']; res['p'] += dm['pro']
                res['l'] += dm['lem']; res['ka'] += dm['kar']; res['h'] += dm['hpp']
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Energi Paket", f"{res['k']:.0f} kkal")
            c2.metric("Total HPP", f"Rp {res['h']:,.0f}")
            c3.metric("Saran Jual", f"Rp {res['h']/0.3:,.0f}")
            st.plotly_chart(px.pie(values=[res['p'], res['l'], res['ka']], names=['Protein', 'Lemak', 'Karbo']))
