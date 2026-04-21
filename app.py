import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.6", layout="wide")

# --- 1. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# --- 2. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v10.6")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Recipe Master)", "4. Set Menu (Paket)"])

# --- MODUL 1: DATABASE BAHAN ---
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

# --- MODUL 2: UPLOAD DATA ---
elif nav == "2. Upload Data":
    st.title("📥 Upload Master Data Bahan")
    uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_new = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_new = pd.read_excel(uploaded_file)
            
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping)
            
            if st.button("🚀 Jalankan Sinkronisasi Massal"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Berhasil Disinkronkan!"); st.rerun()
        except Exception as e: st.error(f"Error Upload: {e}")

# --- MODUL 3: BUAT RESEP (STABLE RESET & NO ERROR) ---
elif nav == "3. Buat Resep (Recipe Master)":
    st.title("🍳 Recipe Builder & Automation")
    
    tab_resep, tab_list = st.tabs(["📝 Formulasi Resep", "📋 Buku Master Resep"])
    
    with tab_resep:
        if st.session_state.db_bahan.empty:
            st.warning("Database bahan kosong. Harap upload data terlebih dahulu.")
        else:
            # Menggunakan kontainer kosong untuk memudahkan reset tampilan
            form_container = st.container()
            
            with form_container:
                col_name, col_select = st.columns([2, 2])
                # Menambahkan key dinamis berdasarkan jumlah data agar bisa di-reset dengan rerun
                nama_resep = col_name.text_input("Nama Produk/Menu Matang", key="inp_nama_resep")
                items_pilih = col_select.multiselect("Pilih Komponen Mentah", st.session_state.db_bahan['nama'].tolist(), key="inp_pilih_bahan")

                res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}

                if items_pilih:
                    st.markdown("---")
                    h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
                    h1.write("**Item Bahan**"); h2.write("**UOM**"); h3.write("**Qty**"); h4.write("**Gramasi**")
                    
                    for item in items_pilih:
                        try:
                            row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == item].iloc[0]
                            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                            c1.write(f"🔹 {item}")
                            c2.write(row.get('uom', 'kg'))
                            
                            # Input Qty
                            qty_val = c3.number_input(f"Qty {item}", min_value=0.0, step=0.01, key=f"qty_{item}")
                            
                            # Kalkulasi per Baris
                            berat_ref = float(row.get('berat', 1000))
                            gram_bersih = qty_val * berat_ref
                            c4.write(f"**{gram_bersih:,.1f} g**")
                            
                            # Akumulasi
                            bdd_val = float(row.get('bdd', 100)) / 100
                            ratio = (berat_ref / 100) * bdd_val
                            res_calc['kal'] += float(row.get('kalori', 0)) * ratio * qty_val
                            res_calc['pro'] += float(row.get('protein', 0)) * ratio * qty_val
                            res_calc['lem'] += float(row.get('lemak', 0)) * ratio * qty_val
                            res_calc['kar'] += float(row.get('karbo', 0)) * ratio * qty_val
                            res_calc['cost'] += float(row.get('harga', 0)) * qty_val
                            res_calc['total_gr'] += gram_bersih
                        except: continue

                    st.divider()
                    st.subheader("⚖️ Yield & Analisis Porsi")
                    f1, f2, f3 = st.columns(3)
                    f1.metric("Total Berat Mentah", f"{res_calc['total_gr']:,.0f} g")
                    berat_matang = f2.number_input("Berat Total Matang (Yield)", min_value=0.1, value=max(res_calc['total_gr'], 1.0))
                    jml_porsi = f3.number_input("Jumlah Porsi", min_value=1, value=1)
                    
                    # Ringkasan Akhir
                    berat_porsi = berat_matang / jml_porsi
                    hpp_porsi = res_calc['cost'] / jml_porsi
                    st.info(f"💡 **Hasil:** 1 Porsi = {berat_porsi:,.1f} g | HPP = Rp {hpp_porsi:,.0f}")

                    # TOMBOL SIMPAN (Di luar form agar lebih stabil)
                    if st.button("💾 SIMPAN RESEP & BERSIHKAN FORM"):
                        if not nama_resep:
                            st.error("Nama Menu wajib diisi!")
                        elif res_calc['total_gr'] <= 0:
                            st.error("Gramasi bahan tidak boleh nol!")
                        else:
                            # Proses simpan data
                            new_row = pd.DataFrame([{
                                "nama": nama_resep,
                                "berat_porsi_gr": round(berat_porsi, 2),
                                "kal_porsi": round(res_calc['kal'] / jml_porsi, 2),
                                "pro_porsi": round(res_calc['pro'] / jml_porsi, 2),
                                "lem_porsi": round(res_calc['lem'] / jml_porsi, 2),
                                "kar_porsi": round(res_calc['kar'] / jml_porsi, 2),
                                "hpp_porsi": round(hpp_porsi, 2)
                            }])
                            st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_row], ignore_index=True)
                            st.success(f"Resep '{nama_resep}' berhasil disimpan!")
                            # Force rerun untuk membersihkan input
                            st.rerun()

    with tab_list:
        st.subheader("Buku Master Resep Jadi")
        if not st.session_state.db_menu.empty:
            updated_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="master_resep_editor")
            if st.button("🗑️ Hapus / Update Resep"):
                st.session_state.db_menu = updated_menu
                st.rerun()
        else:
            st.info("Belum ada resep matang yang tersimpan.")

# --- MODUL 4: SET MENU (PAKET) ---
elif nav == "4. Set Menu (Paket)":
    st.title("🍱 Aggregator Set Menu")
    if st.session_state.db_menu.empty:
        st.warning("Buat Master Resep terlebih dahulu di Tahap 3.")
    else:
        with st.container():
            nama_pkt = st.text_input("Nama Paket Gabungan")
            items = st.multiselect("Pilih Item dari Master Resep", st.session_state.db_menu['nama'].tolist())
            margin = st.slider("Target Food Cost (%)", 10, 50, 30)
        
        if items:
            p_res = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
            for itm in items:
                d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                p_res['k']+=d['kal_porsi']; p_res['p']+=d['pro_porsi']; p_res['l']+=d['lem_porsi']
                p_res['ka']+=d['kar_porsi']; p_res['h']+=d['hpp_porsi']; p_res['b']+=d['berat_porsi_gr']
            
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Energi Paket", f"{p_res['k']:.0f} kkal")
            m2.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
            m3.metric("Saran Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
            m4.metric("Berat Paket", f"{p_res['b']:.0f} g")
