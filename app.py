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

# --- LIBRERÍAS PARA PLANTILLAS WORD ---
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
    DOCXTPL_INSTALLED = True
except ImportError:
    DOCXTPL_INSTALLED = False

# --- CONFIGURACIÓN PARA IMÁGENES ---
ImageFile.LOAD_TRUNCATED_IMAGES = True
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

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    button[kind="primary"] { background-color: #E30613 !important; color: white !important; font-weight: bold !important; }
    button[kind="primary"]:hover { background-color: #CC0510 !important; border-color: #CC0510 !important; }
    button[kind="secondary"] { background-color: #00A0E0 !important; color: white !important; font-weight: bold !important; }
    button[kind="secondary"]:hover { background-color: #008BBF !important; border-color: #008BBF !important; }
    .email-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #4285F4; color: white; padding: 10px 20px;
        text-decoration: none; border-radius: 5px; font-weight: bold; width: 100%; text-align: center; margin-top: 10px;
    }
    .email-btn:hover { background-color: #3367D6; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO ---
if "app_mode" not in st.session_state: st.session_state.app_mode = "HOME"
if "pdf_informe" not in st.session_state: st.session_state.pdf_informe = None
if "pdf_cert" not in st.session_state: st.session_state.pdf_cert = None
if "pdf_dialogo" not in st.session_state: st.session_state.pdf_dialogo = None
if "pdf_visita" not in st.session_state: st.session_state.pdf_visita = None
if "pdf_aviso" not in st.session_state: st.session_state.pdf_aviso = None
if "sucursal_filtro" not in st.session_state: st.session_state.sucursal_filtro = "SANTIAGO"
if "nom_p" not in st.session_state: st.session_state.nom_p = [f"Punto {i+1}" for i in range(10)]
if "hora_emision_default" not in st.session_state: st.session_state.hora_emision_default = datetime.datetime.now().time()
if "fn_informe" not in st.session_state: st.session_state.fn_informe = "Informe.pdf"
if "fn_cert" not in st.session_state: st.session_state.fn_cert = "Certificado.pdf"
if "fn_trabajo" not in st.session_state: st.session_state.fn_trabajo = "Trabajo.pdf"
if "fn_visita" not in st.session_state: st.session_state.fn_visita = "Visita.pdf"
if "fn_aviso" not in st.session_state: st.session_state.fn_aviso = "Aviso.pdf"

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

if "df_d_est" not in st.session_state:
    st.session_state.df_d_est = pd.DataFrame([{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}])
if "df_m_est" not in st.session_state:
    d_me = []
    for i in range(3): d_me.append([(datetime.date.today() + datetime.timedelta(days=i)).strftime("%d-%m"), "10:00"] + [0]*10)
    st.session_state.df_m_est = pd.DataFrame(d_me, columns=["Fecha", "Hora"] + [f"P{i+1}" for i in range(10)])

# ==============================================================================
# LECTURA NUCLEAR DE EXCEL
# ==============================================================================
DATABASE_COMBINADA = {}
DATABASE_REPRESENTANTES = {}
LISTA_SUCURSALES_SET = set()

def deep_clean(text):
    if pd.isna(text) or text is None: return ""
    return str(text).replace('\xa0', ' ').replace('\u200b', '').replace('\n', ' ').strip()

def clean_filename(name):
    for char in '<>:"/\\|?*.': name = str(name).replace(char, '')
    return name.replace(' ', '_')

def obtener_columna(df, palabras):
    for col in df.columns:
        c_norm = deep_clean(col).lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        if any(p in c_norm for p in palabras): return col
    return None

df_c_raw = pd.DataFrame()
df_t_raw = pd.DataFrame()
for f in os.listdir('.'):
    if "base de datos" in f.lower() and f.endswith(('.xlsx', '.xls')):
        try: df_c_raw = pd.read_excel(f).dropna(how='all')
        except: pass
    if "representantes" in f.lower() and f.endswith(('.xlsx', '.xls')):
        try: df_t_raw = pd.read_excel(f).dropna(how='all')
        except: pass

if not df_c_raw.empty:
    c_cli = obtener_columna(df_c_raw, ['razon', 'cliente', 'planta', 'social'])
    c_rut = obtener_columna(df_c_raw, ['rut'])
    c_dir = obtener_columna(df_c_raw, ['dir'])
    c_suc = obtener_columna(df_c_raw, ['sucursal', 'suc'])
    if c_suc:
        df_c_raw['Filtro'] = df_c_raw[c_suc].apply(deep_clean).str.upper()
        LISTA_SUCURSALES_SET.update(df_c_raw['Filtro'].replace('', np.nan).dropna().unique())
else: c_cli, c_rut, c_dir, c_suc = None, None, None, None

if not df_t_raw.empty:
    t_nom = obtener_columna(df_t_raw, ['nombre', 'rep', 'tec'])
    t_rut = obtener_columna(df_t_raw, ['rut'])
    t_mail = obtener_columna(df_t_raw, ['correo', 'mail'])
    t_suc = obtener_columna(df_t_raw, ['sucursal', 'suc'])
    if t_suc:
        df_t_raw['Filtro'] = df_t_raw[t_suc].apply(deep_clean).str.upper()
        LISTA_SUCURSALES_SET.update(df_t_raw['Filtro'].replace('', np.nan).dropna().unique())
else: t_nom, t_rut, t_mail, t_suc = None, None, None, None

lista_limpia_sucursales = sorted(list(LISTA_SUCURSALES_SET))
LISTA_SUCURSALES = ["TODAS"] + lista_limpia_sucursales

if "SANTIAGO" in lista_limpia_sucursales and st.session_state.sucursal_filtro not in LISTA_SUCURSALES:
    st.session_state.sucursal_filtro = "SANTIAGO"
elif lista_limpia_sucursales and st.session_state.sucursal_filtro not in LISTA_SUCURSALES:
    st.session_state.sucursal_filtro = lista_limpia_sucursales[0]
elif not lista_limpia_sucursales:
    st.session_state.sucursal_filtro = "TODAS"

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    if st.session_state.app_mode != "HOME":
        st.info(f"📍 Base: **{st.session_state.sucursal_filtro}**")
        st.markdown("---")
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): 
            st.session_state.app_mode = "HOME"; st.rerun()
    else: st.info("👋 Bienvenido")

f_act = st.session_state.sucursal_filtro

if not df_c_raw.empty and c_cli:
    df_f = df_c_raw[df_c_raw['Filtro'] == f_act] if f_act != "TODAS" else df_c_raw
    for _, r in df_f.iterrows():
        n = deep_clean(r[c_cli])
        if n: DATABASE_COMBINADA[n] = {"cliente": n, "rut": deep_clean(r[c_rut]) if c_rut else "", "direccion": deep_clean(r[c_dir]) if c_dir else "", "volumen": 0}
DATABASE_COMBINADA["OTRO"] = {"cliente": "", "rut": "", "direccion": "", "volumen": 0}

if not df_t_raw.empty and t_nom:
    df_tf = df_t_raw[df_t_raw['Filtro'] == f_act] if f_act != "TODAS" else df_t_raw
    for _, r in df_tf.iterrows():
        n = deep_clean(r[t_nom])
        if n: DATABASE_REPRESENTANTES[n] = {"rut": deep_clean(r[t_rut]) if t_rut else "", "correo": deep_clean(r[t_mail]) if t_mail else ""}
DATABASE_REPRESENTANTES["OTRO"] = {"rut": "", "correo": ""}
LISTA_REPRESENTANTES = list(DATABASE_REPRESENTANTES.keys())

# --- FUNCIONES ---
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
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img).convert('RGB')
        img_f = ImageOps.fit(img, (800, 600), method=Image.Resampling.LANCZOS, centering=(0.5, 0.95))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        img_f.save(tmp.name, format='JPEG', quality=85)
        return tmp.name
    except: return None

def procesar_imagen_full(uploaded_file):
    try:
        if isinstance(uploaded_file, io.BytesIO): uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img).convert('RGB')
        if img.width > 1600 or img.height > 1600: img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        img.save(tmp.name, format='JPEG', quality=85)
        return tmp.name, img.width, img.height
    except: return None, 0, 0

def procesar_firma(uploaded_file):
    try:
        img = Image.open(uploaded_file).convert('RGBA')
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        bg.save(tmp.name, format='JPEG', quality=90)
        return tmp.name
    except: return None

# ==============================================================================
# CLASES PDF
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
        self.set_font("Arial", "B", 9); self.set_fill_color(*color); self.set_text_color(255, 255, 255)
        x_start = self.get_x(); y_start = self.get_y()
        self.rounded_rect(x_start, y_start, sum(widths), 7, 2, 'F')
        for i, h in enumerate(header): self.cell(widths[i], 7, h, border=0, align='C', fill=False)
        self.ln(); self.set_font("Arial", "", 9); self.set_text_color(0, 0, 0)
        for row in data:
            for i, d in enumerate(row): self.cell(widths[i], 8, str(d), border='B', align='C', fill=False)
            self.ln()
        self.ln(3)

    def tabla_visita(self, label, lines):
        self.set_font("Arial", "B", 9); y_start = self.get_y(); h = max(len(lines) * 5 + 4, 8)
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
        titulo = "VISITA TÉCNICA PRE-FUMIGACIÓN" if getattr(self, 'is_visita', False) else "INFORME TÉCNICO DE FUMIGACIÓN"
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
            self.set_font("Arial", "B" if bold_last and idx == len(data)-1 else "", 7)
            for i, d in enumerate(row): self.cell(widths[i], 6, str(d), 1, 0, 'C', True)
            self.ln()
            
    def galeria(self, fotos, titulo=None):
        if not fotos: return
        if titulo: self.ln(2); self.set_font("Arial", "B", 9); self.cell(0, 6, titulo, ln=1)
        for i, f in enumerate(fotos):
            tmp = procesar_imagen(f)
            if tmp:
                if self.get_y() > 210: self.add_page(); self.set_y(45)
                if i % 2 == 0: y_act = self.get_y(); self.image(tmp, x=10, y=y_act, w=90, h=65)
                else: self.image(tmp, x=110, y=y_act, w=90, h=65); self.ln(70)
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
# PANTALLA HOME
# ==============================================================================
if st.session_state.app_mode == "HOME":
    st.write("")
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<div style='text-align: center; color: #E30613; font-weight: bold; font-size: 1.2em; margin-top: 10px;'>📍 SELECCIONE BASE OPERATIVA</div>", unsafe_allow_html=True)
        idx_s = LISTA_SUCURSALES.index(st.session_state.sucursal_filtro) if st.session_state.sucursal_filtro in LISTA_SUCURSALES else 0
        n_suc = st.selectbox("Base", LISTA_SUCURSALES, index=idx_s, label_visibility="collapsed")
        if n_suc != st.session_state.sucursal_filtro:
            st.session_state.sucursal_filtro = n_suc; st.rerun()
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🏭 MOLINOS", use_container_width=True, type="primary"): st.session_state.app_mode = "MOLINOS"; st.rerun()
    with c2:
        if st.button("🏗️ ESTRUCTURAS", use_container_width=True, type="primary"): st.session_state.app_mode = "ESTRUCTURAS"; st.rerun()
    with c3:
        if st.button("📋 VISITA TÉCNICA", use_container_width=True, type="primary"): st.session_state.app_mode = "VISITA"; st.rerun()
    st.write(""); c4, c5 = st.columns(2)
    with c4:
        if st.button("📢 NOTIFICACIÓN SEREMI", use_container_width=True, type="secondary"): st.session_state.app_mode = "AVISO"; st.rerun()
    with c5:
        if st.button("📸 INFORME TRABAJO", use_container_width=True, type="secondary"): st.session_state.app_mode = "TRABAJO"; st.rerun()

# ==============================================================================
# MÓDULO AVISO (SEREMI + PDF + GMAIL)
# ==============================================================================
elif st.session_state.app_mode == "AVISO":
    st.title("📢 Aviso de Fumigación al Seremi")
    if not DOCXTPL_INSTALLED: st.warning("⚠️ Instala 'docxtpl' en requirements.txt para Word.")
    
    st.subheader("📝 I. Datos Generales")
    op_a = st.selectbox("Seleccione Cliente", list(DATABASE_COMBINADA.keys()))
    db_a = DATABASE_COMBINADA
    
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        cliente_a = st.text_input("Razón Social", db_a[op_a].get("cliente", op_a))
        rut_cliente_a = st.text_input("RUT Cliente", db_a[op_a].get("rut", ""))
        contacto_a = st.text_input("Atención a", "Jefe de Planta")
    with col_a2:
        dir_a = st.text_input("Dirección", db_a[op_a].get("direccion", ""))
        comuna_a = st.text_input("Comuna", "")
        tel_cliente_a = st.text_input("Teléfono Cliente", "")
    with col_a3:
        fecha_emision_a = st.date_input("Fecha Emisión", datetime.date.today())
        fecha_visita_a = st.date_input("Fecha Visita Previa", datetime.date.today() - datetime.timedelta(days=1))
        hora_emision_a = st.time_input("Hora Emisión", st.session_state.hora_emision_default)
        st.session_state.hora_emision_default = hora_emision_a

    st.subheader("👨‍💼 II. Representante")
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        rep_a_sel = st.selectbox("Representante", LISTA_REPRESENTANTES)
        repre_a = st.text_input("Nombre Manual") if rep_a_sel == "OTRO" else rep_a_sel
    with col_r2:
        rut_repre_a = st.text_input("RUT", DATABASE_REPRESENTANTES.get(rep_a_sel, {}).get("rut", ""))
    with col_r3:
        correo_repre_a = st.text_input("Correo", DATABASE_REPRESENTANTES.get(rep_a_sel, {}).get("correo", ""))

    st.subheader("☣️ III. Detalles Técnicos")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        fecha_fumi_a = st.date_input("Fecha Fumigación", datetime.date.today() + datetime.timedelta(days=2))
        tipo_fum_a = st.selectbox("Tipo", ["Preventiva", "Curativa"])
    with col_f2:
        hora_ini_a = st.time_input("Hora Inicio", datetime.time(9, 0))
        hora_ter_a = st.time_input("Hora Término", datetime.time(18, 0))
    with col_f3:
        horas_exp_a = st.number_input("Horas Exposición", value=72)
        dosis_a = st.text_input("Dosis", "3 g/m3")
    with col_f4:
        estructura_lote_a = st.text_input("Estructura", "Lote 1")
        areas_a = st.text_input("Área General", "Bodega Principal")
        
    c_f5, c_f6, c_f7 = st.columns(3)
    with c_f5: producto_a = st.text_input("Producto/Cultivo", "Nueces de exportación")
    with c_f6: quimico_a = st.selectbox("Químico", ["Fosfina (Fosfuro de Aluminio)", "Fosfuro de Magnesio", "Ambos"])
    with c_f7: plaga_a = st.text_input("Plaga", "Tribolium confusum" if tipo_fum_a == "Curativa" else "N/A", disabled=tipo_fum_a != "Curativa")

    st.subheader("🛠️ IV. Modalidad y Mapa")
    modalidad_a = st.selectbox("Modalidad", ["Lote bajo carpa", "Silos", "Estructuras", "Contenedores", "Otros"])
    texto_otro_a = st.text_input("Especifique:") if modalidad_a == "Otros" else "____________________"

    # --- MAPA AUTO ---
    mapa_path = None
    c_limpio = str(cliente_a).strip()
    for ext in ['.jpg', '.jpeg', '.png', '.heic', '.HEIC']:
        p = os.path.join("mapas", c_limpio + ext)
        if os.path.exists(p): mapa_path = p; break
            
    c_img1, c_img2 = st.columns(2)
    with c_img1:
        if mapa_path: st.success(f"✅ Mapa de **{c_limpio}** detectado.")
        else: st.warning(f"⚠️ No se halló mapa para **{c_limpio}** en 'mapas/'")
        f_mapa = st.file_uploader("Mapa Plan B", type=["png","jpg","jpeg","heic"])
    with c_img2:
        f_firma = st.file_uploader("Firma RT", type=["png","jpg","jpeg","heic"])

    if st.button("🚀 GENERAR PDF Y PREPARAR CORREO", use_container_width=True, type="primary"):
        if not os.path.exists("plantilla_aviso.docx"): st.error("❌ Falta 'plantilla_aviso.docx'.")
        else:
            try:
                st.session_state.fn_aviso = f"{fecha_emision_a.strftime('%d%m%y')}_Aviso_Seremi_{clean_filename(cliente_a)}.pdf"
                doc = DocxTemplate("plantilla_aviso.docx")
                context = {
                    'fecha_emision': format_fecha_es(fecha_emision_a), 'visita_previa': format_fecha_es(fecha_visita_a),
                    'hora_emision': hora_emision_a.strftime("%H:%M"), 'cliente': cliente_a, 'rut_cliente': rut_cliente_a,
                    'tel_cliente': tel_cliente_a, 'comuna': comuna_a, 'direccion': dir_a, 'contacto': contacto_a,
                    'nombre_repre': repre_a, 'rut_repre': rut_repre_a, 'correo_repre': correo_repre_a,
                    'fecha_fumi': format_fecha_es(fecha_fumi_a), 'hora_ini': hora_ini_a.strftime("%H:%M"),
                    'hora_ter': hora_ter_a.strftime("%H:%M"), 'horas_exp': str(horas_exp_a), 'dosis': dosis_a,
                    'tipo_fum': tipo_fum_a, 'estructura_lote': estructura_lote_a, 'areas': areas_a, 'producto': producto_a,
                    'quimico': quimico_a, 'plaga': plaga_a,
                    'check_carpa': "☒" if modalidad_a == "Lote bajo carpa" else "☐",
                    'check_silo': "☒" if modalidad_a == "Silos" else "☐",
                    'check_estructura': "☒" if modalidad_a == "Estructuras" else "☐",
                    'check_contenedor': "☒" if modalidad_a == "Contenedores" else "☐",
                    'check_otro': "☒" if modalidad_a == "Otros" else "☐", 'texto_otro': texto_otro_a
                }

                m_final = None
                if f_mapa: m_final, _, _ = procesar_imagen_full(f_mapa)
                elif mapa_path:
                    with open(mapa_path, "rb") as f_auto: m_final, _, _ = procesar_imagen_full(io.BytesIO(f_auto.read()))
                if m_final: context['mapa_img'] = InlineImage(doc, m_final, width=Mm(135))
                
                s_final = procesar_firma(f_firma) if f_firma else None
                if s_final: context['firma_img'] = InlineImage(doc, s_final, width=Mm(35))

                doc.render(context)
                
                # Conversión a PDF vía LibreOffice
                with tempfile.TemporaryDirectory() as td:
                    dx = os.path.join(td, "t.docx")
                    doc.save(dx)
                    try:
                        subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', td, dx], check=True)
                        with open(os.path.join(td, "t.pdf"), "rb") as fp: st.session_state.pdf_aviso = fp.read()
                    except:
                        st.error("❌ Falló conversión a PDF. Asegúrate de tener 'packages.txt' con 'libreoffice' en GitHub.")
                        # Fallback a word
                        with open(dx, "rb") as fw: st.session_state.pdf_aviso = fw.read()
                        st.session_state.fn_aviso = st.session_state.fn_aviso.replace('.pdf', '.docx')
                
                # Preparar URL de Mailto
                dest = "intoxicacionesplaguicidas@redsalud.gob.cl"
                asunto = f"Aviso de Fumigación - {cliente_a}"
                cuerpo = (f"Señores Seremi,\n\nA través del presente, estamos notificando el tratamiento con gas fosfina, "
                          f"el cual se llevará a cabo el {fecha_fumi_a.strftime('%d-%m-%Y')} en las dependencias de {cliente_a}, "
                          f"ubicadas en {dir_a}.\n\nAdjunto documento oficial con los detalles técnicos del servicio.\n\n"
                          f"Sin otro particular,\nAtentamente,\n{repre_a}\nRentokil Initial Chile SpA")
                st.session_state.mailto_url = f"mailto:{dest}?subject={quote(asunto)}&body={quote(cuerpo)}"

                if m_final and os.path.exists(m_final): os.remove(m_final)
                if s_final and os.path.exists(s_final): os.remove(s_final)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}"); st.code(traceback.format_exc())

    if st.session_state.pdf_aviso:
        st.success("✅ Documento generado y listo para enviar.")
        st.download_button("📥 DESCARGAR AVISO", data=st.session_state.pdf_aviso, file_name=st.session_state.fn_aviso, use_container_width=True)
        st.markdown(f'<a href="{st.session_state.mailto_url}" target="_blank" class="email-btn">📧 ABRIR GMAIL / CORREO Y ADJUNTAR</a>', unsafe_allow_html=True)

# ==============================================================================
# MÓDULO VISITA
# ==============================================================================
elif st.session_state.app_mode == "VISITA":
    st.title("📋 Visita Técnica")
    f_portada = st.file_uploader("Foto Portada", type=['png','jpg','jpeg','heic'])
    op_v = st.selectbox("Cliente", list(DATABASE_COMBINADA.keys()))
    
    cv1, cv2 = st.columns(2)
    with cv1:
        cli_v = st.text_input("Razón Social", DATABASE_COMBINADA[op_v]["cliente"])
        dir_v = st.text_input("Dirección", DATABASE_COMBINADA[op_v]["direccion"])
        t_fum = st.text_input("Tipo Fumigación", "Lote bajo carpa")
    with cv2:
        prod_v = st.text_input("Producto", "Alimento")
        vol_v = st.number_input("Volumen (m³)", value=50)
        tiemp_v = st.text_input("Tiempo exp.", "120 días")

    cs1, cs2, cs3 = st.columns(3)
    with cs1: chimen = st.radio("Chimenea?", ["Sí", "No"], index=1)
    with cs2: 
        alt = st.radio("Altura?", ["Sí", "No"], index=1)
        lv = st.radio("Líneas de vida?", ["Sí", "No"]) if alt=="Sí" else "No"
    with cs3: 
        ofic = st.radio("Oficinas?", ["Sí", "No"], index=1)
        do = st.selectbox("Distancia", ["10m","20m","30m","40m","+50m"]) if ofic=="Sí" else "N/A"

    rq1, rq2, rq3, rq4 = st.checkbox("Ordenar lote"), st.checkbox("Modificar ub."), st.checkbox("Retirar film", True), st.checkbox("Perímetro", True)
    req_n = st.text_input("Notas")

    co1, co2 = st.columns(2)
    with co1:
        piso = st.selectbox("Piso", ["Cemento", "Asfalto", "Tierra", "Losa", "Otro"])
        sello = st.selectbox("Sello", ["Cinta PVC", "Mangas", "AGOREX", "Otro"])
    with co2:
        jsys, mang = st.checkbox("J-System", True), st.checkbox("Manga riego", True)
        dchim = st.selectbox("Dist. chimenea", ["10m","20m","30m","40m","+50m"]) if chimen=="Sí" else "N/A"

    fotos_v = st.file_uploader("Fotos anexo", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    if st.button("🚀 GENERAR VISITA", use_container_width=True, type="primary"):
        st.session_state.fn_visita = f"{datetime.date.today().strftime('%d%m%y')}_Visita_{clean_filename(cli_v)}.pdf"
        pdf = InformePDF(); pdf.is_visita = True; pdf.add_page()
        if f_portada:
            p, w, h = procesar_imagen_full(f_portada)
            if p:
                r = w/h; calc_h = min(190/r, 120); max_w = calc_h*r
                pdf.image(p, x=10+(190-max_w)/2, y=pdf.get_y(), w=max_w, h=calc_h)
                pdf.set_y(pdf.get_y() + calc_h + 10); os.remove(p)
        
        pdf.set_font("Arial", "B", 10); pdf.set_fill_color(*COLOR_CELESTE_CLARO); pdf.set_text_color(255,255,255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F'); pdf.cell(50, 8, "Elemento", align='C'); pdf.cell(140, 8, "Descripción Técnica", ln=1, align='C')
        pdf.set_text_color(0,0,0)

        sl = [f"- Chimenea: {chimen}", f"- Altura: {alt} ({lv})", f"- Oficinas: {ofic} ({do})"]
        rl = []
        if rq1: rl.append("- Ordenar lote")
        if rq2: rl.append("- Modificar ubicación")
        if rq3: rl.append("- Retirar film")
        if rq4: rl.append("- Generar perímetro")
        if req_n: rl.append(f"- {req_n}")
        ol = [f"- Piso: {piso}", f"- Sello: {sello}"]
        if jsys: ol.append("- Traer J-System")
        if mang: ol.append("- Traer manga")
        if chimen=="Sí": ol.append(f"- Dist. chimenea: {dchim}")

        pdf.tabla_visita("Cliente", [cli_v]); pdf.tabla_visita("Dirección", [dir_v]); pdf.tabla_visita("Tipo fumi.", [t_fum])
        pdf.tabla_visita("Producto", [prod_v]); pdf.tabla_visita("Vol/Tiempo", [f"{vol_v}m3 / {tiemp_v}"])
        pdf.tabla_visita("Análisis seg.", sl); pdf.tabla_visita("Req. cliente", rl if rl else ["- Ninguno"]); pdf.tabla_visita("Operativo", ol)
        if fotos_v: pdf.ln(8); pdf.t_seccion("FOTOS", "REGISTRO FOTOGRÁFICO", force=True); pdf.galeria(fotos_v)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            with open(tmp.name, "rb") as f: st.session_state.pdf_visita = f.read()
        st.rerun()

    if st.session_state.pdf_visita: st.download_button("📥 DESCARGAR VISITA", st.session_state.pdf_visita, file_name=st.session_state.fn_visita, use_container_width=True)

# ==============================================================================
# MÓDULO MOLINOS
# ==============================================================================
elif st.session_state.app_mode == "MOLINOS":
    st.title("🏭 Informe y Certificado Molinos")
    op_m = st.selectbox("Cliente", list(DATABASE_COMBINADA.keys()))
    d_m = DATABASE_COMBINADA[op_m]
    
    cm1, cm2, cm3 = st.columns(3)
    with cm1: cli_m = st.text_input("Razón Social", d_m["cliente"]); pl_m = st.text_input("Planta", op_m)
    with cm2: rut_m = st.text_input("RUT", d_m["rut"]); dir_m = st.text_input("Dirección", d_m["direccion"])
    with cm3: f_inf_m = st.date_input("Fecha", datetime.date.today()); vol_m = st.number_input("Volumen (m³)", value=d_m["volumen"])
    
    ct1, ct2 = st.columns(2)
    with ct1: tt_m = st.radio("Tipo Tratamiento", ["Preventivo", "Curativo"], horizontal=True)
    with ct2: pg_m = st.text_input("Plaga", "Tribolium confusum" if tt_m=="Curativo" else "N/A")
        
    cc1, cc2, cc3 = st.columns(3)
    with cc1: n_cert_m = st.text_input("N° Certificado", "28251")
    with cc2: ing_m = st.selectbox("Fumigante", ["Fosfuro de Aluminio (AIP) 56%", "Fosfuro de Magnesio", "Mixto"])
    with cc3: iref_m = st.text_input("Inf. Ref.", f"2026-{n_cert_m} NP")

    cl1, cl2 = st.columns(2)
    with cl1:
        el_m = st.text_input("Encargado Limpieza", "Jefe de Planta")
        rm_sel = st.selectbox("Rep. Rentokil", LISTA_REPRESENTANTES)
        rep_m = st.text_input("Nombre Manual") if rm_sel=="OTRO" else rm_sel
    with cl2:
        frev_m = st.date_input("Fecha Revisión", datetime.date.today())
        hrev_m = st.time_input("Hora Revisión", datetime.time(10, 0))
    
    obs_b_m = st.checkbox("Agregar observaciones")
    txt_o_m = st.text_area("Hallazgos") if obs_b_m else ""
    fot_s_m = st.file_uploader("Fotos sellado", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    cti1, cti2 = st.columns(2)
    with cti1:
        fi_m = st.date_input("Inicio Inyección", datetime.date.today())
        hi_m = st.time_input("Hora Inicio", datetime.time(19, 0))
    with cti2:
        ft_m = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=3))
        ht_m = st.time_input("Hora Término", datetime.time(19, 0))
    he_m = (datetime.datetime.combine(ft_m, ht_m) - datetime.datetime.combine(fi_m, hi_m)).total_seconds() / 3600

    df_dos_m = st.data_editor(st.session_state.df_d_mol, num_rows="dynamic", use_container_width=True)
    fot_d_m = st.file_uploader("Fotos dosis", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    tot_g_m = (df_dos_m["Bandejas"].apply(clean_number).sum() * 500) + (df_dos_m["Mini-Ropes"].apply(clean_number).sum() * 333)
    dos_f_m = tot_g_m / vol_m if vol_m > 0 else 0

    df_med_m = st.data_editor(st.session_state.df_m_mol, num_rows="dynamic", use_container_width=True)
    fot_m_m = st.file_uploader("Fotos Monitoreo", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    fot_a_m = st.file_uploader("Otras Fotos", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    fir_m = st.file_uploader("Firma RT", type=["png", "jpg", "jpeg", "heic"])

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        st.session_state.fn_informe = f"{f_inf_m.strftime('%d%m%y')}_Informe_Molinos_{clean_filename(cli_m)}.pdf"
        st.session_state.fn_cert = f"{f_inf_m.strftime('%d%m%y')}_Certificado_Molinos_{clean_filename(cli_m)}.pdf"
        
        df_mc = df_med_m.copy()
        df_mc = df_mc[~((df_mc['Fecha'].astype(str).str.lower().isin(['none','nan',''])) | (df_mc['Hora'].astype(str).str.lower().isin(['none','nan',''])))]
        sf_m = procesar_firma(fir_m) if fir_m else ('firma.png' if os.path.exists('firma.png') else None)
        
        pdf = InformePDF(); pdf.add_page()
        pdf.set_font("Arial", "", 11)
        pdf.cell(35, 7, "Cliente:", 0); pdf.cell(0, 7, str(cli_m), 0, ln=1)
        pdf.cell(35, 7, "Planta:", 0); pdf.cell(0, 7, f"{pl_m} - {dir_m}", 0, ln=1)
        pdf.cell(35, 7, "Tratamiento:", 0); pdf.cell(0, 7, f"{tt_m} - Plaga: {pg_m}", 0, ln=1)
        pdf.cell(35, 7, "Fecha:", 0); pdf.cell(0, 7, format_fecha_es(f_inf_m), 0, ln=1)
        
        pdf.t_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, f"Limpieza mecánica realizada.\nSupervisión: {el_m} | Visado RT: {rep_m}.\nFecha: {frev_m} a las {hrev_m} hrs.")
        if obs_b_m and txt_o_m: pdf.set_font("Arial", "B", 11); pdf.set_text_color(200,0,0); pdf.cell(0,7,"HALLAZGOS:",ln=1); pdf.set_text_color(0,0,0); pdf.set_font("Arial", "", 11); pdf.multi_cell(0,6,txt_o_m)
        if fot_s_m: pdf.galeria(fot_s_m)
        
        pdf.t_seccion("II", "VOLÚMENES Y TIEMPOS")
        pdf.multi_cell(0, 6, f"Volumen: {vol_m} m3.\nTiempo expo: {he_m:.1f} hrs.")
        pdf.tabla(["Evento", "Fecha", "Hora", "Horas"], [["Inyección", str(fi_m), str(hi_m), f"{he_m:.1f}"], ["Ventilación", str(ft_m), str(ht_m), "---"]], [45, 45, 45, 55])
        
        pdf.t_seccion("III", "DOSIFICACIÓN") 
        dp = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_dos_m.iterrows()]
        dp.append(["TOTALES", str(int(df_dos_m["Bandejas"].apply(clean_number).sum())), str(int(df_dos_m["Mini-Ropes"].apply(clean_number).sum()))])
        pdf.tabla(["Sector", "Bandejas", "Mini-Ropes"], dp, [80, 55, 55], bold_last=True)
        if fot_d_m: pdf.galeria(fot_d_m)
        pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, f"DOSIS FINAL: {dos_f_m:.2f} g/m3", ln=1, align="R")
        
        pdf.t_seccion("IV", "MONITOREO (PPM)", force=True)
        fig, ax = plt.subplots(figsize=(10, 4)); ex = df_mc["Fecha"].astype(str) + "\n" + df_mc["Hora"].astype(str); hg=False
        for i in range(2, len(df_mc.columns)):
            v = pd.to_numeric(df_mc.iloc[:, i], errors='coerce').fillna(0)
            if v.sum() > 0: ax.plot(ex, v, marker='o', label=df_mc.columns[i]); hg=True
        ax.axhline(300, color='red', linestyle='--'); 
        if hg: ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4, frameon=False)
        plt.tight_layout()
        with tempfile.NamedTemporaryFile(suffix=".png") as tg: fig.savefig(tg.name, dpi=300); pdf.image(tg.name, x=10, w=190)
        pdf.ln(5); clist = list(df_mc.columns); pdf.tabla(clist, [[str(x) for x in r] for _, r in df_mc.iterrows()], [25, 15] + [25]*(len(clist)-2))
        if fot_m_m: pdf.galeria(fot_m_m)
        if fot_a_m: pdf.t_seccion("V", "ANEXO", force=True); pdf.galeria(fot_a_m)
        
        pdf.t_seccion("VI", "CONCLUSIONES", force=True)
        pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, "Servicio CONFORME. Cumple estándares de calidad.")
        if sf_m: 
            if pdf.get_y() > 240: pdf.add_page()
            pdf.image(sf_m, x=75, w=60)

        # Certificado
        fvals = df_mc.iloc[:, 2:].values.flatten()
        ppm_m = pd.to_numeric(pd.Series(fvals), errors='coerce').dropna().mean()
        ppm_m = 0 if pd.isna(ppm_m) else ppm_m

        cert = CertificadoPDF(); cert.add_page(); cert.set_font("Arial", "B", 10)
        cert.cell(0, 6, "Rentokil Initial Chile SpA certifica que ha fumigado lo siguiente:", ln=1)
        cert.t_rojo("I. ANTECEDENTES DEL CLIENTE")
        cert.t_cert(["RAZÓN SOCIAL", "RUT", "DIRECCIÓN"], [[cli_m, rut_m, dir_m]], [70, 30, 90])
        cert.t_rojo("II. APLICACIÓN")
        cert.t_cert(["Área", "Volumen", "Fecha"], [[pl_m, f"{vol_m} m3", f"Ini: {fi_m.strftime('%d-%m-%Y')}\nTer: {ft_m.strftime('%d-%m-%Y')}"]], [50, 30, 110])
        cert.t_cert(["Tiempo", "Fumigante", "Lugar"], [[f"{he_m:.0f} Hrs", ing_m, dir_m]], [30, 60, 100])
        cert.t_cert(["Dosis", "PPM Promedio", "Ref."], [[f"{dos_f_m:.2f} g/m3", f"{ppm_m:.0f} PPM", iref_m]], [50, 70, 70])
        cert.ln(10); cert.set_font("Arial", "", 10)
        cert.multi_cell(0, 6, f"Certificado N° {n_cert_m}, emitido el {format_fecha_es(f_inf_m)}.")
        if sf_m: cert.image(sf_m, x=75, w=60)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as t1, tempfile.NamedTemporaryFile(suffix=".pdf") as t2:
            pdf.output(t1.name); cert.output(t2.name)
            with open(t1.name, "rb") as f1: st.session_state.pdf_informe = f1.read()
            with open(t2.name, "rb") as f2: st.session_state.pdf_cert = f2.read()
        if sf_m and sf_m != 'firma.png' and os.path.exists(sf_m): os.remove(sf_m)
        st.rerun()

    if st.session_state.pdf_informe:
        c_b1, c_b2 = st.columns(2)
        with c_b1: st.download_button("📥 INFORME", st.session_state.pdf_informe, file_name=st.session_state.fn_informe, use_container_width=True)
        with c_b2: st.download_button("📥 CERTIFICADO", st.session_state.pdf_cert, file_name=st.session_state.fn_cert, use_container_width=True)

# ==============================================================================
# MÓDULO ESTRUCTURAS (10 PUNTOS)
# ==============================================================================
elif st.session_state.app_mode == "ESTRUCTURAS":
    st.title("🏗️ Informe y Certificado Estructuras")
    op_e = st.selectbox("Cliente", list(DATABASE_COMBINADA.keys()))
    d_e = DATABASE_COMBINADA[op_e]
    
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1: cli_e = st.text_input("Razón Social", d_e["cliente"]); dir_e = st.text_input("Dirección", d_e["direccion"])
    with col_e2: rut_e = st.text_input("RUT Cliente", d_e["rut"]); fec_e = st.date_input("Fecha Emisión", datetime.date.today())
    with col_e3: tt_e = st.radio("Tipo Tratamiento", ["Preventivo", "Curativo"], horizontal=True); plg_e = st.text_input("Plaga", "Tribolium confusum" if tt_e=="Curativo" else "N/A")

    cc1, cc2, cc3 = st.columns(3)
    with cc1: n_cert_e = st.text_input("N° Certificado", "28252")
    with cc2: ing_e = st.selectbox("Fumigante", ["Fosfuro de Aluminio (AIP) 56%", "Fosfuro de Magnesio", "Mixto"])
    with cc3: iref_e = st.text_input("Informe Ref.", f"2026-{n_cert_e} NP")

    cl1, cl2 = st.columns(2)
    with cl1:
        enc_e = st.text_input("Encargado Limpieza", "Jefe de Turno")
        re_sel = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES)
        rep_e = st.text_input("Nombre Manual") if re_sel=="OTRO" else re_sel
    with cl2:
        frev_e = st.date_input("Fecha Revisión", datetime.date.today())
        hrev_e = st.time_input("Hora Revisión", datetime.time(10, 0))
    
    est_sel = st.multiselect("Estructuras", ["Silos", "Tolvas", "Roscas", "Elevadores", "Pozos", "Ductos", "Pavos", "Celdas"])
    obs_b_e = st.checkbox("Agregar observaciones")
    txt_o_e = st.text_area("Hallazgos") if obs_b_e else ""
    fot_s_e = st.file_uploader("Fotos limpieza", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    df_dos_e = st.data_editor(st.session_state.df_d_est, num_rows="dynamic", use_container_width=True)
    fot_d_e = st.file_uploader("Fotos dosificación", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])

    ct1, ct2 = st.columns(2)
    with ct1: fi_e = st.date_input("Inicio", datetime.date.today()); hi_e = st.time_input("H. Inicio", datetime.time(18, 0))
    with ct2: ft_e = st.date_input("Término", datetime.date.today() + datetime.timedelta(days=4)); ht_e = st.time_input("H. Término", datetime.time(10, 0))
    he_e = (datetime.datetime.combine(ft_e, ht_e) - datetime.datetime.combine(fi_e, hi_e)).total_seconds() / 3600

    st.markdown("**Nombres de Puntos (10 Puntos Max):**")
    cn1, cn2 = st.columns(5), st.columns(5)
    for i in range(5): st.session_state.nom_p[i] = cn1[i].text_input(f"P {i+1}", st.session_state.nom_p[i])
    for i in range(5, 10): st.session_state.nom_p[i] = cn2[i-5].text_input(f"P {i+1}", st.session_state.nom_p[i])
    
    col_c = {"Fecha": "Fecha", "Hora": "Hora"}
    for i in range(10): col_c[f"P{i+1}"] = st.session_state.nom_p[i]
    df_med_e = st.data_editor(st.session_state.df_m_est, column_config=col_c, num_rows="dynamic", use_container_width=True)
    fot_m_e = st.file_uploader("Fotos mediciones", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    fot_a_e = st.file_uploader("Otras fotos", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    fir_e = st.file_uploader("Firma RT", type=["png", "jpg", "jpeg", "heic"])

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        st.session_state.fn_informe = f"{fec_e.strftime('%d%m%y')}_Informe_Est_{clean_filename(cli_e)}.pdf"
        st.session_state.fn_cert = f"{fec_e.strftime('%d%m%y')}_Certificado_Est_{clean_filename(cli_e)}.pdf"
        
        df_me = df_med_e.copy()
        df_me.columns = ["Fecha", "Hora"] + st.session_state.nom_p
        df_me = df_me[~((df_me['Fecha'].astype(str).str.lower().isin(['none','nan',''])) | (df_me['Hora'].astype(str).str.lower().isin(['none','nan',''])))]
        
        c_keep = ["Fecha", "Hora"]
        for i in range(2, 12):
            v = pd.to_numeric(df_me.iloc[:, i], errors='coerce').fillna(0)
            if v.sum() > 0 or df_me.columns[i].strip().lower() != f"punto {i-1}".lower(): c_keep.append(df_me.columns[i])
        df_me = df_me[c_keep]

        sf_e = procesar_firma(fir_e) if fir_e else ('firma.png' if os.path.exists('firma.png') else None)
        
        pdf = InformePDF(); pdf.add_page(); pdf.set_font("Arial", "", 11)
        pdf.cell(35, 7, "Cliente:", 0); pdf.cell(0, 7, str(cli_e), 0, ln=1)
        pdf.cell(35, 7, "Dirección:", 0); pdf.cell(0, 7, str(dir_e), 0, ln=1)
        pdf.cell(35, 7, "Tratamiento:", 0); pdf.cell(0, 7, f"{tt_e} - Plaga: {plg_e}", 0, ln=1)
        
        pdf.t_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
        pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 5, f"Limpieza mecánica realizada. Estructuras: {', '.join(est_sel)}\nSupervisión: {enc_e} | Visado RT: {rep_e}.")
        if obs_b_e and txt_o_e: pdf.set_font("Arial", "B", 11); pdf.set_text_color(200,0,0); pdf.cell(0,7,"HALLAZGOS:",ln=1); pdf.set_text_color(0,0,0); pdf.set_font("Arial", "", 11); pdf.multi_cell(0,6,txt_o_e)
        if fot_s_e: pdf.galeria(fot_s_e)
        
        pdf.t_seccion("II", "VOLUMEN Y DOSIFICACIÓN")
        ddp = []; tg=0; tv=0
        for _, r in df_dos_e.iterrows():
            v=clean_number(r.get("Volumen (m3)",0)); pl=clean_number(r.get("Cant. Placas",0)); ro=clean_number(r.get("Cant. Mini-Ropes",0)); ph=clean_number(r.get("Cant. Phostoxin",0))
            if v>0 or pl>0 or ro>0 or ph>0:
                g=(pl*33)+(ro*333)+(ph*1); dr=g/v if v>0 else 0; tg+=g; tv+=v
                ddp.append([str(r.get("Estructura (Nombre/N°)", "")), f"{v:.1f}", f"{int(pl)}", f"{int(ro)}", f"{int(ph)}", f"{dr:.2f}"])
        ddp.append(["TOTALES", f"{tv:.1f}", "", "", "", ""])
        pdf.tabla(["Estructura", "Vol(m3)", "Plac", "Rope", "Phos", "Dosis g/m3"], ddp, [60, 25, 20, 20, 25, 40], bold_last=True)
        d_prom = tg/tv if tv>0 else 0
        pdf.cell(0, 6, f"Gas Generado: {tg:.1f} g.", ln=1, align="R")
        if fot_d_e: pdf.galeria(fot_d_e)

        pdf.t_seccion("III", "MEDICIONES", force=True)
        pdf.tabla(["Evento", "Fecha", "Hora", "Hrs"], [["Inicio", str(fi_e), str(hi_e), f"{he_e:.1f}"], ["Término", str(ft_e), str(ht_e), "---"]], [45, 45, 45, 55])
        fig, ax = plt.subplots(figsize=(10, 5)); ex = df_me["Fecha"].astype(str) + "\n" + df_me["Hora"].astype(str); hg=False
        for i in range(2, len(df_me.columns)):
            v = pd.to_numeric(df_me.iloc[:, i], errors='coerce').fillna(0)
            if v.sum() > 0: ax.plot(ex, v, marker='o', label=df_me.columns[i]); hg=True
        ax.axhline(300, color='red', linestyle='--'); 
        if hg: ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=5, frameon=False)
        plt.tight_layout()
        with tempfile.NamedTemporaryFile(suffix=".png") as tg_e: fig.savefig(tg_e.name, dpi=300); pdf.image(tg_e.name, x=10, w=190)
        pdf.ln(5); clist = list(df_me.columns); wp = 155/(len(clist)-2) if len(clist)>2 else 0
        pdf.tabla(clist, [[str(x) for x in r] for _, r in df_me.iterrows()], [20, 15] + [wp]*(len(clist)-2))
        
        if fot_m_e: pdf.galeria(fot_m_e)
        if fot_a_e: pdf.t_seccion("IV", "ANEXO", force=True); pdf.galeria(fot_a_e)
        pdf.t_seccion("V", "CONCLUSIONES", force=True)
        pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, "Servicio CONFORME. Cumple estándares técnicos.")
        if sf_e: 
            if pdf.get_y() > 240: pdf.add_page()
            pdf.image(sf_e, x=75, w=60)

        # Certificado
        fvals = df_me.iloc[:, 2:].values.flatten()
        ppm_e = pd.to_numeric(pd.Series(fvals), errors='coerce').dropna().mean()
        ppm_e = 0 if pd.isna(ppm_e) else ppm_e

        cert = CertificadoPDF(); cert.add_page(); cert.set_font("Arial", "B", 10)
        cert.cell(0, 6, "Rentokil Initial Chile SpA certifica que ha fumigado lo siguiente:", ln=1)
        cert.t_rojo("I. ANTECEDENTES DEL CLIENTE")
        cert.t_cert(["RAZÓN SOCIAL", "RUT", "DIRECCIÓN"], [[cli_e, rut_e, dir_e]], [70, 30, 90])
        cert.t_rojo("II. APLICACIÓN")
        ps = ", ".join(est_sel)[:30]+"..." if est_sel else "Estructuras"
        cert.t_cert(["Área", "Volumen", "Fecha"], [[ps, f"{tv:.1f} m3", f"Ini: {fi_e.strftime('%d-%m-%Y')}\nTer: {ft_e.strftime('%d-%m-%Y')}"]], [50, 30, 110])
        cert.t_cert(["Tiempo", "Fumigante", "Lugar"], [[f"{he_e:.0f} Hrs", ing_e, dir_e]], [30, 60, 100])
        cert.t_cert(["Dosis", "PPM Promedio", "Ref."], [[f"{d_prom:.2f} g/m3", f"{ppm_e:.0f} PPM", iref_e]], [50, 70, 70])
        cert.ln(10); cert.set_font("Arial", "", 10); cert.multi_cell(0, 6, f"Certificado N° {n_cert_e}, emitido el {format_fecha_es(fec_e)}.")
        if sf_e: cert.image(sf_e, x=75, w=60)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as t1, tempfile.NamedTemporaryFile(suffix=".pdf") as t2:
            pdf.output(t1.name); cert.output(t2.name)
            with open(t1.name, "rb") as f1: st.session_state.pdf_informe = f1.read()
            with open(t2.name, "rb") as f2: st.session_state.pdf_cert = f2.read()
        if sf_e and sf_e != 'firma.png' and os.path.exists(sf_e): os.remove(sf_e)
        st.rerun()

    if st.session_state.pdf_informe:
        c_b1, c_b2 = st.columns(2)
        with c_b1: st.download_button("📥 INFORME", st.session_state.pdf_informe, file_name=st.session_state.fn_informe, use_container_width=True)
        with c_b2: st.download_button("📥 CERTIFICADO", st.session_state.pdf_cert, file_name=st.session_state.fn_cert, use_container_width=True)

# ==============================================================================
# MÓDULO TRABAJO (FOTOS)
# ==============================================================================
elif st.session_state.app_mode == "TRABAJO":
    st.title("📸 Registro Fotográfico de Trabajo")
    op_d = st.selectbox("Cliente", list(DATABASE_COMBINADA.keys()))
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1: cli_d = st.text_input("Razón Social", DATABASE_COMBINADA[op_d].get("cliente", op_d))
    with col_d2: dir_d = st.text_input("Dirección", DATABASE_COMBINADA[op_d].get("direccion", ""))
    with col_d3: fec_d = st.date_input("Fecha", datetime.date.today())
        
    detalles_d = st.text_area("Detalle de Labores")
    fotos_dialogo = st.file_uploader("Subir fotos", accept_multiple_files=True, type=['png','jpg','jpeg','heic'])
    
    if st.button("🚀 GENERAR INFORME", use_container_width=True, type="primary"):
        if fotos_dialogo:
            try:
                st.session_state.fn_trabajo = f"{fec_d.strftime('%d%m%y')}_Trabajo_{clean_filename(cli_d)}.pdf"
                pdf = InformePDF(); pdf.add_page()
                pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.set_text_color(*COLOR_PRIMARIO)
                pdf.cell(0, 8, "REGISTRO FOTOGRÁFICO DE TRABAJO", ln=1, align="C")
                pdf.set_text_color(0, 0, 0); pdf.ln(5)
                pdf.tabla_moderna(["CLIENTE", "DIRECCIÓN", "FECHA"], [[str(cli_d), str(dir_d), format_fecha_es(fec_d)]], [80, 70, 40], color=COLOR_PRIMARIO)
                
                pdf.set_font("Arial", "B", 9); pdf.set_fill_color(*COLOR_PRIMARIO); pdf.set_text_color(255, 255, 255)
                pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 7, 2, 'F')
                pdf.cell(190, 7, "DETALLE DE LABORES", border=0, align='C', fill=False); pdf.ln()
                pdf.set_font("Arial", "", 9); pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(190, 5, str(detalles_d).strip() if str(detalles_d).strip() else "Sin observaciones.", border='B', align='L')
                pdf.ln(5)
                
                my_bar = st.progress(0, "Procesando imágenes...")
                for i, f in enumerate(fotos_dialogo):
                    tmp_p, w, h = procesar_imagen_full(f)
                    if tmp_p:
                        ratio = w / h
                        if i == 0:
                            avail_h = 260 - pdf.get_y(); mw = 150 
                            fh = avail_h if (mw/ratio) > avail_h else mw/ratio
                            fw = avail_h*ratio if (mw/ratio) > avail_h else mw
                            pdf.image(tmp_p, x=10+(190-fw)/2, y=pdf.get_y(), w=fw, h=fh)
                        else:
                            pdf.add_page()
                            fw, fh = (190, 190/ratio) if (190/ratio) <= 240 else (240*ratio, 240)
                            pdf.image(tmp_p, x=10+(190-fw)/2, y=35+(240-fh)/2, w=fw, h=fh)
                        os.remove(tmp_p)
                    my_bar.progress((i + 1) / len(fotos_dialogo))
                my_bar.empty()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_d:
                    pdf.output(tmp_d.name)
                    with open(tmp_d.name, "rb") as fd: st.session_state.pdf_dialogo = fd.read()
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Sube fotos para continuar.")

    if st.session_state.pdf_dialogo: st.download_button("📥 DESCARGAR INFORME", st.session_state.pdf_dialogo, file_name=st.session_state.fn_trabajo, use_container_width=True)
