import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro 1500+", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    # Memasukkan beberapa data awal agar aplikasi tidak kosong
    initial_data = [
        {"nama": "Beras giling, mentah", "kalori": 357, "protein": 8.4, "lemak": 1.7, "karbo": 77.1, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 0},
        {"nama": "Ayam Paha", "kalori": 165, "protein": 31, "lemak": 3.6, "karbo": 0, "bdd": 100, "uom": "Kg", "berat": 1000, "harga": 55000}
    ]
    st.session_state.db_bahan = pd.DataFrame(initial_data)

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Scalable v7.0")
nav = st.sidebar.radio("Navigasi", ["Data Master & Harga", "Upload Database Massal", "Buat Menu Satuan", "Set Menu (Paket)"])

# --- MODUL 1: DATA MASTER & HARGA ---
if nav == "Data Master & Harga":
    st.title("📂 Database Bahan Baku")
    st.write(f"Total Database: {len(st.session_state.db_bahan)} item")
    
    # Fitur Pencarian untuk memudahkan navigasi 1500 item
    search_query = st.text_input("🔍 Cari Bahan (Contoh: Beras, Cabai, Bawang...)")
    
    df_to_edit = st.session_state.db_bahan
    if search_query:
        df_to_edit = df_to_edit[df_to_edit['nama'].str.contains(search_query, case=False)]

    st.info("Anda bisa mengedit harga langsung pada tabel di bawah ini.")
    edited_df = st.data_editor(
        df_to_edit,
        column_config={
            "harga": st.column_config.NumberColumn("Harga Beli (Rp)", format="Rp %d"),
            "berat": "Berat Bersih (gr)",
            "uom": "Satuan"
        },
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 Simpan Perubahan"):
        # Menggabungkan kembali data yang diedit ke database utama
        st.session_state.db_bahan.update(edited_df)
        st.success("Perubahan berhasil disimpan ke database!")

# --- MODUL 2: UPLOAD DATABASE MASSAL ---
elif nav == "Upload Database Massal":
    st.title("📥 Import Database (Scale-Up)")
    st.markdown("""
    Gunakan modul ini untuk menambah hingga ribuan data sekaligus. 
    **Pastikan file CSV/Excel memiliki kolom:** `nama, kalori, protein, lemak, karbo, bdd, uom, berat, harga`.
    """)
    
    up_file = st.file_uploader("Pilih File Master Nutrisi", type=["csv", "xlsx"])
    
    if up_file:
    try:
        df_new = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
        
        # Bersihkan nama kolom dari spasi dan karakter aneh
        df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
        
        # LOGIKA MAPPING OTOMATIS (Solusi untuk KeyError 'uom')
        # Jika sistem cari 'uom' tapi di file namanya 'satuan_beli_uom', kita samakan.
        if 'satuan_beli_uom' in df_new.columns and 'uom' not in df_new.columns:
            df_new = df_new.rename(columns={'satuan_beli_uom': 'uom'})
        
        # Jika kolom 'berat' tidak ada tapi adanya 'berat_bersih_per_uom_gr'
        if 'berat_bersih_per_uom_gr' in df_new.columns and 'berat' not in df_new.columns:
            df_new = df_new.rename(columns={'berat_bersih_per_uom_gr': 'berat'})
            
        # Jika kolom 'harga' tidak ada tapi adanya 'harga_beli_per_uom'
        if 'harga_beli_per_uom' in df_new.columns and 'harga' not in df_new.columns:
            df_new = df_new.rename(columns={'harga_beli_per_uom': 'harga'})

        # Isi data kosong dengan 0
        df_new = df_new.fillna(0)
        
        if st.button("🚀 Konfirmasi Sinkronisasi"):
            st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
            st.success("Data Sinkron!")
            st.rerun()
            
    except Exception as e:
        st.error(f"Gagal memproses kolom: {e}")

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
