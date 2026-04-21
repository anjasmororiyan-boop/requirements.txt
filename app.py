import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v11.2", layout="wide")

# --- 1. FUNGSI PENYIMPANAN PERSISTEN ---
def load_data(file_name, columns):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)
    return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("database_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_menu' not in st.session_state:
    st.session_state.db_menu = load_data("master_resep.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_master_paket' not in st.session_state:
    st.session_state.db_master_paket = load_data("master_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori"])

# --- 3. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost Control v11.2")
nav = st.sidebar.radio("Navigasi", ["1. Database Bahan", "2. Upload Data", "3. Master Resep", "4. Master Paket"])

# --- MODUL 1 & 2 (Database & Upload - Singkat) ---
if nav == "1. Database Bahan":
    st.title("📂 Database Bahan Baku")
    edited_df = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Simpan Bahan"):
        st.session_state.db_bahan = edited_df.fillna(0)
        save_data(st.session_state.db_bahan, "database_bahan.csv"); st.success("Tersimpan!")

elif nav == "2. Upload Data":
    st.title("📥 Upload Data")
    uploaded_file = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file and st.button("🚀 Sinkronisasi"):
        df_new = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data(st.session_state.db_bahan, "database_bahan.csv"); st.success("Sinkron!"); st.rerun()

# --- MODUL 3: MASTER RESEP (DENGAN FORM RESET) ---
elif nav == "3. Master Resep":
    st.title("🍳 Master Resep (Menu Tunggal)")
    tab1, tab2 = st.tabs(["📝 Buat Resep", "📋 Database Resep"])
    with tab1:
        if "resep_id" not in st.session_state: st.session_state.resep_id = 0
        nm = st.text_input("Nama Produk", key=f"nm_{st.session_state.resep_id}")
        items = st.multiselect("Pilih Bahan", st.session_state.db_bahan['nama'].tolist(), key=f"it_{st.session_state.resep_id}")
        if items:
            res = {'kal':0,'pro':0,'lem':0,'kar':0,'cost':0,'gr':0}
            for i in items:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == i].iloc[0]
                qty = st.number_input(f"Qty {i}", min_value=0.0, key=f"q_{i}_{st.session_state.resep_id}")
                gr = qty * float(r['berat'])
                f = (gr/100)*(float(r['bdd'])/100)
                res['kal']+=float(r['kalori'])*f; res['pro']+=float(r['protein'])*f
                res['lem']+=float(r['lemak'])*f; res['kar']+=float(r['karbo'])*f; res['cost']+=float(r['harga'])*qty; res['gr']+=gr
            st.divider()
            y = st.number_input("Yield Matang", value=max(res['gr'],1.0)); p = st.number_input("Porsi", min_value=1)
            if st.button("💾 Simpan Resep"):
                new = pd.DataFrame([{"nama":nm,"berat_porsi_gr":y/p,"kal_porsi":res['kal']/p,"pro_porsi":res['pro']/p,"lem_porsi":res['lem']/p,"kar_porsi":res['kar']/p,"hpp_porsi":res['cost']/p}])
                st.session_state.db_menu = pd.concat([st.session_state.db_menu, new], ignore_index=True)
                save_data(st.session_state.db_menu, "master_resep.csv"); st.session_state.resep_id+=1; st.rerun()

# --- MODUL 4: MASTER PAKET (DENGAN DETAIL, GRAFIK & RESET) ---
elif nav == "4. Master Paket":
    st.title("🍱 Master Paket (Set Menu)")
    
    # Inisialisasi ID Form Paket untuk fitur Clear
    if "paket_form_id" not in st.session_state: st.session_state.paket_form_id = 0
    
    tab_a, tab_b = st.tabs(["🆕 Buat Paket Baru", "🗄️ Database Paket"])
    
    with tab_a:
        if st.session_state.db_menu.empty:
            st.warning("Buat Master Resep dulu.")
        else:
            col_clear, _ = st.columns([1, 4])
            if col_clear.button("🧹 Reset & Buat Paket Baru"):
                st.session_state.paket_form_id += 1
                st.rerun()

            c1, c2 = st.columns([2,1])
            nama_pkt = c1.text_input("Nama Paket", key=f"pkt_nm_{st.session_state.paket_form_id}")
            margin = c2.slider("Food Cost (%)", 10, 50, 30, key=f"m_{st.session_state.paket_form_id}")
            items_pkt = st.multiselect("Pilih Menu", st.session_state.db_menu['nama'].tolist(), key=f"pkt_it_{st.session_state.paket_form_id}")

            if items_pkt:
                st.markdown("### 📋 Rincian Nutrisi & Gramasi")
                p_res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'b':0,'isi':[]}
                
                # Tabel Detail
                detail_data = []
                for itm in items_pkt:
                    d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                    c_gr = st.number_input(f"Gramasi {itm} (gr)", value=float(d['berat_porsi_gr']), key=f"gr_{itm}_{st.session_state.paket_form_id}")
                    ratio = c_gr / d['berat_porsi_gr'] if d['berat_porsi_gr'] > 0 else 0
                    
                    # Hitung Pro-rata
                    val_k = d['kal_porsi']*ratio; val_p = d['pro_porsi']*ratio; val_l = d['lem_porsi']*ratio; val_ka = d['kar_porsi']*ratio; val_h = d['hpp_porsi']*ratio
                    
                    detail_data.append({"Menu": itm, "Berat (g)": c_gr, "Kalori": round(val_k,1), "Protein": round(val_p,1), "Lemak": round(val_l,1), "Karbo": round(val_ka,1), "HPP": round(val_h,0)})
                    
                    p_res['k']+=val_k; p_res['p']+=val_p; p_res['l']+=val_l; p_res['ka']+=val_ka; p_res['h']+=val_h; p_res['b']+=c_gr
                    p_res['isi'].append(f"{itm}({c_gr}g)")

                st.table(pd.DataFrame(detail_data))

                # Ringkasan & Grafik
                st.divider()
                col_m1, col_m2, col_chart = st.columns([1,1,2])
                with col_m1:
                    st.metric("Total Kalori", f"{p_res['k']:,.1f} kkal")
                    st.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
                with col_m2:
                    st.metric("Harga Jual (Target)", f"Rp {p_res['h']/(margin/100):,.0f}")
                    st.metric("Total Berat", f"{p_res['b']:,.1f} g")
                
                with col_chart:
                    fig = px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein','Lemak','Karbo'], title="Komposisi Makronutrisi Paket", hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)

                if st.button("💾 SIMPAN PAKET KE DATABASE"):
                    new_p = pd.DataFrame([{"nama_paket":nama_pkt, "rincian_isi":", ".join(p_res['isi']), "total_hpp":p_res['h'], "total_kalori":p_res['k']}])
                    st.session_state.db_master_paket = pd.concat([st.session_state.db_master_paket, new_p], ignore_index=True)
                    save_data(st.session_state.db_master_paket, "master_paket.csv"); st.success("Paket Tersimpan!"); st.rerun()

    with tab_b:
        st.subheader("🗄️ Daftar Master Paket")
        edited_p = st.data_editor(st.session_state.db_master_paket, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Update Master Paket"):
            st.session_state.db_master_paket = edited_p
            save_data(st.session_state.db_master_paket, "master_paket.csv"); st.success("Database Diperbarui!")
