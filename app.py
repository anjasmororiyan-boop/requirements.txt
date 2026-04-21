import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.0", layout="wide")

# --- INISIALISASI DATABASE ---
# 1. Database Bahan Baku (Mentah)
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"
    ])

# 2. Database Master Resep (Hasil Jadi/Matang)
if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=[
        "nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"
    ])

# 3. Database Set Menu (Paket Gabungan)
if 'db_paket' not in st.session_state:
    st.session_state.db_paket = []

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v10.0")
nav = st.sidebar.radio("Navigasi", [
    "1. Data Master Bahan", 
    "2. Upload Database Bahan", 
    "3. Buat Resep (Recipe Master)",
    "4. Set Menu (Paket Gabungan)"
])

# --- MODUL 1: DATA MASTER BAHAN ---
if nav == "1. Data Master Bahan":
    st.title("📂 Database Bahan Baku")
    if st.session_state.db_bahan.empty:
        st.info("Database kosong. Silakan ke menu Upload.")
    else:
        search = st.text_input("🔍 Cari Bahan...")
        df_display = st.session_state.db_bahan
        if search:
            df_display = df_display[df_display['nama'].str.contains(search, case=False)]
        edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan"):
            st.session_state.db_bahan = edited_df.fillna(0)
            st.success("Database bahan diperbarui!")

# --- MODUL 2: UPLOAD DATABASE ---
elif nav == "2. Upload Database Bahan":
    st.title("📥 Upload Master Data Bahan")
    uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df_new = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping)
            cols = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
            for c in cols:
                if c not in df_new.columns: df_new[c] = 0 if c != "uom" else "kg"
            df_new = df_new[cols].fillna(0)
            if st.button("🚀 Sinkronkan Data"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Sinkron!")
                st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (RECIPE MASTER) ---
elif nav == "3. Buat Resep (Recipe Master)":
    st.title("🍳 Recipe Builder & Automation")
    tab1, tab2 = st.tabs(["📝 Buat Resep Baru", "📋 Daftar Master Resep"])
    
    with tab1:
        if st.session_state.db_bahan.empty: st.warning("Upload bahan dulu!")
        else:
            c1, c2 = st.columns(2)
            n_resep = c1.text_input("Nama Menu")
            p_bahan = c2.multiselect("Komponen", st.session_state.db_bahan['nama'].tolist())
            if p_bahan:
                t_d = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'brt': 0.0}
                h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
                h1.write("**Bahan**"); h2.write("**UOM**"); h3.write("**Qty**"); h4.write("**Gram**")
                for b in p_bahan:
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    c_n, c_u, c_q, c_g = st.columns([3, 1, 1, 1])
                    c_n.write(f"🔹 {b}"); c_u.write(row.get('uom','kg'))
                    qty = c_q.number_input(f"Q_{b}", min_value=0.0, step=0.01, key=f"r_{b}", label_visibility="collapsed")
                    gr = qty * float(row.get('berat', 1000))
                    c_g.write(f"{gr:,.0f} g")
                    ratio = (float(row.get('berat',1000))/100) * (float(row.get('bdd',100))/100)
                    t_d['kal']+=float(row.get('kalori',0))*ratio*qty; t_d['pro']+=float(row.get('protein',0))*ratio*qty
                    t_d['lem']+=float(row.get('lemak',0))*ratio*qty; t_d['kar']+=float(row.get('karbo',0))*ratio*qty
                    t_d['cost']+=float(row.get('harga',0))*qty; t_d['brt']+=gr
                st.divider()
                y1, y2 = st.columns(2)
                b_matang = y1.number_input("Berat Matang (gr)", value=t_d['brt'])
                porsi = y2.number_input("Porsi", min_value=1, value=1)
                if st.button("💾 Simpan Ke Master"):
                    new = {"nama": n_resep, "berat_porsi_gr": b_matang/porsi, "kal_porsi": t_d['kal']/porsi, "pro_porsi": t_d['pro']/porsi, "lem_porsi": t_d['lem']/porsi, "kar_porsi": t_d['kar']/porsi, "hpp_porsi": t_d['cost']/porsi}
                    st.session_state.db_menu = pd.concat([st.session_state.db_menu, pd.DataFrame([new])], ignore_index=True)
                    st.success("Resep Tersimpan!")

    with tab2:
        st.dataframe(st.session_state.db_menu, use_container_width=True)

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
