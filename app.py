import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v11.0", layout="wide")

# --- 1. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_master_paket' not in st.session_state:
    st.session_state.db_master_paket = pd.DataFrame(columns=["nama_paket", "rincian_isi", "total_hpp", "total_kalori"])

# --- 2. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v11.0")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Master)", "4. Set Menu (Custom Paket)"])

# --- MODUL 1 & 2 (Database & Upload - Tetap) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    search = st.text_input("🔍 Cari Nama Bahan...")
    df_disp = st.session_state.db_bahan
    if search: df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    edited_df = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic", key="edit_bahan_v11")
    if st.button("💾 Simpan Perubahan"):
        st.session_state.db_bahan = edited_df.fillna(0); st.success("Tersimpan!")

elif nav == "2. Upload Data":
    st.title("📥 Upload Master Data")
    uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df_new = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping).fillna(0)
            if st.button("🚀 Jalankan Sinkronisasi"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Sinkronisasi Berhasil!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (LOGIKA GIZI DIPERBAIKI) ---
elif nav == "3. Buat Resep (Master)":
    st.title("🍳 Recipe Builder (Precision Nutrition)")
    
    if st.session_state.db_bahan.empty:
        st.warning("Database bahan kosong.")
    else:
        if "recipe_form_id" not in st.session_state: st.session_state.recipe_form_id = 0
        
        nama_resep = st.text_input("Nama Produk", key=f"nm_{st.session_state.recipe_form_id}")
        items_pilih = st.multiselect("Pilih Komponen", st.session_state.db_bahan['nama'].tolist(), key=f"it_{st.session_state.recipe_form_id}")
        
        if items_pilih:
            st.markdown("### 📋 Rincian Gramasi & Nutrisi Mentah")
            res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
            
            h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
            h1.write("**Bahan**"); h2.write("**UOM**"); h3.write("**Qty**"); h4.write("**Berat (g)**")

            for itm in items_pilih:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == itm].iloc[0]
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"🔹 {itm}"); c2.write(row['uom'])
                qty = c3.number_input(f"Qty {itm}", min_value=0.0, step=0.01, key=f"q_{itm}_{st.session_state.recipe_form_id}")
                
                # --- KALKULASI AKURAT ---
                berat_uom = float(row['berat'])
                gr_mentah = qty * berat_uom
                c4.write(f"{gr_mentah:,.1f} g")
                
                # Rumus: (Berat/100) * (BDD/100) * Nutrisi_Dasar
                factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
                
                res_calc['kal'] += float(row['kalori']) * factor
                res_calc['pro'] += float(row['protein']) * factor
                res_calc['lem'] += float(row['lemak']) * factor
                res_calc['kar'] += float(row['karbo']) * factor
                res_calc['cost'] += float(row['harga']) * qty
                res_calc['total_gr'] += gr_mentah

            st.divider()
            f1, f2, f3 = st.columns(3)
            f1.metric("Total Berat Mentah", f"{res_calc['total_gr']:,.1f} g")
            berat_matang = f2.number_input("Berat Matang (Yield)", min_value=0.1, value=max(res_calc['total_gr'], 1.0))
            jml_porsi = f3.number_input("Jumlah Porsi", min_value=1, value=1)
            
            # HASIL PER PORSI
            st.success(f"**Gizi Per Porsi:** {res_calc['kal']/jml_porsi:,.1f} kkal | Pro: {res_calc['pro']/jml_porsi:,.1f}g | Lemak: {res_calc['lem']/jml_porsi:,.1f}g | Karbo: {res_calc['kar']/jml_porsi:,.1f}g")

            if st.button("💾 SIMPAN KE MASTER"):
                new_row = pd.DataFrame([{
                    "nama": nama_resep, "berat_porsi_gr": berat_matang/jml_porsi,
                    "kal_porsi": res_calc['kal']/jml_porsi, "pro_porsi": res_calc['pro']/jml_porsi,
                    "lem_porsi": res_calc['lem']/jml_porsi, "kar_porsi": res_calc['kar']/jml_porsi,
                    "hpp_porsi": res_calc['cost']/jml_porsi
                }])
                st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_row], ignore_index=True)
                st.session_state.recipe_form_id += 1; st.rerun()

# --- MODUL 4: SET MENU (CUSTOM PORTION FIX) ---
elif nav == "4. Set Menu (Custom Paket)":
    st.title("🍱 Custom Package Builder")
    if st.session_state.db_menu.empty:
        st.warning("Buat Master Resep dulu.")
    else:
        nama_pkt = st.text_input("Nama Paket")
        items = st.multiselect("Pilih Item Menu", st.session_state.db_menu['nama'].tolist())
        
        if items:
            st.markdown("### ✍️ Atur Gramasi Manual")
            p_tot = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
            
            for itm in items:
                d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"🔹 {itm}")
                # User mengisi gramasi matang yang diinginkan dalam paket
                custom_gr = c2.number_input(f"Gramasi Matang (gr) - {itm}", min_value=0.0, value=float(d['berat_porsi_gr']), key=f"c_{itm}")
                
                # Hitung Rasio terhadap porsi standar resep
                ratio = custom_gr / d['berat_porsi_gr'] if d['berat_porsi_gr'] > 0 else 0
                
                # Pro-rata gizi & cost
                p_tot['k'] += d['kal_porsi'] * ratio
                p_tot['p'] += d['pro_porsi'] * ratio
                p_tot['l'] += d['lem_porsi'] * ratio
                p_tot['ka'] += d['kar_porsi'] * ratio
                p_tot['h'] += d['hpp_porsi'] * ratio
                p_tot['b'] += custom_gr
            
            st.divider()
            st.subheader("📊 Hasil Akhir Paket")
            st.write(f"**Total Kalori:** {p_tot['k']:,.1f} kkal")
            st.write(f"**Protein:** {p_tot['p']:,.1f}g | **Lemak:** {p_tot['l']:,.1f}g | **Karbo:** {p_tot['ka']:,.1f}g")
            st.metric("Total HPP Paket", f"Rp {p_tot['h']:,.0f}")
