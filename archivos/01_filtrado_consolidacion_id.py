import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings
import re

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

st.title("🧬 Consolidador de datos V.13")

# 2. CARGA BLINDADA
def cargar_archivos(f_muestra, f_correcciones):
    def leer_blindado(archivo):
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
        for b in ['ï»¿', '\ufeff', '"', "'"]:
            df.columns = df.columns.str.replace(b, '', regex=False)
        
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        basura = ['', ' ', 'nan', 'NaN', 'null', 'NULL', 'None', 'none']
        df.replace(basura, np.nan, inplace=True)
        return df

    df_p = leer_blindado(f_muestra)
    df_c = leer_blindado(f_correcciones)

    if df_p is None or df_c is None: return None, None, "Error de formato (revisar separadores)."
    if 'nif_valido' not in df_c.columns: return None, None, "Falta columna 'nif_valido'."
    
    if 'nif_erroneo1' not in df_c.columns:
        if 'nif_erroneo' in df_c.columns: df_c.rename(columns={'nif_erroneo': 'nif_erroneo1'}, inplace=True)
        else: return None, None, "Falta columna 'nif_erroneo1'."

    cols_fecha = ['fecha_inicio', 'fecha_fin', 'fecha_nacimiento', 'fecha_defuncion', 'fecha_actualizacion']
    for col in cols_fecha:
        if col in df_p.columns:
            df_p[col] = pd.to_datetime(df_p[col], dayfirst=True, errors='coerce')

    return df_p, df_c, None

# 3. LÓGICA DE PROCESAMIENTO
def procesar_datos(df_personas, df_correcciones):
    if 'persona_id' not in df_personas.columns:
        st.error("Falta 'persona_id'.")
        return None

    df_personas['pid_clean'] = df_personas['persona_id'].astype(str).str.replace(r'[- ]', '', regex=True).str.upper().str.strip()
    
    def clean_key(s): return s.astype(str).str.replace(r'[- ]', '', regex=True).str.upper().str.strip()
    
    mapa_dict = {}
    for col_err in ['nif_erroneo1', 'nif_erroneo2']:
        if col_err in df_correcciones.columns:
            temp = df_correcciones.dropna(subset=[col_err]).copy()
            k_bad = clean_key(temp[col_err])
            k_good = clean_key(temp['nif_valido'])
            mapa_dict.update(zip(k_bad, k_good))

    df_personas['id_maestro'] = df_personas['pid_clean'].map(mapa_dict).fillna(df_personas['pid_clean'])

    def reducir_grupo(grupo):
        filas_maestras = grupo[grupo['pid_clean'] == grupo['id_maestro']]
        base = filas_maestras.iloc[0] if not filas_maestras.empty else grupo.iloc[0]
        resultado = base.copy()
        
        if len(grupo) > 1:
            otros = grupo[grupo.index != base.name].copy()
            if 'fecha_actualizacion' in otros.columns:
                otros = otros.sort_values('fecha_actualizacion', ascending=False)
            mejor_otro = otros.iloc[0]

            cols_protegidas = ['nif', 'rol', 'sir_eppn', 'fecha_fin_ficcionada']
            cols_especiales = ['persona_id', 'id_maestro', 'pid_clean', 'fecha_inicio', 'fecha_fin', 'genero'] + cols_protegidas
            cols_rellenar = [c for c in grupo.columns if c not in cols_especiales]
            
            for col in cols_rellenar:
                if pd.isna(base[col]):
                    val_otro = mejor_otro[col]
                    if pd.notna(val_otro): resultado[col] = val_otro

            if 'genero' in grupo.columns:
                gb, go = base['genero'], mejor_otro['genero']
                def es_f(g): return str(g).upper().strip() in ['HOMBRE', 'MUJER']
                if es_f(gb): resultado['genero'] = gb
                elif es_f(go): resultado['genero'] = go
                elif pd.notna(gb): resultado['genero'] = gb
                else: resultado['genero'] = go

            if 'fecha_inicio' in grupo.columns:
                resultado['fecha_inicio'] = pd.to_datetime(grupo['fecha_inicio'], errors='coerce').min()
            
            if 'fecha_fin' in grupo.columns:
                ff_val = pd.to_datetime(base['fecha_fin'], errors='coerce')
                if pd.isna(ff_val): resultado['fecha_fin'] = pd.NaT 
                else: resultado['fecha_fin'] = pd.to_datetime(grupo['fecha_fin'], errors='coerce').max()

        resultado['persona_id'] = grupo['id_maestro'].iloc[0]
        return resultado

    df_final = df_personas.groupby('id_maestro', group_keys=False).apply(reducir_grupo)
    df_final = df_final.drop(columns=['id_maestro', 'pid_clean', 'k_bad', 'k_good'], errors='ignore')

    if 'nif' in df_final.columns:
        patron_dni = r'^[0-9]{8}[A-Z]$'
        df_final['nif'] = df_final['nif'].astype(str).str.upper().str.strip().str.replace(r'[- .]', '', regex=True)
        df_final['nif'] = df_final['nif'].replace('NAN', np.nan)
        es_dni = df_final['nif'].str.match(patron_dni, na=False)
        df_final.loc[~es_dni, 'nif'] = np.nan
        pid_norm = df_final['persona_id'].astype(str).str.upper().str.strip().str.replace(r'[- .]', '', regex=True)
        id_es_dni = pid_norm.str.match(patron_dni, na=False)
        cond = df_final['nif'].isna() & id_es_dni
        df_final.loc[cond, 'nif'] = pid_norm

    for col_int in ['area_id', 'categoria_id']:
        if col_int in df_final.columns:
            df_final[col_int] = pd.to_numeric(df_final[col_int], errors='coerce').astype('Int64')

    if 'nombre' in df_final.columns and 'apellido1' in df_final.columns:
        df_final = df_final.sort_values(by=['nombre', 'apellido1'])
    
    return df_final

# 4. INTERFAZ
col1, col2 = st.columns(2)
fm = col1.file_uploader("📂 Personas", type=['csv'])
fc = col2.file_uploader("🛠️ Correcciones", type=['csv'])

if 'ultimo_archivo_01' not in st.session_state: st.session_state['ultimo_archivo_01'] = None

if fm and fc:
    current_files = f"{fm.name}_{fc.name}"
    if st.session_state['ultimo_archivo_01'] != current_files:
        keys = ['res_consol_01', 'metrics_consol_01', 'excel_bytes_01']
        for k in keys:
            if k in st.session_state: del st.session_state[k]
        st.session_state['ultimo_archivo_01'] = current_files

if st.button("Consolidar Datos", type="primary"):
    if fm and fc:
        with st.spinner("Procesando..."):
            dfp, dfc, err = cargar_archivos(fm, fc)
            if err: st.error(err)
            else:
                try:
                    res = procesar_datos(dfp, dfc)
                    
                    for c in ['fecha_inicio', 'fecha_fin', 'fecha_nacimiento', 'fecha_actualizacion']:
                        if c in res.columns:
                            res[c] = pd.to_datetime(res[c]).dt.strftime('%d/%m/%Y').replace('NaT', '')

                    # Guardar en sesión
                    st.session_state['res_consol_01'] = res
                    st.session_state['metrics_consol_01'] = (len(dfp), len(res))
                    
                    # Generar Excel (Pesado) una sola vez
                    try:
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                            res.to_excel(writer, index=False, sheet_name="Consolidado")
                        st.session_state['excel_bytes_01'] = buf.getvalue()
                    except:
                        st.session_state['excel_bytes_01'] = None

                    st.success("✅ Completado.")
                except Exception as e:
                    st.error(f"Error Lógico: {e}")

# 5. VISUALIZACIÓN Y DESCARGAS
if 'res_consol_01' in st.session_state:
    df = st.session_state['res_consol_01']
    ini, fin = st.session_state['metrics_consol_01']
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Originales", ini)
    m2.metric("Finales", fin)
    m3.metric("Fusionados", ini - fin, delta_color="inverse")
    
    st.dataframe(df.head(50))
    
    st.divider()
    st.subheader("💾 Descargar")
    
    c_conf_dl, c_btn_dl = st.columns([1, 2])
    
    with c_conf_dl:
        modo_sep = st.radio(
            "Separador CSV:", 
            ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
            horizontal=False,
            key="sep_radio_01"
        )
        
        sep_final = ";"
        if "Coma" in modo_sep: sep_final = ","
        elif "Pipe" in modo_sep: sep_final = "|"
        elif "Personalizado" in modo_sep:
            sep_final = st.text_input("Carácter:", value=";", max_chars=1, key="sep_custom_01")

    with c_btn_dl:
        st.write("###") # Espaciado
        
        # 1. Generar CSV al vuelo
        try:
            csv_data = df.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
            st.download_button(
                label=f"📥 Descargar CSV ({sep_final})", 
                data=csv_data, 
                file_name="consolidadov13.csv", 
                mime="text/csv",
                type="secondary"
            )
        except Exception as e:
            st.error(f"Separador inválido: {e}")
            
        # 2. Descargar Excel (Desde caché)
        if st.session_state.get('excel_bytes_01'):
            st.download_button(
                label="📥 Descargar Excel", 
                data=st.session_state['excel_bytes_01'], 
                file_name="consolidadov13.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )