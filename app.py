import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v2", layout="wide")

# --- DATABASE STATE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "satuan_uom", "berat_bersih_gr", "harga_beli", "kalori", "protein", "lemak", "karbo", "bdd"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v2.0")
nav = st.sidebar.radio("Menu Utama", ["Master Bahan Baku", "Master Item (Single Menu)", "Set Menu (Paket)", "Dashboard"])

# --- MODUL 1: MASTER BAHAN BAKU ---
if nav == "Master Bahan Baku":
    st.title("📦 Management & Kalkulasi Bahan Baku")
    
    # Form Input Bahan Baru
    with st.expander("➕ Tambah / Kalkulasi Bahan Baru", expanded=True):
        with st.form("input_bahan"):
            c1, c2, c3 = st.columns(3)
            nama_b = c1.text_input("Nama Bahan")
            uom = c2.selectbox("Satuan (UOM)", ["kg", "gr", "L", "ml", "pcs", "pack", "karung"])
            berat_gr = c3.number_input("Berat Bersih per Satuan (gram/ml)", min_value=0.0, help="Contoh: 1 kg isi 1000gr")
            
            c4, c5, c6 = st.columns(3)
            harga = c4.number_input("Harga Beli per Satuan (Rp)", min_value=0.0)
            bdd = c5.number_input("BDD (%)", min_value=1, max_value=100, value=100)
            
            st.markdown("---")
            st.write("**Input Nutrisi Dasar (per 100g)**")
            n1, n2, n3, n4 = st.columns(4)
            in_kal = n1.number_input("Kalori", min_value=0.0)
            in_pro = n2.number_input("Protein", min_value=0.0)
            in_lem = n3.number_input("Lemak", min_value=0.0)
            in_kar = n4.number_input("Karbo", min_value=0.0)
            
            submit_b = st.form_submit_button("Kalkulasi & Simpan Bahan")
            
            if submit_b:
                # Logika Kalkulasi Nutrisi Otomatis berdasarkan Berat yang diinput
                ratio = berat_gr / 100
                total_kal = (in_kal * ratio) * (bdd/100)
                total_pro = (in_pro * ratio) * (bdd/100)
                total_lem = (in_lem * ratio) * (bdd/100)
                total_kar = (in_kar * ratio) * (bdd/100)
                
                new_row = {
                    "nama": nama_b, "satuan_uom": uom, "berat_bersih_gr": berat_gr,
                    "harga_beli": harga, "kalori": round(total_kal, 2), 
                    "protein": round(total_pro, 2), "lemak": round(total_lem, 2), 
                    "karbo": round(total_kar, 2), "bdd": bdd
                }
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"Berhasil mengkalkulasi nutrisi untuk {nama_b} per {uom}")

    st.subheader("Data Master Bahan Baku")
    st.dataframe(st.session_state.db_bahan, use_container_width=True)
    
    if st.button("Clear Semua Data Bahan"):
        st.session_state.db_bahan = pd.DataFrame(columns=["nama", "satuan_uom", "berat_bersih_gr", "harga_beli", "kalori", "protein", "lemak", "karbo", "bdd"])
        st.rerun()

# --- MODUL 2: MASTER ITEM (SINGLE MENU) ---
elif nav == "Master Item (Single Menu)":
    st.title("🍳 Rakit Menu dari Master")
    if st.session_state.db_bahan.empty:
        st.warning("Input bahan baku di Master terlebih dahulu.")
    else:
        with st.form("buat_menu"):
            nama_m = st.text_input("Nama Item Menu")
            pilih_b = st.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())
            lanjut = st.form_submit_button("Proses Porsi")
            
        if pilih_b:
            st.subheader(f"Porsi Resep: {nama_m}")
            summary = {'kal':0, 'pro':0, 'lem':0, 'kar':0, 'cost':0}
            
            with st.form("porsi_detail"):
                for b in pilih_b:
                    data_b = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    qty = st.number_input(f"Jumlah {b} ({data_b['satuan_uom']})", min_value=0.0, step=0.1, key=f"q_{b}")
                    
                    # Kalkulasi Cost & Nutrisi Berdasarkan Satuan UOM
                    summary['kal'] += data_b['kalori'] * qty
                    summary['pro'] += data_b['protein'] * qty
                    summary['lem'] += data_b['lemak'] * qty
                    summary['kar'] += data_b['karbo'] * qty
                    summary['cost'] += data_b['harga_beli'] * qty
                
                simpan_m = st.form_submit_button("Simpan Item Master")
                if simpan_m:
                    st.session_state.db_menu.append({
                        "nama_menu": nama_m, "total_kalori": summary['kal'], 
                        "total_protein": summary['pro'], "total_lemak": summary['lem'], 
                        "total_karbo": summary['kar'], "total_hpp": summary['cost']
                    })
                    st.success(f"Menu {nama_m} Berhasil Disimpan!")

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
