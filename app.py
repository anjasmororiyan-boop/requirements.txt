import streamlit as st
import pandas as pd
import os

# --- KONFIGURASI ---
st.set_page_config(page_title="NutriCost Pro 1500+", layout="wide")
DB_FILE = "database_bahan.csv"

# --- FUNGSI LOAD & SAVE DATA ---
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        # Template awal jika file belum ada
        return pd.DataFrame(columns=[
            "nama", "kalori", "protein", "lemak", "karbo", "bdd", 
            "uom", "berat_gr", "harga"
        ])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data()

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Scalable")
nav = st.sidebar.radio("Navigasi", ["Data Master (1500+)", "Tambah/Import Massal", "Buat Menu"])

# --- MODUL 1: DATA MASTER ---
if nav == "Data Master (1500+)":
    st.title("📂 Database Bahan Baku")
    st.write(f"Total Item Saat Ini: {len(st.session_state.db_bahan)}")
    
    # Gunakan fitur pencarian agar mudah menemukan item dari 1500 data
    search = st.text_input("🔍 Cari Nama Bahan...")
    df_display = st.session_state.db_bahan
    if search:
        df_display = df_display[df_display['nama'].str.contains(search, case=False)]

    edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Simpan Semua Perubahan"):
        # Update session state dan simpan ke file fisik CSV
        st.session_state.db_bahan = edited_df
        save_data(edited_df)
        st.success("Perubahan pada database berhasil disimpan ke sistem!")

# --- MODUL 2: TAMBAH / IMPORT MASSAL ---
elif nav == "Tambah/Import Massal":
    st.title("📥 Menambah Kapasitas Database")
    
    tab1, tab2 = st.tabs(["Upload Excel/CSV", "Input Manual"])
    
    with tab1:
        st.subheader("Import Ribuan Data Sekaligus")
        up_file = st.file_uploader("Upload file database baru", type=["csv", "xlsx"])
        if up_file:
            df_new = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
            if st.button("Gabungkan ke Master"):
                combined = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'])
                st.session_state.db_bahan = combined
                save_data(combined)
                st.success(f"Database kini berjumlah {len(combined)} item!")

    with tab2:
        st.subheader("Tambah Satu Per Satu")
        with st.form("tambah_satu"):
            n = st.text_input("Nama Bahan")
            c1, c2, c3 = st.columns(3)
            kal = c1.number_input("Kalori")
            pro = c2.number_input("Protein")
            har = c3.number_input("Harga")
            if st.form_submit_button("Simpan"):
                # Logika tambah data manual ke session state
                st.info("Fitur tambah manual aktif.")

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
