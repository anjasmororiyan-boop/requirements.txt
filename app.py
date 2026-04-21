import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.8", layout="wide")

# --- 1. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_master_paket' not in st.session_state:
    st.session_state.db_master_paket = pd.DataFrame(columns=["nama_paket", "isi_menu", "total_hpp", "harga_jual", "total_kalori"])

# --- 2. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v10.8")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Master)", "4. Set Menu (Master Paket)"])

# --- MODUL 1 & 2 (Tetap Sama) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    search = st.text_input("🔍 Cari Nama Bahan...")
    df_disp = st.session_state.db_bahan
    if search:
        df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    edited_df = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic", key="edit_bahan_table")
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
            df_new = df_new.rename(columns=mapping)
            if st.button("🚀 Jalankan Sinkronisasi"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Berhasil Sinkron!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (DENGAN FIX RESET FORM) ---
elif nav == "3. Buat Resep (Master)":
    st.title("🍳 Recipe Builder")
    tab_resep, tab_list = st.tabs(["📝 Formulasi Resep", "📋 Buku Master Resep"])
    
    with tab_resep:
        if st.session_state.db_bahan.empty:
            st.warning("Database bahan kosong.")
        else:
            # Gunakan key dinamis untuk reset total
            if "recipe_form_id" not in st.session_state:
                st.session_state.recipe_form_id = 0

            with st.container():
                nama_resep = st.text_input("Nama Produk/Menu Matang", key=f"nm_{st.session_state.recipe_form_id}")
                items_pilih = st.multiselect("Pilih Komponen Mentah", st.session_state.db_bahan['nama'].tolist(), key=f"it_{st.session_state.recipe_form_id}")
                
                res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
                
                if items_pilih:
                    st.markdown("---")
                    for item in items_pilih:
                        row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == item].iloc[0]
                        c1, c2, c3 = st.columns([3, 1, 1])
                        qty_val = c2.number_input(f"Qty {item} ({row['uom']})", min_value=0.0, step=0.01, key=f"q_{item}_{st.session_state.recipe_form_id}")
                        gr_bersih = qty_val * float(row.get('berat', 1000))
                        c3.write(f"**{gr_bersih:,.0f} g**")
                        
                        ratio = (float(row.get('berat', 1000))/100) * (float(row.get('bdd', 100))/100)
                        res_calc['kal'] += float(row.get('kalori', 0)) * ratio * qty_val
                        res_calc['pro'] += float(row.get('protein', 0)) * ratio * qty_val
                        res_calc['lem'] += float(row.get('lemak', 0)) * ratio * qty_val
                        res_calc['kar'] += float(row.get('karbo', 0)) * ratio * qty_val
                        res_calc['cost'] += float(row.get('harga', 0)) * qty_val
                        res_calc['total_gr'] += gr_bersih
                    
                    st.divider()
                    f1, f2, f3 = st.columns(3)
                    f1.metric("Total Berat Mentah", f"{res_calc['total_gr']:,.0f} g")
                    berat_matang = f2.number_input("Berat Total Matang (Yield)", min_value=0.1, value=max(res_calc['total_gr'], 1.0), key=f"yield_{st.session_state.recipe_form_id}")
                    jml_porsi = f3.number_input("Jumlah Porsi", min_value=1, value=1, key=f"porsi_{st.session_state.recipe_form_id}")
                    
                    if st.button("💾 SIMPAN RESEP & RESET FORM"):
                        if nama_resep:
                            new_row = pd.DataFrame([{
                                "nama": nama_resep, "berat_porsi_gr": berat_matang/jml_porsi,
                                "kal_porsi": res_calc['kal']/jml_porsi, "pro_porsi": res_calc['pro']/jml_porsi,
                                "lem_porsi": res_calc['lem']/jml_porsi, "kar_porsi": res_calc['kar']/jml_porsi,
                                "hpp_porsi": res_calc['cost']/jml_porsi
                            }])
                            st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_row], ignore_index=True)
                            st.session_state.recipe_form_id += 1 # Trigger reset
                            st.success("Resep Berhasil Disimpan!"); st.rerun()

    with tab_list:
        updated_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="edit_master_resep")
        if st.button("🗑️ Update / Hapus Resep"):
            st.session_state.db_menu = updated_menu; st.rerun()

# --- MODUL 4: SET MENU (DENGAN MASTER SIMPAN PAKET) ---
elif nav == "4. Set Menu (Master Paket)":
    st.title("🍱 Master Set Menu & Paket")
    tab_buat_pkt, tab_master_pkt = st.tabs(["🆕 Buat Paket Baru", "🗄️ Database Master Paket"])
    
    with tab_buat_pkt:
        if st.session_state.db_menu.empty:
            st.warning("Buat Master Resep terlebih dahulu di Tahap 3.")
        else:
            col1, col2 = st.columns([2, 1])
            nama_pkt = col1.text_input("Nama Paket", placeholder="Contoh: Paket Healthy A")
            margin = col2.slider("Target Food Cost (%)", 10, 50, 30)
            items = st.multiselect("Pilih Isi Menu", st.session_state.db_menu['nama'].tolist())
            
            if items:
                st.markdown("### 📋 Rincian Detail Paket")
                rincian_data = []
                p_res = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
                
                for itm in items:
                    d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                    rincian_data.append({
                        "Item Menu": d['nama'], "Berat (g)": f"{d['berat_porsi_gr']:,.1f}",
                        "Protein (g)": f"{d['pro_porsi']:,.1f}", "Lemak (g)": f"{d['lem_porsi']:,.1f}",
                        "Karbo (g)": f"{d['kar_porsi']:,.1f}", "HPP (Rp)": f"{d['hpp_porsi']:,.0f}"
                    })
                    p_res['k']+=d['kal_porsi']; p_res['p']+=d['pro_porsi']; p_res['l']+=d['lem_porsi']
                    p_res['ka']+=d['kar_porsi']; p_res['h']+=d['hpp_porsi']; p_res['b']+=d['berat_porsi_gr']
                
                st.table(pd.DataFrame(rincian_data))
                
                st.divider()
                s1, s2, s3 = st.columns(3)
                s1.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
                harga_jual = p_res['h']/(margin/100)
                s2.metric("Saran Harga Jual", f"Rp {harga_jual:,.0f}")
                s3.metric("Total Kalori", f"{p_res['k']:,.0f} kkal")
                
                if st.button("💾 SIMPAN PAKET KE MASTER"):
                    if nama_pkt:
                        new_pkt = pd.DataFrame([{
                            "nama_paket": nama_pkt, "isi_menu": ", ".join(items),
                            "total_hpp": p_res['h'], "harga_jual": harga_jual, "total_kalori": p_res['k']
                        }])
                        st.session_state.db_master_paket = pd.concat([st.session_state.db_master_paket, new_pkt], ignore_index=True)
                        st.success(f"Paket '{nama_pkt}' disimpan ke Master Paket!"); st.rerun()

    with tab_master_pkt:
        st.subheader("🗄️ Database Paket yang Tersimpan")
        if st.session_state.db_master_paket.empty:
            st.info("Belum ada paket yang disimpan.")
        else:
            edited_pkt = st.data_editor(st.session_state.db_master_paket, use_container_width=True, num_rows="dynamic")
            if st.button("🗑️ Update / Hapus Paket"):
                st.session_state.db_master_paket = edited_pkt; st.rerun()
