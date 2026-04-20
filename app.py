import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

# --- KONFIGURASI AI ---
# Masukkan API Key Anda di sini atau via Streamlit Secrets
API_KEY = "MASUKKAN_GEMINI_API_KEY_ANDA" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="NutriCost Pro AI", layout="wide")

# --- DATABASE STATE ---
if 'db_bahan' not in st.session_state:
    st.session_state.db_bahan = pd.DataFrame(columns=[
        "nama", "satuan_uom", "berat_bersih_gr", "harga_beli", "total_kalori", "total_protein", "total_lemak", "total_karbo", "bdd"
    ])

if 'calc_result' not in st.session_state:
    st.session_state.calc_result = {"kal": 0.0, "pro": 0.0, "lem": 0.0, "kar": 0.0}

if 'ai_raw' not in st.session_state:
    st.session_state.ai_raw = {"kal": 0.0, "pro": 0.0, "lem": 0.0, "kar": 0.0}

# --- FUNGSI AI UNTUK MENCARI NUTRISI ---
def get_ai_nutrition(food_name):
    prompt = f"""
    Berikan data nutrisi standar per 100g untuk bahan makanan: {food_name}.
    Respon harus dalam format JSON murni:
    {{"kalori": 0.0, "protein": 0.0, "lemak": 0.0, "karbo": 0.0}}
    Pastikan angka realistis berdasarkan database gizi internasional/Kemenkes.
    """
    try:
        response = model.generate_content(prompt)
        # Membersihkan output AI agar menjadi JSON valid
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(json_str)
    except:
        return None

# --- SIDEBAR ---
st.sidebar.title("NutriCost Pro AI v3.0")
nav = st.sidebar.radio("Menu Utama", ["Master Bahan Baku", "Master Item (Single Menu)", "Set Menu (Paket)"])

# --- MODUL 1: MASTER BAHAN BAKU ---
if nav == "Master Bahan Baku":
    st.title("📦 Management Bahan Baku & AI Integration")
    
    with st.expander("➕ Tambah Bahan dengan AI Auto-Fill", expanded=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        nama_b = c1.text_input("Nama Bahan", placeholder="Contoh: Fillet Paha Ayam")
        
        # TOMBOL AI
        if c1.button("✨ Cari Nutrisi Otomatis (AI)"):
            if nama_b:
                with st.spinner("AI sedang mencari data gizi standar..."):
                    data_gizi = get_ai_nutrition(nama_b)
                    if data_gizi:
                        st.session_state.ai_raw['kal'] = float(data_gizi.get('kalori', 0))
                        st.session_state.ai_raw['pro'] = float(data_gizi.get('protein', 0))
                        st.session_state.ai_raw['lem'] = float(data_gizi.get('lemak', 0))
                        st.session_state.ai_raw['kar'] = float(data_gizi.get('karbo', 0))
                        st.success(f"Data ditemukan untuk {nama_b}!")
                    else:
                        st.error("AI gagal menemukan data. Silakan input manual.")
            else:
                st.warning("Masukkan nama bahan dulu!")

        uom = c2.selectbox("Satuan (UOM)", ["kg", "gr", "L", "ml", "pcs", "pack"])
        berat_gr = c3.number_input("Berat per Satuan (gr/ml)", min_value=0.01, value=1.0)
        
        c4, c5 = st.columns(2)
        harga = c4.number_input("Harga Beli per Satuan (Rp)", min_value=0.0)
        bdd = c5.number_input("BDD (%)", min_value=1, max_value=100, value=100)

        st.markdown("---")
        st.write("**Nutrisi Dasar per 100g (Auto-filled by AI)**")
        n1, n2, n3, n4 = st.columns(4)
        ref_kal = n1.number_input("Kalori Dasar", value=st.session_state.ai_raw['kal'])
        ref_pro = n2.number_input("Protein Dasar", value=st.session_state.ai_raw['pro'])
        ref_lem = n3.number_input("Lemak Dasar", value=st.session_state.ai_raw['lem'])
        ref_kar = n4.number_input("Karbo Dasar", value=st.session_state.ai_raw['kar'])

        # TOMBOL KALKULASI AKHIR
        if st.button("🔄 Jalankan Kalkulasi Final"):
            ratio = berat_gr / 100
            bdd_fac = bdd / 100
            st.session_state.calc_result["kal"] = ref_kal * ratio * bdd_fac
            st.session_state.calc_result["pro"] = ref_pro * ratio * bdd_fac
            st.session_state.calc_result["lem"] = ref_lem * ratio * bdd_fac
            st.session_state.calc_result["kar"] = ref_kar * ratio * bdd_fac
            st.info("Kalkulasi per Satuan Selesai!")

        st.markdown("---")
        st.write("**Hasil Akhir per Satuan (Read-Only)**")
        res1, res2, res3, res4 = st.columns(4)
        out_kal = res1.number_input("Total Kalori", value=st.session_state.calc_result["kal"], disabled=True)
        out_pro = res2.number_input("Total Protein", value=st.session_state.calc_result["pro"], disabled=True)
        out_lem = res3.number_input("Total Lemak", value=st.session_state.calc_result["lem"], disabled=True)
        out_kar = res4.number_input("Total Karbo", value=st.session_state.calc_result["kar"], disabled=True)

        if st.button("💾 Simpan ke Master Database"):
            new_row = {
                "nama": nama_b, "satuan_uom": uom, "berat_bersih_gr": berat_gr,
                "harga_beli": harga, "total_kalori": out_kal, 
                "total_protein": out_pro, "total_lemak": out_lem, 
                "total_karbo": out_kar, "bdd": bdd
            }
            st.session_state.db_bahan = pd.concat([st.session_state.db_bahan, pd.DataFrame([new_row])], ignore_index=True)
            st.success("Tersimpan!")
            st.rerun()

    st.subheader("📋 Master Data")
    st.dataframe(st.session_state.db_bahan, use_container_width=True)

# --- MODUL 2: MASTER ITEM (SINGLE MENU) ---
elif nav == "Master Item (Single Menu)":
    st.title("🍳 Rakit Menu dari Master")
    if st.session_state.db_bahan.empty:
        st.warning("Input bahan baku di Master terlebih dahulu.")
    else:
        with st.form("buat_menu"):
            nama_m = st.text_input("Nama Item Menu")
            pilih_b = st.multiselect("Pilih Komponen Bahan", st.session_state.db_bahan['nama'].tolist())
            lanjut = st.form_submit_button("Proses Porsi")
            
        if pilih_b:
            st.subheader(f"Porsi Resep: {nama_m}")
            summary = {'kal':0, 'pro':0, 'lem':0, 'kar':0, 'cost':0}
            
            with st.form("porsi_detail"):
                for b in pilih_b:
                    data_b = st.session_state.db_bahan[st.session_state.db_bahan['nama'] == b].iloc[0]
                    qty = st.number_input(f"Jumlah {b} ({data_b['satuan_uom']})", min_value=0.0, step=0.1, key=f"q_{b}")
                    
                    # Kalkulasi Cost & Nutrisi Berdasarkan Satuan UOM
                    summary['kal'] += data_b['kalori'] * qty
                    summary['pro'] += data_b['protein'] * qty
                    summary['lem'] += data_b['lemak'] * qty
                    summary['kar'] += data_b['karbo'] * qty
                    summary['cost'] += data_b['harga_beli'] * qty
                
                simpan_m = st.form_submit_button("Simpan Item Master")
                if simpan_m:
                    st.session_state.db_menu.append({
                        "nama_menu": nama_m, "total_kalori": summary['kal'], 
                        "total_protein": summary['pro'], "total_lemak": summary['lem'], 
                        "total_karbo": summary['kar'], "total_hpp": summary['cost']
                    })
                    st.success(f"Menu {nama_m} Berhasil Disimpan!")

# --- MODUL 3: SET MENU ---
elif nav == "Set Menu (Paket)":
    st.title("🍱 Gabungkan Menu Menjadi Paket")
    if not st.session_state.db_menu:
        st.info("Buat Item Master (Single Menu) terlebih dahulu.")
    else:
        nama_p = st.text_input("Nama Paket")
        pilih_item = st.multiselect("Pilih Menu Satuan", [m['nama_menu'] for m in st.session_state.db_menu])
        
        if pilih_item:
            tot = {'k':0, 'p':0, 'l':0, 'ka':0, 'h':0}
            for pi in pilih_item:
                dm = next(item for item in st.session_state.db_menu if item["nama_menu"] == pi)
                tot['k'] += dm['total_kalori']; tot['p'] += dm['total_protein']
                tot['l'] += dm['total_lemak']; tot['ka'] += dm['total_karbo']
                tot['h'] += dm['total_hpp']
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Energi", f"{tot['k']:.0f} kkal")
            c2.metric("Total HPP", f"Rp {tot['h']:,.0f}")
            c3.metric("Harga Jual (FC 30%)", f"Rp {tot['h']/0.3:,.0f}")

# --- MODUL 4: DASHBOARD ---
elif nav == "Dashboard":
    st.title("📊 Analisis Data")
    if st.session_state.db_menu:
        st.table(pd.DataFrame(st.session_state.db_menu))
    else:
        st.info("Belum ada data menu untuk dianalisis.")
