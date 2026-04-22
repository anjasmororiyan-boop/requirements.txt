import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro v22.0", layout="wide")

# --- 1. SISTEM PERSISTENSI DATA (FIXED COLUMNS) ---
def load_data_permanent(file_name, columns):
    if os.path.exists(file_name):
        try:
            df = pd.read_csv(file_name)
            # Pastikan semua kolom yang diperlukan ada
            for col in columns:
                if col not in df.columns:
                    df[col] = 0
            return df[columns].fillna(0)
        except:
            return pd.DataFrame(columns=columns)
    # Jika file tidak ada, buat baru dengan kolom lengkap
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
            # qty di sini adalah jumlah porsi matang
            return {
                'k': float(row['kal_porsi']) * qty,
                'p': float(row['pro_porsi']) * qty,
                'l': float(row['lem_porsi']) * qty,
                'ka': float(row['karbo']) * qty,
                'h': float(row['hpp_porsi']) * qty,
                'g': float(row['berat_porsi_gr']) * qty
            }
    except:
        return {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("NutriCost ERP v22.0")
nav = st.sidebar.radio("Navigasi Utama", ["📦 Database RM", "📥 Upload Data", "🍳 Master WIP", "🍱 Master FG", "🛒 Set Menu (Paket)"])

# --- MODUL 4: MASTER FG (FIXED CALCULATION) ---
if nav == "🍱 Master FG":
    st.title("🍱 Master Finished Goods (FG)")
    if "f_id" not in st.session_state: st.session_state.f_id = 0
    t1, t2 = st.tabs(["📝 Formulasi FG", "📋 Database FG"])
    
    with t1:
        nm_f = st.text_input("Nama Produk FG (Produk Jadi)", key=f"fnm_{st.session_state.f_id}")
        c1, c2 = st.columns(2)
        s_rm = c1.multiselect("Bahan Baku Mentah (RM)", st.session_state.db_bahan['nama'].tolist(), key=f"frm_{st.session_state.f_id}")
        s_wp = c2.multiselect("Resep Setengah Jadi (WIP)", st.session_state.db_wip['nama'].tolist(), key=f"fwp_{st.session_state.f_id}")
        
        if s_rm or s_wp:
            res_f = {'k':0.0, 'p':0.0, 'l':0.0, 'ka':0.0, 'h':0.0, 'g':0.0}
            
            st.markdown("### 🛠️ Input Detail Komponen")
            # Loop RM
            for x in s_rm:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == x].iloc[0]
                q = st.number_input(f"Qty Mentah {x} ({row['uom']})", key=f"fqrm_{x}_{st.session_state.f_id}")
                d = universal_calc(q, row, 'RM')
                for k in res_f: res_f[k] += d[k]
            
            # Loop WIP
            for x in s_wp:
                row = st.session_state.db_wip[st.session_state.db_wip['nama'] == x].iloc[0]
                q_porsi = st.number_input(f"Jumlah Porsi WIP: {x}", value=1.0, key=f"fqwp_{x}_{st.session_state.f_id}")
                d = universal_calc(q_porsi, row, 'WIP')
                for k in res_f: res_f[k] += d[k]
            
            st.divider()
            st.subheader("📊 Hasil Kalkulasi Gizi FG")
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Energi", f"{res_f['k']:.1f} kkal")
            col_m2.metric("Total Protein", f"{res_f['p']:.1f} g")
            col_m3.metric("Total HPP", f"Rp {res_f['h']:,.0f}")
            
            y_fg = st.number_input("Yield Berat Akhir Produk (gr)", value=max(res_f['g'], 1.0), key=f"fy_{st.session_state.f_id}")
            
            if st.button("💾 Simpan Master FG"):
                new_f = pd.DataFrame([{
                    "nama": nm_f, 
                    "berat_porsi_gr": y_fg, 
                    "kal_porsi": res_f['k'], 
                    "pro_porsi": res_f['p'], 
                    "lem_porsi": res_f['l'], 
                    "kar_porsi": res_f['ka'], 
                    "hpp_porsi": res_f['h']
                }])
                st.session_state.db_fg = pd.concat([st.session_state.db_fg, new_f], ignore_index=True)
                save_data_permanent(st.session_state.db_fg, "db_fg.csv")
                st.session_state.f_id += 1 # Reset Form
                st.success(f"Produk '{nm_f}' berhasil disimpan!"); st.rerun()

    with t2:
        st.subheader("📋 Daftar Master Finished Goods")
        ed_fg = st.data_editor(st.session_state.db_fg, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan Database FG"):
            st.session_state.db_fg = ed_fg.fillna(0)
            save_data_permanent(st.session_state.db_fg, "db_fg.csv")
            st.success("Database FG diperbarui!")

# --- MODUL 2: UPLOAD DATA (SISTEM SYNC) ---
elif nav == "📥 Upload Data":
    st.title("📥 Upload Data Massal")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up and st.button("🚀 Jalankan Sinkronisasi"):
        df_new = pd.read_csv(up, sep=None, engine='python') if up.name.endswith('.csv') else pd.read_excel(up)
        # Gabungkan data lama dengan baru
        st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, df_new], ignore_index=True).drop_duplicates(subset=['nama'], keep='last')
        save_data_permanent(st.session_state.db_bahan, "db_bahan.csv")
        st.success("Sinkronisasi Berhasil!"); st.rerun()
# --- MODUL 3: WIP ---
elif nav == "🍳 Master WIP":
    st.title("🍳 Master Resep Dasar (WIP)")
    t1, t2 = st.tabs(["📝 Formulasi WIP", "📋 Database WIP"])
    with t1:
        if "w_id" not in st.session_state: st.session_state.w_id = 0
        nm_w = st.text_input("Nama WIP", key=f"wnm_{st.session_state.w_id}")
        sel_b = st.multiselect("Pilih Bahan RM", st.session_state.db_bahan['nama'].tolist(), key=f"wsel_{st.session_state.w_id}")
        if sel_b:
            res_w = {'k':0,'p':0,'l':0,'ka':0,'h':0,'g':0}
            for b in sel_b:
                row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==b].iloc[0]
                q = st.number_input(f"Qty {b}", key=f"wq_{b}_{st.session_state.w_id}")
                d = universal_calc(q, row, 'RM')
                for k in res_w: res_w[k]+=d[k]
            y = st.number_input("Yield Matang (gr)", value=max(res_w['g'], 1.0), key=f"wy_{st.session_state.w_id}")
            if st.button("💾 Simpan Master WIP"):
                new = pd.DataFrame([{"nama":nm_w, "berat_porsi_gr":y, "kal_porsi":res_w['k'], "pro_porsi":res_w['p'], "lem_porsi":res_w['l'], "kar_porsi":res_w['ka'], "hpp_porsi":res_w['h']}])
                st.session_state.db_wip = pd.concat([st.session_state.db_wip, new], ignore_index=True); save_data_permanent(st.session_state.db_wip, "db_wip.csv"); st.session_state.w_id+=1; st.rerun()
    with t2:
        ed_wip = st.data_editor(st.session_state.db_wip, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan WIP"):
            st.session_state.db_wip = ed_wip.fillna(0); save_data_permanent(st.session_state.db_wip, "db_wip.csv"); st.success("WIP Updated!")
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

# --- MODUL 5: SET MENU (DENGAN CLEAR BUTTON & GRAFIK) ---
elif nav == "🛒 Set Menu (Paket)":
    st.title("🛒 Master Paket & Analisis Nutrisi")
    if "p_id" not in st.session_state: st.session_state.p_id = 0
    if st.button("🧹 Clear Form / Buat Paket Baru"):
        st.session_state.p_id += 1; st.rerun()
    
    nm_p = st.text_input("Nama Paket Jual", key=f"pnm_{st.session_state.p_id}")
    margin = st.slider("Target Food Cost (%)", 10, 50, 30, key=f"psl_{st.session_state.p_id}")
    c1, c2, c3 = st.columns(3)
    p_rm = c1.multiselect("Tambah RM", st.session_state.db_bahan['nama'].tolist(), key=f"prm_{st.session_state.p_id}")
    p_wp = c2.multiselect("Tambah WIP", st.session_state.db_wip['nama'].tolist(), key=f"pwp_{st.session_state.p_id}")
    p_fg = c3.multiselect("Tambah FG", st.session_state.db_fg['nama'].tolist(), key=f"pfg_{st.session_state.p_id}")
    
    if p_rm or p_wp or p_fg:
        p_res = {'k':0.0,'p':0.0,'l':0.0,'ka':0.0,'h':0.0,'b':0.0,'isi':[]}
        for x in p_rm:
            row = st.session_state.db_bahan[st.session_state.db_bahan['nama']==x].iloc[0]
            q = st.number_input(f"Gr Mentah: {x}", key=f"pqrm_{x}_{st.session_state.p_id}")
            d = universal_calc(q/row['berat'] if row['berat']>0 else 0, row, 'RM')
            for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
            p_res['isi'].append(x)
        for src, db in [('WIP', st.session_state.db_wip), ('FG', st.session_state.db_fg)]:
            choices = p_wp if src == 'WIP' else p_fg
            for x in choices:
                row = db[db['nama']==x].iloc[0]
                q = st.number_input(f"Gr {src}: {x}", value=float(row['berat_porsi_gr']), key=f"pq{src}_{x}_{st.session_state.p_id}")
                d = universal_calc(q, row, src)
                for k,v in zip(['k','p','l','ka','h','b'],['k','p','l','ka','h','g']): p_res[k]+=d[v]
                p_res['isi'].append(x)
        
        st.divider()
        m1, m2, m3 = st.columns([1,1,2])
        m1.metric("Total HPP", f"Rp {p_res['h']:,.0f}"); m1.metric("Kalori", f"{p_res['k']:,.1f} kkal")
        m2.metric("Berat Total", f"{p_res['b']:,.1f} g"); m2.metric("Saran Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
        with m3:
            if p_res['k'] > 0:
                fig = px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein','Lemak','Karbo'], hole=0.4, title="Macro Nutrisi")
                st.plotly_chart(fig, use_container_width=True)
        if st.button("💾 Simpan Paket"):
            new_p = pd.DataFrame([{"nama_paket":nm_p, "rincian_isi":", ".join(p_res['isi']), "total_hpp":p_res['h'], "total_kalori":p_res['k'], "pro_total":p_res['p'], "lem_total":p_res['l'], "kar_total":p_res['ka']}])
            st.session_state.db_paket = pd.concat([st.session_state.db_paket, new_p], ignore_index=True)
            save_data_permanent(st.session_state.db_paket, "db_paket.csv"); st.session_state.p_id+=1; st.rerun()

# --- MODUL WIP & MASTER DATABASE LAINNYA ---
else:
    st.info("Gunakan Sidebar untuk navigasi.")
