import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.9", layout="wide")

# --- 1. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_master_paket' not in st.session_state:
    st.session_state.db_master_paket = pd.DataFrame(columns=["nama_paket", "rincian_isi", "total_hpp", "harga_jual", "total_kalori"])

# --- 2. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v10.9")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Master)", "4. Set Menu (Custom Paket)"])

# --- MODUL 1 & 2 (Database & Upload) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    search = st.text_input("🔍 Cari Nama Bahan...")
    df_disp = st.session_state.db_bahan
    if search: df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    edited_df = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic", key="edit_bahan_v109")
    if st.button("💾 Simpan Perubahan Database"):
        st.session_state.db_bahan = edited_df.fillna(0); st.success("Database diperbarui!")

elif nav == "2. Upload Data":
    st.title("📥 Upload Master Data")
    uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df_new = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping); df_new = df_new.fillna(0)
            if st.button("🚀 Jalankan Sinkronisasi"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Berhasil Sinkron!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (MASTER MENU) ---
elif nav == "3. Buat Resep (Master)":
    st.title("🍳 Recipe Builder")
    tab1, tab2 = st.tabs(["📝 Formulasi Resep", "📋 Buku Master Resep"])
    with tab1:
        if st.session_state.db_bahan.empty: st.warning("Database bahan kosong.")
        else:
            if "recipe_form_id" not in st.session_state: st.session_state.recipe_form_id = 0
            nama_resep = st.text_input("Nama Produk/Menu Matang", key=f"nm_{st.session_state.recipe_form_id}")
            items_pilih = st.multiselect("Pilih Komponen Mentah", st.session_state.db_bahan['nama'].tolist(), key=f"it_{st.session_state.recipe_form_id}")
            res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
            if items_pilih:
                for itm in items_pilih:
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == itm].iloc[0]
                    qty = st.number_input(f"Qty {itm} ({row['uom']})", min_value=0.0, step=0.01, key=f"q_{itm}_{st.session_state.recipe_form_id}")
                    gr_bersih = qty * float(row.get('berat', 1000))
                    ratio = (float(row.get('berat', 1000))/100) * (float(row.get('bdd', 100))/100)
                    res_calc['kal'] += float(row.get('kalori', 0)) * ratio * qty
                    res_calc['pro'] += float(row.get('protein', 0)) * ratio * qty
                    res_calc['lem'] += float(row.get('lemak', 0)) * ratio * qty
                    res_calc['kar'] += float(row.get('karbo', 0)) * ratio * qty
                    res_calc['cost'] += float(row.get('harga', 0)) * qty
                    res_calc['total_gr'] += gr_bersih
                st.divider()
                berat_matang = st.number_input("Berat Total Matang (Yield)", min_value=0.1, value=max(res_calc['total_gr'], 1.0), key=f"y_{st.session_state.recipe_form_id}")
                jml_porsi = st.number_input("Jumlah Porsi", min_value=1, value=1, key=f"p_{st.session_state.recipe_form_id}")
                if st.button("💾 SIMPAN RESEP & RESET"):
                    if nama_resep:
                        new_row = pd.DataFrame([{"nama": nama_resep, "berat_porsi_gr": berat_matang/jml_porsi, "kal_porsi": res_calc['kal']/jml_porsi, "pro_porsi": res_calc['pro']/jml_porsi, "lem_porsi": res_calc['lem']/jml_porsi, "kar_porsi": res_calc['kar']/jml_porsi, "hpp_porsi": res_calc['cost']/jml_porsi}])
                        st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_row], ignore_index=True)
                        st.session_state.recipe_form_id += 1; st.success("Tersimpan!"); st.rerun()
    with tab2:
        updated_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="ed_master_v109")
        if st.button("🗑️ Update / Hapus"): st.session_state.db_menu = updated_menu; st.rerun()

# --- MODUL 4: SET MENU (CUSTOM PORTION GRAMASI) ---
elif nav == "4. Set Menu (Custom Paket)":
    st.title("🍱 Custom Package Builder (Manual Gramasi)")
    tab_buat, tab_master = st.tabs(["🆕 Buat Paket", "🗄️ Database Paket"])
    
    with tab_buat:
        if st.session_state.db_menu.empty:
            st.warning("Buat Master Resep terlebih dahulu.")
        else:
            col1, col2 = st.columns([2, 1])
            nama_pkt = col1.text_input("Nama Paket", key="pkt_name_v109")
            margin = col2.slider("Target Food Cost (%)", 10, 50, 30, key="margin_v109")
            items = st.multiselect("Pilih Item Menu", st.session_state.db_menu['nama'].tolist(), key="pkt_items_v109")
            
            if items:
                st.markdown("### ✍️ Atur Gramasi Manual Per Item")
                st.info("Sistem akan menyesuaikan nutrisi & biaya berdasarkan gramasi yang Anda ketik di bawah.")
                
                final_rincian = []
                p_tot = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
                
                # Header Tabel Manual
                h1, h2, h3, h4 = st.columns([3, 2, 2, 3])
                h1.write("**Nama Menu**"); h2.write("**Berat Std (gr)**"); h3.write("**Berat Paket (gr)**"); h4.write("**HPP Pro-rata**")

                for itm in items:
                    d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                    
                    c1.write(f"🔹 {itm}")
                    c2.write(f"{d['berat_porsi_gr']:,.0f} g")
                    # Input Gramasi Manual
                    custom_gr = c3.number_input(f"Set Berat (gr) untuk {itm}", min_value=0.0, value=float(d['berat_porsi_gr']), step=1.0, key=f"custom_{itm}")
                    
                    # Hitung Ratio (Berat Manual / Berat Resep Master)
                    ratio = custom_gr / d['berat_porsi_gr'] if d['berat_porsi_gr'] > 0 else 0
                    
                    # Hitung Nutrisi & HPP Pro-rata
                    cost_pro = d['hpp_porsi'] * ratio
                    c4.write(f"Rp {cost_pro:,.0f}")
                    
                    p_tot['k'] += d['kal_porsi'] * ratio
                    p_tot['p'] += d['pro_porsi'] * ratio
                    p_tot['l'] += d['lem_porsi'] * ratio
                    p_tot['ka'] += d['kar_porsi'] * ratio
                    p_tot['h'] += cost_pro
                    p_tot['b'] += custom_gr
                    
                    final_rincian.append(f"{itm} ({custom_gr}g)")

                st.divider()
                s1, s2, s3 = st.columns(3)
                s1.metric("Total HPP Paket", f"Rp {p_tot['h']:,.0f}")
                harga_jual = p_tot['h']/(margin/100)
                s2.metric("Saran Harga Jual", f"Rp {harga_jual:,.0f}")
                s3.metric("Total Kalori", f"{p_tot['k']:,.1f} kkal")
                
                # Tabel Detail Nutrisi Lengkap
                st.markdown("#### Detail Nutrisi Paket (Custom)")
                nutri_df = pd.DataFrame([{
                    "Protein (g)": round(p_tot['p'], 1),
                    "Lemak (g)": round(p_tot['l'], 1),
                    "Karbo (g)": round(p_tot['ka'], 1),
                    "Total Berat (g)": round(p_tot['b'], 1)
                }])
                st.table(nutri_df)

                if st.button("💾 SIMPAN PAKET CUSTOM KE MASTER"):
                    if nama_pkt:
                        new_pkt = pd.DataFrame([{
                            "nama_paket": nama_pkt, 
                            "rincian_isi": ", ".join(final_rincian),
                            "total_hpp": p_tot['h'], 
                            "harga_jual": harga_jual, 
                            "total_kalori": p_tot['k']
                        }])
                        st.session_state.db_master_paket = pd.concat([st.session_state.db_master_paket, new_pkt], ignore_index=True)
                        st.success(f"Paket '{nama_pkt}' Berhasil Disimpan!"); st.rerun()

    with tab_master:
        st.subheader("🗄️ Database Paket Custom")
        if st.session_state.db_master_paket.empty:
            st.info("Belum ada paket yang disimpan.")
        else:
            edited_pkt = st.data_editor(st.session_state.db_master_paket, use_container_width=True, num_rows="dynamic", key="ed_paket_v109")
            if st.button("🗑️ Update / Hapus Paket"):
                st.session_state.db_master_paket = edited_pkt; st.rerun()
