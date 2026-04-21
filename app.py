import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro ERP v12.5", layout="wide")

# --- 1. FUNGSI PERSISTENSI DATA ---
def load_data(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df
        except: return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE ---
# Tier 1: Raw Material (Bahan Baku)
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("db_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

# Tier 2: WIP (Work In Process / Resep Dasar)
if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data("db_wip.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# Tier 3: Finished Goods (Produk Jadi)
if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data("db_fg.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

# Tier 4: Master Paket
if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data("db_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"])

# --- 3. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v12.5")
nav = st.sidebar.radio("Alur Produksi & Penjualan", [
    "📦 1. Database Bahan Baku (RM)", 
    "📥 2. Upload Master Data",
    "🍳 3. Master Resep Dasar (WIP)", 
    "🍱 4. Finished Goods (FG)",
    "🛒 5. Set Menu (Paket Jual)"
])

# --- HELPER: KALKULASI GIZI ---
def get_nutrisi(qty, row, type='RM'):
    if type == 'RM':
        gr = qty * float(row['berat'])
        f = (gr/100) * (float(row['bdd'])/100)
        return {'k': float(row['kalori'])*f, 'p': float(row['protein'])*f, 'l': float(row['lemak'])*f, 'ka': float(row['karbo'])*f, 'h': float(row['harga'])*qty, 'g': gr}
    else:
        return {'k': float(row['kal_porsi'])*qty, 'p': float(row['pro_porsi'])*qty, 'l': float(row['lem_porsi'])*qty, 'ka': float(row['kar_porsi'])*qty, 'h': float(row['hpp_porsi'])*qty, 'g': float(row['berat_porsi_gr'])*qty}

# --- MODUL 1: DATABASE BAHAN ---
if nav == "1. Database Bahan Baku (RM)":
    st.title("📂 Database Bahan Baku (Raw Material)")
    edited = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Simpan Perubahan Bahan"):
        st.session_state.db_bahan = edited.fillna(0)
        save_data(st.session_state.db_bahan, "db_bahan.csv"); st.success("Tersimpan!")

# --- MODUL 2: UPLOAD DATA ---
elif nav == "2. Upload Master Data":
    st.title("📥 Upload Database Massal")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up and st.button("🚀 Jalankan Sinkronisasi"):
        df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
        df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
        df_new = df_new.rename(columns={'satuan_beli_uom':'uom','berat_bersih_per_uom_gr':'berat','harga_beli_per_uom':'harga'})
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data(st.session_state.db_bahan, "db_bahan.csv"); st.success("Data Sinkron!"); st.rerun()

# --- MODUL 3: MASTER RESEP (WIP) ---
elif nav == "3. Master Resep Dasar (WIP)":
    st.title("🍳 Master Resep (Bumbu/WIP)")
    if "wip_id" not in st.session_state: st.session_state.wip_id = 0
    t1, t2 = st.tabs(["📝 Buat WIP", "📋 Database WIP"])
    with t1:
        nm = st.text_input("Nama Resep WIP", key=f"wnm_{st.session_state.wip_id}")
        it = st.multiselect("Bahan Baku", st.session_state.db_bahan['nama'].tolist(), key=f"wit_{st.session_state.wip_id}")
        if it:
            res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for i in it:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==i].iloc[0]
                q = st.number_input(f"Qty {i}", min_value=0.0, key=f"wq_{i}_{st.session_state.wip_id}")
                d = get_nutrisi(q, r, 'RM')
                for k in res: res[k]+=d[k]
            y = st.number_input("Yield Matang (gr)", value=max(res['g'],1.0), key=f"wy_{st.session_state.wip_id}")
            p = st.number_input("Porsi", min_value=1, key=f"wp_{st.session_state.wip_id}")
            if st.button("💾 Simpan WIP"):
                new = pd.DataFrame([{"nama":nm, "berat_porsi_gr":y/p, "kal_porsi":res['k']/p, "pro_porsi":res['p']/p, "lem_porsi":res['l']/p, "kar_porsi":res['ka']/p, "hpp_porsi":res['h']/p}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new], ignore_index=True)
                save_data(st.session_state.db_wip, "db_wip.csv"); st.session_state.wip_id+=1; st.rerun()
    with t2:
        ed = st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Update WIP"): st.session_state.db_wip = ed; save_data(ed, "db_wip.csv"); st.rerun()

# --- MODUL 4: FINISHED GOODS (HYBRID RM + WIP) ---
elif nav == "4. Finished Goods (FG)":
    st.title("🍱 Finished Goods Production (RM + WIP)")
    if "fg_id" not in st.session_state: st.session_state.fg_id = 0
    t1, t2 = st.tabs(["🆕 Buat FG", "📋 Database FG"])
    with t1:
        nm_fg = st.text_input("Nama Produk FG", key=f"fnm_{st.session_state.fg_id}")
        c1, c2 = st.columns(2)
        rm_f = c1.multiselect("Pilih Bahan Mentah (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.fg_id}")
        wp_f = c2.multiselect("Pilih Resep (WIP)", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.fg_id}")
        if rm_f or wp_f:
            res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for x in rm_f:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x}", key=f"fqrm_{x}_{st.session_state.fg_id}")
                d = get_nutrisi(q, r, 'RM')
                for k in res: res[k]+=d[k]
            for x in wp_f:
                r = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Porsi {x}", key=f"fqwp_{x}_{st.session_state.fg_id}")
                d = get_nutrisi(q, r, 'WIP')
                for k in res: res[k]+=d[k]
            y = st.number_input("Yield FG (gr)", value=max(res['g'],1.0))
            if st.button("💾 Simpan FG"):
                new = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":y, "kal_porsi":res['k'], "pro_porsi":res['p'], "lem_porsi":res['l'], "kar_porsi":res['ka'], "hpp_porsi":res['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new], ignore_index=True)
                save_data(st.session_state.db_fg, "db_fg.csv"); st.session_state.fg_id+=1; st.rerun()
    with t2:
        ed = st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Update FG"): st.session_state.db_fg = ed; save_data(ed, "db_fg.csv"); st.rerun()

# --- MODUL 5: SET MENU (UNIVERSAL AGGREGATOR) ---
elif nav == "5. Set Menu (Paket Jual)":
    st.title("🛒 Set Menu / Paket Penjualan (RM + WIP + FG)")
    if "pkt_id" not in st.session_state: st.session_state.pkt_id = 0
    t1, t2 = st.tabs(["🆕 Buat Paket Baru", "📋 Database Paket"])
    with t1:
        if st.button("🧹 Clear & Reset Form"): st.session_state.pkt_id += 1; st.rerun()
        nm_p = st.text_input("Nama Paket", key=f"pnm_{st.session_state.pkt_id}")
        col1, col2, col3 = st.columns(3)
        prm = col1.multiselect("Tambah RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.pkt_id}")
        pwip = col2.multiselect("Tambah WIP", st.session_state.db_wip['nama'].tolist(), key=f"pwip_{st.session_state.pkt_id}")
        pfg = col3.multiselect("Tambah FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.pkt_id}")
        if prm or pwip or pfg:
            res_p = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0,'isi':[]}
            for x in prm:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Gr {x}", key=f"pqrm_{x}")/r['berat']
                d = get_nutrisi(q, r, 'RM'); [res_p.update({k: res_p[k]+d[k]}) for k in res_p if k!='isi']; res_p['isi'].append(f"{x}")
            for x in pwip:
                r = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Gr {x}", value=float(r['berat_porsi_gr']), key=f"pqwp_{x}")/r['berat_porsi_gr']
                d = get_nutrisi(q, r, 'WIP'); [res_p.update({k: res_p[k]+d[k]}) for k in res_p if k!='isi']; res_p['isi'].append(f"{x}")
            for x in pfg:
                r = st.session_state.db_fg[st.session_state.db_fg['nama']==x].iloc[0]
                q = st.number_input(f"Gr {x}", value=float(r['berat_porsi_gr']), key=f"pqfg_{x}")/r['berat_porsi_gr']
                d = get_nutrisi(q, r, 'WIP'); [res_p.update({k: res_p[k]+d[k]}) for k in res_p if k!='isi']; res_p['isi'].append(f"{x}")
            st.divider()
            m1, m2, m3 = st.columns([1,1,2])
            m1.metric("Energi", f"{res_p['k']:,.1f} kkal"); m1.metric("HPP", f"Rp {res_p['h']:,.0f}")
            m2.metric("Berat", f"{res_p['g']:,.1f} g"); st.plotly_chart(px.pie(values=[res_p['p'],res_p['l'],res_p['ka']], names=['Pro','Lem','Kar']))
            if st.button("💾 Simpan Paket"):
                new = pd.DataFrame([{"nama_paket":nm_p, "rincian_isi":", ".join(res_p['isi']), "total_hpp":res_p['h'], "total_kalori":res_p['k'], "pro_total":res_p['p'], "lem_total":res_p['l'], "kar_total":res_p['ka']}])
                st.session_state.db_paket = pd.concat([st.session_state.db_paket, new], ignore_index=True)
                save_data(st.session_state.db_paket, "db_paket.csv"); st.success("Paket Disimpan!"); st.rerun()
    with t2:
        ed = st.data_editor(st.session_state.db_paket, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Update Paket"): st.session_state.db_paket = ed; save_data(ed, "db_paket.csv"); st.rerun()
