import streamlit as st
import pandas as pd

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v5.4", layout="wide")

# --- DATABASE STATE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", 
        "satuan_beli_uom", "berat_bersih_per_uom_gr", "harga_beli_per_uom"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR ---
st.sidebar.title("NutriCost Pro v5.4")
nav = st.sidebar.radio("Menu Utama", ["Master & Edit Bahan", "Master Item (Single Menu)", "Set Menu (Paket)"])

# --- MODUL 1: MASTER & EDIT BAHAN ---
if nav == "Master & Edit Bahan":
    st.title("📂 Database Management (Fixed Column Error)")
    
    with st.expander("📥 Import Data Baru (CSV/Excel)"):
        uploaded_file = st.file_uploader("Upload file template Anda", type=["csv", "xlsx"])
        if uploaded_file:
            df_new = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # NORMALISASI NAMA KOLOM (Hapus spasi & huruf kecil semua)
            df_new.columns = df_new.columns.str.strip().str.lower()
            
            # MEMASTIKAN KOLOM WAJIB ADA (Jika tidak ada, buatkan kolom kosong)
            required_cols = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", 
                             "satuan_beli_uom", "berat_bersih_per_uom_gr", "harga_beli_per_uom"]
            for col in required_cols:
                if col not in df_new.columns:
                    df_new[col] = 0 if col != "satuan_beli_uom" else "kg"
            
            df_new = df_new.fillna(0)
            
            if st.button("Tambahkan ke Database"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data berhasil disinkronkan!")
                st.rerun()

    st.subheader("📝 Edit & Lengkapi Data")
    # Tabel Editable dengan fitur deteksi error
    edited_df = st.data_editor(
        st.session_state.db_bahan, 
        use_container_width=True, 
        num_rows="dynamic"
    )
    
    if st.button("💾 Simpan Perubahan"):
        st.session_state.db_bahan = edited_df.fillna(0)
        st.success("Perubahan disimpan!")

# --- MODUL 2: MASTER ITEM (SINGLE MENU) ---
elif nav == "Master Item (Single Menu)":
    st.title("🍳 Pembuatan Single Menu")
    if st.session_state.db_bahan.empty:
        st.warning("Data bahan kosong.")
    else:
        with st.form("buat_menu"):
            nama_m = st.text_input("Nama Item Menu")
            pilih_b = st.multiselect("Pilih Komponen", st.session_state.db_bahan['nama'].tolist())
            st.form_submit_button("Proses Resep")
            
        if pilih_b:
            total = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0}
            
            with st.form("porsi_res"):
                for b in pilih_b:
                    # Ambil data bahan secara aman
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    
                    # Cek UOM agar tidak KeyError
                    uom_label = row.get('satuan_beli_uom', 'unit')
                    qty = st.number_input(f"Jumlah {b} ({uom_label})", min_value=0.0, step=0.01, key=f"inp_{b}")
                    
                    # KALKULASI AMAN
                    try:
                        berat_uom = float(row.get('berat_bersih_per_uom_gr', 1000))
                        if berat_uom <= 0: berat_uom = 1000
                        
                        bdd_val = float(row.get('bdd', 100)) / 100
                        ratio = (berat_uom / 100) * bdd_val
                        
                        total['kal'] += float(row.get('kalori', 0)) * ratio * qty
                        total['pro'] += float(row.get('protein', 0)) * ratio * qty
                        total['lem'] += float(row.get('lemak', 0)) * ratio * qty
                        total['kar'] += float(row.get('karbo', 0)) * ratio * qty
                        total['cost'] += float(row.get('harga_beli_per_uom', 0)) * qty
                    except Exception as e:
                        st.error(f"Error pada bahan {b}: {e}")
                
                if st.form_submit_button("Simpan Item Master"):
                    st.session_state.db_menu.append({
                        "nama_menu": nama_m, 
                        "total_kalori": total['kal'], 
                        "total_hpp": total['cost']
                    })
                    st.success(f"Tersimpan! HPP: Rp {total['cost']:,.0f}")

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
