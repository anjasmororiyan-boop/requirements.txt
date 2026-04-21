import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v6.0", layout="wide")

# --- DATABASE HARDCODE (DATA NASIONAL LENGKAP) ---
if 'db_bahan' not in st.session_state:
    raw_data = [
        {"nama": "Beras giling, mentah", "kalori": 357, "protein": 8.4, "lemak": 1.7, "karbo": 77.1, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 15000},
        {"nama": "Beras giling var pelita, mentah", "kalori": 369, "protein": 9.5, "lemak": 1.4, "karbo": 77.1, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Beras giling var rojolele, mentah", "kalori": 357, "protein": 8.4, "lemak": 1.7, "karbo": 77.1, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Beras hitam, mentah", "kalori": 351, "protein": 8.0, "lemak": 1.3, "karbo": 76.9, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Beras jagung kuning, kering, mentah", "kalori": 358, "protein": 5.5, "lemak": 0.1, "karbo": 82.7, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Beras jagung putih, kering, mentah", "kalori": 307, "protein": 4.8, "lemak": 0.1, "karbo": 71.8, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Beras ketan hitam tumbuk, mentah", "kalori": 360, "protein": 8.0, "lemak": 2.3, "karbo": 74.5, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Beras ketan putih tumbuk, mentah", "kalori": 361, "protein": 7.4, "lemak": 0.8, "karbo": 78.4, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Asam payak, segar", "kalori": 135, "protein": 0.8, "lemak": 0.4, "karbo": 32.1, "bdd": 95, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Bawang merah, segar", "kalori": 46, "protein": 1.5, "lemak": 0.3, "karbo": 9.2, "bdd": 90, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Bawang putih, segar", "kalori": 112, "protein": 4.5, "lemak": 0.2, "karbo": 23.1, "bdd": 88, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Boros kunci, segar", "kalori": 40, "protein": 1.0, "lemak": 0.8, "karbo": 7.2, "bdd": 80, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Boros laja (lengkuas), segar", "kalori": 26, "protein": 1.0, "lemak": 0.3, "karbo": 4.7, "bdd": 80, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Cabai gembor merah, segar", "kalori": 38, "protein": 1.6, "lemak": 0.8, "karbo": 6.3, "bdd": 89, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Cabai hijau, segar", "kalori": 26, "protein": 0.7, "lemak": 0.3, "karbo": 5.2, "bdd": 82, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Cabai merah, kering", "kalori": 367, "protein": 15.9, "lemak": 6.2, "karbo": 61.8, "bdd": 85, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Cabai merah, segar", "kalori": 36, "protein": 1.0, "lemak": 0.3, "karbo": 7.3, "bdd": 85, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Cabai rawit, segar", "kalori": 120, "protein": 4.7, "lemak": 2.4, "karbo": 19.9, "bdd": 85, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Ayam Paha", "kalori": 165, "protein": 31.0, "lemak": 3.6, "karbo": 0.0, "bdd": 100, "uom": "kg", "berat": 1000, "harga": 55000},
        {"nama": "Daging Sapi", "kalori": 249, "protein": 18.0, "lemak": 14.0, "karbo": 0.0, "bdd": 100, "uom": "kg", "berat": 1000, "harga": 120000},
        {"nama": "Telur Ayam", "kalori": 154, "protein": 12.4, "lemak": 10.8, "karbo": 0.7, "bdd": 90, "uom": "kg", "berat": 1000, "harga": 28000},
        {"nama": "Minyak Goreng", "kalori": 862, "protein": 0.0, "lemak": 100.0, "karbo": 0.0, "bdd": 100, "uom": "L", "berat": 1000, "harga": 18000}
    ]
    st.session_state.db_bahan = pd.DataFrame(raw_data)

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- NAVIGASI ---
st.sidebar.title("NutriCost v6.0")
nav = st.sidebar.radio("Navigasi", ["Database & Harga", "Master Item (Single Menu)", "Set Menu (Paket)"])

# --- MODUL 1: DATABASE ---
if nav == "Database & Harga":
    st.title("📂 Database Bahan Baku Nasional")
    st.info("Edit kolom 'harga' langsung pada tabel untuk menghitung HPP.")
    
    # Editor tabel untuk update harga secara fleksibel
    edited_df = st.data_editor(
        st.session_state.db_bahan,
        column_config={
            "harga": st.column_config.NumberColumn("Harga Beli (Rp)", format="Rp %d"),
            "uom": "Satuan",
            "berat": "Berat Bersih (gr)",
            "bdd": "BDD %"
        },
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 Simpan Perubahan Data"):
        st.session_state.db_bahan = edited_df.fillna(0)
        st.success("Database berhasil diperbarui!")

# --- MODUL 2: SINGLE MENU ---
elif nav == "Master Item (Single Menu)":
    st.title("🍳 Pembuatan Single Menu")
    
    with st.form("form_item"):
        nama_m = st.text_input("Nama Menu")
        pilih_b = st.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())
        submit_pilih = st.form_submit_button("Lanjut")
    
    if pilih_b:
        total = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0}
        with st.form("form_porsi"):
            for b in pilih_b:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                qty = st.number_input(f"Porsi {b} ({row['uom']})", min_value=0.0, step=0.01)
                
                # Kalkulasi: (Dasar/100) * Berat_UOM * BDD_Fac * Qty
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

# --- MODUL 3: SET MENU ---
elif nav == "Set Menu (Paket)":
    st.title("🍱 Set Menu (Paket)")
    if not st.session_state.db_menu:
        st.warning("Belum ada Master Item.")
    else:
        nama_p = st.text_input("Nama Paket")
        pilihan = st.multiselect("Pilih Item Master", [m['nama'] for m in st.session_state.db_menu])
        
        if pilihan:
            set_res = {'kal': 0, 'pro': 0, 'lem': 0, 'kar': 0, 'hpp': 0}
            for p in pilihan:
                m_data = next(item for item in st.session_state.db_menu if item["nama"] == p)
                set_res['kal'] += m_data['kal']; set_res['pro'] += m_data['pro']
                set_res['lem'] += m_data['lem']; set_res['kar'] += m_data['kar']
                set_res['hpp'] += m_data['hpp']
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Energi", f"{set_res['kal']:.0f} kkal")
            c2.metric("HPP", f"Rp {set_res['hpp']:,.0f}")
            c3.metric("Harga Jual (FC 30%)", f"Rp {set_res['hpp']/0.3:,.0f}")
            
            fig = px.pie(values=[set_res['pro'], set_res['lem'], set_res['kar']], 
                         names=['Protein', 'Lemak', 'Karbo'], title="Komposisi Gizi")
            st.plotly_chart(fig)
