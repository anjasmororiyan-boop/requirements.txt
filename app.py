import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost ERP v16.5", layout="wide")

# --- 1. FUNGSI PERSISTENSI DATA ---
def load_data_safe(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name).fillna(0)
            for col in columns:
                if col not in df.columns: df[col] = 0
            return df[columns]
        except: return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data_safe(df, file_name):
    df.to_csv(file_name, index=False)

# --- 2. INISIALISASI DATABASE ---
cols_rm = ["nama", "kalori", "protein", "lemak", "karbo", "bdd", "uom", "berat", "harga"]
cols_master = ["nama", "berat_porsi_gr", "kal_porsi", "pro_porsi", "lem_porsi", "kar_porsi", "hpp_porsi"]

if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = load_data_safe("db_bahan.csv", cols_rm)
if 'db_wip' not in st.session_state:
    st.session_state.db_wip = load_data_safe("db_wip.csv", cols_master)
if 'db_fg' not in st.session_state:
    st.session_state.db_fg = load_data_safe("db_fg.csv", cols_master)

# --- 3. FUNGSI KALKULASI GIZI (FIXED UNTUK FG) ---
def core_calculator(qty, row, source_type='RM'):
    try:
        qty = float(qty) if qty else 0.0
        if source_type == 'RM':
            # Hitung berdasarkan Database Bahan Baku
            gr_total = qty * float(row['berat'])
            factor = (gr_total / 100) * (float(row['bdd']) / 100)
            return {
                'k': float(row['kalori']) * factor,
                'p': float(row['protein']) * factor,
                'l': float(row['lemak']) * factor,
                'ka': float(row['karbo']) * factor,
                'h': float(row['harga']) * qty,
                'g': gr_total
            }
        else:
            # Hitung berdasarkan Master Resep (WIP)
            # Karena WIP sudah per porsi, qty di sini adalah jumlah porsi yang dipakai
            return {
                'k': float(row['kal_porsi']) * qty,
                'p': float(row['pro_porsi']) * qty,
                'l': float(row['lem_porsi']) * qty,
                'ka': float(row['kar_porsi']) * qty,
                'h': float(row['hpp_porsi']) * qty,
                'g': float(row['berat_porsi_gr']) * qty
            }
    except Exception as e:
        return {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}

# --- 4. SIDEBAR ---
st.sidebar.title("NutriCost ERP v16.5")
nav = st.sidebar.radio("Navigasi Utama", ["📦 1. Database Bahan", "🍳 2. Master Resep (WIP)", "🍱 3. Finished Goods (FG)", "🛒 4. Set Menu (Paket)"])

# --- MODUL 1: DATABASE BAHAN ---
if nav == "📦 1. Database Bahan":
    st.title("📂 Database Bahan Baku (RM)")
    edited = st.data_editor(st.session_state.db_bahan, use_container_width=True, num_rows="dynamic", key="ed_rm_165")
    if st.button("💾 Simpan Database RM"):
        st.session_state.db_bahan = edited.fillna(0)
        save_data_safe(st.session_state.db_bahan, "db_bahan.csv")
        st.success("Tersimpan!")

# --- MODUL 2: MASTER RESEP (WIP) ---
elif nav == "🍳 2. Master Resep (WIP)":
    st.title("🍳 Master Resep Setengah Jadi (WIP)")
    t1, t2 = st.tabs(["📝 Buat WIP", "📋 Database WIP"])
    with t1:
        if "w_id" not in st.session_state: st.session_state.w_id = 0
        nm_w = st.text_input("Nama WIP (Contoh: Sambal Goreng)", key=f"wnm_{st.session_state.w_id}")
        sel_b = st.multiselect("Pilih Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"wsb_{st.session_state.w_id}")
        if sel_b:
            res_w = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for b in sel_b:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==b].iloc[0]
                q = st.number_input(f"Qty {b}", min_value=0.0, key=f"wq_{b}")
                d = core_calculator(q, row, 'RM')
                for k in res_w: res_w[k]+=d[k]
            y = st.number_input("Yield Matang (gr)", value=max(res_w['g'], 1.0))
            p = st.number_input("Jumlah Porsi", min_value=1, value=1)
            if st.button("💾 Simpan Master WIP"):
                new = pd.DataFrame([{"nama":nm_w, "berat_porsi_gr":y/p, "kal_porsi":res_w['k']/p, "pro_porsi":res_w['p']/p, "lem_porsi":res_w['l']/p, "kar_porsi":res_w['ka']/p, "hpp_porsi":res_w['h']/p}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new], ignore_index=True)
                save_data_safe(st.session_state.db_wip, "db_wip.csv"); st.session_state.w_id+=1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic", key="dbw_165")

# --- MODUL 3: FINISHED GOODS (FG) ---
elif nav == "🍱 3. Finished Goods (FG)":
    st.title("🍱 Master Finished Goods (RM + WIP)")
    t1, t2 = st.tabs(["📝 Buat Produk FG", "📋 Database FG"])
    with t1:
        if "f_id" not in st.session_state: st.session_state.f_id = 0
        nm_fg = st.text_input("Nama Produk Jadi (FG)", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Pilih Bahan Baku (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"f_rm_{st.session_state.f_id}")
        s_wp = c2.multiselect("Pilih Resep Dasar (WIP)", st.session_state.db_wip['nama'].tolist(), key=f"f_wp_{st.session_state.f_id}")
        
        if s_rm or s_wp:
            res_f = {'k':0.0,'p':0.0,'l':0.0,'ka':0.0,'h':0.0,'g':0.0}
            st.markdown("### Rincian Input Komponen FG")
            
            for x in s_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty Mentah {x} ({row['uom']})", key=f"fqrm_{x}")
                d = core_calculator(q, row, 'RM')
                for k in res_f: res_f[k]+=d[k]
                
            for x in s_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Berapa Porsi {x} matang yang dipakai?", key=f"fqwp_{x}", value=1.0)
                d = core_calculator(q, row, 'WIP')
                for k in res_f: res_f[k]+=d[k]
                
            st.divider()
            y_fg = st.number_input("Total Berat Produk FG (gr)", value=max(res_f['g'], 1.0))
            
            # Tampilan Live Calculation
            st.info(f"**Live Gizi FG:** {res_f['k']:.1f} kkal | Pro: {res_f['p']:.1f}g | Lemak: {res_f['l']:.1f}g | HPP: Rp {res_f['h']:,.0f}")
            
            if st.button("💾 Simpan Master FG"):
                new_f = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":y_fg, "kal_porsi":res_f['k'], "pro_porsi":res_f['p'], "lem_porsi":res_f['l'], "kar_porsi":res_f['ka'], "hpp_porsi":res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new_f], ignore_index=True)
                save_data_safe(st.session_state.db_fg, "db_fg.csv")
                st.session_state.f_id += 1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic", key="dbf_165")

# --- MODUL 4: FG ---
elif nav == "🍱 4. Finished Goods (FG)":
    st.title("🍱 Master Finished Goods (FG)")
    if "f_id" not in st.session_state: st.session_state.f_id = 0
    t1, t2 = st.tabs(["🆕 Buat FG Baru", "📋 Database FG"])
    with t1:
        nm_fg = st.text_input("Nama FG", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Bahan Baku (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"f_rm_{st.session_state.f_id}")
        s_wp = c2.multiselect("Resep (WIP)", st.session_state.db_wip['nama'].tolist(), key=f"f_wp_{st.session_state.f_id}")
        if s_rm or s_wp:
            res_f = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for x in s_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Qty {x}", key=f"fqrm_{x}")
                d = global_calc(q, row, 'RM'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            for x in s_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Porsi {x}", key=f"fqwp_{x}")
                d = global_calc(q, row, 'WIP'); [res_f.update({k: res_f[k]+d[k]}) for k in res_f]
            if st.button("💾 Simpan FG"):
                new = pd.DataFrame([{"nama":nm_fg, "berat_porsi_gr":res_f['g'], "kal_porsi":res_f['k'], "pro_porsi":res_f['p'], "lem_porsi":res_f['l'], "kar_porsi":res_f['ka'], "hpp_porsi":res_f['h']}])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new], ignore_index=True); save_data_safe(st.session_state.db_fg, "db_fg.csv"); st.session_state.f_id+=1; st.rerun()
    with t2:
        st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")

# --- MODUL 5: PAKET ---
elif nav == "🛒 5. Set Menu (Paket)":
    st.title("🍱 Master Paket & Analisis Nutrisi")
    if "p_id" not in st.session_state: st.session_state.p_id = 0
    tab_a, tab_b = st.tabs(["🆕 Buat Paket", "🗄️ Database Paket"])
    with tab_a:
        if st.button("🧹 Clear Form"): st.session_state.p_id += 1; st.rerun()
        nm_p = st.text_input("Nama Paket", key=f"pnm_{st.session_state.p_id}")
        margin = st.slider("Target Food Cost (%)", 10, 50, 30, key=f"psl_{st.session_state.p_id}")
        c1, c2, c3 = st.columns(3)
        prm = c1.multiselect("Pilih RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.p_id}")
        pwp = c2.multiselect("Pilih WIP", st.session_state.db_wip['nama'].tolist(), key=f"pwp_{st.session_state.p_id}")
        pfg = c3.multiselect("Pilih FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.p_id}")
        if prm or pwp or pfg:
            res_p = {'k':0,'p':0,'l':0,'ka':0,'h':0,'b':0,'isi':[]}
            for x in prm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
                q = st.number_input(f"Gram Mentah: {x}", min_value=0.0, key=f"pqrm_{x}")
                d = global_calc(q/row['berat'], row, 'RM'); [res_p.update({k: res_p[k]+d[v]}) for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g'])]; res_p['isi'].append(f"{x}")
            for x in pwp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama']==x].iloc[0]
                q = st.number_input(f"Gram Matang: {x}", value=float(row['berat_porsi_gr']), key=f"pqwp_{x}")
                d = global_calc(q, row, 'WIP'); [res_p.update({k: res_p[k]+d[v]}) for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g'])]; res_p['isi'].append(f"{x}")
            for x in pfg:
                row = st.session_state.db_fg[st.session_state.db_fg['nama']==x].iloc[0]
                q = st.number_input(f"Gram Produk: {x}", value=float(row['berat_porsi_gr']), key=f"pqfg_{x}")
                d = global_calc(q, row, 'FG'); [res_p.update({k: res_p[k]+d[v]}) for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g'])]; res_p['isi'].append(f"{x}")
            st.divider()
            m1, m2, m3 = st.columns([1,1,2])
            m1.metric("Kalori", f"{res_p['k']:,.1f} kkal"); m1.metric("HPP", f"Rp {res_p['h']:,.0f}")
            m2.metric("Berat", f"{res_p['b']:,.1f} g"); m2.metric("Saran Jual", f"Rp {res_p['h']/(margin/100):,.0f}")
            with m3:
                if res_p['k'] > 0: st.plotly_chart(px.pie(values=[res_p['p'],res_p['l'],res_p['ka']], names=['Pro','Lem','Kar'], hole=0.4), use_container_width=True)
            if st.button("💾 Simpan Paket"):
                new_p = pd.DataFrame([{"nama_paket":nm_p, "rincian_isi":", ".join(res_p['isi']), "total_hpp":res_p['h'], "total_kalori":res_p['k'], "pro_total":res_p['p'], "lem_total":res_p['l'], "kar_total":res_p['ka']}])
                st.session_state.db_paket = pd.concat([st.session_state.db_paket, new_p], ignore_index=True); save_data_safe(st.session_state.db_paket, "db_paket.csv"); st.success("Paket Tersimpan!"); st.rerun()
    with tab_b:
        st.data_editor(st.session_state.db_paket, use_container_width=True, num_rows="dynamic")
