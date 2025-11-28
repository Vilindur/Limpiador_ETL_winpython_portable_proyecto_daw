import streamlit as st
import pandas as pd
import io
import warnings

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

st.title("🔗 Cruzador de Tablas (Vlookup)")
st.markdown("Realiza cruces entre dos archivos (**Joins**) de forma masiva y sin bloqueos de Excel.")

# 2. CARGA DE DATOS
def cargar_csv(archivo):
    archivo.seek(0)
    try:
        df = pd.read_csv(archivo, sep=';', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        if len(df.columns) < 2: raise ValueError()
    except:
        archivo.seek(0)
        try:
            df = pd.read_csv(archivo, sep=',', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        except:
            return None
    
    # Normalizar cabeceras ligeramente para facilitar lectura
    df.columns = df.columns.str.strip()
    return df

# 3. INTERFAZ DE CARGA
col1, col2 = st.columns(2)
f_left = col1.file_uploader("📂 Archivo Izquierdo (Principal)", type=['csv'])
f_right = col2.file_uploader("📂 Archivo Derecho (A buscar)", type=['csv'])

# Gestión de Estado
if 'ultimo_cruce_08' not in st.session_state: st.session_state['ultimo_cruce_08'] = None

if f_left and f_right:
    # Reset si cambian archivos
    if st.session_state['ultimo_cruce_08'] != f"{f_left.name}_{f_right.name}":
        if 'res_join_08' in st.session_state: del st.session_state['res_join_08']
        st.session_state['ultimo_cruce_08'] = f"{f_left.name}_{f_right.name}"

    df_L = cargar_csv(f_left)
    df_R = cargar_csv(f_right)

    if df_L is not None and df_R is not None:
        st.success(f"Archivos cargados. Izq: {len(df_L)} filas | Der: {len(df_R)} filas")
        st.divider()

        # 4. CONFIGURACIÓN DEL JOIN
        st.subheader("⚙️ Configuración del Cruce")
        
        c_keys, c_type = st.columns(2)
        
        # Selección de Claves
        key_L = c_keys.selectbox("Clave en Archivo Izquierdo:", df_L.columns)
        key_R = c_keys.selectbox("Clave en Archivo Derecho:", df_R.columns)
        
        # Tipo de Join
        join_type = c_type.selectbox(
            "Tipo de Cruce:",
            ["left", "inner", "outer", "right"],
            format_func=lambda x: {
                "left": "LEFT JOIN (Mantiene todo lo Izquierda + Coincidencias)",
                "inner": "INNER JOIN (Solo lo que coincida en ambos)",
                "outer": "FULL OUTER (Todo de ambos)",
                "right": "RIGHT JOIN (Prioridad Derecha)"
            }[x]
        )
        
        # Selección de columnas a traer (Para no duplicar)
        st.markdown("**Selecciona qué columnas quieres traer del archivo derecho:**")
        cols_disponibles_R = [c for c in df_R.columns if c != key_R]
        cols_to_add = st.multiselect("Columnas a añadir:", cols_disponibles_R, default=cols_disponibles_R)

        # 5. EJECUCIÓN
        st.divider()
        if st.button("Ejecutar Cruce", type="primary"):
            with st.spinner("Cruzando datos..."):
                try:
                    # Preparar lado derecho (Solo clave + seleccionadas)
                    cols_finales_R = [key_R] + cols_to_add
                    df_R_cut = df_R[cols_finales_R].copy()
                    
                    # Ejecutar Merge
                    # Convertimos claves a string y mayusculas para asegurar match
                    df_L['_key_temp'] = df_L[key_L].astype(str).str.strip().str.upper()
                    df_R_cut['_key_temp'] = df_R_cut[key_R].astype(str).str.strip().str.upper()
                    
                    df_result = pd.merge(
                        df_L,
                        df_R_cut,
                        on='_key_temp',
                        how=join_type,
                        suffixes=('', '_der')
                    )
                    
                    # Limpieza final
                    if '_key_temp' in df_result.columns: del df_result['_key_temp']
                    if key_R in df_result.columns and key_R != key_L: 
                        pass 

                    st.session_state['res_join_08'] = df_result
                    
                    # Generación Excel
                    try:
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                            df_result.to_excel(writer, index=False, sheet_name="Cruce")
                        st.session_state['excel_bytes_08'] = buf.getvalue()
                    except:
                        st.session_state['excel_bytes_08'] = None

                    st.success(f"✅ Cruce finalizado. Resultado: {len(df_result)} filas.")
                    
                except Exception as e:
                    st.error(f"Error en el cruce: {e}")

    # 6. RESULTADOS Y DESCARGA
    if 'res_join_08' in st.session_state:
        df_final = st.session_state['res_join_08']
        
        st.divider()
        st.subheader("📊 Resultado")
        st.dataframe(df_final.head(50))
        
        st.subheader("💾 Descargar")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            modo_sep = st.radio(
                "Separador CSV:", 
                ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
                horizontal=False,
                key="sep_radio_08"
            )

            sep_final = ";"
            if "Coma" in modo_sep: sep_final = ","
            elif "Pipe" in modo_sep: sep_final = "|"
            elif "Personalizado" in modo_sep:
                sep_final = st.text_input("Carácter:", value=";", max_chars=1, key="sep_custom_08")
        
        with c2:
            st.write("###")
            try:
                csv_data = df_final.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
                st.download_button("📥 Descargar CSV", csv_data, "cruce_resultado.csv", "text/csv", type="secondary")
            except: pass
            
            if st.session_state.get('excel_bytes_08'):
                st.download_button("📥 Descargar Excel", st.session_state['excel_bytes_08'], "cruce_resultado.xlsx", type="primary")

else:
    st.info("Sube dos archivos CSV para comenzar a cruzar datos.")