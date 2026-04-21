import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v15.0", layout="wide")

# --- 1. FUNGSI PERSISTENSI DATA ---
def load_data_safe(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df[columns]
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data_safe(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE (4 TIER) ---
cols_rm = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
cols_master = ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"]
cols_paket = ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"]

if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data_safe("db_bahan.csv", cols_rm)
if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data_safe("db_wip.csv", cols_master)
if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data_safe("db_fg.csv", cols_master)
if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data_safe("db_paket.csv", cols_paket)

# --- 3. HELPER KALKULASI GIZI PRESISI ---
def calc_nutri(qty, row, source_type='RM'):
    try:
        if source_type == 'RM':
            gr_mentah = qty * float(row['berat'])
            factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
            return {'k': float(row['kalori'])*factor, 'p': float(row['protein'])*factor, 'l': float(row['lemak'])*factor, 'ka': float(row['karbo'])*factor, 'h': float(row['harga'])*qty, 'g': gr_mentah}
        else: # WIP atau FG
            ratio = qty # Qty di sini adalah pengali porsi (misal 0.5 porsi)
            return {'k': float(row['kal_porsi'])*ratio, 'p': float(row['pro_porsi'])*ratio, 'l': float(row['lem_porsi'])*ratio, 'ka': float(row['kar_porsi'])*ratio, 'h': float(row['hpp_porsi'])*ratio, 'g': float(row['berat_porsi_gr'])*ratio}
    except: return {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'g':0}

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v15.0")
nav = st.sidebar.radio("Navigasi Utama", [
    "📦 1. Database Bahan Baku (RM)", 
    "📥 2. Upload Master Data",
    "🍳 3. Master Resep (WIP)", 
    "🍱 4. Finished Goods (FG)",
    "🛒 5. Set Menu (Paket)"
])

# --- MODUL 1 & 2 (Database & Upload) ---
if nav == "📦 1. Database Bahan Baku (RM)":
    st.title("📂 Database Bahan Baku")
    edited = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Simpan Perubahan RM"):
        st.session_state.db_bahan = edited.fillna(0)
        save_data_safe(st.session_state.db_bahan, "db_bahan.csv"); st.success("Tersimpan!")

elif nav == "📥 2. Upload Master Data":
    st.title("📥 Upload Database Massal")
    up = st.file_uploader("Upload file", type=["csv", "xlsx"])
    if up and st.button("🚀 Sinkronisasi"):
        df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data_safe(st.session_state.db_bahan, "db_bahan.csv"); st.success("Selesai!"); st.rerun()

# --- MODUL 3: MASTER RESEP (WIP) ---
elif nav == "🍳 3. Master Resep (WIP)":
    st.title("🍳 Master Resep Setengah Jadi (WIP)")
    t1, t2 = st.tabs(["📝 Buat Resep WIP", "📋 Database WIP"])
    with t1:
        if "w_id" not in st.session_state: st.session_state.w_id = 0
        nm_w = st.text_input("Nama Resep WIP (Contoh: Sambal)", key=f"wnm_{st.session_state.w_id}")
        sel_rm = st.multiselect("Pilih Bahan Baku", st.session_state.db_bahan['nama'].tolist(), key=f"wrm_{st.session_state.w_id}")
        if sel_rm:
            res_w = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for b in sel_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                q = st.number_input(f"Qty {b}", min_value=0.0, key=f"wq_{b}")
                calc = calc_nutrition(q, row, 'RM')
                for k in res_w: res_w[k] += calc[k]
            y = st.number_input("Yield Matang (gr)", value=max(res_w['g'], 1.0))
            p = st.number_input("Porsi", min_value=1, value=1)
            if st.button("💾 Simpan Resep WIP"):
                new_w = pd.DataFrame([{"nama":nm_w, "berat_porsi_gr":y/p, "kal_porsi":res_w['k']/p, "pro_porsi":res_w['p']/p, "lem_porsi":res_w['l']/p, "kar_porsi":res_w['ka']/p, "hpp_porsi":res_w['h']/p}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new_w], ignore_index=True)
                save_data_safe(st.session_state.db_wip, "db_wip.csv")
                st.session_state.w_id += 1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic")

# --- MODUL 4: FINISHED GOODS (FG) ---
elif nav == "🍱 4. Finished Goods (FG)":
    st.title("🍱 Master Finished Goods (Hybrid RM + WIP)")
    st.info("Gabungkan Bahan Mentah (Ikan Nila) dan Resep Matang (Sambal) di sini.")
    t1, t2 = st.tabs(["📝 Buat FG Baru", "📋 Database FG"])
    with t1:
        if "f_id" not in st.session_state: st.session_state.f_id = 0
        nm_fg = st.text_input("Nama Produk Jadi (FG)", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        f_rm = c1.multiselect("Ambil dari Database Bahan (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.f_id}")
        f_wp = c2.multiselect("Ambil dari Master Resep (WIP)", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.f_id}")
        if f_rm or f_wp:
            res_f = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for x in f_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == x].iloc[0]
                q = st.number_input(f"Qty RM: {x}", key=f"fqrm_{x}")
                d = calc_nutrition(q, row, 'RM'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            for x in f_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama'] == x].iloc[0]
                q = st.number_input(f"Porsi WIP: {x}", key=f"fqwp_{x}")
                d = calc_nutrition(q, row, 'WIP'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            if st.button("💾 Simpan Master FG"):
                new_f = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":res_f['g'], "kal_porsi":res_f['k'], "pro_porsi":res_f['p'], "lem_porsi":res_f['l'], "kar_porsi":res_f['ka'], "hpp_porsi":res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new_f], ignore_index=True)
                save_data_safe(st.session_state.db_fg, "db_fg.csv")
                st.session_state.f_id += 1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")

# --- MODUL 5: SET MENU (FIXED NULL DISPLAY) ---
elif nav == "🛒 5. Set Menu (Paket)":
    st.title("🍱 Master Paket & Analisis Nutrisi")
    if "p_id" not in st.session_state: st.session_state.p_id = 0
    
    tab_buat, tab_master = st.tabs(["🆕 Buat Paket Jual", "🗄️ Database Paket"])
    
    with tab_buat:
        if st.button("🧹 Clear Form Paket"):
            st.session_state.p_id += 1; st.rerun()
            
        col1, col2 = st.columns([2,1])
        nm_pkt = col1.text_input("Nama Paket", key=f"pnm_{st.session_state.p_id}")
        margin = col2.slider("Food Cost (%)", 10, 50, 30, key=f"pm_{st.session_state.p_id}")
        
        c_rm, c_wp, c_fg = st.columns(3)
        sel_rm = c_rm.multiselect("Tambah RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.p_id}")
        sel_wp = c_wp.multiselect("Tambah WIP", st.session_state.db_wip['nama'].tolist(), key=f"pwp_{st.session_state.p_id}")
        sel_fg = c_fg.multiselect("Tambah FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.p_id}")
        
        if sel_rm or sel_wp or sel_fg:
            p_res = {'k':0.0,'p':0.0,'l':0.0,'ka':0.0,'h':0.0,'b':0.0,'isi':[]}
            detail_table = []

            # Proses RM, WIP, FG dengan proteksi NULL
            for x in sel_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == x].iloc[0]
                q_gr = st.number_input(f"Gram Mentah: {x}", min_value=0.0, key=f"pqrm_{x}")
                d = calc_nutri_safe(q_gr/row['berat'], row, 'RM')
                detail_table.append({"Source": "RM", "Item": x, "Gram": q_gr, "HPP": d['h'], "Kalori": d['k']})
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
                p_res['isi'].append(f"{x}")

            for x in sel_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama'] == x].iloc[0]
                q_gr = st.number_input(f"Gram Matang: {x}", value=float(row['berat_porsi_gr']), key=f"pqwp_{x}")
                d = calc_nutri_safe(q_gr, row, 'WIP')
                detail_table.append({"Source": "WIP", "Item": x, "Gram": q_gr, "HPP": d['h'], "Kalori": d['k']})
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
                p_res['isi'].append(f"{x}")

            for x in sel_fg:
                row = st.session_state.db_fg[st.session_state.db_fg['nama'] == x].iloc[0]
                q_gr = st.number_input(f"Gram Produk: {x}", value=float(row['berat_porsi_gr']), key=f"pqfg_{x}")
                d = calc_nutri_safe(q_gr, row, 'FG')
                detail_table.append({"Source": "FG", "Item": x, "Gram": q_gr, "HPP": d['h'], "Kalori": d['k']})
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
                p_res['isi'].append(f"{x}")

            st.table(pd.DataFrame(detail_table))
            
            # --- ANALISIS GRAFIK ---
            st.divider()
            m1, m2, m3 = st.columns([1,1,2])
            m1.metric("Total Kalori", f"{p_res['k']:,.1f} kkal")
            m2.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
            with m3:
                # Pastikan pie chart tidak NULL
                if p_res['p'] + p_res['l'] + p_res['ka'] > 0:
                    fig = px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein','Lemak','Karbo'], hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Isi gramasi untuk melihat grafik gizi.")
