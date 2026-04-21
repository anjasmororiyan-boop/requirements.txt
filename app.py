import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.3", layout="wide")

# --- 1. INISIALISASI DATABASE (SESSION STATE) ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=[
        "nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"
    ])

# --- 2. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control Center")
nav = st.sidebar.radio("Tahapan Proses", [
    "📦 Tahap 1: Management Bahan Baku", 
    "🍳 Tahap 2: Recipe Engineering (Buat Menu)", 
    "🍱 Tahap 3: Set Menu & Analisis Harga"
])

# --- 3. PROSES TAHAP 1: MANAGEMENT BAHAN BAKU ---
if nav == "📦 Tahap 1: Management Bahan Baku":
    st.title("Management Database Bahan Baku")
    
    t1, t2 = st.tabs(["🔍 Lihat & Cari Data", "📥 Import Massal (1500+ Item)"])
    
    with t1:
        search = st.text_input("Cari Bahan...")
        df_display = st.session_state.db_bahan
        if search:
            df_display = df_display[df_display['nama'].str.contains(search, case=False)]
        
        edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic", key="editor_bahan")
        if st.button("💾 Update Database Bahan"):
            st.session_state.db_bahan = edited_df.fillna(0)
            st.success("Database bahan berhasil diperbarui!")

    with t2:
        up_file = st.file_uploader("Upload Template V2 (CSV/Excel)", type=["csv", "xlsx"])
        if up_file:
            try:
                df_new = pd.read_csv(up_file, sep=None, engine='python') if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
                mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
                df_new = df_new.rename(columns=mapping)
                # Sinkronisasi kolom wajib
                cols = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
                for c in cols:
                    if c not in df_new.columns: df_new[c] = 0 if c != "uom" else "kg"
                df_new = df_new[cols].fillna(0)
                if st.button("🚀 Jalankan Sinkronisasi Massal"):
                    st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                    st.success("Sinkronisasi Berhasil!")
            except Exception as e: st.error(f"Error: {e}")

# --- 4. PROSES TAHAP 2: RECIPE ENGINEERING (PROSES MENU) ---
elif nav == "🍳 Tahap 2: Recipe Engineering (Buat Menu)":
    st.title("Proses Engineering Menu & Yield")
    
    tab_buat, tab_master = st.tabs(["📝 Formulasi Resep Baru", "📜 Buku Master Resep Jadi"])
    
    with tab_buat:
        if st.session_state.db_bahan.empty:
            st.warning("Silakan isi Database Bahan Baku terlebih dahulu.")
        else:
            with st.form("form_proses_menu", clear_on_submit=True):
                col_a, col_b = st.columns([2, 2])
                nama_menu = col_a.text_input("Nama Produk/Menu Matang", placeholder="Contoh: Ayam Goreng Serundeng")
                items_pilih = col_b.multiselect("Pilih Komponen Mentah", st.session_state.db_bahan['nama'].tolist())
                
                st.markdown("### 📋 Tabel Rincian Komposisi")
                
                res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'berat_m': 0.0}
                
                if items_pilih:
                    # Header tabel rincian
                    h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
                    h1.write("**Item Bahan**"); h2.write("**UOM**"); h3.write("**Qty Input**"); h4.write("**Gramasi**")
                    
                    for item in items_pilih:
                        row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == item].iloc[0]
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                        
                        c1.write(f"🔸 {item}")
                        uom_item = row.get('uom', 'kg')
                        c2.write(uom_item)
                        
                        # Input Qty berdasarkan UOM
                        qty_input = c3.number_input(f"Qty {item}", min_value=0.0, step=0.01, key=f"p_{item}")
                        
                        # Konversi ke gramasi
                        berat_satuan = float(row.get('berat', 1000))
                        gram_total = qty_input * berat_satuan
                        c4.write(f"{gram_total:,.0f} g")
                        
                        # Kalkulasi Nutrisi (Memperhitungkan BDD)
                        bdd_factor = float(row.get('bdd', 100)) / 100
                        nutri_ratio = (berat_satuan / 100) * bdd_factor
                        
                        res_calc['kal'] += float(row.get('kalori', 0)) * nutri_ratio * qty_input
                        res_calc['pro'] += float(row.get('protein', 0)) * nutri_ratio * qty_input
                        res_calc['lem'] += float(row.get('lemak', 0)) * nutri_ratio * qty_input
                        res_calc['kar'] += float(row.get('karbo', 0)) * nutri_ratio * qty_input
                        res_calc['cost'] += float(row.get('harga', 0)) * qty_input
                        res_calc['berat_m'] += gram_total

                st.divider()
                st.subheader("⚖️ Yield & Analisis Porsi")
                f1, f2, f3 = st.columns(3)
                f1.metric("Total Berat Mentah", f"{res_calc['berat_m']:,.0f} g")
                berat_jadi = f2.number_input("Berat Jadi (Matang) - gr", min_value=1.0, value=max(res_calc['berat_m'], 1.0))
                jml_porsi = f3.number_input("Jumlah Porsi", min_value=1, value=1)
                
                submit_menu = st.form_submit_button("💾 Simpan Resep & Reset Form")
                
                if submit_menu:
                    if not nama_menu or not items_pilih:
                        st.error("Nama Menu dan Bahan wajib diisi!")
                    else:
                        new_entry = {
                            "nama": nama_menu,
                            "berat_porsi_gr": berat_jadi / jml_porsi,
                            "kal_porsi": res_calc['kal'] / jml_porsi,
                            "pro_porsi": res_calc['pro'] / jml_porsi,
                            "lem_porsi": res_calc['lem'] / jml_porsi,
                            "kar_porsi": res_calc['kar'] / jml_porsi,
                            "hpp_porsi": res_calc['cost'] / jml_porsi
                        }
                        st.session_state.db_menu = pd.concat([st.session_state.db_menu, pd.DataFrame([new_entry])], ignore_index=True)
                        st.success(f"Menu '{nama_menu}' Berhasil Disimpan ke Master Resep!")
                        st.rerun()

    with tab_master:
        st.subheader("Buku Master Resep (Hasil Engineering)")
        if st.session_state.db_menu.empty:
            st.info("Belum ada resep matang yang tersimpan.")
        else:
            up_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="edit_master_resep")
            if st.button("🗑️ Hapus / Update Resep Terpilih"):
                st.session_state.db_menu = up_menu
                st.rerun()

# --- 5. PROSES TAHAP 3: SET MENU ---
elif nav == "🍱 Tahap 3: Set Menu & Analisis Harga":
    st.title("Aggregator Set Menu (Paket)")
    if st.session_state.db_menu.empty:
        st.warning("Buat Master Resep Matang terlebih dahulu di Tahap 2.")
    else:
        with st.form("form_paket"):
            nama_pkt = st.text_input("Nama Paket Gabungan")
            pilih_item = st.multiselect("Pilih Item dari Master Resep", st.session_state.db_menu['nama'].tolist())
            margin_target = st.slider("Target Food Cost (%)", 10, 50, 30)
            if st.form_submit_button("Analisis Paket"):
                pass
        
        if pilih_item:
            # Kalkulasi Gabungan
            p_res = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
            for itm in pilih_item:
                d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                p_res['k']+=d['kal_porsi']; p_res['p']+=d['pro_porsi']; p_res['l']+=d['lem_porsi']
                p_res['ka']+=d['kar_porsi']; p_res['h']+=d['hpp_porsi']; p_res['b']+=d['berat_porsi_gr']
            
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Energi Paket", f"{p_res['k']:.0f} kkal")
            m2.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
            m3.metric("Saran Jual", f"Rp {p_res['h']/(margin_target/100):,.0f}")
            m4.metric("Berat Paket", f"{p_res['b']:.0f} g")
            
            st.plotly_chart(px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein', 'Lemak', 'Karbo'], title=f"Profil Gizi: {nama_pkt}"))

# --- MODUL 4: SET MENU (PAKET GABUNGAN) ---
elif nav == "4. Set Menu (Paket Gabungan)":
    st.title("🍱 Set Menu Builder (Paket)")
    
    if st.session_state.db_menu.empty:
        st.info("Buat Master Resep dulu di menu nomor 3 sebelum membuat paket.")
    else:
        with st.form("buat_paket"):
            nama_paket = st.text_input("Nama Paket (Contoh: Paket Hemat A)")
            items_paket = st.multiselect("Pilih Item dari Master Resep", st.session_state.db_menu['nama'].tolist())
            margin = st.slider("Target Food Cost (%)", 10, 50, 30)
            submit_paket = st.form_submit_button("Kalkulasi Paket")

        if submit_paket and items_paket:
            res_p = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
            st.subheader(f"Analisis Gizi & Harga: {nama_paket}")
            
            # Tampilkan rincian item dalam paket
            for item_n in items_paket:
                d = st.session_state.db_menu[st.session_state.db_menu['nama'] == item_n].iloc[0]
                res_p['k']+=d['kal_porsi']; res_p['p']+=d['pro_porsi']; res_p['l']+=d['lem_porsi']
                res_p['ka']+=d['kar_porsi']; res_p['h']+=d['hpp_porsi']; res_p['b']+=d['berat_porsi_gr']
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Energi", f"{res_p['k']:.0f} kkal")
            c2.metric("Total HPP", f"Rp {res_p['h']:,.0f}")
            c3.metric("Saran Jual", f"Rp {res_p['h']/(margin/100):,.0f}")
            c4.metric("Berat Total", f"{res_p['b']:.0f} gr")

            # Chart Gizi Paket
            fig = px.pie(values=[res_p['p'], res_p['l'], res_p['ka']], names=['Protein', 'Lemak', 'Karbo'], title="Komposisi Gizi Paket")
            st.plotly_chart(fig)
            
            if st.button("💾 Simpan Paket"):
                st.session_state.db_paket.append({"paket": nama_paket, "total_hpp": res_p['h'], "total_kal": res_p['k']})
                st.success("Paket Berhasil Disimpan!")
