import streamlit as st
import pandas as pd

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro Nasional", layout="wide")

# --- DATABASE STANDAR NASIONAL (MOCKUP TKPI) ---
# Anda bisa menambahkan ribuan baris di sini sesuai buku TKPI Kemenkes
data_tkpi = {
    "Ayam (Paha)": {"kalori": 165, "protein": 31.0, "lemak": 3.6, "karbo": 0.0, "bdd": 100},
    "Ayam (Dada)": {"kalori": 150, "protein": 33.0, "lemak": 1.2, "karbo": 0.0, "bdd": 100},
    "Beras Putih": {"kalori": 357, "protein": 8.4, "lemak": 1.7, "karbo": 77.1, "bdd": 100},
    "Telur Ayam": {"kalori": 154, "protein": 12.4, "lemak": 10.8, "karbo": 0.7, "bdd": 90},
    "Minyak Sawit": {"kalori": 862, "protein": 0.0, "lemak": 100.0, "karbo": 0.0, "bdd": 100},
    "Daging Sapi (Murni)": {"kalori": 249, "protein": 18.0, "lemak": 14.0, "karbo": 0.0, "bdd": 100},
    "Ikan Kembung": {"kalori": 112, "protein": 21.4, "lemak": 2.3, "karbo": 0.0, "bdd": 80},
    "Tempe Kedelai": {"kalori": 201, "protein": 20.8, "lemak": 8.8, "karbo": 13.5, "bdd": 100},
}

# --- DATABASE STATE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "satuan_uom", "berat_bersih_gr", "harga_beli", "total_kalori", "total_protein", "total_lemak", "total_karbo", "bdd"
    ])

# --- SIDEBAR ---
st.sidebar.title("NutriCost Pro v4.0")
nav = st.sidebar.radio("Menu Utama", ["Master Bahan Baku", "Master Item (Single Menu)", "Set Menu (Paket)"])

# --- MODUL 1: MASTER BAHAN BAKU ---
if nav == "Master Bahan Baku":
    st.title("📦 Management Bahan Baku (Standar Nasional)")
    
    with st.expander("➕ Tambah Bahan dari Tabel Standar", expanded=True):
        c1, c2 = st.columns([2, 1])
        
        # PILIH DARI TABEL STANDAR
        pilihan_tkpi = c1.selectbox("Pilih Jenis Bahan (Database TKPI)", ["Input Manual"] + list(data_tkpi.keys()))
        
        nama_b = c1.text_input("Nama Spesifik Bahan Anda", value=pilihan_tkpi if pilihan_tkpi != "Input Manual" else "")
        
        # Ambil data dasar jika user memilih dari list
        if pilihan_tkpi != "Input Manual":
            ref_data = data_tkpi[pilihan_tkpi]
            def_kal, def_pro, def_lem, def_kar, def_bdd = ref_data['kalori'], ref_data['protein'], ref_data['lemak'], ref_data['karbo'], ref_data['bdd']
        else:
            def_kal = def_pro = def_lem = def_kar = 0.0
            def_bdd = 100

        c3, c4, c5 = st.columns(3)
        uom = c3.selectbox("Satuan (UOM)", ["kg", "gr", "L", "ml", "pcs", "pack"])
        berat_gr = c4.number_input("Berat per Satuan (gr/ml)", min_value=0.01, value=1000.0 if uom == "kg" else 1.0)
        harga = c5.number_input("Harga Beli per Satuan (Rp)", min_value=0.0)

        st.markdown("---")
        st.write("**Data Nutrisi Dasar (per 100g)**")
        n1, n2, n3, n4, n5 = st.columns(5)
        
        # Kolom ini otomatis terisi dari tabel standar
        in_kal = n1.number_input("Kalori Dasar", value=float(def_kal))
        in_pro = n2.number_input("Protein Dasar", value=float(def_pro))
        in_lem = n3.number_input("Lemak Dasar", value=float(def_lem))
        in_kar = n4.number_input("Karbo Dasar", value=float(def_kar))
        in_bdd = n5.number_input("BDD %", value=int(def_bdd))

        if st.button("🔄 Kalkulasi & Simpan ke Master"):
            # Rumus Kalkulasi
            ratio = berat_gr / 100
            bdd_fac = in_bdd / 100
            
            final_kal = in_kal * ratio * bdd_fac
            final_pro = in_pro * ratio * bdd_fac
            final_lem = in_lem * ratio * bdd_fac
            final_kar = in_kar * ratio * bdd_fac
            
            new_row = {
                "nama": nama_b, "satuan_uom": uom, "berat_bersih_gr": berat_gr,
                "harga_beli": harga, "total_kalori": round(final_kal, 2), 
                "total_protein": round(final_pro, 2), "total_lemak": round(final_lem, 2), 
                "total_karbo": round(final_kar, 2), "bdd": in_bdd
            }
            st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Berhasil menyimpan {nama_b} dengan data standar nasional!")
            st.rerun()

    st.subheader("📋 Master Data Bahan")
    st.dataframe(st.session_state.db_bahan, use_container_width=True)
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
