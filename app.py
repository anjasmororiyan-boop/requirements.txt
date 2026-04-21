import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.7", layout="wide")

# --- 1. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# --- 2. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v10.7")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Master)", "4. Set Menu (Paket)"])

# --- MODUL 1 & 2 (Database & Upload) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    search = st.text_input("🔍 Cari Nama Bahan...")
    df_disp = st.session_state.db_bahan
    if search:
        df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    edited_df = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic", key="edit_bahan_table")
    if st.button("💾 Simpan Perubahan Database"):
        st.session_state.db_bahan = edited_df.fillna(0)
        st.success("Database berhasil diperbarui!")

elif nav == "2. Upload Data":
    st.title("📥 Upload Master Data")
    uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df_new = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping)
            if st.button("🚀 Jalankan Sinkronisasi Massal"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Berhasil Sinkron!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (Sama Seperti v10.6) ---
elif nav == "3. Buat Resep (Master)":
    st.title("🍳 Recipe Builder")
    tab_resep, tab_list = st.tabs(["📝 Formulasi Resep", "📋 Buku Master Resep"])
    with tab_resep:
        if st.session_state.db_bahan.empty: st.warning("Database bahan kosong.")
        else:
            nama_resep = st.text_input("Nama Produk/Menu Matang", key="inp_nama_resep")
            items_pilih = st.multiselect("Pilih Komponen Mentah", st.session_state.db_bahan['nama'].tolist(), key="inp_pilih_bahan")
            res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
            if items_pilih:
                for item in items_pilih:
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == item].iloc[0]
                    qty_val = st.number_input(f"Qty {item} ({row['uom']})", min_value=0.0, step=0.01, key=f"qty_{item}")
                    gr_bersih = qty_val * float(row.get('berat', 1000))
                    ratio = (float(row.get('berat', 1000))/100) * (float(row.get('bdd', 100))/100)
                    res_calc['kal'] += float(row.get('kalori', 0)) * ratio * qty_val
                    res_calc['pro'] += float(row.get('protein', 0)) * ratio * qty_val
                    res_calc['lem'] += float(row.get('lemak', 0)) * ratio * qty_val
                    res_calc['kar'] += float(row.get('karbo', 0)) * ratio * qty_val
                    res_calc['cost'] += float(row.get('harga', 0)) * qty_val
                    res_calc['total_gr'] += gr_bersih
                berat_matang = st.number_input("Berat Total Matang (Yield)", min_value=0.1, value=max(res_calc['total_gr'], 1.0))
                jml_porsi = st.number_input("Jumlah Porsi", min_value=1, value=1)
                if st.button("💾 SIMPAN RESEP"):
                    new_row = pd.DataFrame([{"nama": nama_resep, "berat_porsi_gr": berat_matang/jml_porsi, "kal_porsi": res_calc['kal']/jml_porsi, "pro_porsi": res_calc['pro']/jml_porsi, "lem_porsi": res_calc['lem']/jml_porsi, "kar_porsi": res_calc['kar']/jml_porsi, "hpp_porsi": res_calc['cost']/jml_porsi}])
                    st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_row], ignore_index=True)
                    st.success("Tersimpan!"); st.rerun()

# --- MODUL 4: SET MENU (UPDATED DENGAN RINCIAN DETAIL) ---
elif nav == "4. Set Menu (Paket)":
    st.title("🍱 Aggregator Set Menu (Paket Gabungan)")
    
    if st.session_state.db_menu.empty:
        st.warning("Buat Master Resep terlebih dahulu di menu nomor 3.")
    else:
        with st.container():
            col1, col2 = st.columns([2, 1])
            nama_pkt = col1.text_input("Nama Paket Gabungan", placeholder="Contoh: Paket Box Lunch A")
            margin = col2.slider("Target Food Cost (%)", 10, 50, 30)
            items = st.multiselect("Pilih Item dari Master Resep", st.session_state.db_menu['nama'].tolist())
        
        if items:
            st.markdown("### 📋 Rincian Detail Isi Paket")
            
            # Tabel Rincian Per Item dalam Paket
            rincian_data = []
            p_res = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
            
            for itm in items:
                d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                # Simpan rincian untuk tabel
                rincian_data.append({
                    "Item Menu": d['nama'],
                    "Berat (gr)": f"{d['berat_porsi_gr']:,.1f}",
                    "HPP (Rp)": f"{d['hpp_porsi']:,.0f}",
                    "Kalori": f"{d['kal_porsi']:,.1f}",
                    "Protein (g)": f"{d['pro_porsi']:,.1f}",
                    "Lemak (g)": f"{d['lem_porsi']:,.1f}",
                    "Karbo (g)": f"{d['kar_porsi']:,.1f}"
                })
                # Akumulasi Total
                p_res['k']+=d['kal_porsi']; p_res['p']+=d['pro_porsi']; p_res['l']+=d['lem_porsi']
                p_res['ka']+=d['kar_porsi']; p_res['h']+=d['hpp_porsi']; p_res['b']+=d['berat_porsi_gr']
            
            # Tampilkan Tabel Rincian
            st.table(pd.DataFrame(rincian_data))
            
            st.divider()
            st.subheader(f"📊 Ringkasan Total: {nama_pkt}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Energi", f"{p_res['k']:,.0f} kkal")
            m2.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
            m3.metric("Saran Harga Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
            m4.metric("Berat Paket", f"{p_res['b']:,.1f} gr")

            # Chart Perbandingan Gizi
            st.plotly_chart(px.pie(
                values=[p_res['p'], p_res['l'], p_res['ka']], 
                names=['Protein (g)', 'Lemak (g)', 'Karbohidrat (g)'], 
                title=f"Komposisi Makronutrisi: {nama_pkt}",
                hole=0.4
            ))
