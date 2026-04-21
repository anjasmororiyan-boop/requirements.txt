import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v19.0", layout="wide")

# --- 1. SISTEM PERSISTENSI DATA ---
def load_data_permanent(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name).fillna(0)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df[columns]
        except: return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

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

# --- 3. FUNGSI KALKULASI GIZI PRESISI (FIXED) ---
def universal_calc(qty, row, source_type='RM'):
    """
    Rumus Standar: (Berat/100) * (BDD/100) * Nilai_Nutrisi
    """
    try:
        qty = float(qty) if qty else 0.0
        if source_type == 'RM':
            # qty adalah jumlah satuan beli (misal 0.5 kg)
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
            # qty adalah berat matang yang digunakan dalam gram
            berat_referensi = float(row['berat_porsi_gr']) if float(row['berat_porsi_gr']) > 0 else 1.0
            ratio = qty / berat_referensi
            return {
                'k': float(row['kal_porsi']) * ratio,
                'p': float(row['pro_porsi']) * ratio,
                'l': float(row['lem_porsi']) * ratio,
                'ka': float(row['kar_porsi']) * ratio,
                'h': float(row['hpp_porsi']) * ratio,
                'g': qty
            }
    except:
        return {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v19.0")
nav = st.sidebar.radio("Menu Navigasi", ["📦 Database RM", "📥 Upload Data", "🍳 Master WIP", "🍱 Master FG", "🛒 Set Menu (Paket)"])

# --- MODUL 3: WIP (FIXED FORMULA) ---
if nav == "🍳 Master WIP":
    st.title("🍳 Master Resep Dasar (WIP)")
    t1, t2 = st.tabs(["📝 Formulasi WIP", "📋 Database WIP"])
    with t1:
        if "w_id" not in st.session_state: st.session_state.w_id = 0
        nm_w = st.text_input("Nama WIP", key=f"wnm_{st.session_state.w_id}")
        sel_b = st.multiselect("Pilih Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"wsel_{st.session_state.w_id}")
        if sel_b:
            res_w = {'k':0.0,'p':0.0,'l':0.0,'ka':0.0,'h':0.0,'g':0.0}
            for b in sel_b:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==b].iloc[0]
                q = st.number_input(f"Qty {b} ({row['uom']})", key=f"wq_{b}_{st.session_state.w_id}")
                d = universal_calc(q, row, 'RM')
                for k in res_w: res_w[k]+=d[k]
            y = st.number_input("Yield Berat Matang (gr)", value=max(res_w['g'], 1.0), key=f"wy_{st.session_state.w_id}")
            if st.button("💾 Simpan Master WIP"):
                new = pd.DataFrame([{"nama":nm_w, "berat_porsi_gr":y, "kal_porsi":res_w['k'], "pro_porsi":res_w['p'], "lem_porsi":res_w['l'], "kar_porsi":res_w['ka'], "hpp_porsi":res_w['h']}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new], ignore_index=True); save_data_permanent(st.session_state.db_wip, "db_wip.csv"); st.session_state.w_id+=1; st.rerun()

# --- MODUL 4: FG (FIXED CALCULATION) ---
elif nav == "🍱 Master FG":
    st.title("🍱 Master Finished Goods (FG)")
    t1, t2 = st.tabs(["📝 Buat FG Baru", "📋 Database FG"])
    with t1:
        if "f_id" not in st.session_state: st.session_state.f_id = 0
        nm_fg = st.text_input("Nama FG", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.f_id}")
        s_wp = c2.multiselect("Resep WIP", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.f_id}")
        if s_rm or s_wp:
            res_f = {'k':0.0,'p':0.0,'l':0.0,'ka':0.0,'h':0.0,'g':0.0}
            for x in s_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x}", key=f"fqrm_{x}_{st.session_state.f_id}")
                d = universal_calc(q, row, 'RM'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            for x in s_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q_gr = st.number_input(f"Gram Matang {x}", value=float(row['berat_porsi_gr']), key=f"fqwp_{x}_{st.session_state.f_id}")
                d = universal_calc(q_gr, row, 'WIP'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            st.info(f"Kalkulasi FG: {res_f['k']:.1f} kkal | HPP: Rp {res_f['h']:,.0f}")
            if st.button("💾 Simpan Master FG"):
                new = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":res_f['g'], "kal_porsi":res_f['k'], "pro_porsi":res_f['p'], "lem_porsi":res_f['l'], "kar_porsi":res_f['ka'], "hpp_porsi":res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new], ignore_index=True); save_data_permanent(st.session_state.db_fg, "db_fg.csv"); st.session_state.f_id+=1; st.rerun()

# --- MODUL 5: PAKET (FIXED CALCULATION & GRAPH) ---
elif nav == "🛒 Set Menu (Paket)":
    st.title("🛒 Set Menu / Paket Jual")
    tab_p1, tab_p2 = st.tabs(["📝 Susun Paket", "📋 Database Paket"])
    with tab_p1:
        if "p_id" not in st.session_state: st.session_state.p_id = 0
        if st.button("🧹 Clear Form"): st.session_state.p_id += 1; st.rerun()
        nm_pkt = st.text_input("Nama Paket", key=f"pnm_{st.session_state.p_id}")
        margin = st.slider("Target Food Cost (%)", 10, 50, 30, key=f"psl_{st.session_state.p_id}")
        c1, c2, c3 = st.columns(3)
        prm = c1.multiselect("Pilih RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.p_id}")
        pwp = c2.multiselect("Pilih WIP", st.session_state.db_wip['nama'].tolist(), key=f"pwp_{st.session_state.p_id}")
        pfg = c3.multiselect("Pilih FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.p_id}")
        if prm or pwp or pfg:
            p_res = {'k':0.0,'p':0.0,'l':0.0,'ka':0.0,'h':0.0,'b':0.0,'isi':[]}
            for x in prm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q_gr = st.number_input(f"Gr Mentah: {x}", key=f"pqrm_{x}")
                d = universal_calc(q_gr/row['berat'] if row['berat']>0 else 0, row, 'RM')
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
                p_res['isi'].append(x)
            for src, db in [('WIP', st.session_state.db_wip), ('FG', st.session_state.db_fg)]:
                choices = pwp if src == 'WIP' else pfg
                for x in choices:
                    row = db[db['nama']==x].iloc[0]
                    q_gr = st.number_input(f"Gr {src}: {x}", value=float(row['berat_porsi_gr']), key=f"pq{src}_{x}")
                    d = universal_calc(q_gr, row, src)
                    for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
                    p_res['isi'].append(x)
            st.divider()
            m1, m2, m3 = st.columns([1,1,2])
            m1.metric("HPP", f"Rp {p_res['h']:,.0f}"); m1.metric("Kalori", f"{p_res['k']:,.1f} kkal")
            m2.metric("Berat", f"{p_res['b']:,.1f} g"); m2.metric("Saran Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
            with m3:
                if p_res['k'] > 0:
                    fig = px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein','Lemak','Karbo'], hole=0.4, title="Macro Ratio")
                    st.plotly_chart(fig, use_container_width=True)
            if st.button("💾 Simpan Paket"):
                new_p = pd.DataFrame([{"nama_paket":nm_pkt, "rincian_isi":", ".join(p_res['isi']), "total_hpp":p_res['h'], "total_kalori":p_res['k'], "pro_total":p_res['p'], "lem_total":p_res['l'], "kar_total":p_res['ka']}])
                st.session_state.db_paket = pd.concat([st.session_state.db_paket, new_p], ignore_index=True); save_data_permanent(st.session_state.db_paket, "db_paket.csv"); st.session_state.p_id+=1; st.rerun()

# --- MODUL LAINNYA (DATABASE RM & UPLOAD) ---
else:
    st.info("Gunakan Sidebar untuk navigasi ke Database atau Upload.")
