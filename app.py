import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v13.5", layout="wide")

# --- 1. FUNGSI PERSISTENSI & AUTO-STARTER ---
def load_data(file_name, columns, default_data=None):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df
        except: return pd.DataFrame(columns=columns)
    # Jika file tidak ada, buat file baru dengan data contoh (Dummy)
    df_new = pd.DataFrame(default_data if default_data else [], columns=columns)
    df_new.to_csv(file_name, index=False)
    return df_new

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. DATA CONTOH (AGAR TIDAK KOSONG) ---
dummy_bahan = [
    {"nama": "Ikan Nila Mentah", "kalori": 128, "protein": 20, "lemak": 5, "karbo": 0, "bdd": 80, "uom": "kg", "berat": 1000, "harga": 35000},
    {"nama": "Cabai Merah", "kalori": 40, "protein": 2, "lemak": 0.5, "karbo": 9, "bdd": 95, "uom": "kg", "berat": 1000, "harga": 40000},
    {"nama": "Minyak Goreng", "kalori": 884, "protein": 0, "lemak": 100, "karbo": 0, "bdd": 100, "uom": "liter", "berat": 1000, "harga": 15000}
]

# --- 3. INISIALISASI DATABASE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("db_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"], dummy_bahan)

if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data("db_wip.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data("db_fg.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data("db_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"])

# --- 4. HELPER KALKULASI GIZI ---
def get_nutrisi_calculated(qty, row, source_type='RM'):
    try:
        if source_type == 'RM':
            gr_mentah = qty * float(row['berat'])
            factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
            return {'k': float(row['kalori'])*factor, 'p': float(row['protein'])*factor, 'l': float(row['lemak'])*factor, 'ka': float(row['karbo'])*factor, 'h': float(row['harga'])*qty, 'g': gr_mentah}
        else:
            ratio = qty
            return {'k': float(row['kal_porsi'])*ratio, 'p': float(row['pro_porsi'])*ratio, 'l': float(row['lem_porsi'])*ratio, 'ka': float(row['kar_porsi'])*ratio, 'h': float(row['hpp_porsi'])*ratio, 'g': float(row['berat_porsi_gr'])*ratio}
    except: return {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0, 'g':0}

# --- 5. SIDEBAR & NAVIGASI ---
st.sidebar.title("NutriCost ERP v13.5")
nav = st.sidebar.radio("Alur Produksi", ["📦 1. Database Bahan (RM)", "📥 2. Upload Master Data", "🍳 3. Master Resep (WIP)", "🍱 4. Finished Goods (FG)", "🛒 5. Set Menu (Paket)"])

# --- MODUL 1: DATABASE BAHAN ---
if nav == "1. Database Bahan (RM)":
    st.title("📂 Database Bahan Baku")
    edited = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Simpan Perubahan Bahan"):
        st.session_state.db_bahan = edited.fillna(0)
        save_data(st.session_state.db_bahan, "db_bahan.csv"); st.success("Data Tersimpan!")

# --- MODUL 2: UPLOAD ---
elif nav == "2. Upload Master Data":
    st.title("📥 Upload Database Massal")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up and st.button("🚀 Jalankan Sinkronisasi"):
        df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data(st.session_state.db_bahan, "db_bahan.csv"); st.success("Selesai!"); st.rerun()

# --- MODUL 3: MASTER RESEP (WIP) ---
elif nav == "3. Master Resep (WIP)":
    st.title("🍳 Master Resep Setengah Jadi (WIP)")
    if "w_id" not in st.session_state: st.session_state.w_id = 0
    t1, t2 = st.tabs(["📝 Buat WIP", "📋 Database WIP"])
    with t1:
        nm = st.text_input("Nama Resep (Misal: Sambal)", key=f"wnm_{st.session_state.w_id}")
        it = st.multiselect("Bahan", st.session_state.db_bahan['nama'].tolist(), key=f"wit_{st.session_state.w_id}")
        if it:
            res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for i in it:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==i].iloc[0]
                q = st.number_input(f"Qty {i}", min_value=0.0, key=f"wq_{i}")
                d = get_nutrisi_calculated(q, r, 'RM')
                for k in res: res[k]+=d[k]
            y = st.number_input("Berat Matang WIP (gr)", value=max(res['g'],1.0))
            p = st.number_input("Porsi", min_value=1)
            if st.button("💾 Simpan WIP"):
                new = pd.DataFrame([{"nama":nm, "berat_porsi_gr":y/p, "kal_porsi":res['k']/p, "pro_porsi":res['p']/p, "lem_porsi":res['l']/p, "kar_porsi":res['ka']/p, "hpp_porsi":res['h']/p}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new], ignore_index=True)
                save_data(st.session_state.db_wip, "db_wip.csv"); st.session_state.w_id+=1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic")

# --- MODUL 4: FINISHED GOODS (FG) ---
elif nav == "4. Finished Goods (FG)":
    st.title("🍱 Finished Goods (Gabungan RM + WIP)")
    if "f_id" not in st.session_state: st.session_state.f_id = 0
    t1, t2 = st.tabs(["🆕 Buat FG", "📋 Database FG"])
    with t1:
        nm_f = st.text_input("Nama Produk FG (Misal: Nila Penyet)", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Pilih RM", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.f_id}")
        s_wp = c2.multiselect("Pilih WIP", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.f_id}")
        if s_rm or s_wp:
            res_f = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for x in s_rm:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x}", key=f"fqrm_{x}")
                d = get_nutrisi_calculated(q, r, 'RM')
                for k in res_f: res_f[k]+=d[k]
            for x in s_wp:
                r = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Porsi {x}", key=f"fqwp_{x}")
                d = get_nutrisi_calculated(q, r, 'WIP')
                for k in res_f: res_f[k]+=d[k]
            if st.button("💾 Simpan FG"):
                new = pd.DataFrame([{"nama":nm_f, "berat_porsi_gr":res_f['g'], "kal_porsi":res_f['k'], "pro_porsi":res_f['p'], "lem_porsi":res_f['l'], "kar_porsi":res_f['ka'], "hpp_porsi":res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new], ignore_index=True)
                save_data(st.session_state.db_fg, "db_fg.csv"); st.session_state.f_id+=1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")

# --- MODUL 5: SET MENU (PAKET) ---
elif nav == "5. Set Menu (Paket)":
    st.title("🛒 Set Menu (RM + WIP + FG)")
    if "p_id" not in st.session_state: st.session_state.p_id = 0
    if st.button("🧹 Clear Form"): st.session_state.p_id += 1; st.rerun()
    
    nm_p = st.text_input("Nama Paket", key=f"pnm_{st.session_state.p_id}")
    c1, c2, c3 = st.columns(3)
    p_rm = c1.multiselect("Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.p_id}")
    p_wp = c2.multiselect("Bahan WIP", st.session_state.db_wip['nama'].tolist(), key=f"pwp_{st.session_state.p_id}")
    p_fg = c3.multiselect("Bahan FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.p_id}")
    
    if p_rm or p_wp or p_fg:
        res_p = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0,'isi':[]}
        for x in p_rm:
            r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
            q = st.number_input(f"Gram Mentah {x}", key=f"pqrm_{x}")/r['berat']
            d = get_nutrisi_calculated(q, r, 'RM')
            for k in res_p: 
                if k!='isi': res_p[k]+=d[k]
            res_p['isi'].append(f"{x}")
        for x in p_wp:
            r = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
            q = st.number_input(f"Gram WIP {x}", value=float(r['berat_porsi_gr']), key=f"pqwp_{x}")/r['berat_porsi_gr']
            d = get_nutrisi_calculated(q, r, 'WIP')
            for k in res_p:
                if k!='isi': res_p[k]+=d[k]
            res_p['isi'].append(f"{x}")
        for x in p_fg:
            r = st.session_state.db_fg[st.session_state.db_fg['nama']==x].iloc[0]
            q = st.number_input(f"Gram FG {x}", value=float(r['berat_porsi_gr']), key=f"pqfg_{x}")/r['berat_porsi_gr']
            d = get_nutrisi_calculated(q, r, 'WIP')
            for k in res_p:
                if k!='isi': res_p[k]+=d[k]
            res_p['isi'].append(f"{x}")
            
        st.divider()
        st.metric("Total Kalori Paket", f"{res_p['k']:,.1f} kkal")
        st.plotly_chart(px.pie(values=[res_p['p'],res_p['l'],res_p['ka']], names=['Protein','Lemak','Karbo'], hole=0.4))
