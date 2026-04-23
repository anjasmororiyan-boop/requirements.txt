import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v23.0", layout="wide")

# --- 1. SISTEM PERSISTENSI DATA ---
def load_data_permanent(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df[columns].fillna(0)
        except:
            return pd.DataFrame(columns=columns)
    df_new = pd.DataFrame(columns=columns)
    df_new.to_csv(file_name, index=False)
    return df_new

def save_data_permanent(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE ---
cols_rm = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
cols_master = ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"]
cols_pkt = ["nama_paket", "rincian_isi", "total_hpp", "total_kalori", "pro_total", "lem_total", "kar_total"]

if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data_permanent("db_bahan.csv", cols_rm)
if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data_permanent("db_wip.csv", cols_master)
if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data_permanent("db_fg.csv", cols_master)
if 'db_paket' not in st.session_state:
    st.session_state.db_paket = load_data_permanent("db_paket.csv", cols_pkt)

# --- 3. FUNGSI KALKULASI GIZI ---
def universal_calc(qty, row, source_type='RM'):
    try:
        qty = float(qty) if qty else 0.0
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
        else:
            return {
                'k': float(row['kal_porsi']) * qty,
                'p': float(row['pro_porsi']) * qty,
                'l': float(row['lem_porsi']) * qty,
                'ka': float(row['kar_porsi']) * qty,
                'h': float(row['hpp_porsi']) * qty,
                'g': float(row['berat_porsi_gr']) * qty
            }
    except:
        return {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v23.0")
nav = st.sidebar.radio("Navigasi", ["📦 Database RM", "🍳 Master WIP", "🍱 Master FG", "🛒 Set Menu (Paket)"])

# --- MODUL 1: DATABASE RM ---
if nav == "📦 Database RM":
    st.title("📂 Database Bahan Baku")
    ed_rm = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Simpan Perubahan RM"):
        st.session_state.db_bahan = ed_rm.fillna(0)
        save_data_permanent(st.session_state.db_bahan, "db_bahan.csv")
        st.success("Data RM Tersimpan!"); st.rerun()
elif nav == "📥 Upload Data":
    st.title("📥 Upload Massal")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up and st.button("🚀 Sinkronisasi"):
        df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data_permanent(st.session_state.db_bahan, "db_bahan.csv"); st.success("Upload Berhasil!"); st.rerun()
# --- MODUL 2: MASTER WIP (FIXED SAVE LOGIC) ---
elif nav == "🍳 Master WIP":
    st.title("🍳 Master Resep Setengah Jadi (WIP)")
    if "w_id" not in st.session_state: st.session_state.w_id = 0
    t1, t2 = st.tabs(["📝 Formulasi WIP", "📋 Database WIP"])
    
    with t1:
        nm_w = st.text_input("Nama WIP", key=f"wnm_{st.session_state.w_id}")
        sel_b = st.multiselect("Pilih Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"wsel_{st.session_state.w_id}")
        if sel_b:
            res_w = {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}
            for b in sel_b:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==b].iloc[0]
                q = st.number_input(f"Qty {b} ({row['uom']})", key=f"wq_{b}_{st.session_state.w_id}")
                d = universal_calc(q, row, 'RM')
                for k in res_w: res_w[k] += d[k]
            
            y_w = st.number_input("Yield Matang (gr)", value=max(res_w['g'], 1.0), key=f"wy_{st.session_state.w_id}")
            st.info(f"Estimasi Gizi WIP: {res_w['k']:.1f} kkal | HPP: Rp {res_w['h']:,.0f}")
            
            if st.button("💾 Simpan Master WIP"):
                new_w = pd.DataFrame([{"nama": nm_w, "berat_porsi_gr": y_w, "kal_porsi": res_w['k'], "pro_porsi": res_w['p'], "lem_porsi": res_w['l'], "kar_porsi": res_w['ka'], "hpp_porsi": res_w['h']}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new_w], ignore_index=True)
                save_data_permanent(st.session_state.db_wip, "db_wip.csv")
                st.session_state.w_id += 1; st.success("WIP Berhasil Disimpan!"); st.rerun()
    with t2:
        st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic")

# --- MODUL 3: MASTER FG (FIXED CALCULATION) ---
elif nav == "🍱 Master FG":
    st.title("🍱 Master Finished Goods (FG)")
    if "f_id" not in st.session_state: st.session_state.f_id = 0
    t1, t2 = st.tabs(["📝 Formulasi FG", "📋 Database FG"])
    
    with t1:
        nm_f = st.text_input("Nama Produk Jadi", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Tambah RM", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.f_id}")
        s_wp = c2.multiselect("Tambah WIP", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.f_id}")
        
        if s_rm or s_wp:
            res_f = {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}
            for x in s_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x}", key=f"fqrm_{x}_{st.session_state.f_id}")
                d = universal_calc(q, row, 'RM'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            for x in s_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q_p = st.number_input(f"Porsi WIP: {x}", value=1.0, key=f"fqwp_{x}_{st.session_state.f_id}")
                d = universal_calc(q_p, row, 'WIP'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            
            st.divider()
            st.metric("Total Kalori FG", f"{res_f['k']:.1f} kkal")
            st.metric("Total HPP FG", f"Rp {res_f['h']:,.0f}")
            
            if st.button("💾 Simpan Master FG"):
                new_f = pd.DataFrame([{"nama": nm_f, "berat_porsi_gr": res_f['g'], "kal_porsi": res_f['k'], "pro_porsi": res_f['p'], "lem_porsi": res_f['l'], "kar_porsi": res_f['ka'], "hpp_porsi": res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new_f], ignore_index=True)
                save_data_permanent(st.session_state.db_fg, "db_fg.csv")
                st.session_state.f_id += 1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")

# --- MODUL 1 & 2 (DATABASE RM & UPLOAD) ---
if nav == "📦 Database RM":
    st.title("📂 Database Bahan Baku")
    ed_rm = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Simpan Perubahan RM"):
        st.session_state.db_bahan = ed_rm.fillna(0)
        save_data_permanent(st.session_state.db_bahan, "db_bahan.csv"); st.success("Data RM Diperbarui!")



st.title("🍳 Master Resep Detail (WIP)")

# --- Section 1: Metadata ---
col1, col2 = st.columns(2)
with col1:
    wip_name = st.text_input("Nama WIP", placeholder="Contoh: Adonan Roti Manis")
    category = st.selectbox("Kategori", ["Bakery", "Pastry", "Sauce", "Syrup"])
with col2:
    target_qty = st.number_input("Target Batch (Gram)", min_value=0)
    shelf_life = st.number_input("Masa Simpan (Hari)", min_value=0)

st.divider()

# --- Section 2: Formulasi (Data Editor) ---
st.subheader("🛒 Formulasi Bahan")
df_template = pd.DataFrame(
    [{"Bahan Baku": "", "Qty (gr)": 0.0, "Harga/kg": 0, "Catatan": ""}]
)
edited_df = st.data_editor(df_template, num_rows="dynamic", use_container_width=True)

# Kalkulasi sederhana
total_weight = edited_df["Qty (gr)"].sum()
st.info(text=f"Total Berat Input: {total_weight} gr")

# --- Section 3: SOP ---
st.subheader("📝 Instruksi Produksi (SOP)")
instructions = st.text_area("Tuliskan langkah-langkah pembuatan di sini...")

# --- Section 4: Tombol Aksi ---
if st.button("Simpan Resep Master", type="primary"):
    st.success(f"Resep {wip_name} berhasil disimpan ke Database!")

# --- MODUL 4: FG (FIXED CALCULATION) ---
elif nav == "🍱 Master FG":
    st.title("🍱 Master Finished Goods (FG)")
    t1, t2 = st.tabs(["📝 Buat FG", "📋 Database"])
    with t1:
        if "f_id" not in st.session_state: st.session_state.f_id = 0
        nm_f = st.text_input("Nama FG", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Bahan RM", st.session_state.db_bahan['nama'].tolist())
        s_wp = c2.multiselect("Bahan WIP", st.session_state.db_wip['nama'].tolist())
        if s_rm or s_wp:
            res_f = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for x in s_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x}", key=f"fqrm_{x}"); d = universal_calc(q, row, 'RM')
                for k in res_f: res_f[k]+=d[k]
            for x in s_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q_porsi = st.number_input(f"Berapa Porsi {x} matang?", value=1.0, key=f"fqwp_{x}")
                # Kalkulasi berdasarkan jumlah porsi matang
                d = universal_calc(q_porsi * row['berat_porsi_gr'], row, 'WIP')
                for k in res_f: res_f[k]+=d[k]
            st.info(f"Kalkulasi FG: {res_f['k']:.1f} kkal | HPP: Rp {res_f['h']:,.0f}")
            if st.button("💾 Simpan FG"):
                new = pd.DataFrame([{"nama":nm_f, "berat_porsi_gr":res_f['g'], "kal_porsi":res_f['k'], "pro_porsi":res_f['p'], "lem_porsi":res_f['l'], "kar_porsi":res_f['ka'], "hpp_porsi":res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new], ignore_index=True); save_data_permanent(st.session_state.db_fg, "db_fg.csv"); st.session_state.f_id+=1; st.rerun()
    with t2:
        ed_fg = st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan FG"):
            st.session_state.db_fg = ed_fg.fillna(0); save_data_permanent(st.session_state.db_fg, "db_fg.csv"); st.success("Updated!")

# --- MODUL 5: SET MENU (COMPLETED) ---
elif nav == "🛒 Set Menu (Paket)":
    st.title("🛒 Set Menu / Paket Jual")
    tab_p1, tab_p2 = st.tabs(["📝 Susun Paket", "📋 Database Paket"])
    with tab_p1:
        if "p_id" not in st.session_state: st.session_state.p_id = 0
        nm_pkt = st.text_input("Nama Paket Jual", key=f"pkt_nm_{st.session_state.p_id}")
        margin = st.slider("Target Food Cost (%)", 10, 50, 30)
        c1, c2, c3 = st.columns(3)
        prm = c1.multiselect("Tambah RM", st.session_state.db_bahan['nama'].tolist())
        pwp = c2.multiselect("Tambah WIP", st.session_state.db_wip['nama'].tolist())
        pfg = c3.multiselect("Tambah FG", st.session_state.db_fg['nama'].tolist())
        
        if prm or pwp or pfg:
            p_total = {'k':0,'p':0,'l':0,'ka':0,'h':0,'b':0, 'isi':[]}
            for x in prm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Gr: {x}", key=f"pqrm_{x}"); d = universal_calc(q/row['berat'], row, 'RM')
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_total[k]+=d[v]
                p_total['isi'].append(x)
            for x in pwp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Gr: {x} (matang)", value=float(row['berat_porsi_gr']), key=f"pqwp_{x}")
                d = universal_calc(q, row, 'WIP')
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_total[k]+=d[v]
                p_total['isi'].append(x)
            for x in pfg:
                row = st.session_state.db_fg[st.session_state.db_fg['nama']==x].iloc[0]
                q = st.number_input(f"Gr: {x} (produk)", value=float(row['berat_porsi_gr']), key=f"pqfg_{x}")
                d = universal_calc(q, row, 'FG')
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_total[k]+=d[v]
                p_total['isi'].append(x)
            
            st.divider()
            m1, m2, m3 = st.columns([1,1,2])
            m1.metric("Total HPP", f"Rp {p_total['h']:,.0f}")
            m1.metric("Kalori", f"{p_total['k']:,.1f} kkal")
            m2.metric("Saran Jual", f"Rp {p_total['h']/(margin/100):,.0f}")
            with m3:
                if p_total['k'] > 0:
                    fig = px.pie(values=[p_total['p'], p_total['l'], p_total['ka']], names=['Protein','Lemak','Karbo'], hole=0.4, title="Macro Nutrisi")
                    st.plotly_chart(fig, use_container_width=True)
            
            if st.button("💾 Simpan Paket Permanen"):
                new_pkt = pd.DataFrame([{"nama_paket":nm_pkt, "rincian_isi":", ".join(p_total['isi']), "total_hpp":p_total['h'], "total_kalori":p_total['k'], "pro_total":p_total['p'], "lem_total":p_total['l'], "kar_total":p_total['ka']}])
                st.session_state.db_paket = pd.concat([st.session_state.db_paket, new_pkt], ignore_index=True); save_data_permanent(st.session_state.db_paket, "db_paket.csv"); st.session_state.p_id+=1; st.rerun()
    with tab_p2:
        st.dataframe(st.session_state.db_paket, use_container_width=True)
