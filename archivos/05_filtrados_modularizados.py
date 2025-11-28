import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings
import time

# Intento de importación robusta de la librería de estrategias
try:
    from pages.lib_estrategias import CATALOGO_ESTRATEGIAS
except ImportError:
    try:
        from lib_estrategias import CATALOGO_ESTRATEGIAS
    except ImportError:
        st.error("❌ No se encuentra 'lib_estrategias.py'.")
        st.stop()

# 1. CONFIGURACIÓN
warnings.filterwarnings("ignore")

# --- ESTILOS CSS UNIFICADOS (VERDE ESMERALDA) ---
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

st.title("🎛️ Consolidador Modular (Específico Personas)")
st.markdown("Versión V1: Optimizado para consolidar censos basándose en **persona_id**.")

# 2. CARGA BLINDADA
def cargar_blindado(archivo):
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
    
    df.columns = df.columns.astype(str).str.lower().str.strip()
    for b in ['ï»¿', '\ufeff', '"', "'"]: df.columns = df.columns.str.replace(b, '', regex=False)
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    basura = ['', ' ', 'nan', 'NaN', 'null', 'NULL', 'None', 'none']
    df.replace(basura, np.nan, inplace=True)
    return df

# 3. INTERFAZ
col1, col2 = st.columns(2)
fm = col1.file_uploader("📂 Datos (Muestra)", type=['csv'])
fc = col2.file_uploader("🛠️ Correcciones (Mapa)", type=['csv'])

# Gestión de Estado
if 'ultimo_archivo_05' not in st.session_state: st.session_state['ultimo_archivo_05'] = None

if fm and fc:
    if st.session_state['ultimo_archivo_05'] != f"{fm.name}_{fc.name}":
        keys_borrar = ['res_consol_05', 'excel_bytes_05']
        for k in keys_borrar:
            if k in st.session_state: del st.session_state[k]
        st.session_state['ultimo_archivo_05'] = f"{fm.name}_{fc.name}"

    df_p = cargar_blindado(fm)
    df_c = cargar_blindado(fc)
    
    if df_p is not None and df_c is not None:
        st.success(f"Cargado: {len(df_p)} filas.")
        st.divider()

        # A. ID MAESTRO
        if 'persona_id' not in df_p.columns:
            st.error("❌ Falta la columna obligatoria 'persona_id'.")
            st.stop()
            
        df_p['pid_clean'] = df_p['persona_id'].astype(str).str.replace(r'[- ]', '', regex=True).str.upper().str.strip()
        
        def clean_key(s): return s.astype(str).str.replace(r'[- ]', '', regex=True).str.upper().str.strip()
        mapa_dict = {}
        
        # Detectar columnas de error
        cols_err = [c for c in df_c.columns if 'erroneo' in c]
        if not cols_err and len(df_c.columns) > 1: cols_err = [df_c.columns[1]]
        
        col_val = 'nif_valido' if 'nif_valido' in df_c.columns else df_c.columns[0]
        
        for c_err in cols_err:
            temp = df_c.dropna(subset=[c_err]).copy()
            k_bad = clean_key(temp[c_err])
            k_good = clean_key(temp[col_val])
            mapa_dict.update(zip(k_bad, k_good))
        
        df_p['id_maestro'] = df_p['pid_clean'].map(mapa_dict).fillna(df_p['pid_clean'])
        
        # B. REGLAS
        st.subheader("🛠️ Configuración de Reglas")
        c_fmt, c_info = st.columns([1, 2])
        user_date_fmt = c_fmt.text_input("Formato Fechas:", value="%d/%m/%Y")
        
        with st.expander("Desplegar Reglas por Columna", expanded=True):
            cols_datos = [c for c in df_p.columns if c not in ['pid_clean', 'id_maestro']]
            reglas_seleccionadas = {}
            cols_ui = st.columns(3)
            cols_tipo_fecha = [] 
            
            opciones_reglas = list(CATALOGO_ESTRATEGIAS.keys())

            def buscar_indice_regla(texto_clave):
                for idx, nombre_regla in enumerate(opciones_reglas):
                    if texto_clave.lower() in nombre_regla.lower():
                        return idx
                return 0 

            for i, col_name in enumerate(cols_datos):
                idx_def = 0
                if 'fecha_fin' in col_name: idx_def = buscar_indice_regla("Fecha Fin")
                elif 'fecha' in col_name: idx_def = buscar_indice_regla("Fecha Inicio")
                elif 'genero' in col_name: idx_def = buscar_indice_regla("Género")
                elif 'nif' in col_name or 'dni' in col_name: idx_def = buscar_indice_regla("NIF")
                
                with cols_ui[i % 3]:
                    estrategia = st.selectbox(
                        f"**{col_name}**", opciones_reglas, index=idx_def, key=f"s_{col_name}"
                    )
                    reglas_seleccionadas[col_name] = CATALOGO_ESTRATEGIAS[estrategia]
                    
                    if "Fecha" in estrategia:
                        cols_tipo_fecha.append(col_name)

        # C. EJECUCIÓN
        st.divider()
        if st.button("Consolidar Registros", type="primary"):
            p_bar = st.progress(0, text="Iniciando motor...")
            
            try:
                # 1. Ordenación
                p_bar.progress(20, text="⚙️ Ordenando registros...")
                df_p['es_original'] = df_p['pid_clean'] == df_p['id_maestro']
                
                sort_cols = ['es_original']
                asc = [False]
                if 'fecha_actualizacion' in df_p.columns:
                    sort_cols.append('fecha_actualizacion')
                    asc.append(False)
                
                df_sorted = df_p.sort_values(by=sort_cols, ascending=asc)
                
                # 2. Agregación
                p_bar.progress(50, text="🧩 Aplicando reglas...")
                df_final = df_sorted.groupby('id_maestro', as_index=False).agg(reglas_seleccionadas)
                
                # 3. Restaurar ID
                if 'persona_id' in df_final.columns: df_final['persona_id'] = df_final['id_maestro']
                if 'id_maestro' in df_final.columns: del df_final['id_maestro']

                # 4. Autorrelleno NIF (Lógica Específica 05)
                p_bar.progress(70, text="🧹 Revisando NIFs vacíos...")
                if 'nif' in df_final.columns and 'persona_id' in df_final.columns:
                    patron_dni = r'^[0-9]{8}[A-Z]$'
                    pid_norm = df_final['persona_id'].astype(str).str.upper().str.strip().str.replace(r'[- .]', '', regex=True)
                    nif_vacio = df_final['nif'].isna() | (df_final['nif'] == "") | (df_final['nif'] == "nan")
                    id_es_bueno = pid_norm.str.match(patron_dni)
                    df_final.loc[nif_vacio & id_es_bueno, 'nif'] = pid_norm.loc[nif_vacio & id_es_bueno]

                # 5. Formato Fecha
                p_bar.progress(85, text="📅 Formateando fechas...")
                for col_fecha in cols_tipo_fecha:
                    if col_fecha in df_final.columns:
                        fechas_obj = pd.to_datetime(df_final[col_fecha], dayfirst=True, errors='coerce')
                        df_final[col_fecha] = fechas_obj.dt.strftime(user_date_fmt).replace('NaT', np.nan)

                p_bar.progress(100, text="✅ ¡Hecho!")
                time.sleep(0.5)
                p_bar.empty()

                # GUARDAR EN SESIÓN
                st.session_state['res_consol_05'] = df_final
                
                try:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, index=False, sheet_name="Consolidado")
                    st.session_state['excel_bytes_05'] = buf.getvalue()
                except:
                    st.session_state['excel_bytes_05'] = None

                st.success("✅ Completado.")
                
            except Exception as e:
                p_bar.empty()
                st.error(f"Error: {e}")

    # D. VISUALIZACIÓN Y DESCARGAS
    if 'res_consol_05' in st.session_state:
        df_res = st.session_state['res_consol_05']
        
        st.divider()
        st.dataframe(df_res.head(50))
        
        st.subheader("💾 Descargar")
        c_conf_dl, c_btn_dl = st.columns([1, 2])
        
        with c_conf_dl:
            modo_sep = st.radio(
                "Separador CSV:", 
                ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
                horizontal=False,
                key="sep_radio_05"
            )
            sep_final = ";"
            if "Coma" in modo_sep: sep_final = ","
            elif "Pipe" in modo_sep: sep_final = "|"
            elif "Personalizado" in modo_sep:
                sep_final = st.text_input("Carácter:", value=";", max_chars=1, key="sep_custom_05")

        with c_btn_dl:
            st.write("###")
            
            # CSV
            try:
                csv_data = df_res.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
                st.download_button(
                    label=f"📥 Descargar CSV ({sep_final})",
                    data=csv_data,
                    file_name="consolidado_personas.csv",
                    mime="text/csv",
                    type="secondary"
                )
            except Exception as e:
                st.error(f"Separador inválido: {e}")

            # Excel
            if st.session_state.get('excel_bytes_05'):
                st.download_button(
                    label="📥 Descargar Excel",
                    data=st.session_state['excel_bytes_05'],
                    file_name="consolidado_personas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )