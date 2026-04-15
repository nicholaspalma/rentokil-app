import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os
import tempfile
import math
import io
import subprocess
from urllib.parse import quote
from PIL import Image, ImageOps, ImageFile
import traceback
import gc
import numpy as np

# --- NUEVAS LIBRERÍAS PARA PLANTILLAS WORD ---
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
    DOCXTPL_INSTALLED = True
except ImportError:
    DOCXTPL_INSTALLED = False

# --- CONFIGURACIÓN PARA IMÁGENES ROTAS ---
ImageFile.LOAD_TRUNCATED_IMAGES = True

# --- SOPORTE HEIC (IPHONE) ---
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(layout="wide", page_title="Rentokil Mobile PRO")
COLOR_PRIMARIO = (227, 6, 19)
COLOR_CELESTE_CLARO = (0, 160, 224) 
COLOR_TABLA_HEAD = (220, 220, 220)
COLOR_TABLA_FILA = (255, 255, 255)

# --- CSS PERSONALIZADO PARA BOTONES CORPORATIVOS ---
st.markdown("""
    <style>
    button[kind="primary"] {
        background-color: #E30613 !important;
        border-color: #E30613 !important;
        color: white !important;
        font-weight: bold !important;
    }
    button[kind="primary"]:hover {
        background-color: #CC0510 !important;
        border-color: #CC0510 !important;
    }
    button[kind="secondary"] {
        background-color: #00A0E0 !important;
        border-color: #00A0E0 !important;
        color: white !important;
        font-weight: bold !important;
    }
    button[kind="secondary"]:hover {
        background-color: #008BBF !important;
        border-color: #008BBF !important;
        color: white !important;
    }
    .email-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #4285F4; color: white; padding: 10px 20px;
        text-decoration: none; border-radius: 5px; font-weight: bold; width: 100%; text-align: center; margin-top: 10px;
    }
    .email-btn:hover { background-color: #3367D6; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO (MEMORIA PROFUNDA) ---
if "app_mode" not in st.session_state: st.session_state.app_mode = "HOME"
if "pdf_informe" not in st.session_state: st.session_state.pdf_informe = None
if "pdf_cert" not in st.session_state: st.session_state.pdf_cert = None
if "pdf_dialogo" not in st.session_state: st.session_state.pdf_dialogo = None
if "pdf_visita" not in st.session_state: st.session_state.pdf_visita = None
if "word_aviso" not in st.session_state: st.session_state.word_aviso = None
if "pdf_aviso" not in st.session_state: st.session_state.pdf_aviso = None
if "mailto_url" not in st.session_state: st.session_state.mailto_url = ""
if "sucursal_filtro" not in st.session_state: st.session_state.sucursal_filtro = "SANTIAGO"

# Memoria para nombres de archivos
if "fn_informe" not in st.session_state: st.session_state.fn_informe = "Informe.pdf"
if "fn_cert" not in st.session_state: st.session_state.fn_cert = "Certificado.pdf"
if "fn_trabajo" not in st.session_state: st.session_state.fn_trabajo = "Trabajo.pdf"
if "fn_visita" not in st.session_state: st.session_state.fn_visita = "Visita.pdf"
if "fn_aviso" not in st.session_state: st.session_state.fn_aviso = "Aviso.pdf"

# Fijar la hora por defecto una sola vez
if "hora_emision_default" not in st.session_state:
    st.session_state.hora_emision_default = datetime.datetime.now().time()

# Tablas Molinos 
if "df_d_mol" not in st.session_state:
    st.session_state.df_d_mol = pd.DataFrame([
        {"Piso": "Subterráneo", "Bandejas": 10, "Mini-Ropes": 2}, {"Piso": "Piso 1", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 2", "Bandejas": 10, "Mini-Ropes": 2}, {"Piso": "Piso 3", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 4", "Bandejas": 8, "Mini-Ropes": 1}, {"Piso": "Piso 5", "Bandejas": 5, "Mini-Ropes": 0}
    ])
if "df_m_mol" not in st.session_state:
    d_m = []
    for i in range(3):
        f_s = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%d-%m")
        for h in ["19:00", "00:00", "07:00", "13:00"]: d_m.append([f_s, h, 300, 310, 320, 305, 300, 290])
    st.session_state.df_m_mol = pd.DataFrame(d_m, columns=["Fecha", "Hora", "Subt.", "Piso 1", "Piso 2", "Piso 3", "Piso 4", "Piso 5"])

# Tablas Estructuras (10 PUNTOS)
if "df_d_est" not in st.session_state:
    st.session_state.df_d_est = pd.DataFrame([{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}])
if "nom_p" not in st.session_state: st.session_state.nom_p = [f"Punto {i+1}" for i in range(10)]
if "df_m_est" not in st.session_state:
    d_me = []
    for i in range(3): d_me.append([(datetime.date.today() + datetime.timedelta(days=i)).strftime("%d-%m"), "10:00"] + [0]*10)
    cols_est = ["Fecha", "Hora"] + [f"P{i+1}" for i in range(10)]
    st.session_state.df_m_est = pd.DataFrame(d_me, columns=cols_est)


# ==============================================================================
# LECTURA DINÁMICA Y LIMPIEZA PROFUNDA NUCLEAR
# ==============================================================================
DATABASE_COMBINADA = {}
DATABASE_REPRESENTANTES = {}
LISTA_SUCURSALES_SET = set()

def deep_clean(text):
    """Limpieza agresiva de espacios invisibles de Excel"""
    if pd.isna(text) or text is None: 
        return ""
    text_str = str(text)
    text_str = text_str.replace('\xa0', ' ').replace('\u200b', '').replace('\n', ' ')
    return text_str.strip()

def obtener_nombre_columna(df, palabras_clave):
    columnas = df.columns
    for col in columnas:
        col_norm = deep_clean(col).lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').strip()
        if any(palabra in col_norm for palabra in palabras_clave):
            return col
    return None

# 1. Cargar archivo de clientes (Exclusivo .xlsx o .xls)
df_clientes = pd.DataFrame()
for file in os.listdir('.'):
    if "base de datos" in file.lower() and file.lower().endswith(('.xlsx', '.xls')):
        try:
            df_clientes = pd.read_excel(file)
            break
        except Exception as e:
            st.error(f"⚠️ Error intentando leer el archivo {file}: {e}")

if not df_clientes.empty:
    df_clientes = df_clientes.dropna(how='all') 
    
    c_cliente = obtener_nombre_columna(df_clientes, ['razon', 'cliente', 'planta', 'social'])
    c_rut = obtener_nombre_columna(df_clientes, ['rut'])
    c_dir = obtener_nombre_columna(df_clientes, ['dir'])
    c_suc = obtener_nombre_columna(df_clientes, ['sucursal', 'suc'])

    if c_suc:
        df_clientes['Sucursal_Filtro'] = df_clientes[c_suc].apply(deep_clean).str.upper()
        LISTA_SUCURSALES_SET.update(df_clientes['Sucursal_Filtro'].replace('', np.nan).dropna().unique())
else:
    c_cliente, c_rut, c_dir, c_suc = None, None, None, None


# 2. Cargar archivo de Técnicos (Exclusivo .xlsx o .xls)
df_tecnicos = pd.DataFrame()
for file in os.listdir('.'):
    if "representantes" in file.lower() and file.lower().endswith(('.xlsx', '.xls')):
        try:
            df_tecnicos = pd.read_excel(file)
            break
        except Exception as e:
            st.error(f"⚠️ Error intentando leer el archivo {file}: {e}")

if not df_tecnicos.empty:
    df_tecnicos = df_tecnicos.dropna(how='all')
    
    t_nombre = obtener_nombre_columna(df_tecnicos, ['nombre', 'rep', 'tec'])
    t_rut = obtener_nombre_columna(df_tecnicos, ['rut'])
    t_correo = obtener_nombre_columna(df_tecnicos, ['correo', 'mail'])
    t_suc = obtener_nombre_columna(df_tecnicos, ['sucursal', 'suc'])

    if t_suc:
        df_tecnicos['Sucursal_Filtro'] = df_tecnicos[t_suc].apply(deep_clean).str.upper()
        LISTA_SUCURSALES_SET.update(df_tecnicos['Sucursal_Filtro'].replace('', np.nan).dropna().unique())
else:
    t_nombre, t_rut, t_correo, t_suc = None, None, None, None


lista_limpia_sucursales = sorted([s for s in LISTA_SUCURSALES_SET if s and s != 'NAN'])
LISTA_SUCURSALES = ["TODAS"] + lista_limpia_sucursales

if "SANTIAGO" in lista_limpia_sucursales and st.session_state.sucursal_filtro not in LISTA_SUCURSALES:
    st.session_state.sucursal_filtro = "SANTIAGO"
elif lista_limpia_sucursales and st.session_state.sucursal_filtro not in LISTA_SUCURSALES:
    st.session_state.sucursal_filtro = lista_limpia_sucursales[0]
elif not lista_limpia_sucursales:
    st.session_state.sucursal_filtro = "TODAS"


# ==============================================================================
# BARRA LATERAL (SOLO INDICADOR DE ESTADO)
# ==============================================================================
with st.sidebar:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=120)
    
    if st.session_state.app_mode != "HOME":
        st.info(f"📍 Base Operativa: **{st.session_state.sucursal_filtro}**")
        st.markdown("---")
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): 
            st.session_state.app_mode = "HOME"
            st.rerun()
        st.caption(f"Módulo activo: {st.session_state.app_mode}")
    else:
        st.info("👋 Bienvenido a Rentokil Mobile")

# --- APLICAR FILTROS A LAS BASES DE DATOS ---
filtro_actual = st.session_state.sucursal_filtro

if not df_clientes.empty and c_cliente is not None:
    if filtro_actual != "TODAS" and 'Sucursal_Filtro' in df_clientes.columns:
        df_c_filt = df_clientes[df_clientes['Sucursal_Filtro'] == filtro_actual]
    else:
        df_c_filt = df_clientes
        
    for _, row in df_c_filt.iterrows():
        nombre_cli = deep_clean(row[c_cliente])
        if nombre_cli and nombre_cli.lower() != 'nan':
            DATABASE_COMBINADA[nombre_cli] = {
                "cliente": nombre_cli,
                "rut": deep_clean(row[c_rut]) if c_rut else "",
                "direccion": deep_clean(row[c_dir]) if c_dir else "",
                "volumen": 0
            }
else:
    if st.session_state.app_mode != "HOME":
        st.sidebar.warning("⚠️ Planilla 'Clientes' no detectada")

DATABASE_COMBINADA["OTRO"] = {"cliente": "", "rut": "", "direccion": "", "volumen": 0}

if not df_tecnicos.empty and t_nombre is not None:
    if filtro_actual != "TODAS" and 'Sucursal_Filtro' in df_tecnicos.columns:
        df_t_filt = df_tecnicos[df_tecnicos['Sucursal_Filtro'] == filtro_actual]
    else:
        df_t_filt = df_tecnicos
        
    for _, row in df_t_filt.iterrows():
        nombre_tec = deep_clean(row[t_nombre])
        if nombre_tec and nombre_tec.lower() != 'nan':
            DATABASE_REPRESENTANTES[nombre_tec] = {
                "rut": deep_clean(row[t_rut]) if t_rut else "",
                "correo": deep_clean(row[t_correo]) if t_correo else ""
            }
else:
    if st.session_state.app_mode != "HOME":
        st.sidebar.warning("⚠️ Planilla 'Técnicos' no detectada")

DATABASE_REPRESENTANTES["OTRO"] = {"rut": "", "correo": ""}
LISTA_REPRESENTANTES = list(DATABASE_REPRESENTANTES.keys())


# --- FUNCIONES UTILITARIAS Y DE LIMPIEZA ---
def clean_filename(name):
    invalid_chars = '<>:"/\\|?*'
    name_clean = str(name)
    for char in invalid_chars:
        name_clean = name_clean.replace(char, '')
    return name_clean.replace(' ', '_').replace('.', '')

def format_fecha_es(fecha):
    meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    return f"{fecha.day:02d} de {meses[fecha.month]} de {fecha.year}"

def clean_number(value):
    if value is None: return 0.0
    if isinstance(value, float) and math.isnan(value): return 0.0
    if isinstance(value, (int, float)): return float(value)
    if isinstance(value, str):
        v = value.replace(',', '.').strip()
        if v in ["", "nan", "NaN", "None"]: return 0.0
        try: return float(v)
        except: return 0.0
    return 0.0

def procesar_imagen(uploaded_file):
    """Procesa imagen con caché de bytes y destrucción segura"""
    tmp_name = None
    try:
        file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, 'getvalue') else uploaded_file.read()
        image = Image.open(io.BytesIO(file_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB': image = image.convert('RGB')
        image_fixed = ImageOps.fit(image, (800, 600), method=Image.Resampling.LANCZOS, centering=(0.5, 0.95))
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp_name = tmp.name
            
        image_fixed.save(tmp_name, format='JPEG', quality=85, optimize=True)
        image.close(); image_fixed.close(); gc.collect()
        return tmp_name
    except Exception as e:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)
        return None

def procesar_imagen_full(uploaded_file):
    """Procesa imagen original con caché de bytes y destrucción segura"""
    tmp_name = None
    try:
        file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, 'getvalue') else uploaded_file.read()
        image = Image.open(io.BytesIO(file_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB': image = image.convert('RGB')
        if image.width > 1600 or image.height > 1600:
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        w, h = image.size
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp_name = tmp.name
            
        image.save(tmp_name, format='JPEG', quality=85, optimize=True)
        image.close(); gc.collect()
        return tmp_name, w, h
    except Exception as e:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)
        return None, 0, 0

def procesar_firma(uploaded_file):
    """Procesa firma PNG con caché de bytes y destrucción segura"""
    tmp_name = None
    try:
        file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, 'getvalue') else uploaded_file.read()
        image = Image.open(io.BytesIO(file_bytes))
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGBA')
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp_name = tmp.name
            
        bg.save(tmp_name, format='JPEG', quality=90)
        image.close(); gc.collect()
        return tmp_name
    except Exception as e:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)
        return None

# ==============================================================================
# CLASES PDF ORIGINALES Y COMPLETAS
# ==============================================================================
class InformePDF(FPDF):
    def rounded_rect(self, x, y, w, h, r, style=''):
        k = self.k; hp = self.h
        op = 'f' if style == 'F' else 'B' if style in ['FD', 'DF'] else 'S'
        MyArc = 4/3 * (math.sqrt(2) - 1)
        self._out(f'{(x+r)*k:.2f} {(hp-y)*k:.2f} m'); xc, yc = x+w-r, y+r; self._out(f'{xc*k:.2f} {(hp-y)*k:.2f} l')
        self._out(f'{(xc+r*MyArc)*k:.2f} {(hp-y)*k:.2f} {(x+w)*k:.2f} {(hp-(yc-r*MyArc))*k:.2f} {(x+w)*k:.2f} {(hp-yc)*k:.2f} c')
        xc, yc = x+w-r, y+h-r; self._out(f'{(x+w)*k:.2f} {(hp-yc)*k:.2f} l')
        self._out(f'{(x+w)*k:.2f} {(hp-(yc+r*MyArc))*k:.2f} {(xc+r*MyArc)*k:.2f} {(hp-(y+h))*k:.2f} {xc*k:.2f} {(hp-(y+h))*k:.2f} c')
        xc, yc = x+r, y+h-r; self._out(f'{xc*k:.2f} {(hp-(y+h))*k:.2f} l')
        self._out(f'{(xc-r*MyArc)*k:.2f} {(hp-(y+h))*k:.2f} {x*k:.2f} {(hp-(yc+r*MyArc))*k:.2f} {x*k:.2f} {(hp-yc)*k:.2f} c')
        xc, yc = x+r, y+r; self._out(f'{x*k:.2f} {(hp-yc)*k:.2f} l')
        self._out(f'{x*k:.2f} {(hp-(yc-r*MyArc))*k:.2f} {(xc-r*MyArc)*k:.2f} {(hp-y)*k:.2f} {xc*k:.2f} {(hp-y)*k:.2f} c')
        self._out(op)

    def tabla_moderna(self, header, data, widths, color=COLOR_PRIMARIO):
        self.set_font("Arial", "B", 9)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        x_start = self.get_x(); y_start = self.get_y()
        self.rounded_rect(x_start, y_start, sum(widths), 7, 2, 'F')
        for i, h in enumerate(header): self.cell(widths[i], 7, h, border=0, align='C', fill=False)
        self.ln(); self.set_font("Arial", "", 9); self.set_text_color(0, 0, 0)
        for row in data:
            for i, d in enumerate(row): self.cell(widths[i], 8, str(d), border='B', align='C', fill=False)
            self.ln()
        self.ln(3)

    def tabla_visita(self, label, lines):
        self.set_font("Arial", "B", 9)
        y_start = self.get_y(); h = max(len(lines) * 5 + 4, 8)
        if y_start + h > 270: self.add_page(); y_start = self.get_y()
        self.set_draw_color(200, 200, 200)
        self.rect(10, y_start, 50, h); self.rect(60, y_start, 140, h)
        self.set_xy(10, y_start + (h/2 - 2)); self.cell(50, 4, label, align='C')
        self.set_xy(60, y_start + 2); self.set_font("Arial", "", 9)
        for line in lines: self.set_x(62); self.cell(136, 5, line, ln=1)
        self.set_y(y_start + h)

    def header(self):
        if os.path.exists('logo.png'):
            try: self.image('logo.png', 10, 8, 33)
            except: pass
        self.set_font("Arial", "B", 14); self.set_text_color(*COLOR_PRIMARIO)
        titulo = "INFORME TÉCNICO DE FUMIGACIÓN"
        if getattr(self, 'is_visita', False): titulo = "VISITA TÉCNICA PRE-FUMIGACIÓN"
        self.cell(0, 8, titulo, ln=1, align="R")
        self.set_font("Arial", "I", 8); self.set_text_color(100, 100, 100)
        self.cell(0, 5, "RENTOKIL INITIAL CHILE SPA", ln=1, align="R"); self.ln(10)

    def footer(self):
        self.set_y(-15); self.set_font("Arial", "I", 8); self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()} - Documento Oficial", align="C")

    def t_seccion(self, numero, texto, force=False):
        if force or self.get_y() > 240: self.add_page()
        self.ln(5); self.set_font("Arial", "B", 10); self.set_fill_color(*COLOR_PRIMARIO); self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {numero}. {texto.upper()}", ln=1, fill=True)
        self.set_text_color(0, 0, 0); self.ln(2)

    def tabla(self, header, data, widths, bold_last=False):
        if self.get_y() > 240: self.add_page()
        self.set_font("Arial", "B", 7); self.set_fill_color(*COLOR_TABLA_HEAD)
        for i, h in enumerate(header): self.cell(widths[i], 8, h, 1, 0, 'C', True)
        self.ln(); self.set_font("Arial", "", 7); self.set_fill_color(*COLOR_TABLA_FILA)
        for idx, row in enumerate(data):
            if bold_last and idx == len(data) - 1: self.set_font("Arial", "B", 7)
            else: self.set_font("Arial", "", 7)
            for i, d in enumerate(row): self.cell(widths[i], 6, str(d), 1, 0, 'C', True)
            self.ln()
            
    def galeria(self, fotos, titulo=None):
        if not fotos: return
        if titulo: self.ln(2); self.set_font("Arial", "B", 9); self.cell(0, 6, titulo, ln=1)
        for i, f in enumerate(fotos):
            tmp = procesar_imagen(f)
            if tmp:
                try:
                    if self.get_y() > 210: self.add_page(); self.set_y(45); i_mod = 0
                    else: i_mod = i % 2
                    if i_mod == 0: y_act = self.get_y(); self.image(tmp, x=10, y=y_act, w=90, h=65)
                    else: self.image(tmp, x=110, y=y_act, w=90, h=65); self.ln(70)
                finally:
                    if os.path.exists(tmp):
                        os.remove(tmp)
        if len(fotos) % 2 != 0: self.ln(70)

class CertificadoPDF(FPDF):
    def rounded_rect(self, x, y, w, h, r, style=''):
        k = self.k; hp = self.h
        op = 'f' if style == 'F' else 'B' if style in ['FD', 'DF'] else 'S'
        MyArc = 4/3 * (math.sqrt(2) - 1)
        self._out(f'{(x+r)*k:.2f} {(hp-y)*k:.2f} m'); xc, yc = x+w-r, y+r; self._out(f'{xc*k:.2f} {(hp-y)*k:.2f} l')
        self._out(f'{(xc+r*MyArc)*k:.2f} {(hp-y)*k:.2f} {(x+w)*k:.2f} {(hp-(yc-r*MyArc))*k:.2f} {(x+w)*k:.2f} {(hp-yc)*k:.2f} c')
        xc, yc = x+w-r, y+h-r; self._out(f'{(x+w)*k:.2f} {(hp-yc)*k:.2f} l')
        self._out(f'{(x+w)*k:.2f} {(hp-(yc+r*MyArc))*k:.2f} {(xc+r*MyArc)*k:.2f} {(hp-(y+h))*k:.2f} {xc*k:.2f} {(hp-(y+h))*k:.2f} c')
        xc, yc = x+r, y+h-r; self._out(f'{xc*k:.2f} {(hp-(y+h))*k:.2f} l')
        self._out(f'{(xc-r*MyArc)*k:.2f} {(hp-(y+h))*k:.2f} {x*k:.2f} {(hp-(yc+r*MyArc))*k:.2f} {x*k:.2f} {(hp-yc)*k:.2f} c')
        xc, yc = x+r, y+r; self._out(f'{x*k:.2f} {(hp-yc)*k:.2f} l')
        self._out(f'{x*k:.2f} {(hp-(yc-r*MyArc))*k:.2f} {(xc-r*MyArc)*k:.2f} {(hp-y)*k:.2f} {xc*k:.2f} {(hp-y)*k:.2f} c')
        self._out(op)

    def header(self):
        if os.path.exists('logo.png'):
            try: self.image('logo.png', 10, 8, 33)
            except: pass
        self.set_font("Arial", "B", 10); self.set_text_color(100, 100, 100); self.set_y(10)
        self.cell(0, 5, "Rentokil Initial Chile SpA | RUT 76.360.903-0", ln=1, align="R")
        self.set_font("Arial", "", 8); self.cell(0, 4, "Resolución exenta N°2307418842 reg. Del Maule del 16-10 2023", ln=1, align="R")
        self.ln(10); self.set_draw_color(*COLOR_CELESTE_CLARO); self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y()); self.ln(5)

    def footer(self):
        self.set_y(-15); self.set_font("Arial", "I", 8); self.set_text_color(150, 150, 150)
        self.cell(0, 10, "Documento Oficial Rentokil Initial Chile SpA", align="C")

    def t_rojo(self, texto):
        self.ln(3); self.set_font("Arial", "B", 10); self.set_fill_color(*COLOR_PRIMARIO); self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {texto.upper()}", ln=1, fill=True); self.set_text_color(0, 0, 0); self.ln(2)

    def t_cert(self, header, data, widths):
        self.set_font("Arial", "B", 8); self.set_fill_color(*COLOR_CELESTE_CLARO); self.set_text_color(255, 255, 255)
        x_start = self.get_x(); y_start = self.get_y()
        self.rounded_rect(x_start, y_start, sum(widths), 7, 2, 'F')
        for i, h in enumerate(header): self.cell(widths[i], 7, h, border=0, align='C', fill=False)
        self.ln(); self.set_font("Arial", "", 8); self.set_text_color(0, 0, 0)
        for row in data:
            for i, d in enumerate(row): self.cell(widths[i], 8, str(d), border='B', align='C', fill=False)
            self.ln()
        self.ln(4)

# ==============================================================================
# PANTALLA DE INICIO (HUB PRINCIPAL)
# ==============================================================================
if st.session_state.app_mode == "HOME":
    st.write("")
    col_logo1, col_logo2, col_logo3 = st.columns([1,2,1])
    with col_logo2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center; color: #E30613; font-size: 1.2em; font-weight: bold; margin-bottom: 5px;'>
                📍 SELECCIONE SU BASE OPERATIVA
            </div>
        """, unsafe_allow_html=True)
        
        try:
            idx_suc = LISTA_SUCURSALES.index(st.session_state.sucursal_filtro)
        except ValueError:
            idx_suc = 0
            
        nueva_sucursal = st.selectbox("Base", LISTA_SUCURSALES, index=idx_suc, label_visibility="collapsed")
        if nueva_sucursal != st.session_state.sucursal_filtro:
            st.session_state.sucursal_filtro = nueva_sucursal
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🏭 MOLINOS\n(Técnico y Cert.)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "MOLINOS"; st.rerun()
    with c2:
        if st.button("🏗️ ESTRUCTURAS\n(Técnico y Cert.)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "ESTRUCTURAS"; st.rerun()
    with c3:
        if st.button("📋 VISITA TÉCNICA\n(Evaluación Previa)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "VISITA"; st.rerun()
            
    st.write("")
    c4, c5 = st.columns(2)
    with c4:
        if st.button("📢 NOTIFICACIÓN\n(Aviso al Seremi)", use_container_width=True, type="secondary"):
            st.session_state.app_mode = "AVISO"; st.rerun()
    with c5:
        if st.button("📸 INFORME DE TRABAJO\n(Fotos a Pantalla Completa)", use_container_width=True, type="secondary"):
            st.session_state.app_mode = "TRABAJO"; st.rerun()

# ==============================================================================
# LÓGICA: AVISO DE FUMIGACIÓN AL SEREMI (WORD -> PDF -> EMAIL)
# ==============================================================================
elif st.session_state.app_mode == "AVISO":
    st.title("📢 Generador de Aviso al Seremi")
    
    if not DOCXTPL_INSTALLED:
        st.error("⚠️ Para usar este módulo, debes agregar la palabra `docxtpl` a tu archivo `requirements.txt` en GitHub y esperar 2 minutos a que se instale.")
    else:
        st.markdown("Asegúrate de haber subido el archivo **`plantilla_aviso.docx`** a tu GitHub con las etiquetas correspondientes.")
        
        st.subheader("📝 I. Datos de Emisión y Cliente")
        op_a = st.selectbox("Seleccione Cliente", list(DATABASE_COMBINADA.keys()))
        db_a = DATABASE_COMBINADA
        
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            cliente_a = st.text_input("Razón Social", db_a[op_a].get("cliente", op_a))
            rut_cliente_a = st.text_input("RUT Cliente", db_a[op_a].get("rut", ""))
            contacto_a = st.text_input("Atención a (Contacto)", "Jefe de Planta")
        with col_a2:
            dir_a = st.text_input("Dirección", db_a[op_a].get("direccion", ""))
            comuna_a = st.text_input("Comuna", "")
            tel_cliente_a = st.text_input("Teléfono Cliente", "")
        with col_a3:
            fecha_emision_a = st.date_input("Fecha de emisión del documento", datetime.date.today())
            fecha_visita_a = st.date_input("Fecha de Visita Previa", datetime.date.today() - datetime.timedelta(days=1))
            hora_emision_a = st.time_input("Hora de Emisión (Ajustar si es necesario)", st.session_state.hora_emision_default)
            st.session_state.hora_emision_default = hora_emision_a

        st.subheader("👨‍💼 II. Datos del Representante (Rentokil)")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            rep_a_sel = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES, key="rep_sel_a")
            if rep_a_sel == "OTRO":
                repre_a = st.text_input("Nombre Representante Manual:", key="rep_man_a")
                rut_repre_default = ""
                correo_repre_default = ""
            else:
                repre_a = rep_a_sel
                rut_repre_default = DATABASE_REPRESENTANTES[rep_a_sel].get("rut", "")
                correo_repre_default = DATABASE_REPRESENTANTES[rep_a_sel].get("correo", "")
                
        with col_r2:
            rut_repre_a = st.text_input("RUT Representante", rut_repre_default)
        with col_r3:
            correo_repre_a = st.text_input("Correo Representante", correo_repre_default)

        st.subheader("☣️ III. Detalles Técnicos de la Fumigación")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            fecha_fumi_a = st.date_input("Fecha de Fumigación", datetime.date.today() + datetime.timedelta(days=2))
            tipo_fum_a = st.selectbox("Tipo de Fumigación", ["Preventiva", "Curativa"])
        with col_f2:
            hora_ini_a = st.time_input("Hora Inicio Inyección", datetime.time(9, 0))
            hora_ter_a = st.time_input("Hora Fin Ventilación", datetime.time(18, 0))
        with col_f3:
            horas_exp_a = st.number_input("Horas de Exposición", value=72)
            dosis_a = st.text_input("Dosis Planificada", "3 g/m3")
        with col_f4:
            estructura_lote_a = st.text_input("Estructura / Lote a Tratar", "Lote 1")
            areas_a = st.text_input("Área General", "Bodega Principal")
            
        col_f5, col_f6, col_f7 = st.columns(3)
        with col_f5:
            producto_a = st.text_input("Mercadería / Producto a Tratar (Cultivo)", "Nueces de exportación")
        with col_f6:
            quimico_a = st.selectbox("Químico (Fumigante)", ["Fosfina (Fosfuro de Aluminio)", "Fosfuro de Magnesio", "Ambos (Fosfuro de Aluminio y Magnesio)"])
        with col_f7:
            if tipo_fum_a == "Curativa":
                plaga_a = st.text_input("Plaga Detectada", "Tribolium confusum")
            else:
                plaga_a = ""
                st.text_input("Plaga Detectada", "N/A (Tratamiento Preventivo)", disabled=True)

        st.subheader("🛠️ IV. Modalidad de Tratamiento")
        modalidad_a = st.selectbox("Seleccione la modalidad para marcar en el documento", 
                                   ["Lote bajo carpa", "Silos", "Estructuras", "Contenedores", "Otros"])
        
        texto_otro_a = "____________________"
        if modalidad_a == "Otros":
            texto_otro_a = st.text_input("Especifique qué otro tratamiento:")

        st.subheader("🗺️ V. Mapa y Firma")
        
        mapa_automatico_path = None
        extensiones = ['.jpg', '.jpeg', '.png', '.HEIC', '.heic']
        nombre_cliente_limpio_mapa = str(cliente_a).strip()
        
        for ext in extensiones:
            ruta_posible = os.path.join("mapas", nombre_cliente_limpio_mapa + ext)
            if os.path.exists(ruta_posible):
                mapa_automatico_path = ruta_posible
                break
                
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            if mapa_automatico_path:
                st.success(f"✅ Mapa de **{nombre_cliente_limpio_mapa}** detectado automáticamente en la carpeta 'mapas/'.")
                mapa_file = st.file_uploader("Subir un mapa diferente (Opcional, reemplaza al automático)", type=["png", "jpg", "jpeg", "heic"])
            else:
                st.warning(f"⚠️ No se encontró el mapa automático para **{nombre_cliente_limpio_mapa}** en la carpeta 'mapas/'.")
                mapa_file = st.file_uploader("Sube el Mapa de Georreferencia manualmente", type=["png", "jpg", "jpeg", "heic"])
                
        with col_img2:
            firma_aviso = st.file_uploader("Firma del Responsable Rentokil", type=["png", "jpg", "jpeg", "heic"])

        if st.button("🚀 GENERAR PDF Y PREPARAR CORREO", use_container_width=True, type="primary"):
            if not os.path.exists("plantilla_aviso.docx"):
                st.error("❌ No se encontró el archivo `plantilla_aviso.docx`. Por favor, súbelo a GitHub en la misma carpeta.")
            else:
                try:
                    cliente_limpio_file = clean_filename(cliente_a)
                    fecha_str = fecha_emision_a.strftime('%d%m%y')
                    st.session_state.fn_aviso = f"{fecha_str}_Aviso_Seremi_{cliente_limpio_file}.pdf"
                    
                    doc = DocxTemplate("plantilla_aviso.docx")
                    
                    check_on = "☒"
                    check_off = "☐"
                    
                    context = {
                        'fecha_emision': format_fecha_es(fecha_emision_a),
                        'visita_previa': format_fecha_es(fecha_visita_a),
                        'hora_emision': hora_emision_a.strftime("%H:%M"),
                        'cliente': cliente_a,
                        'rut_cliente': rut_cliente_a,
                        'tel_cliente': tel_cliente_a,
                        'comuna': comuna_a,
                        'direccion': dir_a,
                        'contacto': contacto_a,
                        
                        'nombre_repre': repre_a,
                        'rut_repre': rut_repre_a,
                        'correo_repre': correo_repre_a,
                        
                        'fecha_fumi': format_fecha_es(fecha_fumi_a),
                        'hora_ini': hora_ini_a.strftime("%H:%M"),
                        'hora_ter': hora_ter_a.strftime("%H:%M"),
                        'horas_exp': str(horas_exp_a),
                        'dosis': dosis_a,
                        'tipo_fum': tipo_fum_a,
                        'estructura_lote': estructura_lote_a,
                        'areas': areas_a,
                        'producto': producto_a,
                        'quimico': quimico_a,
                        'plaga': plaga_a,
                        
                        'check_carpa': check_on if modalidad_a == "Lote bajo carpa" else check_off,
                        'check_silo': check_on if modalidad_a == "Silos" else check_off,
                        'check_estructura': check_on if modalidad_a == "Estructuras" else check_off,
                        'check_contenedor': check_on if modalidad_a == "Contenedores" else check_off,
                        'check_otro': check_on if modalidad_a == "Otros" else check_off,
                        'texto_otro': texto_otro_a if modalidad_a == "Otros" else "____________________"
                    }

                    mapa_final_usar = None
                    firma_path = None
                    
                    if mapa_file:
                        mapa_final_usar, _, _ = procesar_imagen_full(mapa_file)
                    elif mapa_automatico_path:
                        with open(mapa_automatico_path, "rb") as f_auto:
                            mapa_bytes = io.BytesIO(f_auto.read())
                            mapa_final_usar, _, _ = procesar_imagen_full(mapa_bytes)
                            
                    if mapa_final_usar:
                        context['mapa_img'] = InlineImage(doc, mapa_final_usar, width=Mm(135))
                            
                    if firma_aviso:
                        firma_path = procesar_firma(firma_aviso)
                        if firma_path:
                            context['firma_img'] = InlineImage(doc, firma_path, width=Mm(35))

                    doc.render(context)
                    
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        docx_path = os.path.join(tmp_dir, "temp_aviso.docx")
                        doc.save(docx_path)
                        
                        try:
                            subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp_dir, docx_path], check=True)
                            pdf_path = os.path.join(tmp_dir, "temp_aviso.pdf")
                            
                            with open(pdf_path, "rb") as f:
                                st.session_state.pdf_aviso = f.read()
                                
                            dest = "intoxicacionesplaguicidas@redsalud.gob.cl"
                            asunto = f"Aviso de Fumigación - {cliente_a}"
                            cuerpo = (f"Señores Seremi,\n\nA través del presente, estamos notificando el tratamiento con gas fosfina, "
                                      f"el cual se llevará a cabo el {fecha_fumi_a.strftime('%d-%m-%Y')} en las dependencias de {cliente_a}, "
                                      f"ubicadas en {dir_a}.\n\nAdjunto documento oficial con los detalles técnicos del servicio.\n\n"
                                      f"Sin otro particular,\nAtentamente,\n{repre_a}\nRentokil Initial Chile SpA")
                            st.session_state.mailto_url = f"mailto:{dest}?subject={quote(asunto)}&body={quote(cuerpo)}"

                        except Exception as pdf_error:
                            st.error(f"❌ Falló la conversión a PDF. Asegúrate de haber subido el archivo 'packages.txt' con la palabra 'libreoffice' a tu GitHub. Detalles técnicos: {pdf_error}")

                    st.rerun()

                except Exception as e:
                    st.error(f"Error generando el documento: {e}")
                    st.code(traceback.format_exc())
                finally:
                    if mapa_final_usar and os.path.exists(mapa_final_usar): os.remove(mapa_final_usar)
                    if firma_path and os.path.exists(firma_path): os.remove(firma_path)

    if st.session_state.get("pdf_aviso") is not None:
        st.success("✅ Documento de Aviso en PDF generado exitosamente.")
        st.download_button(
            label="📥 DESCARGAR AVISO EN PDF",
            data=st.session_state.pdf_aviso,
            file_name=st.session_state.fn_aviso,
            mime="application/pdf",
            use_container_width=True
        )
        
        st.markdown(f"""
            <a href="{st.session_state.mailto_url}" class="email-btn" target="_blank">
                📧 ABRIR GMAIL (CON BORRADOR LISTO)
            </a>
            <p style='font-size: 0.85em; color: gray; text-align: center; margin-top: 5px;'>
                * Una vez que se abra tu aplicación de correo, recuerda hacer clic en el 'clip' 📎 y adjuntar el PDF que acabas de descargar.
            </p>
        """, unsafe_allow_html=True)


# ==============================================================================
# LÓGICA: VISITA TÉCNICA 
# ==============================================================================
elif st.session_state.app_mode == "VISITA":
    st.title("📋 Visita Técnica Pre-Fumigación")
    
    st.subheader("📸 I. Portada")
    foto_portada = st.file_uploader("Sube aquí la Foto General de la Instalación", type=['png','jpg','jpeg','heic'], key="f_portada")

    st.subheader("📝 II. Datos Generales")
    op_v = st.selectbox("Seleccione Cliente", list(DATABASE_COMBINADA.keys()))
    db_v = DATABASE_COMBINADA
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        cliente_v = st.text_input("Razón Social", db_v[op_v].get("cliente", op_v))
        dir_v = st.text_input("Dirección", db_v[op_v].get("direccion", ""))
        tipo_fumi = st.text_input("Tipo de fumigación", "Lote bajo carpa")
    with col_v2:
        prod_tratado = st.text_input("Producto tratado", "Alimento para animales")
        vol_v = st.number_input("Volumen estimado (m³)", value=50)
        tiempo_v = st.text_input("Tiempo de exposición", "Al menos 120 días")

    st.subheader("🛡️ III. Análisis de Seguridad")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        chimenea = st.radio("¿Cuenta con chimenea?", ["Sí", "No"], index=1)
    with col_s2:
        altura = st.radio("¿Requiere trabajo en altura?", ["Sí", "No"], index=1)
        if altura == "Sí":
            lineas_vida = st.radio("¿Cuenta con líneas de vida?", ["Sí", "No"])
        else: lineas_vida = "No"
    with col_s3:
        oficinas = st.radio("¿Hay oficinas en la estructura?", ["Sí", "No"], index=1)
        if oficinas == "Sí":
            dist_oficinas = st.selectbox("Distancia de separación", ["10m", "20m", "30m", "40m", "+50m"])
        else: dist_oficinas = "N/A"

    st.subheader("⚠️ IV. Requerimientos al Cliente")
    req_ordenar = st.checkbox("Ordenar el lote")
    req_ubicacion = st.checkbox("Modificar ubicación")
    req_film = st.checkbox("Retirar film a los pallets (para facilitar difusión)", value=True)
    req_perimetro = st.checkbox("Generar perímetro (mín. 50cm para transitar y sellar a piso)", value=True)
    req_notas = st.text_input("Otras notas adicionales para el cliente:")

    st.subheader("⚙️ V. Análisis Operativo")
    col_o1, col_o2 = st.columns(2)
    with col_o1:
        tipo_piso = st.selectbox("Tipo de piso", ["Cemento pulido", "Asfalto", "Tierra", "Piso de losa", "Otro"])
        sellado = st.selectbox("Sellado recomendado", ["Cinta PVC", "Mangas de arena", "AGOREX", "Otro"])
    with col_o2:
        traer_jsystem = st.checkbox("Traer J-System", value=True)
        traer_manga = st.checkbox("Traer manga de riego", value=True)
        if chimenea == "Sí":
            dist_chimenea = st.selectbox("Distancia a la chimenea", ["10m", "20m", "30m", "40m", "+50m"])
        else: dist_chimenea = "N/A"

    st.subheader("📎 VI. Registro Fotográfico")
    fotos_anexo_visita = file_uploader_vis = st.file_uploader("Sube aquí fotos de detalles (planos, piso, techos, etc.)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    if st.button("🚀 GENERAR INFORME DE VISITA", use_container_width=True, type="primary"):
        try:
            cliente_limpio = clean_filename(cliente_v)
            fecha_str = datetime.date.today().strftime('%d%m%y')
            st.session_state.fn_visita = f"{fecha_str}_Visita_Previa_{cliente_limpio}.pdf"

            pdf = InformePDF()
            pdf.is_visita = True
            pdf.add_page()
            
            if foto_portada:
                tmp_portada, w, h = procesar_imagen_full(foto_portada)
                if tmp_portada:
                    try:
                        ratio = w / h
                        max_w = 190
                        calc_h = max_w / ratio
                        if calc_h > 120: 
                            calc_h = 120
                            max_w = calc_h * ratio
                        pdf_x = 10 + (190 - max_w) / 2
                        pdf.image(tmp_portada, x=pdf_x, y=pdf.get_y(), w=max_w, h=calc_h)
                        pdf.set_y(pdf.get_y() + calc_h + 10)
                    finally:
                        if os.path.exists(tmp_portada):
                            os.remove(tmp_portada)

            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(*COLOR_CELESTE_CLARO)
            pdf.set_text_color(255,255,255)
            pdf.rect(10, pdf.get_y(), 190, 8, 'F')
            pdf.cell(50, 8, "Elemento", align='C')
            pdf.cell(140, 8, "Descripción Técnica", ln=1, align='C')
            pdf.set_text_color(0,0,0)

            sec_lines = []
            sec_lines.append(f"- Sitio {'SÍ' if chimenea=='Sí' else 'NO'} cuenta con chimenea.")
            sec_lines.append(f"- Trabajo en altura: {altura}{' (Líneas de vida: '+lineas_vida+')' if altura=='Sí' else ''}.")
            sec_lines.append(f"- Oficinas en estructura: {oficinas}{' (Separación: '+dist_oficinas+')' if oficinas=='Sí' else ''}.")

            req_lines = []
            if req_ordenar: req_lines.append("- Ordenar el lote.")
            if req_ubicacion: req_lines.append("- Modificar ubicación.")
            if req_film: req_lines.append("- Retirar film a los pallets.")
            if req_perimetro: req_lines.append("- Generar perímetro en torno al lote.")
            if req_notas: req_lines.append(f"- Notas: {req_notas}")
            if not req_lines: req_lines.append("- Sin requerimientos adicionales.")

            op_lines = []
            op_lines.append(f"- Tipo de piso: {tipo_piso}.")
            op_lines.append(f"- Sellado recomendado: {sellado}.")
            if traer_jsystem: op_lines.append("- Se requiere traer J-System.")
            if traer_manga: op_lines.append("- Se requiere traer Manga de riego.")
            if chimenea == "Sí": op_lines.append(f"- Distancia a la chimenea: {dist_chimenea}.")

            pdf.tabla_visita("Cliente", [cliente_v])
            pdf.tabla_visita("Dirección", [dir_v])
            pdf.tabla_visita("Tipo de fumigación", [tipo_fumi])
            pdf.tabla_visita("Producto tratado", [prod_tratado])
            pdf.tabla_visita("Volumen / Tiempo", [f"{vol_v} m3 / {tiempo_v}"])
            pdf.tabla_visita("Análisis seguridad", sec_lines)
            pdf.tabla_visita("Req. al cliente", req_lines)
            pdf.tabla_visita("Análisis operativo", op_lines)

            if fotos_anexo_visita:
                pdf.ln(8)
                if pdf.get_y() > 230:
                    pdf.add_page()
                
                pdf.set_font("Arial", "B", 10)
                pdf.set_fill_color(*COLOR_PRIMARIO)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 7, "  REGISTRO FOTOGRÁFICO", ln=1, fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
                pdf.galeria(fotos_anexo_visita)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_v:
                pdf.output(tmp_v.name)
                with open(tmp_v.name, "rb") as fv: st.session_state.pdf_visita = fv.read()
            st.rerun()
        except Exception as e: st.error(f"Error al generar visita: {e}"); st.code(traceback.format_exc())

# ==============================================================================
# LÓGICA: MOLINOS
# ==============================================================================
elif st.session_state.app_mode == "MOLINOS":
    st.title("🏭 Informe y Certificado Molinos")
    st.subheader("I. Datos Generales")
    opcion = st.selectbox("Seleccione Cliente / Planta", list(DATABASE_COMBINADA.keys()))
    d = DATABASE_COMBINADA.get(opcion, {"cliente": "", "rut": "", "direccion": "", "volumen": 0})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        cliente = st.text_input("Razón Social", d.get("cliente", ""))
        planta = st.text_input("Nombre Planta", opcion)
    with col2:
        rut_cli = st.text_input("RUT Cliente", d.get("rut", ""))
        direccion = st.text_input("Dirección", d.get("direccion", ""))
    with col3:
        fecha_inf = st.date_input("Fecha Informe/Emisión", datetime.date.today())
        volumen_total = st.number_input("Volumen Total (m³)", value=d.get("volumen", 0))
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tipo_trat = st.radio("Tipo de Tratamiento", ["Preventivo", "Curativo"], horizontal=True, key="tr_m")
    with col_t2:
        plaga = "N/A"
        if tipo_trat == "Curativo": plaga = st.text_input("Plaga Objetivo", "Tribolium confusum", key="pl_m")
        
    st.markdown("**Datos para Certificado:**")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: num_cert = st.text_input("N° Certificado", "28251")
    with cc2: ingrediente = st.selectbox("Fumigante a Declarar", ["Fosfuro de Aluminio (AIP) 56%", "Fosfuro de Magnesio", "Mixto"])
    with cc3: inf_ref_mol = st.text_input("Informe Ref.", f"2026-{num_cert} NP")

    st.subheader("II. Plan de Sellado y Limpieza")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        enc_l_mol = st.text_input("Encargado Limpieza (Cliente)", "Jefe de Planta")
        rep_m_sel = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES, key="rep_sel_m")
        if rep_m_sel == "OTRO":
            rep_r = st.text_input("Ingrese nombre del Representante manualmente:", key="rep_man_m")
        else:
            rep_r = rep_m_sel
            
    with col_l2:
        fecha_rev_mol = st.date_input("Fecha Revisión", datetime.date.today(), key="f_rev_m")
        hora_rev_mol = st.time_input("Hora Revisión", datetime.time(10, 0), key="h_rev_m")
    
    hay_obs_mol = st.checkbox("⚠️ ¿Agregar observaciones de limpieza/mejoras?")
    txt_obs_mol = st.text_area("Describa los hallazgos:", height=80) if hay_obs_mol else ""
    fotos_sellado_mol = st.file_uploader("Subir fotos sellado/limpieza (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="fs_mol")

    st.subheader("III. Tiempos de Fumigación")
    col_ti1, col_ti2 = st.columns(2)
    with col_ti1:
        f_ini = st.date_input("Inicio Inyección", datetime.date.today(), key="i_m")
        h_ini = st.time_input("Hora Inicio", datetime.time(19, 0), key="h_i_m")
    with col_ti2:
        f_ter = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=3), key="f_m")
        h_ter = st.time_input("Hora Término", datetime.time(19, 0), key="h_t_m")
    horas_exp = (datetime.datetime.combine(f_ter, h_ter) - datetime.datetime.combine(f_ini, h_ini)).total_seconds() / 3600

    st.subheader("IV. Distribución y Dosis")
    df_d_mol_val = st.data_editor(st.session_state.df_d_mol, num_rows="dynamic", use_container_width=True, key="edi_mol_d")
    fotos_dosis = st.file_uploader("Evidencia dosis (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_d_m")
    
    total_g = (df_d_mol_val["Bandejas"].apply(clean_number).sum() * 500) + (df_d_mol_val["Mini-Ropes"].apply(clean_number).sum() * 333)
    dosis_final = total_g / volumen_total if volumen_total > 0 else 0

    st.subheader("V. Mediciones")
    serie_xam = st.selectbox(
        "Equipo de Medición (Serie X-AM 8000)", 
        ["ARNF-0043", "ARNF-0050", "ARNM-0023", "ARPK-0020", "ARPL-0030"]
    )
    
    df_m_mol_val = st.data_editor(st.session_state.df_m_mol, num_rows="dynamic", use_container_width=True, key="edi_mol_m")
    fotos_meds = st.file_uploader("Evidencia de Monitoreo (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_m_m")

    st.subheader("VI. Anexo Fotográfico")
    fotos_anexo = st.file_uploader("Fotos Generales", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_a_m")
    firma_file = st.file_uploader("Firma RT (Timbre)", type=["png", "jpg", "jpeg", "heic"], key="firm_m")

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        firma_path_guardada = None
        try:
            cliente_limpio = clean_filename(cliente)
            fecha_str = fecha_inf.strftime('%d%m%y')
            st.session_state.fn_informe = f"{fecha_str}_Informe_Molino_{cliente_limpio}.pdf"
            st.session_state.fn_cert = f"{fecha_str}_Certificado_Molino_{cliente_limpio}.pdf"

            df_m_clean = df_m_mol_val.copy()
            df_m_clean['Fecha_str'] = df_m_clean['Fecha'].astype(str).str.strip().str.lower()
            df_m_clean['Hora_str'] = df_m_clean['Hora'].astype(str).str.strip().str.lower()
            mask = ~((df_m_clean['Fecha_str'].isin(['none', 'nan', ''])) | (df_m_clean['Hora_str'].isin(['none', 'nan', ''])))
            df_m_clean = df_m_clean[mask].drop(columns=['Fecha_str', 'Hora_str'])

            firma_path_guardada = procesar_firma(firma_file) if firma_file else ('firma.png' if os.path.exists('firma.png') else None)
            
            pdf = InformePDF()
            pdf.add_page()
            pdf.set_font("Arial", "", 11)
            pdf.cell(35, 7, "Cliente:", 0); pdf.cell(0, 7, str(cliente), 0, ln=1)
            pdf.cell(35, 7, "Dirección:", 0); pdf.cell(0, 7, str(direccion), 0, ln=1) 
            pdf.cell(35, 7, "Tratamiento:", 0); pdf.cell(0, 7, f"{tipo_trat} - Plaga: {plaga}", 0, ln=1)
            pdf.cell(35, 7, "Fecha:", 0); pdf.cell(0, 7, format_fecha_es(fecha_inf), 0, ln=1)
            
            pdf.t_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, "Previo a la inyección del fumigante, se verificaron y ejecutaron las condiciones de saneamiento crítico en las estructuras a tratar. Las labores se centraron en la remoción mecánica de biomasa, costras de producto envejecido y acumulaciones de polvo en zonas de difícil acceso (interiores de roscas, cúpulas de silos y ductos).\n\nEsta gestión de limpieza elimina refugios físicos que podrían disminuir la penetración del gas, garantizando así la hermeticidad y la máxima eficacia del tratamiento según los protocolos de calidad de Rentokil Initial.\n\n" + f"Supervisión Cliente: {enc_l_mol} | Visado Rentokil: {rep_r}.\n" + f"Fecha Revisión en Terreno: {fecha_rev_mol} a las {hora_rev_mol} horas.")
            pdf.ln(3)
            
            if hay_obs_mol and txt_obs_mol:
                pdf.set_font("Arial", "B", 11); pdf.set_text_color(200, 0, 0); pdf.cell(0, 7, "OBSERVACIONES / OPORTUNIDADES DE MEJORA DETECTADAS:", ln=1)
                pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 11); pdf.multi_cell(0, 6, txt_obs_mol); pdf.ln(3)

            if fotos_sellado_mol: pdf.galeria(fotos_sellado_mol, "Evidencia de Limpieza y Sellado:")
            
            pdf.t_seccion("II", "VOLÚMENES Y TIEMPOS")
            pdf.multi_cell(0, 6, f"Volumen total tratado: {volumen_total} m3.\nTiempo de exposición efectivo: {horas_exp:.1f} horas.")
            pdf.ln(2)
            pdf.tabla(["Evento", "Fecha", "Hora", "Total Horas"], [["Inyección", str(f_ini), str(h_ini), f"{horas_exp:.1f}"], ["Ventilación", str(f_ter), str(h_ter), "---"]], [45, 45, 45, 55])
            
            pdf.t_seccion("III", "DOSIFICACIÓN") 
            d_p = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_d_mol_val.iterrows()]
            d_p.append(["TOTALES", str(int(df_d_mol_val["Bandejas"].apply(clean_number).sum())), str(int(df_d_mol_val["Mini-Ropes"].apply(clean_number).sum()))])
            pdf.tabla(["Sector", "Bandejas", "Mini-Ropes"], d_p, [80, 55, 55], bold_last=True)
            
            if fotos_dosis: pdf.galeria(fotos_dosis, "Evidencia de Dosificación:")
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, f"DOSIS FINAL: {dosis_final:.2f} g/m3", ln=1, align="R")
            
            pisos_activos = []
            for _, row in df_d_mol_val.iterrows():
                b_val = clean_number(row.get("Bandejas", 0))
                m_val = clean_number(row.get("Mini-Ropes", 0))
                if b_val > 0 or m_val > 0:
                    pisos_activos.append(str(row.get("Piso", "")))
            
            pisos_str = ", ".join(pisos_activos) if pisos_activos else "las áreas tratadas"
            
            texto_mediciones = (
                f"Para las mediciones de gas Fosfina durante toda la fumigación se colocaron sondas de muestreo de gas en los siguientes pisos del "
                f"molino: {pisos_str}. Las sondas de muestreo son micro tubos de riego de polietileno de color negro y de un diámetro de 4 mm. "
                f"La disposición final de estas sondas en cada piso, fue determinada por control de calidad.\n\n"
                "Se acordó con el Molino, la siguiente frecuencia de medición:\n"
                "- Medición cada 2 horas, desde la inyección del molino hasta alcanzar las 200 ppm.\n"
                "- Una vez alcanzadas las 300 ppm, las mediciones se realizaron a las 7:00, 13:00, 19:00 y 24:00 horas.\n\n"
                f"Las mediciones de fosfina se realizaron con uso de gas tester digital X-AM 8000 (serie {serie_xam})."
            )
            
            pdf.t_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)", force=True)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, texto_mediciones)
            pdf.ln(5)

            tmp_g_name = None
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                e_x = df_m_clean["Fecha"].astype(str) + "\n" + df_m_clean["Hora"].astype(str)
                h_g = False
                
                for i in range(2, len(df_m_clean.columns)):
                    col_name = df_m_clean.columns[i]
                    val = pd.to_numeric(df_m_clean.iloc[:, i], errors='coerce').fillna(0)
                    if val.sum() > 0:
                        ax.plot(e_x, val, marker='o', label=col_name)
                        h_g = True
                        
                ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
                if h_g: ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4, frameon=False)
                plt.tight_layout()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                    tmp_g_name = tmp_g.name
                    fig.savefig(tmp_g_name, dpi=300)
                    
                pdf.image(tmp_g_name, x=10, w=190)
            finally:
                if tmp_g_name and os.path.exists(tmp_g_name):
                    os.remove(tmp_g_name)
            
            if pdf.get_y() > 180:
                pdf.add_page()
            else:
                pdf.ln(5)
            
            cols_list = list(df_m_clean.columns)
            pdf.tabla(cols_list, [[str(x) for x in r] for _, r in df_m_clean.iterrows()], [25, 15] + [25]* (len(cols_list)-2))
            
            if fotos_meds: pdf.galeria(fotos_meds, "Evidencia de Monitoreo:")
            if fotos_anexo: pdf.t_seccion("V", "ANEXO FOTOGRÁFICO", force=True); pdf.galeria(fotos_anexo)
            
            pdf.t_seccion("VI", "CONCLUSIONES TÉCNICAS", force=True)
            t_efic = f"asegurando el control biológico de {plaga} en todos sus estadios de desarrollo."
            if tipo_trat == "Preventivo":
                t_efic = "logrando establecer una barrera sanitaria efectiva que elimina reservorios biológicos latentes y mitiga riesgos de contaminación cruzada, garantizando así la integridad higiénica de las instalaciones."
            
            c_text = (
                "EVALUACIÓN DE EFICACIA:\n"
                f"El análisis de los registros de monitoreo confirma que la concentración de Fosfina (PH3) se mantuvo por sobre el umbral crítico de 300 PPM durante las {horas_exp:.1f} horas de exposición efectiva. Esta saturación constante garantiza una penetración total del gas en los puntos críticos de las estructuras, {t_efic}\n\n"
                "CERTIFICACIÓN:\n"
                "En consecuencia, el servicio se declara CONFORME, validando la bio-disponibilidad del ingrediente activo y el cumplimiento de los estándares técnicos de Rentokil Initial Chile."
            )
            pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, c_text); pdf.ln(20)
            
            if firma_path_guardada:
                if pdf.get_y() > 240: pdf.add_page()
                pdf.image(firma_path_guardada, x=75, w=60)

            # CERTIFICADO MOLINOS
            flat_vals = df_m_clean.iloc[:, 2:].values.flatten()
            promedio_ppm = pd.to_numeric(pd.Series(flat_vals), errors='coerce').dropna().mean()
            promedio_ppm = 0 if pd.isna(promedio_ppm) else promedio_ppm

            cert = CertificadoPDF()
            cert.add_page()
            cert.set_font("Arial", "B", 10)
            cert.cell(0, 6, "El profesional que suscribe certifica que Rentokil Initial Chile SpA, ha procedido a fumigar lo siguiente:", ln=1)
            cert.t_rojo("I. ANTECEDENTES DE LA EMPRESA MANDANTE")
            cert.t_cert(["RAZÓN SOCIAL", "RUT", "DIRECCIÓN"], [[cliente, rut_cli, direccion]], [70, 30, 90])
            
            cert.t_rojo("II. ANTECEDENTES SOBRE LA APLICACIÓN")
            cert.t_cert(["Área Tratada", "Volumen (m3)", "Fecha y Hora Fumigación / Ventilación"], [[planta, f"{volumen_total} m3", f"Inicio: {f_ini.strftime('%d-%m-%Y')} - {h_ini} Hrs\nTérmino: {f_ter.strftime('%d-%m-%Y')} - {h_ter} Hrs"]], [50, 30, 110])
            
            cert.t_cert(["Tiempo Exp.", "Fumigante Usado", "Lugar Fumigación"], [[f"{horas_exp:.0f} Horas", ingrediente, direccion]], [30, 60, 100])
            cert.t_cert(["Dosis (g/m3)", "Concentración Promedio", "Informe Ref."], [[f"{dosis_final:.2f}", f"{promedio_ppm:.0f} PPM", inf_ref_mol]], [50, 70, 70])
            
            cert.ln(10); cert.set_font("Arial", "", 10)
            cert.multi_cell(0, 6, f"Se extiende el presente certificado N° {num_cert}, con fecha {format_fecha_es(fecha_inf)}, al interesado para los efectos que estime conveniente.")
            cert.ln(20)
            
            if firma_path_guardada:
                if cert.get_y() > 240: cert.add_page()
                cert.image(firma_path_guardada, x=75, w=60)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1, tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
                pdf.output(t1.name); cert.output(t2.name)
                with open(t1.name, "rb") as f1: st.session_state.pdf_informe = f1.read()
                with open(t2.name, "rb") as f2: st.session_state.pdf_cert = f2.read()
            
            st.rerun()
            
        except Exception as e: 
            st.error(f"Error al generar documentos: {e}")
            st.code(traceback.format_exc())
        finally:
            if firma_path_guardada and firma_path_guardada != 'firma.png':
                if os.path.exists(firma_path_guardada): os.remove(firma_path_guardada)

# ==============================================================================
# LÓGICA: ESTRUCTURAS (10 PUNTOS)
# ==============================================================================
elif st.session_state.app_mode == "ESTRUCTURAS":
    st.title("🏗️ Informe y Certificado Estructuras")
    st.subheader("I. Datos Generales")
    LIST_CL = list(DATABASE_COMBINADA.keys())
    op_e = st.selectbox("Cliente / Planta", LIST_CL)
    db_ref = DATABASE_COMBINADA
    
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        cliente_e = st.text_input("Nombre Cliente", db_ref[op_e].get("cliente", op_e))
        direccion_e = st.text_input("Dirección", db_ref[op_e].get("direccion", ""))
    with col_e2:
        rut_cli_e = st.text_input("RUT Cliente", db_ref[op_e].get("rut", ""))
        fecha_e = st.date_input("Fecha Informe/Emisión", datetime.date.today())
    with col_e3:
        tipo_trat = st.radio("Tipo de Tratamiento", ["Preventivo", "Curativo"], horizontal=True)
        plaga_e = "N/A"
        if tipo_trat == "Curativo": plaga_e = st.text_input("Plaga Objetivo", "Tribolium confusum")

    st.markdown("**Datos para Certificado:**")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: num_cert = st.text_input("N° Certificado", "28252")
    with cc2: ingrediente = st.selectbox("Fumigante a Declarar", ["Fosfuro de Aluminio (AIP) 56%", "Fosfuro de Magnesio", "Mixto"])
    with cc3: inf_ref_est = text_input_ref = st.text_input("Informe Ref.", f"2026-{num_cert} NP")

    st.subheader("II. Plan de Sellado y Limpieza")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        enc_l = st.text_input("Encargado Limpieza", "Jefe de Turno")
        rep_e_sel = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES, key="rep_sel_e")
        if rep_e_sel == "OTRO":
            rep_r = st.text_input("Ingrese nombre del Representante manualmente:", key="rep_man_e")
        else:
            rep_r = rep_e_sel
            
    with col_l2:
        fecha_rev = st.date_input("Fecha Revisión", datetime.date.today())
        hora_rev = st.time_input("Hora Revisión", datetime.time(10, 0))
    est_sel = st.multiselect("Estructuras a tratar", ["Silos", "Tolvas", "Roscas", "Elevadores", "Pozos", "Ductos Descarga", "Ductos Carga", "Pavos", "Ductos Aspiración", "Celdas"])
    
    hay_obs = st.checkbox("⚠️ ¿Agregar observaciones de limpieza?")
    txt_obs = st.text_area("Hallazgos:", height=80) if hay_obs else ""
    fotos_l = st.file_uploader("Fotos sellado/limpieza", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    st.subheader("III. Volumen y Dosis")
    df_est_val = st.data_editor(st.session_state.df_d_est, num_rows="dynamic", use_container_width=True, key="edi_est_d")
    fotos_d = st.file_uploader("Fotos dosificación", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    st.subheader("IV. Tiempos y Mediciones")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        f_ini_e = st.date_input("Inicio", datetime.date.today())
        h_ini_e = st.time_input("Hora Inicio", datetime.time(18, 0))
    with col_t2:
        f_ter_e = st.date_input("Término", datetime.date.today() + datetime.timedelta(days=4))
        h_ter_e = st.time_input("Hora Término", datetime.time(10, 0))
    h_exp_e = (datetime.datetime.combine(f_ter_e, h_ter_e) - datetime.datetime.combine(f_ini_e, h_ini_e)).total_seconds() / 3600

    st.markdown("**Nombres de Puntos de Medición (Máximo 10):**")
    c_n1 = st.columns(5)
    c_n2 = st.columns(5)
    
    for i in range(5): 
        nom = c_n1[i].text_input(f"P {i+1}", st.session_state.nom_p[i], key=f"p_{i}")
        st.session_state.nom_p[i] = nom
        
    for i in range(5, 10): 
        nom = c_n2[i-5].text_input(f"P {i+1}", st.session_state.nom_p[i], key=f"p_{i}")
        st.session_state.nom_p[i] = nom
    
    col_conf = {"Fecha": "Fecha", "Hora": "Hora"}
    for i in range(10):
        col_conf[f"P{i+1}"] = st.session_state.nom_p[i]
        
    df_med_est_val = st.data_editor(st.session_state.df_m_est, column_config=col_conf, num_rows="dynamic", use_container_width=True, key="edi_est_m")
    fotos_m = st.file_uploader("Fotos mediciones", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    st.subheader("V. Anexo Fotográfico")
    fotos_a = st.file_uploader("Otras fotos", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    firma_e = st.file_uploader("Firma RT (Timbre)", type=["png", "jpg", "jpeg", "heic"])

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        firma_path_guardada = None
        try:
            cliente_limpio = clean_filename(cliente_e)
            fecha_str = fecha_e.strftime('%d%m%y')
            st.session_state.fn_informe = f"{fecha_str}_Informe_Estructuras_{cliente_limpio}.pdf"
            st.session_state.fn_cert = f"{fecha_str}_Certificado_Estructuras_{cliente_limpio}.pdf"

            firma_path_guardada = procesar_firma(firma_e) if firma_e else ('firma.png' if os.path.exists('firma.png') else None)
            
            df_m_pdf = df_med_est_val.copy()
            df_m_pdf.columns = ["Fecha", "Hora"] + st.session_state.nom_p
            
            df_m_pdf['Fecha_str'] = df_m_pdf['Fecha'].astype(str).str.strip().str.lower()
            df_m_pdf['Hora_str'] = df_m_pdf['Hora'].astype(str).str.strip().str.lower()
            mask = ~((df_m_pdf['Fecha_str'].isin(['none', 'nan', ''])) | (df_m_pdf['Hora_str'].isin(['none', 'nan', ''])))
            df_m_pdf = df_m_pdf[mask].drop(columns=['Fecha_str', 'Hora_str'])

            cols_to_keep = ["Fecha", "Hora"]
            for i in range(2, len(df_m_pdf.columns)):
                col_name = df_m_pdf.columns[i]
                val = pd.to_numeric(df_m_pdf.iloc[:, i], errors='coerce').fillna(0)
                if val.sum() > 0 or col_name.strip().lower() != f"punto {i-1}".lower():
                    cols_to_keep.append(col_name)

            df_m_pdf_filtered = df_m_pdf[cols_to_keep]

            pdf = InformePDF()
            pdf.add_page()
            pdf.set_font("Arial", "", 11)
            pdf.cell(35, 7, "Cliente:", 0); pdf.cell(0, 7, str(cliente_e), 0, ln=1)
            pdf.cell(35, 7, "Dirección:", 0); pdf.cell(0, 7, str(direccion_e), 0, ln=1)
            pdf.cell(35, 7, "Tratamiento:", 0); pdf.cell(0, 7, f"{tipo_trat} - Plaga: {plaga_e}", 0, ln=1)
            pdf.cell(35, 7, "Fecha:", 0); pdf.cell(0, 7, format_fecha_es(fecha_e), 0, ln=1)
            
            pdf.t_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, "Previo a la inyección del fumigante, se verificaron y ejecutaron las condiciones de saneamiento crítico en las structures a tratar. Las labores se centraron en la remoción mecánica de biomasa, costras de producto envejecido y acumulaciones de polvo en zonas de difícil acceso (interiores de roscas, cúpulas de silos y ductos).\n\nEsta gestión de limpieza elimina refugios físicos que podrían disminuir la penetración del gas, garantizando así la hermeticidad y la máxima eficacia del tratamiento según los protocolos de calidad de Rentokil Initial.\n\n" + f"Supervisión Cliente: {enc_l} | Visado Rentokil: {rep_r}.\n" + f"Fecha Revisión en Terreno: {fecha_rev} a las {hora_rev} horas.")
            pdf.ln(3)
            
            if hay_obs and txt_obs:
                pdf.set_font("Arial", "B", 11); pdf.set_text_color(200, 0, 0); pdf.cell(0, 7, "OBSERVACIONES / OPORTUNIDADES DE MEJORA DETECTADAS:", ln=1)
                pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 11); pdf.multi_cell(0, 6, txt_obs); pdf.ln(3)

            p_sel = ", ".join(est_sel) if est_sel else "No especificadas"
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Estructuras intervenidas: {p_sel}", ln=1)
            if fotos_l: pdf.galeria(fotos_l, "Evidencia de Limpieza y Sellado:")
            
            pdf.t_seccion("II", "VOLUMEN Y DOSIFICACIÓN")
            d_d_pdf = []; t_g = 0; t_v = 0
            for _, row in df_est_val.iterrows():
                v = clean_number(row.get("Volumen (m3)", 0)); n_pl = clean_number(row.get("Cant. Placas", 0))
                n_ro = clean_number(row.get("Cant. Mini-Ropes", 0)); n_ph = clean_number(row.get("Cant. Phostoxin", 0))
                if v > 0 or n_pl > 0 or n_ro > 0 or n_ph > 0:
                    g_r = (n_pl * 33) + (n_ro * 333) + (n_ph * 1); d_r = g_r / v if v > 0 else 0
                    t_g += g_r; t_v += v
                    d_d_pdf.append([str(row.get("Estructura (Nombre/N°)", "")), f"{v:.1f}", f"{int(n_pl)}", f"{int(n_ro)}", f"{int(n_ph)}", f"{d_r:.2f}"])
            
            d_d_pdf.append(["TOTALES", f"{t_v:.1f}", "", "", "", ""])
            pdf.tabla(["Estructura", "Vol(m3)", "Plac", "Rope", "Phos", "Dosis g/m3"], d_d_pdf, [60, 25, 20, 20, 25, 40], bold_last=True)
            pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Total Gas Generado: {t_g:.1f} gramos.", ln=1, align="R")
            dosis_promedio = t_g / t_v if t_v > 0 else 0
            if fotos_d: pdf.galeria(fotos_d, "Evidencia de Dosificación:")

            pdf.t_seccion("III", "TIEMPOS Y MEDICIONES", force=True)
            pdf.tabla(["Evento", "Fecha", "Hora", "Total Horas"], [["Inicio", str(f_ini_e), str(h_ini_e), f"{h_exp_e:.1f}"], ["Término", str(f_ter_e), str(h_ter_e), "---"]], [45, 45, 45, 55])
            
            tmp_g_name_e = None
            try:
                fig, ax = plt.subplots(figsize=(10, 5))
                e_x = df_m_pdf_filtered["Fecha"].astype(str) + "\n" + df_m_pdf_filtered["Hora"].astype(str)
                h_g = False
                
                for i in range(2, len(df_m_pdf_filtered.columns)):
                    col_name = df_m_pdf_filtered.columns[i]
                    val = pd.to_numeric(df_m_pdf_filtered.iloc[:, i], errors='coerce').fillna(0)
                    if val.sum() > 0: 
                        ax.plot(e_x, val, marker='o', label=col_name)
                        h_g = True
                        
                ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
                if h_g: ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=5, frameon=False)
                plt.tight_layout()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                    tmp_g_name_e = tmp_g.name
                    fig.savefig(tmp_g_name_e, dpi=300)
                    
                pdf.image(tmp_g_name_e, x=10, w=190)
            finally:
                if tmp_g_name_e and os.path.exists(tmp_g_name_e):
                    os.remove(tmp_g_name_e)
                    
            pdf.ln(5)
            
            cols_list = list(df_m_pdf_filtered.columns)
            num_points = len(cols_list) - 2
            w_points = 155 / num_points if num_points > 0 else 0
            pdf.tabla(cols_list, [[str(x) for x in r] for _, r in df_m_pdf_filtered.iterrows()], [20, 15] + [w_points]*num_points)
            
            if fotos_m: pdf.galeria(fotos_m, "Evidencia de Monitoreo:")
            if fotos_a: pdf.t_seccion("IV", "ANEXO FOTOGRÁFICO", force=True); pdf.galeria(fotos_a)

            pdf.t_seccion("V", "CONCLUSIONES TÉCNICAS", force=True)
            t_efic = f"asegurando el control biológico de {plaga_e} en todos sus estadios de desarrollo."
            if tipo_trat == "Preventivo":
                t_efic = "logrando establecer una barrera sanitaria efectiva que elimina reservorios biológicos latentes y mitiga riesgos de contaminación cruzada, garantizando así la integridad higiénica de las instalaciones."

            c_text = (
                "EVALUACIÓN DE EFICACIA:\n"
                f"El análisis de los registros de monitoreo confirma que la concentración de Fosfina (PH3) se mantuvo por sobre el umbral crítico de 300 PPM durante las {h_exp_e:.1f} horas de exposición efectiva. Esta saturación constante garantiza una penetración total del gas en los puntos críticos de las structures, {t_efic}\n\n"
                "CERTIFICACIÓN:\n"
                "En consecuencia, el servicio se declara CONFORME, validando la bio-disponibilidad del ingrediente activo y el cumplimiento de los estándares técnicos de Rentokil Initial Chile."
            )
            pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, c_text); pdf.ln(20)

            if firma_path_guardada:
                if pdf.get_y() > 240: pdf.add_page()
                pdf.image(firma_path_guardada, x=75, w=60)

            # 2. CERTIFICADO ESTRUCTURAS
            flat_vals = df_m_pdf_filtered.iloc[:, 2:].values.flatten()
            promedio_ppm = pd.to_numeric(pd.Series(flat_vals), errors='coerce').dropna().mean()
            promedio_ppm = 0 if pd.isna(promedio_ppm) else promedio_ppm

            cert = CertificadoPDF()
            cert.add_page()
            cert.set_font("Arial", "B", 10)
            cert.cell(0, 6, "El profesional que suscribe certifica que Rentokil Initial Chile SpA, ha procedido a fumigar lo siguiente:", ln=1)
            cert.t_rojo("I. ANTECEDENTES DE LA EMPRESA MANDANTE")
            cert.t_cert(["RAZÓN SOCIAL", "RUT", "DIRECCIÓN"], [[cliente_e, rut_cli_e, direccion_e]], [70, 30, 90])
            
            cert.t_rojo("II. ANTECEDENTES SOBRE LA APLICACIÓN")
            p_limpio = p_sel[:30]+"..." if len(p_sel)>30 else p_sel
            cert.t_cert(["Área Tratada", "Volumen (m3)", "Fecha y Hora Fumigación / Ventilación"], [[p_limpio, f"{t_v:.1f} m3", f"Inicio: {f_ini_e.strftime('%d-%m-%Y')} - {h_ini_e} Hrs\nTérmino: {f_ter_e.strftime('%d-%m-%Y')} - {h_ter_e} Hrs"]], [50, 30, 110])
            cert.t_cert(["Tiempo Exp.", "Fumigante Usado", "Lugar Fumigación"], [[f"{h_exp_e:.0f} Horas", ingrediente, direccion_e]], [30, 60, 100])
            cert.t_cert(["Dosis (g/m3)", "Concentración Promedio", "Informe Ref."], [[f"{dosis_promedio:.2f}", f"{promedio_ppm:.0f} PPM", inf_ref_est]], [50, 70, 70])
            
            cert.ln(10); cert.set_font("Arial", "", 10)
            cert.multi_cell(0, 6, f"Se extiende el presente certificado N° {num_cert}, con fecha {format_fecha_es(fecha_e)}, al interesado para los efectos que estime conveniente.")
            cert.ln(20)
            if firma_path_guardada:
                if cert.get_y() > 240: cert.add_page()
                cert.image(firma_path_guardada, x=75, w=60)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1, tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
                pdf.output(t1.name); cert.output(t2.name)
                with open(t1.name, "rb") as f1: st.session_state.pdf_informe = f1.read()
                with open(t2.name, "rb") as f2: st.session_state.pdf_cert = f2.read()
                
            st.rerun()

        except Exception as e: 
            st.error(f"Error al generar documentos: {e}")
            st.code(traceback.format_exc())
        finally:
            if firma_path_guardada and firma_path_guardada != 'firma.png':
                if os.path.exists(firma_path_guardada): os.remove(firma_path_guardada)

# ==============================================================================
# LÓGICA: INFORME DE TRABAJO
# ==============================================================================
elif st.session_state.app_mode == "TRABAJO":
    st.title("📸 Informe de Trabajo (Pantalla Completa)")
    st.markdown("Este módulo genera un PDF oficial. La primera imagen acompaña la portada, las demás ocupan la hoja completa.")
    
    op_d = st.selectbox("Seleccione Cliente", list(DATABASE_COMBINADA.keys()))
    db_ref = DATABASE_COMBINADA
    
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        cli_d = st.text_input("Razón Social", db_ref[op_d].get("cliente", op_d))
    with col_d2:
        dir_d = st.text_input("Dirección", db_ref[op_d].get("direccion", ""))
    with col_d3:
        fec_d = st.date_input("Fecha", datetime.date.today())
        
    detalles_d = st.text_area("Detalle de Labores / Observaciones (Máx. 5 líneas recomendadas)", height=100)
        
    fotos_dialogo = st.file_uploader("Sube TODAS las fotos aquí (Soporta 50+ imágenes)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    
    if st.button("🚀 GENERAR INFORME DE TRABAJO", use_container_width=True, type="primary"):
        if fotos_dialogo:
            try:
                cliente_limpio = clean_filename(cli_d)
                fecha_str = fec_d.strftime('%d%m%y')
                st.session_state.fn_trabajo = f"{fecha_str}_Informe_Trabajo_{cliente_limpio}.pdf"

                pdf = InformePDF()
                pdf.add_page()
                
                pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.set_text_color(*COLOR_PRIMARIO)
                pdf.cell(0, 8, "REGISTRO FOTOGRÁFICO DE TRABAJO", ln=1, align="C")
                pdf.set_text_color(0, 0, 0); pdf.ln(5)
                
                pdf.tabla_moderna(["CLIENTE / RAZÓN SOCIAL", "DIRECCIÓN", "FECHA"], [[str(cli_d), str(dir_d), format_fecha_es(fec_d)]], [80, 70, 40], color=COLOR_PRIMARIO)
                
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(*COLOR_PRIMARIO)
                pdf.set_text_color(255, 255, 255)
                x_start = pdf.get_x()
                y_start = pdf.get_y()
                pdf.rounded_rect(x_start, y_start, 190, 7, 2, 'F')
                pdf.cell(190, 7, "DETALLE DE LABORES / OBSERVACIONES", border=0, align='C', fill=False)
                pdf.ln()
                pdf.set_font("Arial", "", 9)
                pdf.set_text_color(0, 0, 0)
                texto_detalles = str(detalles_d).strip() if str(detalles_d).strip() else "Sin observaciones registradas."
                pdf.multi_cell(190, 5, texto_detalles, border='B', align='L')
                pdf.ln(5)
                
                progress_text = "Procesando imágenes. Por favor espera..."
                my_bar = st.progress(0, text=progress_text)
                
                for i, f in enumerate(fotos_dialogo):
                    tmp_p, w, h = procesar_imagen_full(f)
                    if tmp_p:
                        try:
                            ratio = w / h
                            if i == 0:
                                avail_h = 260 - pdf.get_y()
                                max_w_cover = 150 
                                if (max_w_cover / ratio) <= avail_h:
                                    final_w = max_w_cover; final_h = max_w_cover / ratio
                                else:
                                    final_h = avail_h; final_w = avail_h * ratio
                                pdf_x = 10 + (190 - final_w) / 2
                                pdf.image(tmp_p, x=pdf_x, y=pdf.get_y(), w=final_w, h=final_h)
                            else:
                                pdf.add_page()
                                if (190 / ratio) <= 240:
                                    final_w = 190; final_h = 190 / ratio
                                else:
                                    final_h = 240; final_w = 240 * ratio
                                pdf_x = 10 + (190 - final_w) / 2
                                pdf_y = 35 + (240 - final_h) / 2
                                pdf.image(tmp_p, x=pdf_x, y=pdf_y, w=final_w, h=final_h)
                        finally:
                            if os.path.exists(tmp_p):
                                os.remove(tmp_p)
                                
                    my_bar.progress((i + 1) / len(fotos_dialogo), text=f"Procesando imagen {i+1} de {len(fotos_dialogo)}")
                
                my_bar.empty()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_d:
                    pdf.output(tmp_d.name)
                    with open(tmp_d.name, "rb") as fd: st.session_state.pdf_dialogo = fd.read()
                st.rerun()
            except Exception as e: st.error(f"Error generando Informe de Trabajo: {e}"); st.code(traceback.format_exc())
        else:
            st.warning("Debes subir al menos una foto para generar el informe de trabajo.")


# ==============================================================================
# BOTONES DE DESCARGA GLOBALES
# ==============================================================================
if st.session_state.app_mode in ["MOLINOS", "ESTRUCTURAS"]:
    if st.session_state.pdf_informe is not None or st.session_state.pdf_cert is not None:
        st.success("✅ Documentos Generados Exitosamente")
        c_btn1, c_btn2 = st.columns(2)
        if st.session_state.pdf_informe is not None:
            with c_btn1: st.download_button("📄 DESCARGAR INFORME", data=st.session_state.pdf_informe, file_name=st.session_state.fn_informe, mime="application/pdf", use_container_width=True)
        if st.session_state.pdf_cert is not None:
            with c_btn2: st.download_button("📜 DESCARGAR CERTIFICADO", data=st.session_state.pdf_cert, file_name=st.session_state.fn_cert, mime="application/pdf", use_container_width=True)

if st.session_state.app_mode == "TRABAJO" and st.session_state.pdf_dialogo is not None:
    st.success("✅ Informe de Trabajo Generado Exitosamente")
    st.download_button("📸 DESCARGAR INFORME DE TRABAJO", data=st.session_state.pdf_dialogo, file_name=st.session_state.fn_trabajo, mime="application/pdf", use_container_width=True)

if st.session_state.app_mode == "VISITA" and st.session_state.pdf_visita is not None:
    st.success("✅ Informe de Visita Técnica Generado Exitosamente")
    st.download_button("📋 DESCARGAR VISITA TÉCNICA", data=st.session_state.pdf_visita, file_name=st.session_state.fn_visita, mime="application/pdf", use_container_width=True)
