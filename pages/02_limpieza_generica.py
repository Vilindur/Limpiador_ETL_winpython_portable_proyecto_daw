import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings
import re

# 1. CONFIGURACIÓN
warnings.filterwarnings("ignore")

# --- ESTILOS CSS---
st.markdown("""
    <style>
    div.stButton > button:first-child[kind="primary"] {
        background-color: #2E8B57;
        border-color: #2E8B57;
        color: white;
        border-radius: 6px;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #236B45;
        border-color: #236B45;
        color: white;
    }
    div.stButton > button:first-child[kind="primary"]:focus,
    div.stButton > button:first-child[kind="primary"]:active {
        background-color: #2E8B57;
        border-color: #2E8B57;
        color: white;
        box-shadow: none;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧹 Limpiador universal de caracteres problemáticos")
st.markdown("Prepara archivos para SQL. Generación instantánea de descargas.")

# 2. BARRA LATERAL
st.sidebar.header("⚙️ Configuración")

st.sidebar.subheader("1. Limpieza Profunda")
opt_trim = st.sidebar.checkbox("Trim espacios", value=True)
opt_clean_chars = st.sidebar.checkbox("Eliminar saltos línea/tabs", value=True)

st.sidebar.subheader("2. Estrategia de Vacíos")
fill_mode = st.sidebar.radio(
    "¿Relleno de huecos?",
    ["Mantener vacío (NaN)", "Literal 'NULL' (SQL)", "Cadena vacía ''", "Valor Personalizado"],
    index=1
)

custom_val = ""
if fill_mode == "Valor Personalizado":
    custom_val = st.sidebar.text_input("Valor relleno:", "SIN_DATO")

# 3. MOTOR BLINDADO
def cargar_dataset(archivo):
    archivo.seek(0)
    try:
        df = pd.read_csv(archivo, sep=';', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        if len(df.columns) < 2: raise ValueError()
    except:
        archivo.seek(0)
        try:
            df = pd.read_csv(archivo, sep=',', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        except:
            return None, "Error crítico: Formato no detectado."

    df.columns = df.columns.astype(str).str.lower().str.strip()
    for b in ['ï»¿', '\ufeff', '"', "'"]: df.columns = df.columns.str.replace(b, '', regex=False)
    
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    basura = ['', ' ', 'nan', 'NaN', 'null', 'NULL', 'None', 'none']
    df.replace(basura, np.nan, inplace=True)
    return df, None

# 4. PROCESAMIENTO
def procesar_limpieza(df):
    df_clean = df.copy()
    if opt_clean_chars: df_clean = df_clean.replace(r'[\r\n\t]+', ' ', regex=True)
    if opt_trim: df_clean = df_clean.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    if fill_mode == "Literal 'NULL' (SQL)": df_clean.fillna("NULL", inplace=True)
    elif fill_mode == "Cadena vacía ''": df_clean.fillna("", inplace=True)
    elif fill_mode == "Valor Personalizado": df_clean.fillna(custom_val, inplace=True)
    return df_clean

# 5. INTERFAZ CACHEADA
uploaded_file = st.file_uploader("📂 Archivo CSV", type=['csv'])

if 'ultimo_archivo_02' not in st.session_state: st.session_state['ultimo_archivo_02'] = None

if uploaded_file:
    # Gestión de memoria al cambiar archivo
    if st.session_state['ultimo_archivo_02'] != uploaded_file.name:
        keys_to_clear = ['res_02', 'excel_bytes_02']
        for k in keys_to_clear:
            if k in st.session_state: del st.session_state[k]
        st.session_state['ultimo_archivo_02'] = uploaded_file.name

    # BOTÓN EJECUTAR
    if st.button("Ejecutar Limpieza", type="primary"):
        with st.spinner("Procesando..."):
            df_raw, error = cargar_dataset(uploaded_file)
            if error: st.error(error)
            else:
                df_final = procesar_limpieza(df_raw)
                
                # Guardar en sesión
                st.session_state['res_02'] = df_final
                
                # Generar Excel una sola vez
                try:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, index=False, sheet_name="Data")
                    st.session_state['excel_bytes_02'] = buf.getvalue()
                except:
                    st.session_state['excel_bytes_02'] = None

                st.success("✅ Limpieza completada.")

    # VISUALIZACIÓN Y DESCARGAS
    if 'res_02' in st.session_state:
        df_visual = st.session_state['res_02']
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Filas", len(df_visual))
        m2.metric("Columnas", len(df_visual.columns))
        
        if fill_mode == "Literal 'NULL' (SQL)": r = (df_visual == "NULL").sum().sum()
        elif fill_mode == "Valor Personalizado": r = (df_visual == custom_val).sum().sum()
        else: r = df_visual.isna().sum().sum()
        m3.metric("Celdas Rellenas/Vacías", int(r))

        st.subheader("🔍 Previsualización")
        st.dataframe(df_visual.head(50))

        # ZONA DE DESCARGA
        st.divider()
        st.subheader("💾 Descargar Resultados")
        
        c_conf_dl, c_btn_dl = st.columns([1, 2])
        
        with c_conf_dl:
            modo_sep = st.radio(
                "Separador CSV:", 
                ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
                horizontal=False,
                key="sep_radio_02"
            )
            
            sep_final = ";"
            if "Coma" in modo_sep: sep_final = ","
            elif "Pipe" in modo_sep: sep_final = "|"
            elif "Personalizado" in modo_sep:
                sep_final = st.text_input("Carácter:", value=";", max_chars=1, key="sep_custom_02")

        with c_btn_dl:
            st.write("###") # Espaciador visual
            
            # 1. Generar CSV al vuelo
            try:
                csv_data = df_visual.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
                st.download_button(
                    label=f"📥 Descargar CSV ({sep_final})",
                    data=csv_data,
                    file_name="datos_limpios.csv",
                    mime="text/csv",
                    type="secondary"
                )
            except Exception as e:
                st.error(f"Separador inválido: {e}")
        
            # 2. Excel (Cacheado)
            if st.session_state.get('excel_bytes_02'):
                st.download_button(
                    label="📥 Descargar Excel", 
                    data=st.session_state['excel_bytes_02'], 
                    file_name="datos_limpios.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )