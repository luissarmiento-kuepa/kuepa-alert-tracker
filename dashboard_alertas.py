import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from pathlib import Path

st.set_page_config(page_title="Kuepa Alert Tracker", layout="wide", page_icon="🔶")

# ============================================================
# IDENTIDAD VISUAL KUEPA
# Colores: #FD531E naranja | #149852 verde | #9725B9 morado
#          #292929 fondo oscuro | #656A71 gris medio | #FAFAFA blanco
# Fuentes: Barlow (disponible en Google Fonts, similar a Gotham)
# ============================================================

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700;800&family=Barlow+Condensed:wght@600;700;800&display=swap');

    /* ---- BASE ---- */
    .stApp {
        background-color: #1A1A1A;
        font-family: 'Barlow', sans-serif;
    }

    /* ---- SIDEBAR ---- */
    [data-testid="stSidebar"] {
        background-color: #292929 !important;
        border-right: 3px solid #FD531E;
    }
    [data-testid="stSidebar"] * {
        color: #FAFAFA !important;
        font-family: 'Barlow', sans-serif !important;
    }
    [data-testid="stSidebar"] label {
        color: #C0C0C0 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] h2 {
        color: #FD531E !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 800 !important;
        font-size: 1.4rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ---- MAIN CONTENT ---- */
    .main .block-container {
        padding: 2rem 2.5rem;
        background-color: #1A1A1A;
    }

    /* ---- TYPOGRAPHY ---- */
    h1 {
        color: #FAFAFA !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    h2, h3 {
        color: #FAFAFA !important;
        font-family: 'Barlow', sans-serif !important;
        font-weight: 700 !important;
    }
    p, span, div, li {
        font-family: 'Barlow', sans-serif;
        color: #C0C0C0;
    }

    /* ---- MÉTRICAS ---- */
    [data-testid="metric-container"] {
        background-color: #292929;
        border: 1px solid #3A3A3A;
        border-top: 3px solid #FD531E;
        border-radius: 8px;
        padding: 1.2rem 1.5rem !important;
    }
    [data-testid="metric-container"] label {
        color: #656A71 !important;
        font-family: 'Barlow', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #FAFAFA !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 2.6rem !important;
        font-weight: 800 !important;
        line-height: 1.1;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-family: 'Barlow', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* ---- DATAFRAME ---- */
    [data-testid="stDataFrame"] {
        background-color: #292929 !important;
        border: 1px solid #3A3A3A !important;
        border-radius: 8px !important;
    }

    /* ---- DIVIDER ---- */
    hr {
        border-color: #3A3A3A !important;
        margin: 1.5rem 0 !important;
    }

    /* ---- SELECTS ---- */
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #FD531E !important;
        color: white !important;
        border-radius: 4px !important;
        font-family: 'Barlow', sans-serif !important;
        font-weight: 600 !important;
    }

    /* Fondo oscuro en todos los inputs/selects del sidebar y general */
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="input"] > div,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div {
        background-color: #2E2E2E !important;
        border: 1px solid #4A4A4A !important;
        color: #FAFAFA !important;
    }

    /* Texto dentro del select */
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #FAFAFA !important;
        background-color: transparent !important;
    }

    /* Dropdown menu desplegable */
    div[data-baseweb="popover"] > div,
    ul[data-baseweb="menu"],
    li[role="option"] {
        background-color: #2E2E2E !important;
        color: #FAFAFA !important;
    }
    li[role="option"]:hover {
        background-color: #3A3A3A !important;
    }

    /* Input de texto dentro del multiselect */
    input[type="text"] {
        background-color: #2E2E2E !important;
        color: #FAFAFA !important;
        caret-color: #FD531E !important;
    }

    /* Placeholder */
    input::placeholder {
        color: #656A71 !important;
    }

    /* ---- SCROLLBAR ---- */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #1A1A1A; }
    ::-webkit-scrollbar-thumb { background: #FD531E; border-radius: 3px; }

    /* ---- BADGES ---- */
    .kuepa-badge {
        display: inline-block;
        background-color: #FD531E;
        color: white !important;
        padding: 3px 14px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-left: 14px;
        vertical-align: middle;
        font-family: 'Barlow', sans-serif !important;
    }
    .comp-badge {
        display: inline-block;
        background-color: #9725B9;
        color: white !important;
        padding: 3px 14px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-left: 10px;
        vertical-align: middle;
        font-family: 'Barlow', sans-serif !important;
    }
    .date-tag {
        display: inline-block;
        background-color: #2E2E2E;
        border: 1px solid #FD531E;
        color: #FD531E !important;
        padding: 2px 12px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 700;
        font-family: 'Barlow', sans-serif !important;
    }
    .section-title {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 700;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #FAFAFA !important;
        border-left: 4px solid #FD531E;
        padding-left: 10px;
        margin-bottom: 1rem;
    }

    /* ---- PESTAÑAS (TABS) ---- */
    [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #232323;
        border: 1px solid #3A3A3A;
        border-radius: 12px;
        padding: 8px;
        margin-bottom: 1.2rem;
    }
    button[data-baseweb="tab"] {
        height: 52px;
        background-color: transparent !important;
        border-radius: 9px;
        padding: 0 26px !important;
        margin: 0 !important;
    }
    button[data-baseweb="tab"] [data-testid="stMarkdownContainer"] p,
    button[data-baseweb="tab"] p {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.25rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #9A9A9A !important;
        margin: 0 !important;
    }
    button[data-baseweb="tab"]:hover {
        background-color: #2E2E2E !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #FD531E !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #FFFFFF !important;
    }
    [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
        background-color: transparent !important;
        height: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---- PALETA KUEPA PARA GRÁFICAS ----
ALERT_RANK = {
    "SIN ALERTA": 0, "ALERTA TIPO 1": 1, "ALERTA TIPO 2": 2,
    "ALERTA TIPO 3": 3, "ALERTA TIPO 4": 4, "ALERTA TIPO 5": 5,
    "SIN CONEXIÓN": 6, "SIN CATEGORÍA": 6
}

# Colores de alertas usando paleta Kuepa
ALERT_COLORS = {
    "SIN ALERTA":    "#149852",   # verde Kuepa
    "ALERTA TIPO 1": "#656A71",   # gris Kuepa
    "ALERTA TIPO 2": "#9725B9",   # morado Kuepa
    "ALERTA TIPO 3": "#F5A623",   # amarillo cálido
    "ALERTA TIPO 4": "#FD531E",   # naranja Kuepa
    "ALERTA TIPO 5": "#C0392B",   # rojo fuerte
    "SIN CONEXIÓN":  "#3A3A3A",
    "SIN CATEGORÍA": "#2E2E2E",
}

ALERT_ORDER = ["SIN ALERTA","ALERTA TIPO 1","ALERTA TIPO 2","ALERTA TIPO 3","ALERTA TIPO 4","ALERTA TIPO 5","SIN CONEXIÓN","SIN CATEGORÍA"]
AXIS = dict(gridcolor="#2E2E2E", linecolor="#3A3A3A", zerolinecolor="#3A3A3A", tickfont=dict(color="#C0C0C0", family="Barlow"))

# ---- PALETA Y ORDEN ESTADO FINANCIERO ----
FIN_ORDER = ["Al día", "Mora temprana", "Mora intermedia", "Mora avanzada", "Baja por mora", "Exento de cobro"]
FIN_COLORS = {
    "Al día":           "#149852",  # verde Kuepa
    "Mora temprana":    "#F5A623",  # amarillo
    "Mora intermedia":  "#FD531E",  # naranja Kuepa
    "Mora avanzada":    "#C0392B",  # rojo
    "Baja por mora":    "#7B0000",  # rojo oscuro
    "Exento de cobro":  "#656A71",  # gris
}
FIN_RANK = {v: i for i, v in enumerate(FIN_ORDER)}

# ---- CARGA DE DATOS DESDE GOOGLE SHEETS ----
SHEET_ID = "1hPWt0oBdbJTuIEbkFh1G9V1NDXh_ADKUt3OqJPocxaU"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"

@st.cache_data(ttl=300)  # Refresca cada 5 minutos
def load_historical_data():
    # Streamlit Cloud: usa st.secrets | Local: usa credentials.json
    try:
        secrets_info = st.secrets["gcp_service_account"]
        from google.oauth2.service_account import Credentials
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(dict(secrets_info), scopes=scopes)
        gc = gspread.authorize(creds)
    except Exception:
        gc = gspread.service_account(filename=str(CREDENTIALS_FILE))
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Hoja 1")  # Pestaña específica
    all_values = worksheet.get_all_values()
    headers = all_values[0]
    rows = all_values[1:]
    df = pd.DataFrame(rows, columns=headers)
    # Eliminar columnas sin nombre (vacías)
    df = df.loc[:, df.columns != '']
    df['fecha_informe'] = df['fecha_informe'].astype(str).str.strip()
    # Detectar formato: si contiene '/' es DD/MM/YYYY, si contiene '-' es YYYY-MM-DD o DD-MM-YYYY
    sample = df['fecha_informe'].iloc[0] if len(df) > 0 else ''
    if '/' in sample:
        # Formato DD/MM/YYYY
        df['fecha_informe'] = pd.to_datetime(df['fecha_informe'], format='%d/%m/%Y', errors='coerce')
    elif '-' in sample and len(sample) >= 10:
        # Verificar si empieza con año (YYYY-) o día (DD-)
        first_part = sample.split('-')[0]
        if len(first_part) == 4:
            # Formato YYYY-MM-DD (ISO)
            df['fecha_informe'] = pd.to_datetime(df['fecha_informe'], format='%Y-%m-%d', errors='coerce')
        else:
            # Formato DD-MM-YYYY
            df['fecha_informe'] = pd.to_datetime(df['fecha_informe'], format='%d-%m-%Y', errors='coerce')
    else:
        df['fecha_informe'] = pd.to_datetime(df['fecha_informe'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['fecha_informe'])
    df = df[df['fecha_informe'] >= pd.Timestamp('2026-01-01')]  # Solo 2026 en adelante
    df['fecha_informe'] = df['fecha_informe'].dt.date
    df['gravedad'] = df['alert_type'].map(ALERT_RANK).fillna(6)
    df['fin_rank'] = df['financial_status_name'].map(FIN_RANK).fillna(99)

    # Categorizar etapa (Lectiva vs Productiva) para técnicos según level_name
    LECTIVA_KEYWORDS = ['Introducción', 'Transición', 'Etapa Lectiva', 'Módulo 0', 'Fundamentación']
    def clasificar_etapa(level):
        if pd.isna(level) or level == '':
            return 'Sin etapa'
        level_str = str(level)
        if 'Productiva' in level_str:
            return 'Productiva'
        for kw in LECTIVA_KEYWORDS:
            if kw in level_str:
                return 'Lectiva'
        return 'Otra'
    df['etapa'] = df['level_name'].apply(clasificar_etapa)

    return df

df_hist = load_historical_data()
fechas_disponibles = sorted(df_hist['fecha_informe'].unique(), reverse=True)

# ---- SIDEBAR ----
with st.sidebar:
    st.markdown("""
        <div style='text-align:center; padding: 1.5rem 1rem 1rem 1rem;'>
            <img src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABDgAAAGeCAYAAABxbbHbAAABCGlDQ1BJQ0MgUHJvZmlsZQAAeJxjYGA8wQAELAYMDLl5JUVB7k4KEZFRCuwPGBiBEAwSk4sLGHADoKpv1yBqL+viUYcLcKakFicD6Q9ArFIEtBxopAiQLZIOYWuA2EkQtg2IXV5SUAJkB4DYRSFBzkB2CpCtkY7ETkJiJxcUgdT3ANk2uTmlyQh3M/Ck5oUGA2kOIJZhKGYIYnBncAL5H6IkfxEDg8VXBgbmCQixpJkMDNtbGRgkbiHEVBYwMPC3MDBsO48QQ4RJQWJRIliIBYiZ0tIYGD4tZ2DgjWRgEL7AwMAVDQsIHG5TALvNnSEfCNMZchhSgSKeDHkMyQx6QJYRgwGDIYMZAKbWPz9HbOBQAAEAAElEQVR4nOzdd5xlx1ng/V9VnXNu7DR5pFG0JFuShS2DbWxMWGzwAusFXnaBJedlYdldlrCLze4CBgwG22CDwRkccDbOOQc5KeecZqSJnW86oep5/6hz7/TIsi1NUE+Pnq8+Vz3d09N9Q91zTj311POAUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSimllFJKKaWUUkoppZRSSiml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' style='width: 100%; max-width: 280px;'/>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<p style='color:#656A71; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:700; margin-bottom:4px'>📅 Fecha principal</p>", unsafe_allow_html=True)
    fechas_str = [f.strftime('%Y-%m-%d') for f in fechas_disponibles]
    fecha_principal_str = st.selectbox("", fechas_str, index=0, label_visibility="collapsed")
    import datetime as _dt
    fecha_principal = _dt.date.fromisoformat(fecha_principal_str)

    st.markdown("<p style='color:#656A71; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:700; margin: 12px 0 4px 0'>🔄 Comparar con (opcional)</p>", unsafe_allow_html=True)
    otras_fechas_str = [f for f in fechas_str if f != fecha_principal_str]
    fechas_comparar_str = st.multiselect("", otras_fechas_str, default=[], label_visibility="collapsed")
    fechas_comparar = [_dt.date.fromisoformat(f) for f in fechas_comparar_str]
    comparar = len(fechas_comparar) > 0

    st.markdown("---")
    st.markdown("<p style='color:#656A71; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:700; margin-bottom:4px'>📚 Etapa</p>", unsafe_allow_html=True)
    etapas_disponibles = sorted([e for e in df_hist['etapa'].unique() if e not in ['Sin etapa', 'Otra']])
    etapas_sel = st.multiselect("", etapas_disponibles, default=[], label_visibility="collapsed", key="etapa", placeholder="Todas las etapas")

    st.markdown("<p style='color:#656A71; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:700; margin: 12px 0 4px 0'>🎓 Programa</p>", unsafe_allow_html=True)
    programas = st.multiselect("", df_hist['program_name'].unique(), label_visibility="collapsed", key="prog")

    st.markdown("<p style='color:#656A71; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:700; margin: 12px 0 4px 0'>👤 Gestor</p>", unsafe_allow_html=True)
    gestores = st.multiselect("", df_hist['gestor_asignado'].unique(), label_visibility="collapsed", key="gest")

    st.markdown("---")
    st.markdown(f"<p style='color:#656A71; font-size:0.78rem; text-align:center'>{len(df_hist):,} registros totales</p>", unsafe_allow_html=True)

# ---- FILTRADO ----
mask = df_hist['fecha_informe'] == fecha_principal
if etapas_sel: mask &= df_hist['etapa'].isin(etapas_sel)
if programas: mask &= df_hist['program_name'].isin(programas)
if gestores: mask &= df_hist['gestor_asignado'].isin(gestores)
df_principal = df_hist[mask]

# ---- HEADER ----
modo = "<span class='comp-badge'>Comparativo</span>" if comparar else ""
st.markdown(
    f"<h1>Seguimiento de Alertas <span class='kuepa-badge'>Kuepa</span>{modo}</h1>",
    unsafe_allow_html=True
)
fecha_str = f"<span class='date-tag'>{fecha_principal}</span>"
comp_str = ""
if comparar:
    comp_tags = " ".join([f"<span class='date-tag' style='border-color:#9725B9; color:#9725B9'>{f}</span>" for f in sorted(fechas_comparar)])
    comp_str = f" → {comp_tags}"
st.markdown(
    f"<p style='color:#656A71; margin-top:-0.3rem; margin-bottom:1.5rem; font-size:0.9rem'>Datos del {fecha_str}{comp_str}</p>",
    unsafe_allow_html=True
)

if len(df_principal) == 0:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# ============================================================
# CARGA DE PESTAÑAS NUEVAS: Asistencia y Notas
# ============================================================
def _get_worksheet_df(sheet_name):
    try:
        secrets_info = st.secrets["gcp_service_account"]
        from google.oauth2.service_account import Credentials
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(dict(secrets_info), scopes=scopes)
        gc = gspread.authorize(creds)
    except Exception:
        gc = gspread.service_account(filename=str(CREDENTIALS_FILE))
    sh = gc.open_by_key(SHEET_ID)
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        # Tolerar diferencias de mayúsculas/espacios en el nombre de la pestaña
        # (p. ej. la pestaña se llama "MATERIAS" y aquí pedimos "Materias").
        target = sheet_name.strip().lower()
        ws = next((w for w in sh.worksheets() if w.title.strip().lower() == target), None)
        if ws is None:
            return pd.DataFrame()
    vals = ws.get_all_values()
    if not vals:
        return pd.DataFrame()
    df = pd.DataFrame(vals[1:], columns=vals[0])
    return df.loc[:, df.columns != '']

def _parse_fecha_series(s):
    s = s.astype(str).str.strip()
    sample = s.iloc[0] if len(s) > 0 else ''
    if '/' in sample:
        dt = pd.to_datetime(s, format='%d/%m/%Y', errors='coerce')
    elif '-' in sample and len(sample) >= 10 and len(sample.split('-')[0]) == 4:
        dt = pd.to_datetime(s, format='%Y-%m-%d', errors='coerce')
    else:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
    return dt.dt.date

@st.cache_data(ttl=300)
def load_asistencia():
    try:
        df = _get_worksheet_df("Asistencia")
    except Exception:
        return pd.DataFrame()
    if df.empty or 'FECHA_REPORTE' not in df.columns:
        return pd.DataFrame()
    num_cols = ['TOTAL_SESIONES_PROGRAMADAS', 'TOTAL_SESIONES_REGISTRADAS', 'SESIONES_SIN_REGISTRAR',
                'SESIONES_ASISTIO', 'SESIONES_NO_ASISTIO', 'SESIONES_TARDE', 'SESIONES_PENDIENTE',
                'PORCENTAJE_ASISTENCIA']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')
    df['fecha_informe'] = _parse_fecha_series(df['FECHA_REPORTE'])
    return df.dropna(subset=['fecha_informe'])

@st.cache_data(ttl=300)
def load_notas():
    try:
        df = _get_worksheet_df("Notas")
    except Exception:
        return pd.DataFrame()
    if df.empty or 'fecha_informe' not in df.columns:
        return pd.DataFrame()
    for c in ['modulos_cursados', 'modulos_aprobados', 'modulos_reprobados', 'nota_promedio']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')
    df['fecha_informe'] = _parse_fecha_series(df['fecha_informe'])
    return df.dropna(subset=['fecha_informe'])

@st.cache_data(ttl=300)
def load_materias():
    """Ranking de materias más reprobadas (1 fila por programa × materia)."""
    try:
        df = _get_worksheet_df("Materias")
    except Exception:
        return pd.DataFrame()
    if df.empty or 'fecha_informe' not in df.columns:
        return pd.DataFrame()
    for c in ['estudiantes_cursaron', 'estudiantes_reprobaron', 'pct_reprobacion', 'nota_promedio']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')
    df['fecha_informe'] = _parse_fecha_series(df['fecha_informe'])
    return df.dropna(subset=['fecha_informe'])

df_asis_all  = load_asistencia()
df_notas_all = load_notas()
df_mat_all   = load_materias()

# Paleta para niveles de asistencia
ASIS_ORDER  = ['🔴 CRÍTICO', '🟡 ALERTA', '🟠 BAJO', '🟢 NORMAL']
ASIS_COLORS = {'🔴 CRÍTICO': '#C0392B', '🟡 ALERTA': '#FD531E', '🟠 BAJO': '#F5A623', '🟢 NORMAL': '#149852'}

def _snapshot_fecha(df, target):
    """Devuelve el snapshot disponible más cercano a 'target' (el <= más reciente,
    o el más antiguo si no hay anteriores). Tolera desfases de fecha entre fuentes."""
    if df.empty or 'fecha_informe' not in df.columns:
        return None
    fechas = sorted(df['fecha_informe'].dropna().unique())
    if not fechas:
        return None
    previos = [f for f in fechas if f <= target]
    return max(previos) if previos else min(fechas)

def _overlap_caption(serie_ids):
    """Cuántos de esos estudiantes también disparan alerta de login (grave) o mora."""
    ids = set(serie_ids.astype(str))
    if not ids:
        return
    bl = df_principal.drop_duplicates('user_incremental')
    riesgo_ids = set(bl[(bl['gravedad'] >= 3) |
                        (bl['financial_status_name'].isin(['Mora avanzada', 'Baja por mora']))]
                     ['user_incremental'].astype(str))
    n = len(ids & riesgo_ids)
    if n > 0:
        st.markdown(
            f"<p style='color:#FD531E; font-size:0.88rem; font-weight:600; margin-top:0.2rem'>"
            f"🔗 {n} de estos estudiantes también tienen alerta de login o mora → revísalos en "
            f"<b>🎯 Riesgo 360</b></p>",
            unsafe_allow_html=True)

def _chart_help(text):
    """Copy explicativo bajo una gráfica: cómo leerla y qué hacer con ella."""
    st.markdown(
        f"<p style='color:#9AA0A6; font-size:0.84rem; line-height:1.45; "
        f"margin:-0.3rem 0 0.6rem 0'>{text}</p>",
        unsafe_allow_html=True)

# ============================================================
# PESTAÑA: AUSENTISMO  ·  [PARKED] fuera del aire (en revisión).
# El feed v2 cambió a "días de falta consecutivos" y este render aún usa
# PORCENTAJE_ASISTENCIA, por eso no se cablea a ninguna pestaña todavía.
# ============================================================
SEV_RANK = {'🔴 CRÍTICO': 3, '🟡 ALERTA': 2, '🟠 BAJO': 1, '🟢 NORMAL': 0}

def render_ausentismo():
    if df_asis_all.empty:
        st.info("Aún no hay datos de ausentismo. Verifica que la pestaña 'Asistencia' del Sheet esté poblada.")
        return
    f_asis = _snapshot_fecha(df_asis_all, fecha_principal)
    d = df_asis_all[df_asis_all['fecha_informe'] == f_asis].copy()
    if programas:
        d = d[d['PROGRAMA'].isin(programas)]
    if len(d) == 0:
        st.warning("No hay datos de ausentismo para los filtros seleccionados.")
        return
    if f_asis != fecha_principal:
        st.caption(f"📅 Snapshot de ausentismo más cercano: {f_asis} (no hay corrida del {fecha_principal})")

    # Nivel más severo por estudiante (un alumno puede tener varias materias)
    d['_sev'] = d['NIVEL_ALERTA'].map(SEV_RANK).fillna(0)
    peor = d.sort_values('_sev', ascending=False).drop_duplicates('user_incremental')
    cnt  = peor['NIVEL_ALERTA'].value_counts()
    n_crit = int(cnt.get('🔴 CRÍTICO', 0))
    n_aler = int(cnt.get('🟡 ALERTA', 0))
    n_bajo = int(cnt.get('🟠 BAJO', 0))
    total  = peor['user_incremental'].nunique()
    prom   = d['PORCENTAJE_ASISTENCIA'].mean()

    # ---- SEMÁFORO (tarjetas) ----
    cards = [
        ('🔴', 'CRÍTICO', str(n_crit), ASIS_COLORS['🔴 CRÍTICO'], 'Asistencia &lt; 50%'),
        ('🟡', 'ALERTA',  str(n_aler), ASIS_COLORS['🟡 ALERTA'],  'Asistencia 50–70%'),
        ('🟠', 'BAJO',    str(n_bajo), ASIS_COLORS['🟠 BAJO'],    'Asistencia 70–85%'),
        ('📊', 'PROMEDIO', f"{prom:.0f}%" if pd.notna(prom) else '—', '#656A71', f'{total} estudiantes'),
    ]
    for col, (emoji, label, val, color, sub) in zip(st.columns(4), cards):
        col.markdown(
            f"<div style='background:#232323;border:1px solid #3A3A3A;border-top:4px solid {color};"
            f"border-radius:10px;padding:14px 10px;text-align:center'>"
            f"<div style='font-size:1.5rem'>{emoji}</div>"
            f"<div style='font-family:Barlow Condensed,sans-serif;font-weight:800;font-size:2.4rem;color:{color};line-height:1.1'>{val}</div>"
            f"<div style='color:#C0C0C0;font-size:0.78rem;text-transform:uppercase;letter-spacing:0.08em;font-weight:700'>{label}</div>"
            f"<div style='color:#656A71;font-size:0.72rem;margin-top:2px'>{sub}</div></div>",
            unsafe_allow_html=True)
    _overlap_caption(peor['user_incremental'])
    st.divider()

    # ---- Dona (distribución por nivel) + Prioridad por programa ----
    g1, g2 = st.columns([1, 1.4])
    with g1:
        st.markdown("<div class='section-title'>Semáforo de ausentismo</div>", unsafe_allow_html=True)
        order = ['🔴 CRÍTICO', '🟡 ALERTA', '🟠 BAJO']
        fig_d = go.Figure(go.Pie(
            labels=order, values=[n_crit, n_aler, n_bajo], hole=0.62, sort=False, direction='clockwise',
            marker=dict(colors=[ASIS_COLORS[k] for k in order], line=dict(color='#1A1A1A', width=2)),
            textinfo='value', textfont=dict(color='white', size=14, family='Barlow'),
            hovertemplate="<b>%{label}</b><br>%{value} estudiantes (%{percent})<extra></extra>",
        ))
        fig_d.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#C0C0C0", family="Barlow"), height=330,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, x=0, font=dict(size=11, color="#C0C0C0")),
            annotations=[dict(text=f"<b>{n_crit + n_aler + n_bajo}</b><br>en riesgo", x=0.5, y=0.5,
                              font=dict(size=17, color="#FAFAFA", family="Barlow Condensed"), showarrow=False)],
        )
        st.plotly_chart(fig_d, use_container_width=True)
    with g2:
        st.markdown("<div class='section-title'>Dónde priorizar — Programas con más estudiantes en riesgo</div>", unsafe_allow_html=True)
        prio = (peor[peor['_sev'] >= 2].groupby('PROGRAMA')['user_incremental']
                .nunique().reset_index(name='en_riesgo').sort_values('en_riesgo'))
        if len(prio) > 0:
            fig_p = go.Figure(go.Bar(
                y=prio['PROGRAMA'], x=prio['en_riesgo'], orientation='h',
                marker=dict(color=prio['en_riesgo'],
                            colorscale=[[0, '#F5A623'], [0.5, '#FD531E'], [1, '#C0392B']], line=dict(width=0)),
                text=prio['en_riesgo'], textposition='outside',
                textfont=dict(color='#FAFAFA', size=13, family='Barlow'),
                hovertemplate="<b>%{y}</b><br>%{x} estudiantes en crítico/alerta<extra></extra>",
            ))
            fig_p.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#C0C0C0", family="Barlow"),
                height=max(330, len(prio) * 42), margin=dict(l=10, r=44, t=10, b=10),
                xaxis=dict(**AXIS), yaxis=dict(**AXIS),
            )
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.success("✅ Ningún programa con estudiantes en nivel crítico o alerta.")
    st.divider()

    st.markdown("<div class='section-title'>Estudiantes a contactar — peor asistencia primero</div>", unsafe_allow_html=True)
    cols_t = ['user_incremental', 'NOMBRE_ESTUDIANTE', 'PROGRAMA', 'ASIGNATURA',
              'PORCENTAJE_ASISTENCIA', 'SESIONES_NO_ASISTIO', 'NIVEL_ALERTA']
    cols_t = [c for c in cols_t if c in d.columns]
    st.dataframe(
        d[cols_t].sort_values('PORCENTAJE_ASISTENCIA').reset_index(drop=True).rename(columns={
            'user_incremental': 'ID', 'NOMBRE_ESTUDIANTE': 'Estudiante', 'PROGRAMA': 'Programa',
            'ASIGNATURA': 'Asignatura', 'PORCENTAJE_ASISTENCIA': '% Asistencia',
            'SESIONES_NO_ASISTIO': 'Sesiones No Asistió', 'NIVEL_ALERTA': 'Nivel',
        }),
        use_container_width=True, height=360,
    )

    st.divider()
    st.markdown("<div class='section-title' style='border-color:#9725B9'>⚠️ Panel operativo — Sesiones sin registrar (docentes)</div>", unsafe_allow_html=True)
    if 'ESTADO_REGISTRO_PROFESORES' in d.columns:
        doc = d[d['ESTADO_REGISTRO_PROFESORES'] == '⚠️ PENDIENTE REGISTRO']
        if len(doc) > 0:
            g = (doc.groupby(['PROGRAMA', 'GRUPO', 'ASIGNATURA'])['SESIONES_SIN_REGISTRAR']
                 .max().reset_index().sort_values('SESIONES_SIN_REGISTRAR', ascending=False))
            st.dataframe(
                g.reset_index(drop=True).rename(columns={
                    'PROGRAMA': 'Programa', 'GRUPO': 'Grupo', 'ASIGNATURA': 'Asignatura',
                    'SESIONES_SIN_REGISTRAR': 'Sesiones sin registrar',
                }),
                use_container_width=True, height=260,
            )
            st.markdown(f"<p style='color:#9725B9; font-size:0.8rem; font-weight:700'>⚠️ {len(g)} grupos/asignaturas con sesiones pendientes de registro</p>", unsafe_allow_html=True)
        else:
            st.success("✅ Todas las sesiones del periodo están registradas.")

# ============================================================
# PESTAÑA: REPROBACIÓN
# ============================================================
def render_reprobacion():
    if df_notas_all.empty:
        st.info("Aún no hay datos de notas. Verifica que la pestaña 'Notas' del Sheet esté poblada.")
        return
    f_notas = _snapshot_fecha(df_notas_all, fecha_principal)
    d = df_notas_all[df_notas_all['fecha_informe'] == f_notas].copy()
    if programas:
        d = d[d['program_name'].isin(programas)]
    if len(d) == 0:
        st.warning("No hay datos de notas para los filtros seleccionados.")
        return
    if f_notas != fecha_principal:
        st.caption(f"📅 Snapshot de notas más cercano: {f_notas} (no hay corrida del {fecha_principal})")

    total   = d['user_incremental'].nunique()
    con_rep = d[d['modulos_reprobados'] > 0]['user_incremental'].nunique()
    tot_rep = int(d['modulos_reprobados'].sum())
    prom    = d['nota_promedio'].mean()
    pct_afect = con_rep / total * 100 if total else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Estudiantes", total)
    c2.metric("📕 Con ≥1 reprobada", con_rep, f"{pct_afect:.1f}%" if total else "0%", delta_color="inverse")
    c3.metric("📚 Módulos reprobados", tot_rep)
    c4.metric("📊 Nota promedio", f"{prom:.2f}" if pd.notna(prom) else "—")
    _chart_help(
        f"Lee así: de <b>{total}</b> estudiantes activos, <b>{con_rep}</b> "
        f"(<b>{pct_afect:.0f}%</b>) arrastran al menos un módulo reprobado, sumando "
        f"<b>{tot_rep}</b> reprobaciones en total. La nota promedio es sobre la mejor "
        f"nota lograda en cada materia, así que <i>ya descuenta recuperaciones</i>: si el "
        f"número baja semana a semana, el gestor está moviendo la aguja.")
    _overlap_caption(d[d['modulos_reprobados'] > 0]['user_incremental'])
    st.divider()

    # ── 1. ¿QUIÉNES? Estudiantes afectados: por programa + por carga de reprobación ──
    g1, g2 = st.columns([1.3, 1])
    with g1:
        st.markdown("<div class='section-title'>¿Dónde están? — Estudiantes con reprobaciones por programa</div>", unsafe_allow_html=True)
        bar = (d[d['modulos_reprobados'] > 0].groupby('program_name')['user_incremental']
               .nunique().reset_index(name='estudiantes').sort_values('estudiantes'))
        fig = go.Figure(go.Bar(
            y=bar['program_name'], x=bar['estudiantes'], orientation='h',
            marker=dict(color="#C0392B", line=dict(width=0)),
            text=bar['estudiantes'], textposition='outside',
            textfont=dict(color='#FAFAFA', size=13, family='Barlow'),
            hovertemplate="<b>%{y}</b><br>%{x} estudiantes con ≥1 reprobada<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#C0C0C0", family="Barlow"),
            height=max(330, bar['program_name'].nunique() * 46), margin=dict(l=10, r=44, t=20, b=20),
            xaxis=dict(**AXIS), yaxis=dict(**AXIS),
        )
        st.plotly_chart(fig, use_container_width=True)
        _chart_help("Cada barra es el <b>nº de estudiantes distintos</b> con al menos un módulo "
                    "reprobado en ese programa. Sirve para repartir la carga de gestión entre coordinaciones.")
    with g2:
        st.markdown("<div class='section-title'>¿Qué tan grave? — Módulos reprobados por estudiante</div>", unsafe_allow_html=True)
        rep = d[d['modulos_reprobados'] > 0]['modulos_reprobados']
        buckets = pd.cut(rep, bins=[0, 1, 2, 3, 100], labels=['1', '2', '3', '4+'])
        dist = buckets.value_counts().reindex(['1', '2', '3', '4+']).fillna(0).astype(int)
        bucket_colors = ['#F5A623', '#FD531E', '#C0392B', '#7B0000']
        fig_b = go.Figure(go.Bar(
            x=dist.index, y=dist.values,
            marker=dict(color=bucket_colors, line=dict(width=0)),
            text=dist.values, textposition='outside',
            textfont=dict(color='#FAFAFA', size=13, family='Barlow'),
            hovertemplate="<b>%{x} módulo(s) reprobado(s)</b><br>%{y} estudiantes<extra></extra>",
        ))
        fig_b.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#C0C0C0", family="Barlow"),
            height=max(330, 330), margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(title="Módulos reprobados", **AXIS), yaxis=dict(**AXIS),
        )
        st.plotly_chart(fig_b, use_container_width=True)
        multi_rep = int((rep >= 3).sum())
        _chart_help(f"Distribución de la <b>severidad</b>. Los <b>{multi_rep}</b> estudiantes con "
                    f"3+ módulos reprobados son los más cerca de la deserción: priorízalos.")
    st.divider()

    # ── 2. ¿QUÉ MATERIAS? Ranking de asignaturas más reprobadas (feed "Materias") ──
    st.markdown("<div class='section-title' style='border-color:#C0392B'>Materias que más se reprueban</div>", unsafe_allow_html=True)
    if df_mat_all.empty:
        st.info("ℹ️ Aún no hay datos a nivel de materia. Falta poblar la pestaña **'Materias'** del "
                "Sheet con la query `queries/materias_reprobadas.sql` (nodo n8n nuevo). "
                "Mientras tanto, arriba ya ves el desempeño resumido por estudiante.")
    else:
        f_mat = _snapshot_fecha(df_mat_all, fecha_principal)
        m = df_mat_all[df_mat_all['fecha_informe'] == f_mat].copy()
        if programas and 'program_name' in m.columns:
            m = m[m['program_name'].isin(programas)]
        if len(m) == 0:
            st.warning("No hay datos de materias para los filtros seleccionados.")
        else:
            if f_mat != fecha_principal:
                st.caption(f"📅 Snapshot de materias más cercano: {f_mat} (no hay corrida del {fecha_principal})")

            # Separar por modalidad: las materias de Bachillerato y de Técnico Laboral
            # no son comparables entre sí (planes y nombres distintos).
            mod_sel = None
            if 'modalidad' in m.columns:
                mods = [x for x in ['Técnico', 'Bachillerato'] if x in set(m['modalidad'])]
                if len(mods) > 1:
                    mod_sel = st.radio("Modalidad", mods, horizontal=True,
                                       key="mat_modalidad", label_visibility="collapsed")
                elif mods:
                    mod_sel = mods[0]
                if mod_sel:
                    m = m[m['modalidad'] == mod_sel]
                    etiqueta = 'Técnico Laboral' if mod_sel == 'Técnico' else mod_sel
                    st.caption(f"Mostrando materias de **{etiqueta}**")

            # Re-agregamos por materia sumando los programas seleccionados (dentro de la modalidad)
            agg = (m.groupby('materia')
                   .agg(reprobaron=('estudiantes_reprobaron', 'sum'),
                        cursaron=('estudiantes_cursaron', 'sum'),
                        nota=('nota_promedio', 'mean'))
                   .reset_index())
            agg['pct'] = (agg['reprobaron'] / agg['cursaron'] * 100).round(1)

            cA, cB = st.columns(2)
            with cA:
                st.markdown("<p style='color:#FAFAFA;font-weight:700;font-size:0.95rem;margin:0 0 .3rem'>Por volumen — más estudiantes reprobados</p>", unsafe_allow_html=True)
                top_v = agg.sort_values('reprobaron').tail(12)
                fig_v = go.Figure(go.Bar(
                    y=top_v['materia'], x=top_v['reprobaron'], orientation='h',
                    marker=dict(color="#C0392B", line=dict(width=0)),
                    text=top_v['reprobaron'], textposition='outside',
                    textfont=dict(color='#FAFAFA', size=12, family='Barlow'),
                    customdata=top_v[['pct', 'cursaron']].values,
                    hovertemplate="<b>%{y}</b><br>%{x} reprobados de %{customdata[1]} (%{customdata[0]}%)<extra></extra>",
                ))
                fig_v.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C0C0C0", family="Barlow"),
                    height=max(380, len(top_v) * 30), margin=dict(l=10, r=44, t=10, b=20),
                    xaxis=dict(**AXIS), yaxis=dict(**AXIS),
                )
                st.plotly_chart(fig_v, use_container_width=True)
                _chart_help("<b>Cuántos</b> estudiantes cargan cada materia. Es la cola de trabajo: "
                            "atender estas materias descarga al mayor número de alumnos.")
            with cB:
                st.markdown("<p style='color:#FAFAFA;font-weight:700;font-size:0.95rem;margin:0 0 .3rem'>Por dificultad — mayor % de reprobación</p>", unsafe_allow_html=True)
                # % solo es comparable con masa suficiente: pedimos ≥5 que la cursaron
                top_p = agg[agg['cursaron'] >= 5].sort_values('pct').tail(12)
                fig_p = go.Figure(go.Bar(
                    y=top_p['materia'], x=top_p['pct'], orientation='h',
                    marker=dict(color=top_p['pct'],
                                colorscale=[[0, '#F5A623'], [0.5, '#FD531E'], [1, '#7B0000']], line=dict(width=0)),
                    text=top_p['pct'].map(lambda v: f"{v:.0f}%"), textposition='outside',
                    textfont=dict(color='#FAFAFA', size=12, family='Barlow'),
                    customdata=top_p[['reprobaron', 'cursaron']].values,
                    hovertemplate="<b>%{y}</b><br>%{x}% reprueban (%{customdata[0]} de %{customdata[1]})<extra></extra>",
                ))
                fig_p.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C0C0C0", family="Barlow"),
                    height=max(380, len(top_p) * 30), margin=dict(l=10, r=50, t=10, b=20),
                    xaxis=dict(ticksuffix="%", **AXIS), yaxis=dict(**AXIS),
                )
                st.plotly_chart(fig_p, use_container_width=True)
                _chart_help("<b>Qué tan dura</b> es cada materia (% de quienes la cursan y la reprueban, "
                            "mín. 5 estudiantes). Señala dónde revisar contenido, evaluación o apoyo docente.")

            st.markdown("<div class='section-title'>Detalle por materia</div>", unsafe_allow_html=True)
            tabla = agg.sort_values('reprobaron', ascending=False).reset_index(drop=True)
            tabla['nota'] = tabla['nota'].round(2)
            st.dataframe(
                tabla[['materia', 'cursaron', 'reprobaron', 'pct', 'nota']].rename(columns={
                    'materia': 'Materia', 'cursaron': 'La cursaron', 'reprobaron': 'La reprobaron',
                    'pct': '% Reprobación', 'nota': 'Nota Prom.',
                }),
                use_container_width=True, height=340,
            )
    st.divider()

    # ── 3. ¿QUIÉNES en detalle? Tabla por estudiante (para gestión 1-a-1) ──
    st.markdown("<div class='section-title'>Estudiantes a gestionar — más reprobaciones primero</div>", unsafe_allow_html=True)
    cols_t = ['user_incremental', 'user_full_name', 'program_name', 'modulos_cursados',
              'modulos_aprobados', 'modulos_reprobados', 'nota_promedio']
    cols_t = [c for c in cols_t if c in d.columns]
    st.dataframe(
        d[d['modulos_reprobados'] > 0][cols_t].sort_values('modulos_reprobados', ascending=False)
        .reset_index(drop=True).rename(columns={
            'user_incremental': 'ID', 'user_full_name': 'Estudiante', 'program_name': 'Programa',
            'modulos_cursados': 'Cursados', 'modulos_aprobados': 'Aprobados',
            'modulos_reprobados': 'Reprobados', 'nota_promedio': 'Nota Prom.',
        }),
        use_container_width=True, height=360,
    )
    _chart_help("Lista accionable para el gestor: cada fila es un estudiante. "
                "<b>Cursados = Aprobados + Reprobados</b>; cuando recupera una materia, baja "
                "<i>Reprobados</i> y la fila mejora en el siguiente snapshot.")

# ============================================================
# PESTAÑA: RIESGO 360 (cruce de las 4 señales)
# ============================================================
def render_riesgo360():
    base = df_principal.drop_duplicates('user_incremental')[
        ['user_incremental', 'user_full_name', 'gestor_asignado', 'gravedad', 'financial_status_name']
    ].copy()
    base['user_incremental'] = base['user_incremental'].astype(str)
    base['sig_login'] = base['gravedad'] >= 3
    base['sig_mora']  = base['financial_status_name'].isin(['Mora avanzada', 'Baja por mora'])

    # 📉 Señal de ausentismo: PAUSADA junto con su pestaña (feed v2 en revisión).
    base['sig_asis'] = False

    base['sig_reprob'] = False
    if not df_notas_all.empty:
        dn = df_notas_all[df_notas_all['fecha_informe'] == _snapshot_fecha(df_notas_all, fecha_principal)].drop_duplicates('user_incremental').copy()
        dn['user_incremental'] = dn['user_incremental'].astype(str)
        repmap = dn.set_index('user_incremental')['modulos_reprobados'] > 0
        base['sig_reprob'] = base['user_incremental'].map(repmap).fillna(False)

    for c in ['sig_login', 'sig_mora', 'sig_asis', 'sig_reprob']:
        base[c] = base[c].astype(bool)
    base['num_senales'] = base[['sig_login', 'sig_mora', 'sig_asis', 'sig_reprob']].sum(axis=1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 Riesgo múltiple (2+)", int((base['num_senales'] >= 2).sum()))
    c2.metric("🔌 Login grave",          int(base['sig_login'].sum()))
    c3.metric("💳 Mora",                  int(base['sig_mora'].sum()))
    c4.metric("📕 Con reprobaciones",    int(base['sig_reprob'].sum()))
    st.divider()

    multi = base[base['num_senales'] >= 2].copy()
    if len(multi) == 0:
        st.success("✅ No hay estudiantes con 2 o más señales de riesgo en esta fecha.")
        return

    def _senales(r):
        partes = []
        if r['sig_login']:  partes.append('🔌 Login')
        if r['sig_mora']:   partes.append('💳 Mora')
        if r['sig_asis']:   partes.append('📉 Ausentismo')
        if r['sig_reprob']: partes.append('📕 Reprobación')
        return '  +  '.join(partes)

    multi['Señales'] = multi.apply(_senales, axis=1)

    # ---- Gráfico: combinaciones de riesgo más frecuentes ----
    st.markdown("<div class='section-title' style='border-color:#C0392B'>Combinaciones de Riesgo más Frecuentes</div>", unsafe_allow_html=True)
    combo = (multi.groupby('Señales')
             .agg(estudiantes=('Señales', 'size'), n=('num_senales', 'max'))
             .reset_index().sort_values('estudiantes'))
    combo_colors = combo['n'].map({2: '#F5A623', 3: '#FD531E', 4: '#7B0000'}).fillna('#FD531E')
    fig_combo = go.Figure(go.Bar(
        y=combo['Señales'], x=combo['estudiantes'], orientation='h',
        marker=dict(color=combo_colors, line=dict(width=0)),
        text=combo['estudiantes'], textposition='outside',
        textfont=dict(color='#FAFAFA', size=13, family='Barlow'),
        hovertemplate="<b>%{y}</b><br>%{x} estudiantes<extra></extra>",
    ))
    fig_combo.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#C0C0C0", family="Barlow"),
        height=max(280, len(combo) * 46), margin=dict(l=10, r=40, t=20, b=20),
        xaxis=dict(**AXIS), yaxis=dict(**AXIS),
    )
    st.plotly_chart(fig_combo, use_container_width=True)
    st.divider()

    st.markdown("<div class='section-title' style='border-color:#C0392B'>🚨 Estudiantes en Riesgo Múltiple — 2+ señales simultáneas</div>", unsafe_allow_html=True)
    show = (multi.sort_values('num_senales', ascending=False)
            [['user_incremental', 'user_full_name', 'gestor_asignado', 'Señales', 'num_senales']]
            .reset_index(drop=True).rename(columns={
                'user_incremental': 'ID', 'user_full_name': 'Estudiante',
                'gestor_asignado': 'Gestor', 'num_senales': '# Señales',
            }))
    st.dataframe(show, use_container_width=True, height=420)
    st.markdown(f"<p style='color:#C0392B; font-size:0.8rem; font-weight:700'>⚠️ {len(multi)} estudiantes con señales combinadas de deserción</p>", unsafe_allow_html=True)

# ============================================================
# NAVEGACIÓN POR PESTAÑAS
# ============================================================
# 📉 Ausentismo: temporalmente FUERA DEL AIRE (feed v2 en revisión, evita confusión).
# La función render_ausentismo() y su loader quedan en el código para reactivarla luego.
tab_360, tab_conexion, tab_reprob = st.tabs(
    ["🎯 Riesgo 360", "🔌 Conexión", "📕 Reprobación"]
)

with tab_360:
    render_riesgo360()

with tab_conexion:
    # ============================================================
    # MÉTRICAS
    # ============================================================
    total_estudiantes = df_principal['user_id'].nunique()
    sin_alerta        = df_principal[df_principal['gravedad'] == 0]['user_id'].nunique()
    alertas_criticas  = df_principal[df_principal['gravedad'] >= 4]['user_id'].nunique()
    pct_sin_alerta    = sin_alerta / total_estudiantes * 100 if total_estudiantes > 0 else 0
    
    # Métricas financieras
    en_mora      = df_principal[df_principal['financial_status_name'].isin(['Mora temprana','Mora intermedia','Mora avanzada','Baja por mora'])]['user_id'].nunique()
    baja_mora    = df_principal[df_principal['financial_status_name'] == 'Baja por mora']['user_id'].nunique()
    pct_mora     = en_mora / total_estudiantes * 100 if total_estudiantes > 0 else 0
    doble_riesgo = df_principal[
        (df_principal['gravedad'] >= 3) &
        (df_principal['financial_status_name'].isin(['Mora avanzada','Baja por mora']))
    ]['user_id'].nunique()
    
    if comparar:
        import datetime
        # Usar la fecha de comparación más reciente para la comparativa de mejoraron/empeoraron
        fecha_comp_reciente = max(fechas_comparar)
        mask_v = df_hist['fecha_informe'] == fecha_comp_reciente
        if etapas_sel: mask_v &= df_hist['etapa'].isin(etapas_sel)
        if programas: mask_v &= df_hist['program_name'].isin(programas)
        if gestores:  mask_v &= df_hist['gestor_asignado'].isin(gestores)
        df_vieja = df_hist[mask_v]
    
        df_v = df_vieja[['user_id', 'gravedad', 'gestor_asignado']].rename(columns={'gravedad': 'gravedad_viejo', 'gestor_asignado': 'gestor_responsable'})
        df_n = df_principal[['user_id', 'user_incremental', 'gravedad', 'user_full_name', 'gestor_asignado']].rename(columns={'gravedad': 'gravedad_nuevo', 'gestor_asignado': 'gestor_actual'})
        comparativa = pd.merge(df_n, df_v, on='user_id')
        comparativa['cambio'] = comparativa['gravedad_viejo'] - comparativa['gravedad_nuevo']
        # gestor_responsable = gestor de la fecha anterior (quien gestionó antes del cambio)
        mejoraron  = comparativa[comparativa['cambio'] > 0]
        empeoraron = comparativa[comparativa['cambio'] < 0]
        estables   = comparativa[comparativa['cambio'] == 0]
    
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("👥 Estudiantes",       total_estudiantes)
        c2.metric("🟢 Sin Alerta",        sin_alerta,       f"{pct_sin_alerta:.1f}%")
        c3.metric("✅ Mejoraron",          len(mejoraron),   f"{len(mejoraron)/len(comparativa):.1%}" if len(comparativa) > 0 else "0%")
        c4.metric("⚠️ Empeoraron",        len(empeoraron),  f"-{len(empeoraron)/len(comparativa):.1%}" if len(comparativa) > 0 else "0%", delta_color="inverse")
        c5.metric("💳 En Mora",           en_mora,          f"{pct_mora:.1f}%", delta_color="inverse")
        c6.metric("🚨 Doble Riesgo",      doble_riesgo,     "login + pago", delta_color="off")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("👥 Total Estudiantes",  total_estudiantes)
        c2.metric("🟢 Sin Alerta",         sin_alerta,       f"{pct_sin_alerta:.1f}%")
        c3.metric("🔴 Alertas Críticas",   alertas_criticas)
        c4.metric("💳 En Mora",            en_mora,          f"{pct_mora:.1f}%", delta_color="inverse")
        c5.metric("🚨 Doble Riesgo",       doble_riesgo,     "login + pago", delta_color="off")
    
    st.divider()
    
    # ============================================================
    # BARRAS APILADAS HORIZONTALES (por programa) — siempre visible
    # ============================================================
    st.markdown(f"<div class='section-title'>Alertas por Programa — {fecha_principal}</div>", unsafe_allow_html=True)
    
    bar_data = df_principal.groupby(['program_name', 'alert_type']).size().reset_index(name='count')
    tipos_presentes = [a for a in ALERT_ORDER if a in bar_data['alert_type'].unique()]
    
    orden = (
        df_principal[df_principal['gravedad'] >= 3]
        .groupby('program_name')['user_id'].count()
        .sort_values(ascending=True).index.tolist()
    )
    for p in df_principal['program_name'].unique():
        if p not in orden:
            orden.insert(0, p)
    
    fig_bar = go.Figure()
    for alert in tipos_presentes:
        subset = bar_data[bar_data['alert_type'] == alert]
        fig_bar.add_trace(go.Bar(
            name=alert,
            y=subset['program_name'],
            x=subset['count'],
            orientation='h',
            marker=dict(color=ALERT_COLORS.get(alert, "#FD531E"), line=dict(width=0)),
            text=subset['count'],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12, family='Barlow'),
            hovertemplate=f"<b>{alert}</b><br>%{{y}}<br><b>%{{x}}</b> estudiantes<extra></extra>",
        ))
    
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#C0C0C0", family="Barlow"),
        barmode='stack',
        height=max(420, len(orden) * 52),
        margin=dict(l=10, r=20, t=60, b=20),
        yaxis=dict(**AXIS, categoryorder='array', categoryarray=orden),
        xaxis=dict(**AXIS, title=dict(text="Número de estudiantes", font=dict(color="#656A71", size=12))),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#C0C0C0"), traceorder="normal"
        ),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()
    
    # ============================================================
    # COMPARATIVA DE FECHAS — Barras verticales apiladas al 100%
    # ============================================================
    if comparar:
        st.markdown("<div class='section-title'>Comparativa entre Fechas</div>", unsafe_allow_html=True)
    
        # Reunir todas las fechas a comparar (principal + seleccionadas)
        todas_fechas = sorted([fecha_principal] + list(fechas_comparar))
    
        # Calcular distribución por fecha
        comp_rows = []
        for fecha in todas_fechas:
            mask_f = df_hist['fecha_informe'] == fecha
            if etapas_sel: mask_f &= df_hist['etapa'].isin(etapas_sel)
            if programas: mask_f &= df_hist['program_name'].isin(programas)
            if gestores:  mask_f &= df_hist['gestor_asignado'].isin(gestores)
            df_fecha = df_hist[mask_f]
            total_fecha = len(df_fecha)
            for alert in ALERT_ORDER:
                cnt = len(df_fecha[df_fecha['alert_type'] == alert])
                pct = (cnt / total_fecha * 100) if total_fecha > 0 else 0
                comp_rows.append({
                    'fecha': str(fecha),
                    'alert_type': alert,
                    'count': cnt,
                    'pct': pct
                })
        comp_df = pd.DataFrame(comp_rows)
    
        # Tipos presentes en la comparativa
        tipos_comp = [a for a in ALERT_ORDER if a in comp_df[comp_df['count'] > 0]['alert_type'].unique()]
    
        col_chart, col_donut = st.columns([2, 1])
    
        with col_chart:
            fig_comp = go.Figure()
            for alert in tipos_comp:
                subset = comp_df[comp_df['alert_type'] == alert]
                # Formatear números con separador de miles (punto)
                text_vals = [f"{int(c):,}".replace(",", ".") for c in subset['count']]
                fig_comp.add_trace(go.Bar(
                    name=alert,
                    x=subset['fecha'],
                    y=subset['pct'],
                    marker=dict(
                        color=ALERT_COLORS.get(alert, "#FD531E"),
                        line=dict(width=0)
                    ),
                    text=text_vals,
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(color='white', size=13, family='Barlow Condensed'),
                    customdata=subset['count'],
                    hovertemplate=f"<b>{alert}</b><br>%{{x}}<br><b>%{{customdata}}</b> estudiantes (%{{y:.1f}}%)<extra></extra>",
                ))
    
            fig_comp.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#C0C0C0", family="Barlow"),
                barmode='stack',
                barnorm='',  # Ya calculamos % manualmente
                height=480,
                margin=dict(l=10, r=10, t=20, b=60),
                xaxis=dict(
                    type="category",  # Fuerza categorías discretas, sin fechas intermedias
                    tickfont=dict(color="#FAFAFA", family="Barlow Condensed", size=14),
                    linecolor="#3A3A3A",
                    gridcolor="rgba(0,0,0,0)",
                ),
                yaxis=dict(
                    tickfont=dict(color="#C0C0C0", family="Barlow", size=11),
                    linecolor="#3A3A3A",
                    gridcolor="#2E2E2E",
                    ticksuffix="%",
                    range=[0, 100],
                    dtick=10,
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#C0C0C0"), traceorder="normal"
                ),
                bargap=0.3,
            )
            st.plotly_chart(fig_comp, use_container_width=True)
    
        with col_donut:
            st.markdown("<div class='section-title'>Resumen de Cambios</div>", unsafe_allow_html=True)
            fig_donut = go.Figure(data=[go.Pie(
                labels=["Mejoraron", "Empeoraron", "Estables"],
                values=[len(mejoraron), len(empeoraron), len(estables)],
                hole=0.65,
                marker=dict(
                    colors=["#149852", "#FD531E", "#9725B9"],
                    line=dict(color="#1A1A1A", width=3)
                ),
                textfont=dict(color="white", size=12, family="Barlow"),
                hovertemplate="<b>%{label}</b><br>%{value} estudiantes (%{percent})<extra></extra>",
            )])
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#C0C0C0", family="Barlow"),
                height=400, margin=dict(l=10, r=10, t=20, b=10),
                showlegend=True,
                legend=dict(orientation="v", font=dict(size=12, color="#C0C0C0"), bgcolor="rgba(0,0,0,0)"),
                annotations=[dict(
                    text=f"<b>{len(comparativa)}</b><br><span style='font-size:11px'>estudiantes</span>",
                    x=0.5, y=0.5, font_size=20, showarrow=False,
                    font=dict(color="#FAFAFA", family="Barlow")
                )]
            )
            st.plotly_chart(fig_donut, use_container_width=True)
    
        st.divider()
    
        # Tabla de empeoraron
        st.markdown("<div class='section-title'>Estudiantes que Empeoraron</div>", unsafe_allow_html=True)
        if len(empeoraron) > 0:
            st.dataframe(
                empeoraron[['user_incremental', 'user_full_name', 'gestor_responsable', 'gravedad_viejo', 'gravedad_nuevo']]
                .sort_values('gravedad_nuevo', ascending=False)
                .reset_index(drop=True)
                .rename(columns={
                    'user_incremental':    'ID',
                    'user_full_name':      'Estudiante',
                    'gestor_responsable':  'Gestor Responsable',
                    'gravedad_viejo':      'Gravedad Anterior',
                    'gravedad_nuevo':      'Gravedad Actual'
                }),
                use_container_width=True, height=340
            )
        else:
            st.success("✅ Ningún estudiante empeoró entre las fechas seleccionadas.")
    
        st.divider()
    
    # ============================================================
    # CARTERA: DISTRIBUCIÓN FINANCIERA + MATRIZ DE RIESGO
    # ============================================================
    col_fin, col_matriz = st.columns([1, 2])
    
    with col_fin:
        st.markdown("<div class='section-title'>Estado de Cartera</div>", unsafe_allow_html=True)
    
        fin_counts = df_principal.groupby('financial_status_name')['user_id'].count().reset_index(name='count')
        fin_counts['rank'] = fin_counts['financial_status_name'].map(FIN_RANK).fillna(99)
        fin_counts = fin_counts.sort_values('rank')
    
        fig_fin = go.Figure(data=[go.Pie(
            labels=fin_counts['financial_status_name'],
            values=fin_counts['count'],
            hole=0.6,
            marker=dict(
                colors=[FIN_COLORS.get(s, "#656A71") for s in fin_counts['financial_status_name']],
                line=dict(color="#1A1A1A", width=3)
            ),
            textfont=dict(color="white", size=11, family="Barlow"),
            hovertemplate="<b>%{label}</b><br><b>%{value}</b> estudiantes (%{percent})<extra></extra>",
            sort=False,
        )])
        al_dia_pct = fin_counts[fin_counts['financial_status_name'] == 'Al día']['count'].sum()
        al_dia_pct = al_dia_pct / total_estudiantes * 100 if total_estudiantes > 0 else 0
        fig_fin.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#C0C0C0", family="Barlow"),
            height=320, margin=dict(l=0, r=0, t=10, b=10),
            showlegend=True,
            legend=dict(orientation="v", font=dict(size=11, color="#C0C0C0"), bgcolor="rgba(0,0,0,0)", x=0.75, y=0.5),
            annotations=[dict(
                text=f"<b>{al_dia_pct:.0f}%</b><br><span style='font-size:10px'>al día</span>",
                x=0.36, y=0.5, font_size=18, showarrow=False,
                font=dict(color="#149852", family="Barlow Condensed")
            )]
        )
        st.plotly_chart(fig_fin, use_container_width=True)
    
    with col_matriz:
        st.markdown("<div class='section-title'>Matriz de Riesgo de Deserción</div>", unsafe_allow_html=True)
    
        alertas_vis = [a for a in ALERT_ORDER if a in df_principal['alert_type'].unique()]
        estados_vis  = [f for f in FIN_ORDER if f in df_principal['financial_status_name'].unique()]
    
        matrix_data = df_principal.groupby(['financial_status_name', 'alert_type'])['user_id'].count().reset_index(name='count')
    
        z_matrix = []
        for estado in estados_vis:
            row_z = []
            for alerta in alertas_vis:
                val = matrix_data[
                    (matrix_data['financial_status_name'] == estado) &
                    (matrix_data['alert_type'] == alerta)
                ]['count'].sum()
                row_z.append(val)
            z_matrix.append(row_z)
    
        alert_rank_map = {a: i for i, a in enumerate(ALERT_ORDER)}
        risk_matrix, text_matrix2 = [], []
        for estado in estados_vis:
            row_r, row_t2 = [], []
            fr = FIN_RANK.get(estado, 0)
            for alerta in alertas_vis:
                ar = alert_rank_map.get(alerta, 0)
                val = z_matrix[estados_vis.index(estado)][alertas_vis.index(alerta)]
                riesgo = (fr + ar) if val > 0 else 0
                row_r.append(riesgo)
                row_t2.append(f"<b>{int(val)}</b>")
            risk_matrix.append(row_r)
            text_matrix2.append(row_t2)
    
        colorscale = [
            [0.0,  "#1E4D30"],
            [0.15, "#149852"],
            [0.4,  "#F5A623"],
            [0.65, "#FD531E"],
            [1.0,  "#7B0000"],
        ]
    
        estados_vis_inv = list(reversed(estados_vis))
        risk_matrix_inv, text_matrix2_inv = [], []
        for estado in estados_vis_inv:
            idx = estados_vis.index(estado)
            risk_matrix_inv.append(risk_matrix[idx])
            text_matrix2_inv.append(text_matrix2[idx])
    
        fig_hm = go.Figure(data=go.Heatmap(
            z=risk_matrix_inv,
            x=alertas_vis,
            y=estados_vis_inv,
            text=text_matrix2_inv,
            texttemplate="%{text}",
            textfont=dict(color="white", size=13, family="Barlow Condensed"),
            colorscale=colorscale,
            showscale=False,
            hovertemplate="<b>%{y}</b> + <b>%{x}</b><br>%{text} estudiantes<extra></extra>",
        ))
        fig_hm.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#C0C0C0", family="Barlow"),
            height=320, margin=dict(l=10, r=10, t=10, b=60),
            xaxis=dict(
                tickfont=dict(color="#C0C0C0", family="Barlow", size=10),
                linecolor="#3A3A3A", gridcolor="rgba(0,0,0,0)",
                tickangle=-20,
            ),
            yaxis=dict(
                tickfont=dict(color="#C0C0C0", family="Barlow", size=11),
                linecolor="#3A3A3A", gridcolor="rgba(0,0,0,0)",
            ),
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    
    # Tabla de doble riesgo
    st.markdown(
        "<div class='section-title' style='border-color:#C0392B'>🚨 Estudiantes en Doble Riesgo — Login Crítico + Mora Avanzada</div>",
        unsafe_allow_html=True
    )
    doble_df = df_principal[
        (df_principal['gravedad'] >= 3) &
        (df_principal['financial_status_name'].isin(['Mora avanzada', 'Baja por mora']))
    ][['user_incremental', 'user_full_name', 'gestor_asignado', 'alert_type', 'financial_status_name', 'gravedad', 'fin_rank']].copy()
    
    if len(doble_df) > 0:
        doble_df['riesgo_total'] = doble_df['gravedad'] + doble_df['fin_rank']
        st.dataframe(
            doble_df.sort_values('riesgo_total', ascending=False)
            .drop(columns=['gravedad', 'fin_rank', 'riesgo_total'])
            .reset_index(drop=True)
            .rename(columns={
                'user_incremental':       'ID',
                'user_full_name':         'Estudiante',
                'gestor_asignado':        'Gestor',
                'alert_type':             'Alerta Login',
                'financial_status_name':  'Estado Financiero',
            }),
            use_container_width=True, height=300
        )
        st.markdown(
            f"<p style='color:#C0392B; font-size:0.8rem; font-weight:700'>⚠️ {len(doble_df)} estudiantes con señales combinadas de deserción</p>",
            unsafe_allow_html=True
        )
    else:
        st.success("✅ No hay estudiantes en doble riesgo para esta fecha.")
    
    st.divider()
    
    # ============================================================
    # DESEMPEÑO DE GESTORES
    # ============================================================
    st.markdown("<div class='section-title' style='border-color:#9725B9'>👤 Desempeño de Gestores</div>", unsafe_allow_html=True)
    
    # Filtrar gestores válidos (no vacíos)
    gestores_validos = df_principal[df_principal['gestor_asignado'].notna() & (df_principal['gestor_asignado'] != '')]['gestor_asignado'].unique()
    
    if comparar and len(comparativa) > 0:
        # ---- MODO COMPARATIVO: Ranking + Scorecard ----
        # El resultado se atribuye al gestor de la fecha anterior (quien gestionó antes del cambio)
    
        # Gestores válidos de la fecha anterior
        gestores_responsables = comparativa[comparativa['gestor_responsable'].notna() & (comparativa['gestor_responsable'] != '')]['gestor_responsable'].unique()
        comp_con_gestor = comparativa[comparativa['gestor_responsable'].isin(gestores_responsables)]
        comp_sin_gestor = len(comparativa) - len(comp_con_gestor)
    
        if comp_sin_gestor > 0:
            st.markdown(
                f"<p style='color:#656A71; font-size:0.8rem; margin-bottom:1rem'>📌 {len(comp_con_gestor):,} de {len(comparativa):,} estudiantes tenían gestor en la fecha anterior. Los resultados se atribuyen al gestor que los gestionó.</p>",
                unsafe_allow_html=True
            )
    
        # Construir scorecard por gestor
        gestor_stats = []
        for gestor in gestores_responsables:
            comp_gestor = comparativa[comparativa['gestor_responsable'] == gestor]
            if len(comp_gestor) == 0:
                continue
            n_total = len(comp_gestor)
            n_mejor = len(comp_gestor[comp_gestor['cambio'] > 0])
            n_empeor = len(comp_gestor[comp_gestor['cambio'] < 0])
            n_estable = len(comp_gestor[comp_gestor['cambio'] == 0])
            pct_mejor = n_mejor / n_total * 100
            pct_empeor = n_empeor / n_total * 100
            pct_estable = n_estable / n_total * 100
            eficacia_neta = pct_mejor - pct_empeor  # Métrica clave
    
            gestor_stats.append({
                'Gestor': gestor,
                'Estudiantes': n_total,
                'Mejoraron': n_mejor,
                '% Mejoraron': round(pct_mejor, 1),
                'Empeoraron': n_empeor,
                '% Empeoraron': round(pct_empeor, 1),
                'Estables': n_estable,
                '% Estables': round(pct_estable, 1),
                'Eficacia Neta': round(eficacia_neta, 1),
            })
    
        if len(gestor_stats) > 0:
            gestor_df = pd.DataFrame(gestor_stats).sort_values('Eficacia Neta', ascending=False)
    
            # ---- RANKING VISUAL ----
            col_rank, col_score = st.columns([1, 1])
    
            with col_rank:
                st.markdown("<div class='section-title'>Ranking de Eficacia</div>", unsafe_allow_html=True)
                st.markdown(
                    "<p style='color:#656A71; font-size:0.78rem; margin-top:-0.8rem; margin-bottom:1rem'>Eficacia neta = % mejoraron − % empeoraron</p>",
                    unsafe_allow_html=True
                )
    
                fig_rank = go.Figure()
    
                # Colores según eficacia neta
                colors_rank = ['#149852' if v >= 0 else '#FD531E' for v in gestor_df['Eficacia Neta']]
    
                fig_rank.add_trace(go.Bar(
                    y=gestor_df['Gestor'],
                    x=gestor_df['Eficacia Neta'],
                    orientation='h',
                    marker=dict(color=colors_rank, line=dict(width=0)),
                    text=[f"{v:+.1f}%" for v in gestor_df['Eficacia Neta']],
                    textposition='outside',
                    textfont=dict(color='white', size=12, family='Barlow Condensed'),
                    hovertemplate="<b>%{y}</b><br>Eficacia neta: <b>%{x:.1f}%</b><extra></extra>",
                ))
    
                fig_rank.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C0C0C0", family="Barlow"),
                    height=max(300, len(gestor_df) * 45),
                    margin=dict(l=10, r=80, t=10, b=10),
                    yaxis=dict(
                        categoryorder='array',
                        categoryarray=list(reversed(gestor_df['Gestor'].tolist())),
                        tickfont=dict(color="#C0C0C0", family="Barlow", size=11),
                        linecolor="#3A3A3A", gridcolor="rgba(0,0,0,0)",
                    ),
                    xaxis=dict(
                        tickfont=dict(color="#C0C0C0", family="Barlow", size=10),
                        linecolor="#3A3A3A", gridcolor="#2E2E2E",
                        ticksuffix="%", zeroline=True, zerolinecolor="#656A71", zerolinewidth=1,
                    ),
                )
                st.plotly_chart(fig_rank, use_container_width=True)
    
            with col_score:
                st.markdown("<div class='section-title'>Scorecard por Gestor</div>", unsafe_allow_html=True)
                st.dataframe(
                    gestor_df[['Gestor', 'Estudiantes', 'Mejoraron', '% Mejoraron', 'Empeoraron', '% Empeoraron', 'Estables', 'Eficacia Neta']]
                    .reset_index(drop=True),
                    use_container_width=True,
                    height=max(300, len(gestor_df) * 45),
                )
    
            st.divider()
    
            # ---- DRILL-DOWN POR GESTOR ----
            st.markdown("<div class='section-title'>Detalle por Gestor</div>", unsafe_allow_html=True)
            gestor_sel = st.selectbox(
                "Selecciona un gestor para ver sus estudiantes:",
                gestor_df['Gestor'].tolist(),
                label_visibility="visible"
            )
    
            if gestor_sel:
                det = comparativa[comparativa['gestor_responsable'] == gestor_sel].copy()
                det['Estado'] = det['cambio'].apply(
                    lambda x: '✅ Mejoró' if x > 0 else ('⚠️ Empeoró' if x < 0 else '➖ Estable')
                )
                det = det.sort_values('cambio', ascending=True)
    
                # Métricas del gestor seleccionado
                g_data = gestor_df[gestor_df['Gestor'] == gestor_sel].iloc[0]
                gc1, gc2, gc3, gc4 = st.columns(4)
                gc1.metric("Estudiantes", int(g_data['Estudiantes']))
                gc2.metric("✅ Mejoraron", int(g_data['Mejoraron']), f"{g_data['% Mejoraron']}%")
                gc3.metric("⚠️ Empeoraron", int(g_data['Empeoraron']), f"-{g_data['% Empeoraron']}%", delta_color="inverse")
                gc4.metric("Eficacia Neta", f"{g_data['Eficacia Neta']:+.1f}%",
                           "positiva" if g_data['Eficacia Neta'] >= 0 else "negativa",
                           delta_color="normal" if g_data['Eficacia Neta'] >= 0 else "inverse")
    
                st.dataframe(
                    det[['user_incremental', 'user_full_name', 'gravedad_viejo', 'gravedad_nuevo', 'cambio', 'Estado']]
                    .reset_index(drop=True)
                    .rename(columns={
                        'user_incremental': 'ID',
                        'user_full_name':   'Estudiante',
                        'gravedad_viejo':   'Gravedad Anterior',
                        'gravedad_nuevo':   'Gravedad Actual',
                        'cambio':           'Cambio',
                    }),
                    use_container_width=True, height=400
                )
        else:
            st.info("No hay gestores con datos comparativos disponibles.")
    
    else:
        # ---- MODO FECHA ÚNICA: Distribución por gestor ----
        st.markdown(
            "<p style='color:#656A71; font-size:0.85rem; margin-bottom:1rem'>Selecciona una fecha de comparación para ver el ranking de eficacia y scorecard detallado.</p>",
            unsafe_allow_html=True
        )
    
        if len(gestores_validos) > 0:
            gestor_alert_data = df_principal[df_principal['gestor_asignado'].isin(gestores_validos)] \
                .groupby(['gestor_asignado', 'alert_type']).size().reset_index(name='count')
    
            tipos_gestor = [a for a in ALERT_ORDER if a in gestor_alert_data['alert_type'].unique()]
    
            orden_gestor = (
                df_principal[df_principal['gravedad'] >= 3]
                .groupby('gestor_asignado')['user_id'].count()
                .sort_values(ascending=True).index.tolist()
            )
            for g in gestores_validos:
                if g not in orden_gestor:
                    orden_gestor.insert(0, g)
    
            fig_gestor = go.Figure()
            for alert in tipos_gestor:
                subset = gestor_alert_data[gestor_alert_data['alert_type'] == alert]
                fig_gestor.add_trace(go.Bar(
                    name=alert,
                    y=subset['gestor_asignado'],
                    x=subset['count'],
                    orientation='h',
                    marker=dict(color=ALERT_COLORS.get(alert, "#FD531E"), line=dict(width=0)),
                    text=subset['count'],
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(color='white', size=12, family='Barlow'),
                    hovertemplate=f"<b>{alert}</b><br>%{{y}}<br><b>%{{x}}</b> estudiantes<extra></extra>",
                ))
    
            fig_gestor.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#C0C0C0", family="Barlow"),
                barmode='stack',
                height=max(350, len(gestores_validos) * 50),
                margin=dict(l=10, r=20, t=60, b=20),
                yaxis=dict(**AXIS, categoryorder='array', categoryarray=orden_gestor),
                xaxis=dict(**AXIS, title=dict(text="Número de estudiantes", font=dict(color="#656A71", size=12))),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#C0C0C0"), traceorder="normal"
                ),
            )
            st.plotly_chart(fig_gestor, use_container_width=True)
        else:
            st.info("No hay gestores asignados en los datos de esta fecha.")

with tab_reprob:
    render_reprobacion()
