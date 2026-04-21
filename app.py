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

# --- MODUL 3: MASTER RESEP (DENGAN RINCIAN NUTRISI) ---
elif nav == "3. Master Resep":
    st.title("🍳 Master Resep (Menu Tunggal)")
    tab1, tab2 = st.tabs(["📝 Buat Resep Baru", "📋 Database Master Resep"])
    
    with tab1:
        if "resep_id" not in st.session_state: st.session_state.resep_id = 0
        nm = st.text_input("Nama Produk Matang", key=f"nm_{st.session_state.resep_id}")
        items = st.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist(), key=f"it_{st.session_state.resep_id}")
        
        if items:
            res = {'kal':0,'pro':0,'lem':0,'kar':0,'cost':0,'gr':0}
            for i in items:
                r = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == i].iloc[0]
                qty = st.number_input(f"Qty {i} ({r['uom']})", min_value=0.0, step=0.01, key=f"q_{i}_{st.session_state.resep_id}")
                gr = qty * float(r['berat'])
                f = (gr/100)*(float(r['bdd'])/100)
                res['kal']+=float(r['kalori'])*f; res['pro']+=float(r['protein'])*f
                res['lem']+=float(r['lemak'])*f; res['kar']+=float(r['karbo'])*f; res['cost']+=float(r['harga'])*qty; res['gr']+=gr
            
            st.divider()
            y = st.number_input("Berat Yield Matang Total (gr)", value=max(res['gr'], 1.0))
            p = st.number_input("Jumlah Porsi", min_value=1, value=1)
            
            if st.button("💾 Simpan ke Master Resep"):
                new_row = pd.DataFrame([{"nama":nm, "berat_porsi_gr":y/p, "kal_porsi":res['kal']/p, "pro_porsi":res['pro']/p, "lem_porsi":res['lem']/p, "kar_porsi":res['kar']/p, "hpp_porsi":res['cost']/p}])
                st.session_state.db_menu = pd.concat([st.session_state.db_menu, new_row], ignore_index=True)
                save_data(st.session_state.db_menu, "master_resep.csv")
                st.session_state.resep_id += 1; st.rerun()

    with tab2:
        st.subheader("🗄️ Tabel Master Resep")
        # Proteksi agar tabel tetap muncul meski kosong
        edited_menu = st.data_editor(st.session_state.db_menu, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Update/Hapus Master Resep"):
            st.session_state.db_menu = edited_menu
            save_data(st.session_state.db_menu, "master_resep.csv"); st.success("Database diperbarui!")

# --- MODUL 4: MASTER PAKET (DETAIL + GRAFIK + RESET) ---
elif nav == "4. Master Paket":
    st.title("🍱 Master Paket (Set Menu)")
    if "pkt_id" not in st.session_state: st.session_state.pkt_id = 0
    
    tab_a, tab_b = st.tabs(["🆕 Buat Paket", "🗄️ Database Paket"])
    
    with tab_a:
        if st.session_state.db_menu.empty:
            st.warning("Master Resep kosong. Selesaikan Modul 3 dulu.")
        else:
            if st.button("🧹 Clear / Buat Paket Baru"):
                st.session_state.pkt_id += 1; st.rerun()
            
            c1, c2 = st.columns([2,1])
            nama_pkt = c1.text_input("Nama Paket", key=f"pnm_{st.session_state.pkt_id}")
            margin = c2.slider("Food Cost (%)", 10, 50, 30, key=f"pm_{st.session_state.pkt_id}")
            items_pkt = st.multiselect("Pilih Menu", st.session_state.db_menu['nama'].tolist(), key=f"pit_{st.session_state.pkt_id}")

            if items_pkt:
                st.markdown("### 📋 Rincian Nutrisi & Gramasi")
                p_res = {'k':0,'p':0,'l':0,'ka':0,'h':0,'b':0,'isi':[]}
                detail_rows = []
                
                for itm in items_pkt:
                    d = st.session_state.db_menu[st.session_state.db_menu['nama'] == itm].iloc[0]
                    c_gr = st.number_input(f"Gramasi {itm} (gr)", value=float(d['berat_porsi_gr']), key=f"gr_{itm}_{st.session_state.pkt_id}")
                    ratio = c_gr / d['berat_porsi_gr'] if d['berat_porsi_gr'] > 0 else 0
                    
                    # Hitung Pro-rata
                    nk, np, nl, nka, nh = d['kal_porsi']*ratio, d['pro_porsi']*ratio, d['lem_porsi']*ratio, d['kar_porsi']*ratio, d['hpp_porsi']*ratio
                    detail_rows.append({"Menu": itm, "Gram": c_gr, "Kalori": round(nk,1), "Pro": round(np,1), "Lem": round(nl,1), "Kar": round(nka,1), "HPP": round(nh,0)})
                    
                    p_res['k']+=nk; p_res['p']+=np; p_res['l']+=nl; p_res['ka']+=nka; p_res['h']+=nh; p_res['b']+=c_gr
                    p_res['isi'].append(f"{itm}({c_gr}g)")

                st.table(pd.DataFrame(detail_rows))

                st.divider()
                m1, m2, m3 = st.columns([1,1,2])
                m1.metric("Total Kalori", f"{p_res['k']:,.1f}")
                m1.metric("Total HPP", f"Rp {p_res['h']:,.0f}")
                m2.metric("Harga Jual", f"Rp {p_res['h']/(margin/100):,.0f}")
                m2.metric("Total Berat", f"{p_res['b']:,.0f} g")
                
                with m3:
                    fig = px.pie(values=[p_res['p'], p_res['l'], p_res['ka']], names=['Protein','Lemak','Karbo'], title="Macro Ratio", hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)

                if st.button("💾 Simpan Paket"):
                    new_p = pd.DataFrame([{"nama_paket":nama_pkt, "rincian_isi":", ".join(p_res['isi']), "total_hpp":p_res['h'], "total_kalori":p_res['k'], "pro_total":p_res['p'], "lem_total":p_res['l'], "kar_total":p_res['ka']}])
                    st.session_state.db_master_paket = pd.concat([st.session_state.db_master_paket, new_p], ignore_index=True)
                    save_data(st.session_state.db_master_paket, "master_paket.csv"); st.success("Paket disimpan!"); st.rerun()

    with tab_b:
        edited_pkt = st.data_editor(st.session_state.db_master_paket, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Simpan Perubahan Paket"):
            st.session_state.db_master_paket = edited_pkt
            save_data(st.session_state.db_master_paket, "master_paket.csv"); st.success("Updated!")
