import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v10.4", layout="wide")

# --- INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = pd.DataFrame(columns=["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# --- FUNGSI RESET FORM ---
def reset_form():
    st.session_state["nama_resep_input"] = ""
    st.session_state["pilih_bahan_input"] = []
    # Membersihkan semua key dinamis untuk qty
    for key in st.session_state.keys():
        if key.startswith("qty_"):
            st.session_state[key] = 0.0

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v10.4")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Buat Resep (Menu Master)", "4. Set Menu (Paket)"])

# --- MODUL 1 & 2 (Tetap Sama) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    edited_df = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("Simpan Perubahan"):
        st.session_state.db_bahan = edited_df.fillna(0); st.success("Update Berhasil!")

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
                st.success("Data Berhasil Masuk!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: BUAT RESEP (BUG FIXED) ---
elif nav == "3. Buat Resep (Menu Master)":
    st.title("🍳 Recipe Engineering & Automation")
    
    tab_resep, tab_list = st.tabs(["📝 Formulasi Menu", "📋 Master Resep Jadi"])
    
    with tab_resep:
        if st.session_state.db_bahan.empty:
            st.warning("Database kosong. Harap upload bahan baku.")
        else:
            # Gunakan key pada text_input dan multiselect agar bisa di-reset
            nama_resep = st.text_input("Nama Produk/Menu", key="nama_resep_input")
            bahan_terpilih = st.multiselect("Pilih Komponen Bahan Mentah", st.session_state.db_bahan['nama'].tolist(), key="pilih_bahan_input")

            if bahan_terpilih:
                st.markdown("### 📋 Rincian Gramasi & Nutrisi")
                
                # Header Tabel
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write("**Bahan**"); c2.write("**UOM**"); c3.write("**Qty Input**"); c4.write("**Gramasi**")
                
                res_calc = {'kal': 0.0, 'pro': 0.0, 'lem': 0.0, 'kar': 0.0, 'cost': 0.0, 'total_gr': 0.0}
                
                # Loop Bahan
                for b in bahan_terpilih:
                    row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    col_n, col_u, col_q, col_g = st.columns([3, 1, 1, 1])
                    
                    col_n.write(f"🔹 {b}")
                    col_u.write(row.get('uom', 'kg'))
                    
                    # Qty Input (Menggunakan key unik untuk reset)
                    qty = col_q.number_input(f"Qty {b}", min_value=0.0, step=0.01, key=f"qty_{b}")
                    
                    # Real-time calculation per baris
                    gr_bersih = qty * float(row.get('berat', 1000))
                    col_g.write(f"**{gr_bersih:,.0f} gr**")
                    
                    # Total Akumulasi
                    ratio = (float(row.get('berat', 1000))/100) * (float(row.get('bdd', 100))/100)
                    res_calc['kal'] += float(row.get('kalori', 0)) * ratio * qty
                    res_calc['pro'] += float(row.get('protein', 0)) * ratio * qty
                    res_calc['lem'] += float(row.get('lemak', 0)) * ratio * qty
                    res_calc['kar'] += float(row.get('karbo', 0)) * ratio * qty
                    res_calc['cost'] += float(row.get('harga', 0)) * qty
                    res_calc['total_gr'] += gr_bersih

                st.divider()
                st.subheader("⚖️ Perhitungan Yield (Hasil Jadi)")
                f1, f2, f3 = st.columns(3)
                f1.metric("Total Berat Mentah", f"{res_calc['total_gr']:,.0f} gr")
                berat_matang = f2.number_input("Berat Total Matang (Yield)", min_value=0.1, value=max(res_calc['total_gr'], 1.0))
                jml_porsi = f3.number_input("Jumlah Porsi", min_value=1, value=1)
                
                # Summary
                berat_porsi = berat_matang / jml_porsi
                hpp_porsi = res_calc['cost'] / jml_porsi
                st.success(f"**Hasil Akhir:** 1 Porsi = {berat_porsi:,.0f} gr | HPP = Rp {hpp_porsi:,.0f}")

                # Tombol Simpan dengan fungsi Reset
                if st.button("💾 Simpan Resep & Reset Form"):
                    if not nama_resep:
                        st.error("Nama Menu harus diisi!")
                    else:
                        new_resep = {
                            "nama": nama_resep,
                            "berat_porsi_gr": berat_porsi,
                            "kal_porsi": res_calc['kal'] / jml_porsi,
                            "pro_porsi": res_calc['pro'] / jml_porsi,
                            "lem_porsi": res_calc['lem'] / jml_porsi,
                            "kar_porsi": res_calc['kar'] / jml_porsi,
                            "hpp_porsi": hpp_porsi
                        }
                        st.session_state.db_menu = pd.concat([st.session_state.db_menu, pd.DataFrame([new_resep])], ignore_index=True)
                        st.balloons()
                        reset_form()
                        st.rerun()

    with tab_list:
        st.subheader("Daftar Master Resep")
        updated_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic")
        if st.button("Update/Hapus Resep"):
            st.session_state.db_menu = updated_menu; st.rerun()

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
