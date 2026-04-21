import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v8.0", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v8.0")
nav = st.sidebar.radio("Navigasi", ["Data Master & Edit", "Upload Database Baru", "Buat Menu Satuan", "Set Menu (Paket)"])

# --- MODUL 1: DATA MASTER ---
if nav == "Data Master & Edit":
    st.title("📂 Database Bahan Baku")
    if st.session_state.db_bahan.empty:
        st.info("Database kosong. Silakan Upload di menu sebelah kiri.")
    else:
        search = st.text_input("🔍 Cari Bahan...")
        df_display = st.session_state.db_bahan
        if search:
            df_display = df_display[df_display['nama'].str.contains(search, case=False)]

        edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan"):
            st.session_state.db_bahan = edited_df.fillna(0)
            st.success("Perubahan tersimpan!")

# --- MODUL 2: UPLOAD (DENGAN PERBAIKAN KOLOM) ---
elif nav == "Upload Database Baru":
    st.title("📥 Upload Master Data")
    uploaded_file = st.file_uploader("Pilih file CSV (Template V2)", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_new = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_new = pd.read_excel(uploaded_file)

            # Normalisasi kolom agar seragam
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            
            # Mapping nama kolom lama ke baru
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping)

            # Pastikan kolom wajib ada
            cols = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
            for c in cols:
                if c not in df_new.columns:
                    df_new[c] = 0 if c != "uom" else "kg"
            
            df_new = df_new[cols].fillna(0)

            if st.button("🚀 Konfirmasi & Sinkronkan"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Sinkron!")
                st.rerun()
        except Exception as e:
            st.error(f"Gagal: {e}")

# --- MODUL 3: BUAT MENU (DENGAN PROTEKSI ERROR) ---
elif nav == "Buat Menu Satuan":
    st.title("🍳 Pembuatan Master Item (Menu)")
    if st.session_state.db_bahan.empty:
        st.warning("Database kosong.")
    else:
        with st.form("form_item"):
            nama_m = st.text_input("Nama Menu Baru")
            pilih_b = st.multiselect("Pilih Bahan Baku", st.session_state.db_bahan['nama'].tolist())
            st.form_submit_button("Lanjut")
        
        if pilih_b:
            total = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0}
            with st.form("form_porsi"):
                for b in pilih_b:
                    # AMBIL DATA DENGAN AMAN (Mencegah KeyError)
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    
                    # Gunakan fungsi .get() agar jika kolom tidak ada, aplikasi tidak mati
                    uom_val = row.get('uom', 'kg')
                    berat_val = float(row.get('berat', 1000))
                    bdd_val = float(row.get('bdd', 100))
                    harga_val = float(row.get('harga', 0))

                    qty = st.number_input(f"Jumlah {b} ({uom_val})", min_value=0.0, step=0.01, key=f"q_{b}")
                    
                    # Kalkulasi
                    ratio = (berat_val / 100) * (bdd_val / 100)
                    total['kal'] += float(row.get('kalori', 0)) * ratio * qty
                    total['pro'] += float(row.get('protein', 0)) * ratio * qty
                    total['lem'] += float(row.get('lemak', 0)) * ratio * qty
                    total['kar'] += float(row.get('karbo', 0)) * ratio * qty
                    total['cost'] += harga_val * qty
                
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
