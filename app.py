import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.2", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"
    ])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=[
        "nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"
    ])

# State untuk mereset form resep
if 'reset_resep' not in st.session_state:
    st.session_state.reset_resep = False

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Pro v10.2")
nav = st.sidebar.radio("Navigasi", [
    "1. Data Master Bahan", 
    "2. Upload Database Bahan", 
    "3. Buat & Kelola Resep",
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
        if st.button("💾 Simpan Perubahan Bahan"):
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

# --- MODUL 3: BUAT & KELOLA RESEP (DENGAN FITUR RESET) ---
elif nav == "3. Buat & Kelola Resep":
    st.title("🍳 Recipe Builder & Master Management")
    tab1, tab2 = st.tabs(["📝 Buat Resep Baru", "📋 Kelola Master Resep"])
    
    with tab1:
        if st.session_state.db_bahan.empty: 
            st.warning("Upload bahan dulu!")
        else:
            # Menggunakan Form dengan key untuk reset otomatis
            with st.form("form_resep_baru", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n_resep = c1.text_input("Nama Menu", placeholder="Contoh: Nasi Goreng")
                p_bahan = c2.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())
                
                # Container untuk rincian gramasi
                st.markdown("#### Rincian Gramasi")
                st.write("Silakan pilih bahan di atas, lalu isi Qty di bawah ini:")
                
                # Perhitungan Nutrisi & Cost
                t_d = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'brt': 0.0}
                
                if p_bahan:
                    for b in p_bahan:
                        row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                        c_n, c_u, c_q = st.columns([3, 1, 2])
                        c_n.write(f"🔹 **{b}**")
                        c_u.write(f"Satuan: {row.get('uom','kg')}")
                        qty = c_q.number_input(f"Qty {b}", min_value=0.0, step=0.01, key=f"r_{b}")
                        
                        gr = qty * float(row.get('berat', 1000))
                        ratio = (float(row.get('berat',1000))/100) * (float(row.get('bdd',100))/100)
                        
                        t_d['kal']+=float(row.get('kalori',0))*ratio*qty
                        t_d['pro']+=float(row.get('protein',0))*ratio*qty
                        t_d['lem']+=float(row.get('lemak',0))*ratio*qty
                        t_d['kar']+=float(row.get('karbo',0))*ratio*qty
                        t_d['cost']+=float(row.get('harga',0))*qty
                        t_d['brt']+=gr
                
                st.divider()
                y1, y2 = st.columns(2)
                b_matang = y1.number_input("Berat Matang Total (gr)", value=t_d['brt'])
                porsi = y2.number_input("Jumlah Porsi Hasil Jadi", min_value=1, value=1)
                
                submit_res = st.form_submit_button("💾 Simpan Ke Master & Bersihkan Form")
                
                if submit_res:
                    if not n_resep or not p_bahan:
                        st.error("Gagal Simpan: Nama menu dan Bahan tidak boleh kosong!")
                    else:
                        new_data = {
                            "nama": n_resep, 
                            "berat_porsi_gr": b_matang/porsi, 
                            "kal_porsi": t_d['kal']/porsi, 
                            "pro_porsi": t_d['pro']/porsi, 
                            "lem_porsi": t_d['lem']/porsi, 
                            "kar_porsi": t_d['kar']/porsi, 
                            "hpp_porsi": t_d['cost']/porsi
                        }
                        st.session_state.db_menu = pd.concat([st.session_state.db_menu, pd.DataFrame([new_data])], ignore_index=True)
                        st.success(f"Resep '{n_resep}' Berhasil Disimpan! Form telah dibersihkan.")
                        # Rerun untuk memastikan tampilan bersih kembali
                        st.rerun()

    with tab2:
        st.subheader("📋 Daftar Master Resep Jadi")
        if st.session_state.db_menu.empty:
            st.info("Belum ada resep yang disimpan.")
        else:
            updated_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="editor_resep_v10")
            if st.button("🗑️ Konfirmasi Hapus / Update Resep"):
                st.session_state.db_menu = updated_menu
                st.success("Database resep diperbarui!")
                st.rerun()

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
