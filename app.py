import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v13.0", layout="wide")

# --- 1. FUNGSI PERSISTENSI DATA (LOCAL STORAGE) ---
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
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data("db_bahan.csv", ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"])

if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data("db_wip.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data("db_fg.csv", ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"])

if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data("db_paket.csv", ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"])

# --- 3. HELPER KALKULASI GIZI (PRESISI v11.0) ---
def get_nutrisi_calculated(qty, row, source_type='RM'):
    if source_type == 'RM':
        gr_mentah = qty * float(row['berat'])
        factor = (gr_mentah / 100) * (float(row['bdd']) / 100)
        return {
            'k': float(row['kalori']) * factor,
            'p': float(row['protein']) * factor,
            'l': float(row['lemak']) * factor,
            'ka': float(row['karbo']) * factor,
            'h': float(row['harga']) * qty,
            'g': gr_mentah
        }
    else: # WIP atau FG
        ratio = qty # Qty di sini bertindak sebagai pengali porsi
        return {
            'k': float(row['kal_porsi']) * ratio,
            'p': float(row['pro_porsi']) * ratio,
            'l': float(row['lem_porsi']) * ratio,
            'ka': float(row['kar_porsi']) * ratio,
            'h': float(row['hpp_porsi']) * ratio,
            'g': float(row['berat_porsi_gr']) * ratio
        }

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v13.0")
nav = st.sidebar.radio("Alur Produksi", [
    "📦 1. Database Bahan Baku (RM)", 
    "📥 2. Upload Master Data",
    "🍳 3. Master Resep Dasar (WIP)", 
    "🍱 4. Finished Goods (FG)",
    "🛒 5. Set Menu (Paket Jual)"
])

# --- MODUL 1: DATABASE BAHAN ---
if nav == "1. Database Bahan Baku (RM)":
    st.title("📂 Database Bahan Baku (Raw Material)")
    search = st.text_input("🔍 Cari Bahan...")
    df_disp = st.session_state.db_bahan
    if search: df_disp = df_disp[df_disp['nama'].str.contains(search, case=False)]
    edited = st.data_editor(df_disp, use_container_width=True, num_rows="dynamic", key="ed_rm")
    if st.button("💾 Simpan Perubahan Bahan"):
        st.session_state.db_bahan = edited.fillna(0)
        save_data(st.session_state.db_bahan, "db_bahan.csv"); st.success("Database RM Diperbarui!")

# --- MODUL 2: UPLOAD DATA ---
elif nav == "2. Upload Master Data":
    st.title("📥 Upload Database Massal")
    up = st.file_uploader("Pilih file CSV/Excel", type=["csv", "xlsx"])
    if up and st.button("🚀 Jalankan Sinkronisasi Massal"):
        try:
            df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
            df_new.columns = df_new.columns.str.strip().str.lower().str.replace('\n', ' ')
            mapping = {'satuan_beli_uom':'uom','berat_bersih_per_uom_gr':'berat','harga_beli_per_uom':'harga'}
            df_new = df_new.rename(columns=mapping)
            st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
            save_data(st.session_state.db_bahan, "db_bahan.csv"); st.success("Sinkronisasi Berhasil!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- MODUL 3: MASTER RESEP (WIP) ---
elif nav == "3. Master Resep Dasar (WIP)":
    st.title("🍳 Master Resep Setengah Jadi (WIP)")
    if "wip_id" not in st.session_state: st.session_state.wip_id = 0
    t1, t2 = st.tabs(["📝 Formulasi WIP", "📋 Database WIP"])
    with t1:
        nm = st.text_input("Nama Resep WIP (Contoh: Sambal)", key=f"wnm_{st.session_state.wip_id}")
        it = st.multiselect("Pilih Bahan Baku (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"wit_{st.session_state.wip_id}")
        if it:
            res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for i in it:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==i].iloc[0]
                q = st.number_input(f"Qty {i} ({r['uom']})", min_value=0.0, key=f"wq_{i}_{st.session_state.wip_id}")
                d = get_nutrisi_calculated(q, r, 'RM')
                for k in res: res[k]+=d[k]
            st.divider()
            y = st.number_input("Total Berat Matang WIP (gr)", value=max(res['g'],1.0), key=f"wy_{st.session_state.wip_id}")
            p = st.number_input("Jumlah Porsi", min_value=1, key=f"wp_{st.session_state.wip_id}")
            if st.button("💾 Simpan WIP & Reset"):
                new = pd.DataFrame([{"nama":nm, "berat_porsi_gr":y/p, "kal_porsi":res['k']/p, "pro_porsi":res['p']/p, "lem_porsi":res['l']/p, "kar_porsi":res['ka']/p, "hpp_porsi":res['h']/p}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new], ignore_index=True)
                save_data(st.session_state.db_wip, "db_wip.csv"); st.session_state.wip_id+=1; st.rerun()
    with t2:
        ed = st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic", key="ed_wip")
        if st.button("💾 Update Database WIP"): st.session_state.db_wip = ed; save_data(ed, "db_wip.csv"); st.success("WIP Updated!")

# --- MODUL 4: FINISHED GOODS (RM + WIP) ---
elif nav == "4. Finished Goods (FG)":
    st.title("🍱 Finished Goods (Gabungan RM + WIP)")
    if "fg_id" not in st.session_state: st.session_state.fg_id = 0
    t1, t2 = st.tabs(["🆕 Buat Produk FG", "📋 Database FG"])
    with t1:
        nm_fg = st.text_input("Nama Produk Jadi (FG)", key=f"fnm_{st.session_state.fg_id}")
        c1, c2 = st.columns(2)
        sel_rm = c1.multiselect("Pilih Bahan Baku (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.fg_id}")
        sel_wp = c2.multiselect("Pilih Resep Setengah Jadi (WIP)", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.fg_id}")
        if sel_rm or sel_wp:
            res_fg = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for x in sel_rm:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x} ({r['uom']})", key=f"fqrm_{x}_{st.session_state.fg_id}")
                d = get_nutrisi_calculated(q, r, 'RM')
                for k in res_fg: res_fg[k]+=d[k]
            for x in sel_wp:
                r = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Berapa Porsi {x}?", key=f"fqwp_{x}_{st.session_state.fg_id}")
                d = get_nutrisi_calculated(q, r, 'WIP')
                for k in res_fg: res_fg[k]+=d[k]
            st.divider()
            y_fg = st.number_input("Berat Produk Jadi FG (gr)", value=max(res_fg['g'], 1.0), key=f"fy_{st.session_state.fg_id}")
            if st.button("💾 Simpan Produk FG & Reset"):
                new_fg = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":y_fg, "kal_porsi":res_fg['k'], "pro_porsi":res_fg['p'], "lem_porsi":res_fg['l'], "kar_porsi":res_fg['ka'], "hpp_porsi":res_fg['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new_fg], ignore_index=True)
                save_data(st.session_state.db_fg, "db_fg.csv"); st.session_state.fg_id+=1; st.rerun()
    with t2:
        ed_fg = st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic", key="ed_fg")
        if st.button("💾 Update Database FG"): st.session_state.db_fg = ed_fg; save_data(ed_fg, "db_fg.csv"); st.success("FG Updated!")

# --- MODUL 5: SET MENU (RM + WIP + FG) ---
elif nav == "5. Set Menu (Paket Jual)":
    st.title("🛒 Set Menu / Paket Penjualan (RM + WIP + FG)")
    if "pkt_id" not in st.session_state: st.session_state.pkt_id = 0
    t1, t2 = st.tabs(["🆕 Buat Paket Jual", "📋 Database Paket"])
    with t1:
        if st.button("🧹 Clear & Reset Form Paket"): st.session_state.pkt_id += 1; st.rerun()
        nm_p = st.text_input("Nama Paket Jual", key=f"pnm_{st.session_state.pkt_id}")
        c1, c2, c3 = st.columns(3)
        prm = c1.multiselect("Tambah RM (Bahan Mentah)", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.pkt_id}")
        pwip = c2.multiselect("Tambah WIP (Resep Setengah Jadi)", st.session_state.db_wip['nama'].tolist(), key=f"pwip_{st.session_state.pkt_id}")
        pfg = c3.multiselect("Tambah FG (Produk Jadi)", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.pkt_id}")
        
        if prm or pwip or pfg:
            res_p = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0,'isi':[]}
            st.markdown("### 📋 Rincian Gramasi Paket")
            
            for x in prm:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q_gr = st.number_input(f"Gram Mentah: {x}", min_value=0.0, key=f"pqrm_{x}_{st.session_state.pkt_id}")
                d = get_nutrisi_calculated(q_gr/r['berat'], r, 'RM')
                for k in res_p: 
                    if k != 'isi': res_p[k]+=d[k]
                res_p['isi'].append(f"{x}({q_gr}g)")
            
            for x in pwip:
                r = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q_gr = st.number_input(f"Gram Matang WIP: {x}", value=float(r['berat_porsi_gr']), key=f"pqwp_{x}_{st.session_state.pkt_id}")
                d = get_nutrisi_calculated(q_gr/r['berat_porsi_gr'], r, 'WIP')
                for k in res_p:
                    if k != 'isi': res_p[k]+=d[k]
                res_p['isi'].append(f"{x}({q_gr}g)")

            for x in pfg:
                r = st.session_state.db_fg[st.session_state.db_fg['nama']==x].iloc[0]
                q_gr = st.number_input(f"Gram Produk FG: {x}", value=float(r['berat_porsi_gr']), key=f"pqfg_{x}_{st.session_state.pkt_id}")
                d = get_nutrisi_calculated(q_gr/r['berat_porsi_gr'], r, 'FG')
                for k in res_p:
                    if k != 'isi': res_p[k]+=d[k]
                res_p['isi'].append(f"{x}({q_gr}g)")

            st.divider()
            m1, m2, m3 = st.columns([1,1,2])
            m1.metric("Total Energi", f"{res_p['k']:,.1f} kkal"); m1.metric("Total HPP", f"Rp {res_p['h']:,.0f}")
            m2.metric("Total Berat", f"{res_p['g']:,.1f} g")
            with m3:
                st.plotly_chart(px.pie(values=[res_p['p'],res_p['l'],res_p['ka']], names=['Protein','Lemak','Karbo'], title="Macro Ratio Paket", hole=0.4), use_container_width=True)

            if st.button("💾 Simpan Paket Jual"):
                new_p = pd.DataFrame([{"nama_paket":nm_p, "rincian_isi":", ".join(res_p['isi']), "total_hpp":res_p['h'], "total_kalori":res_p['k'], "pro_total":res_p['p'], "lem_total":res_p['l'], "kar_total":res_p['ka']}])
                st.session_state.db_paket = pd.concat([st.session_state.db_paket, new_p], ignore_index=True)
                save_data(st.session_state.db_paket, "db_paket.csv"); st.success("Paket Jual Disimpan!"); st.rerun()
    with t2:
        ed_p = st.data_editor(st.session_state.db_paket, use_container_width=True, num_rows="dynamic", key="ed_p")
        if st.button("💾 Update Database Paket"): st.session_state.db_paket = ed_p; save_data(ed_p, "db_paket.csv"); st.success("Paket Database Updated!")
