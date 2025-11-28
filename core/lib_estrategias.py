import pandas as pd
import numpy as np
import re

# ==========================================
# LIBRERÍA DE ESTRATEGIAS (LÓGICA PURA)
# ==========================================

def regla_nif_maestro_estricto(series):
    """
    REGLA NIF (Estricta):
    Solo mira el primer valor (Maestro).
    - Si es DNI válido (8 nums + Letra) -> Lo devuelve.
    - Si NO es DNI -> Devuelve None.
    """
    if series.empty: return None
    
    # Limpieza básica del valor maestro
    val = str(series.iloc[0]).upper().strip().replace('-', '').replace(' ', '').replace('.', '')
    
    # Regex DNI Español
    if re.match(r'^[0-9]{8}[A-Z]$', val):
        return val
        
    return None

def regla_genero_estricto(series):
    """Prioriza HOMBRE/MUJER sobre desconocidos."""
    s_clean = series.dropna().astype(str).str.upper().str.strip()
    prioritarios = s_clean[s_clean.isin(['HOMBRE', 'MUJER'])]
    
    if not prioritarios.empty: return prioritarios.iloc[0]
    if not s_clean.empty: return series.mode().iloc[0]
    return None

def regla_fecha_fin_logica_negocio(series):
    """
    REGLA DE ORO FECHA FIN:
    1. Miramos el registro MAESTRO (el primero de la serie).
    2. Si Maestro es NaT (Nulo) -> El contrato sigue VIGENTE -> Resultado: NaT.
    3. Si Maestro tiene fecha -> Comparamos con el resto y nos quedamos con la MÁXIMA.
    """
    # Convertir a fechas reales
    s_fechas = pd.to_datetime(series, dayfirst=True, errors='coerce')
    
    if s_fechas.empty: return pd.NaT

    # 1. Analizar el Maestro (El primero)
    fecha_maestro = s_fechas.iloc[0]
    
    # CONDICIÓN 1: Si el maestro es Nulo (Vigente), se queda Nulo a la fuerza.
    if pd.isna(fecha_maestro):
        return pd.NaT
        
    # CONDICIÓN 2: Si el maestro tiene fecha, buscamos la mayor de todo el grupo.
    return s_fechas.max()

def regla_fecha_inicio_antiguedad(series):
    """
    REGLA FECHA INICIO:
    - La más antigua (Mínima) de todo el grupo.
    """
    s_fechas = pd.to_datetime(series, dayfirst=True, errors='coerce')
    validas = s_fechas.dropna()
    
    if not validas.empty:
        return validas.min()
        
    return pd.NaT

def regla_rellenar_huecos(series):
    """Coalesce: Devuelve el primer valor no vacío (Prioridad Maestro)."""
    s_clean = series.fillna("").astype(str).str.strip()
    # Filtramos basura
    s_clean = s_clean[s_clean != ""]
    s_clean = s_clean[~s_clean.str.lower().isin(["nan", "null", "none"])]
    
    if not s_clean.empty:
        return s_clean.iloc[0]
    return None

def regla_concatenar(series):
    """Une valores únicos con |"""
    vals = series.dropna().astype(str).unique()
    clean = [v for v in vals if v.strip() != ""]
    return " | ".join(clean) if clean else None

# ==========================================
# CATÁLOGO MAESTRO
# ==========================================
CATALOGO_ESTRATEGIAS = {
    "⚡ Rellenar Huecos (Prioridad Maestro)": regla_rellenar_huecos,
    "🆔 NIF (Estricto Maestro: Solo DNI válido)": regla_nif_maestro_estricto,
    
    # Nueva regla corregida
    "📅 Fecha Fin (Regla Negocio: Maestro Nulo Manda)": regla_fecha_fin_logica_negocio,
    
    "📅 Fecha Inicio (Más Antigua)": regla_fecha_inicio_antiguedad,
    "🚻 Género (H/M)": regla_genero_estricto,
    "🔗 Concatenar Texto": regla_concatenar
}