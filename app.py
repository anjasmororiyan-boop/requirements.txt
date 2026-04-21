import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.5", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# --- FUNGSI RESET FORM ---
def reset_recipe_form():
    st.session_state["nama_resep_input"] = ""
    st.session_state["pilih_bahan_input"] = []
    # Bersihkan qty keys
    for key in list(st.session_state.keys()):
        if key.startswith("qty_"):
            st.session_state[key] = 0.0

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v10.5")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Menu Master)", "4. Set Menu (Paket)"])

# --- MODUL 1 & 2 (Tetap Sama) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    search = st.text_input("Cari Bahan...")
    df_disp = st.session_state.db_bahan
    if search:
        df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    edited_df = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic")
    if st.button("Simpan Perubahan"):
        st.session_state.db_bahan = edited_df.fillna(0)
        st.success("Update Berhasil!")

elif nav == "2. Upload Data":
    st.title("📥 Upload Master Data")
    uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df_new = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom': 'uom', 'berat_bersih_per_uom_gr': 'berat', 'harga_beli_per_uom': 'harga'}
            df_new = df_new.rename(columns=mapping)
            if st.button("Jalankan Sinkronisasi"):
                st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
                st.success("Data Berhasil Sinkron!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (FIXED ERROR) ---
elif nav == "3. Buat Resep (Menu Master)":
    st.title("🍳 Recipe Builder & Automation")
    tab_resep, tab_list = st.tabs(["📝 Formulasi Menu", "📋 Master Resep Jadi"])
    
    with tab_resep:
        if st.session_state.db_bahan.empty:
            st.warning("Database kosong. Harap upload bahan baku.")
        else:
            # Gunakan key untuk mempermudah reset
            nama_resep = st.text_input("Nama Produk/Menu", key="nama_resep_input")
            bahan_terpilih = st.multiselect("Pilih Komponen Bahan Mentah", st.session_state.db_bahan['nama'].tolist(), key="pilih_bahan_input")

            if bahan_terpilih:
                st.markdown("### 📋 Rincian Komposisi Bahan")
                res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
                
                h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
                h1.write("**Bahan**"); h2.write("**UOM**"); h3.write("**Qty**"); h4.write("**Gramasi**")
                
                for b in bahan_terpilih:
                    # Ambil data bahan baku secara aman
                    try:
                        row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                        c_n, c_u, c_q, c_g = st.columns([3, 1, 1, 1])
                        c_n.write(f"🔹 {b}")
                        c_u.write(row.get('uom', 'kg'))
                        
                        qty = c_q.number_input(f"Qty {b}", min_value=0.0, step=0.01, key=f"qty_{b}")
                        
                        gr_bersih = qty * float(row.get('berat', 1000))
                        c_g.write(f"**{gr_bersih:,.0f} gr**")
                        
                        ratio = (float(row.get('berat', 1000))/100) * (float(row.get('bdd', 100))/100)
                        res_calc['kal'] += float(row.get('kalori', 0)) * ratio * qty
                        res_calc['pro'] += float(row.get('protein', 0)) * ratio * qty
                        res_calc['lem'] += float(row.get('lemak', 0)) * ratio * qty
                        res_calc['kar'] += float(row.get('karbo', 0)) * ratio * qty
                        res_calc['cost'] += float(row.get('harga', 0)) * qty
                        res_calc['total_gr'] += gr_bersih
                    except Exception:
                        continue

                st.divider()
                st.subheader("⚖️ Perhitungan Yield")
                f1, f2, f3 = st.columns(3)
                f1.metric("Total Berat Mentah", f"{res_calc['total_gr']:,.0f} gr")
                berat_matang = f2.number_input("Berat Total Matang (Yield)", min_value=0.01, value=max(res_calc['total_gr'], 1.0))
                jml_porsi = f3.number_input("Jumlah Porsi", min_value=1, value=1)
                
                # Kalkulasi Final
                berat_porsi = berat_matang / jml_porsi
                hpp_porsi = res_calc['cost'] / jml_porsi
                st.info(f"Hasil Akhir: 1 Porsi = {berat_porsi:,.0f} gr | HPP = Rp {hpp_porsi:,.0f}")

                # Tombol Simpan
                if st.button("💾 Simpan Resep & Reset"):
                    if not nama_resep:
                        st.error("Nama Menu tidak boleh kosong!")
                    elif res_calc['total_gr'] == 0:
                        st.error("Isi gramasi bahan terlebih dahulu!")
                    else:
                        try:
                            # Membuat DataFrame baru untuk resep
                            new_data = pd.DataFrame([{
                                "nama": str(nama_resep),
                                "berat_porsi_gr": float(berat_porsi),
                                "kal_porsi": float(res_calc['kal'] / jml_porsi),
                                "pro_porsi": float(res_calc['pro'] / jml_porsi),
                                "lem_porsi": float(res_calc['lem'] / jml_porsi),
                                "kar_porsi": float(res_calc['kar'] / jml_porsi),
                                "hpp_porsi": float(hpp_porsi)
                            }])
                            
                            # Menggabungkan ke database resep
                            st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_data], ignore_index=True)
                            st.success(f"Resep '{nama_resep}' Berhasil Disimpan!")
                            reset_recipe_form()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan resep: {e}")

    with tab_list:
        st.subheader("📋 Master Buku Resep")
        if not st.session_state.db_menu.empty:
            updated_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic", key="edit_resep_final")
            if st.button("Update/Hapus Resep Matang"):
                st.session_state.db_menu = updated_menu
                st.rerun()
        else:
            st.info("Belum ada resep yang disimpan.")

# --- MODUL 4: SET MENU (PAKET) ---
elif nav == "4. Set Menu (Paket)":
    st.title("🍱 Aggregator Set Menu")
    if st.session_state.db_menu.empty:
        st.warning("Buat Master Resep terlebih dahulu.")
    else:
        with st.form("form_paket"):
            nama_pkt = st.text_input("Nama Paket Gabungan")
            items = st.multiselect("Pilih Master Resep", st.session_state.db_menu['nama'].tolist())
            margin = st.slider("Target Food Cost (%)", 10, 50, 30)
            if st.form_submit_button("Analisis Paket"):
                pass
        
        if items:
            p_res = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'b':0}
            for itm in items:
                d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                p_res['k']+=d['kal_porsi']; p_res['p']+=d['pro_porsi']; p_res['l']+=d['lem_porsi']
                p_res['ka']+=d['kar_porsi']; p_res['h']+=d['hpp_porsi']; p_res['b']+=d['berat_porsi_gr']
            
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Energi", f"{p_res['k']:.0f} kkal")
            m2.metric("HPP", f"Rp {p_res['h']:,.0f}")
            m3.metric("Harga Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
            m4.metric("Berat Total", f"{p_res['b']:.0f} g")
