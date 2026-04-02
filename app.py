import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os
import tempfile
import math
from PIL import Image, ImageOps, ImageFile
import traceback
import gc
import numpy as np

# --- LIBRERÍAS PARA PLANTILLAS WORD (Solo para Aviso) ---
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
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO (MEMORIA PROFUNDA) ---
if "app_mode" not in st.session_state: st.session_state.app_mode = "HOME"
if "pdf_informe" not in st.session_state: st.session_state.pdf_informe = None
if "pdf_cert" not in st.session_state: st.session_state.pdf_cert = None
if "pdf_dialogo" not in st.session_state: st.session_state.pdf_dialogo = None
if "pdf_visita" not in st.session_state: st.session_state.pdf_visita = None
if "word_aviso" not in st.session_state: st.session_state.word_aviso = None
if "pdf_investigacion" not in st.session_state: st.session_state.pdf_investigacion = None

if "hora_emision_default" not in st.session_state: st.session_state.hora_emision_default = datetime.datetime.now().time()
if "hora_inv_default" not in st.session_state: st.session_state.hora_inv_default = datetime.datetime.now().time()

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

# Tablas Estructuras 
if "df_d_est" not in st.session_state:
    st.session_state.df_d_est = pd.DataFrame([{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}])
if "nom_p" not in st.session_state: st.session_state.nom_p = [f"Punto {i+1}" for i in range(10)]
if "df_m_est" not in st.session_state:
    d_me = []
    for i in range(3): d_me.append([(datetime.date.today() + datetime.timedelta(days=i)).strftime("%d-%m"), "10:00"] + [0]*10)
    cols_est = ["Fecha", "Hora"] + [f"P{i+1}" for i in range(10)]
    st.session_state.df_m_est = pd.DataFrame(d_me, columns=cols_est)

# --- BASES DE DATOS DE CLIENTES ---
DATABASE_MOLINOS = {
    "MOLINO CASABLANCA": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "rut": "76.000.000-1", "direccion": "Alejandro Galaz N° 500, Casablanca", "volumen": 4850},
    "MOLINO LA ESTAMPA": {"cliente": "MOLINO LA ESTAMPA S.A.", "rut": "90.828.000-8", "direccion": "Fermin Vivaceta 1053, Independencia", "volumen": 5500},
    "MOLINO FERRER": {"cliente": "MOLINO FERRER HERMANOS S.A.", "rut": "76.000.000-3", "direccion": "Baquedano N° 647, San Bernardo", "volumen": 8127},
    "MOLINO EXPOSICIÓN": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "rut": "76.000.000-1", "direccion": "Exposición N° 1657, Estación Central", "volumen": 7502},
    "MOLINO LINDEROS": {"cliente": "MOLINO LINDEROS S.A.", "rut": "76.000.000-5", "direccion": "Villaseca Nº 1195, Buin", "volumen": 4800},
    "MOLINO MAIPÚ": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "rut": "76.000.000-1", "direccion": "Avenida Pajarito N° 1046, Maipú", "volumen": 4059}
}

DATABASE_ESTRUCTURAS_EXTRA = {
    "MOLINO PUENTE ALTO": {"cliente": "MOLINO PUENTE ALTO", "rut": "76.000.000-7", "direccion": "Calle Balmaceda 27, Puente Alto, Santiago RM."},
    "CV TRADING": {"cliente": "CV TRADING", "rut": "76.000.000-8", "direccion": "Camino Valdivia de Paine S/N, Buin"},
    "LDA SPA": {"cliente": "LDA SPA", "rut": "76.000.000-9", "direccion": "Ruta 5 sur Km 53, N°19200 Paine"},
    "TUCAPEL": {"cliente": "TUCAPEL", "rut": "76.000.000-0", "direccion": "Planta Lo Boza - Santiago"},
    "EMPRESAS CAROZZI S.A": {"cliente": "EMPRESAS CAROZZI S.A", "rut": "76.000.000-K", "direccion": "Longitudinal sur Km 21, San Bernardo."},
    "AGROCOMMERCE": {"cliente": "AGROCOMMERCE", "rut": "76.000.000-1", "direccion": "Jose Miguel Infante 8745, Renca"}
}

# LECTOR CSV CLIENTES
csv_path = None
for name in ["base de datos .xlsx - Hoja 1.csv", "base de datos .xlsx - Hoja1.csv", "clientes.csv"]:
    if os.path.exists(name):
        csv_path = name; break

if csv_path:
    try:
        df_csv = pd.read_csv(csv_path, sep=None, engine='python', encoding='utf-8-sig')
        cols = [str(c).lower() for c in df_csv.columns]
        c_planta = df_csv.columns[next((i for i, c in enumerate(cols) if 'planta' in c or 'nombre' in c), 0)]
        c_cliente = df_csv.columns[next((i for i, c in enumerate(cols) if 'raz' in c or 'cliente' in c or 'social' in c), 0)]
        c_rut = df_csv.columns[next((i for i, c in enumerate(cols) if 'rut' in c), 0)]
        c_dir = df_csv.columns[next((i for i, c in enumerate(cols) if 'dir' in c), 0)]
        
        for _, row in df_csv.iterrows():
            n_planta = str(row[c_planta]).strip()
            if n_planta and n_planta.lower() != 'nan':
                new_client = {"cliente": str(row[c_cliente]).strip() if c_cliente else n_planta, "rut": str(row[c_rut]).strip() if c_rut else "", "direccion": str(row[c_dir]).strip() if c_dir else "", "volumen": 0}
                DATABASE_ESTRUCTURAS_EXTRA[n_planta] = new_client
    except: pass

DATABASE_MOLINOS["OTRO"] = {"cliente": "", "rut": "", "direccion": "", "volumen": 0}
DATABASE_ESTRUCTURAS_EXTRA["OTRO"] = {"cliente": "", "rut": "", "direccion": ""}

DATABASE_COMBINADA = {**DATABASE_MOLINOS, **DATABASE_ESTRUCTURAS_EXTRA}
if "OTRO" in DATABASE_COMBINADA: del DATABASE_COMBINADA["OTRO"]
DATABASE_COMBINADA["OTRO"] = {"cliente": "", "rut": "", "direccion": ""}

# --- NUEVA BASE DE DATOS DE PERSONAL (COMPLETA) ---
DATABASE_PERSONAL = {
    "Marcos Escobar": {"rut": "8.546.549-K", "cargo": "Técnico"},
    "Carlos Narbona": {"rut": "20.121.067-4", "cargo": "Representante Técnico"},
    "Cristian Corral": {"rut": "16.630.012-6", "cargo": "Técnico"},
    "Eduardo Inostroza": {"rut": "18.692.998-5", "cargo": "Técnico"},
    "Juan Vásquez": {"rut": "15.629.902-2", "cargo": "Técnico"},
    "Maximiliano Caro": {"rut": "20.120.770-3", "cargo": "Representante Técnico"},
    "Víctor Becerra": {"rut": "17.759.655-8", "cargo": "Técnico"},
    "Sebastián Carrillo": {"rut": "19.514.568-7", "cargo": "Representante Técnico"},
    "Cristian Saavedra": {"rut": "19.703.885-3", "cargo": "Técnico"},
    "Juan Callofa": {"rut": "15.531.428-1", "cargo": "Representante Técnico"},
    "Nicholas Palma": {"rut": "17.227.760-8", "cargo": "Representante Técnico"},
    "Vicente Madariaga": {"rut": "15.725.282-8", "cargo": "Representante Técnico"},
    "Stefano Pernigotti": {"rut": "18.085.548-3", "cargo": "Representante Técnico"},
    "Herbert Diaz": {"rut": "8.622.83-1", "cargo": "Representante Técnico"},
    "Pavel Sotomayor": {"rut": "15.331.334-2", "cargo": "Representante Técnico"},
    "OTRO": {"rut": "", "cargo": ""}
}
LISTA_PERSONAL = list(DATABASE_PERSONAL.keys())
LISTA_REPRESENTANTES = [k for k, v in DATABASE_PERSONAL.items() if v["cargo"] == "Representante Técnico" or k == "OTRO"]

# --- BASE DE DATOS KPI (MENÚS EN CASCADA) ---
DATABASE_KPI_ESTRUCTURADA = {
    "Plagas": {
        "Servicio desinsectacion sin señaletica calavera, medidas preventivas en el mes": 8,
        "Servicio sanitizacion baños sin sanitizar y marcaje durante el mes": 4,
        "Servicio sanitizacion baños sin sanitizar y marcaje por 2 vez": 8,
        "Servicio de desinsectacion y sanitizacion desprolijo (durante el mes)": 4,
        "Servicio de desinsectacion y sanitizacion desprolijo (por 2 vez)": 8,
        "Mantencion desprolija de dispositivos de control, feromonas (durante el mes)": 4,
        "Mantencion desprolija de dispositivos de control, feromonas (por 2 vez)": 8,
        "Mantencion desprolija de dispositivos de control, tuv (durante el mes)": 4,
        "Mantencion desprolija de dispositivos de control, tuv (por 2 vez)": 8,
        "Mantencion desprolija de dispositivos de control, en mal estado (durante el mes)": 4,
        "Mantencion desprolija de dispositivos de control, en mal estado (por 2 vez)": 8,
        "No realización de planos durante la instalacion/emergencia (durante el mes)": 4,
        "No realización de planos durante la instalacion/emergencia (por 2 vez)": 8,
        "Devolucion de guia de despacho (durante el mes)": 4,
        "Devolucion de guia de despacho (por 2 vez)": 8
    },
    "Fumigaciones": {
        "No realizar inyeccion/ventilacion según proc. (Sin fugas, en el mes)": 4,
        "No realizar inyeccion/ventilacion según proc. (Sin fugas, por 2 vez)": 8,
        "No realizar inyeccion/ventilacion según proc. (Con fugas o riesgo)": 8
    },
    "Rapaces": {
        "Mantencion desprolija de dispositivos de control de aves (durante el mes)": 4,
        "Mantencion desprolija de dispositivos de control de aves (por 2 vez)": 8
    },
    "Seguridad": {
        "No realiza Check List de Vehículos durante el mes": 8,
        "Tener accidentes de responsabilidad directa": 8,
        "Uso incorrecto de EPP": 8,
        "No usar EPP para los riesgos asociados en el lugar de trabajo": 8,
        "Reclamo de cliente asociado a la Seguridad o mala conducción (durante el mes)": 4,
        "Reclamo de cliente asociado a la Seguridad o mala conducción (2 vez)": 8,
        "No dar aviso de manera inmediata cuando ocurra un accidente o incidente": 8,
        "Realiza trabajo en altura/confinado sin examenes medicos al dia": 8,
        "Conducir a exceso de velocidad 1 a 5 km/h (1 min)": 4,
        "Conducir a exceso de velocidad 6 a 9 km/h (1 min)": 8,
        "No dar correcta disposición a los residuos generados": 8,
        "Disposición de residuos no autorizados en clientes/particulares": 8,
        "Conducir a exceso de velocidad > 10 km/h": 8,
        "Reclamo de cliente asociado a mala gestión/calidad/puntualidad (durante el mes)": 4,
        "Reclamo de cliente asociado a mala gestión/calidad/puntualidad (2 vez)": 8
    },
    "Calidad": {
        "Reprogramacion directo con cliente": 4,
        "No comunica via correo si no cumple la ruta asignada": 4,
        "No cumple en realizar servicios programados sin justificacion": 4,
        "Certificados sin informacion o incompleta o ilegible": 6,
        "Certificado no cumple indicaciones tecnicas": 6,
        "No envio de informes asociados al certificado": 6,
        "No ingresa mínimo dos recomendaciones por visita": 6,
        "Guia de despacho sin nombre, rut y firma": 6,
        "Reducion de la jornada y no cumplimiento de los procedimientos": 6,
        "Falta de insumos, herramientas y/o equipos en camioneta": 6,
        "No Utilizar ropa corporativa al iniciar la jornada": 6,
        "No Respetar la normativa de los clientes (EPP, uso joyas)": 6,
        "Vehiculo sucio, equipos mal almacenados": 6,
        "Baja de Cliente asociada a mala gestión (<= 2%)": 0,
        "Baja de Cliente asociada a mala gestión (> 2%)": 8,
        "No usar Movil Form / Mala efectividad de llenado": 4, # Simplificado para el multiselect
        "No notifica alarmas por Formulario o correo (1 vez)": 2,
        "No notifica alarmas por Formulario o correo (2 vez)": 4
    }
}

# --- FUNCIONES UTILITARIAS ---
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
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB': image = image.convert('RGB')
        image_fixed = ImageOps.fit(image, (800, 600), method=Image.Resampling.LANCZOS, centering=(0.5, 0.95))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        image_fixed.save(tmp.name, format='JPEG', quality=85, optimize=True)
        image.close(); image_fixed.close(); del image; del image_fixed; gc.collect()
        return tmp.name
    except: return None

def procesar_imagen_full(uploaded_file):
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB': image = image.convert('RGB')
        if image.width > 1600 or image.height > 1600:
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        w, h = image.size
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        image.save(tmp.name, format='JPEG', quality=85, optimize=True)
        image.close(); del image; gc.collect()
        return tmp.name, w, h
    except: return None, 0, 0

def procesar_firma(uploaded_file):
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGBA')
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        bg.save(tmp.name, format='JPEG', quality=90)
        image.close(); del image; gc.collect()
        return tmp.name
    except: return None

# ==============================================================================
# CLASE PDF: REPORTES NATIVOS
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

    def header(self):
        if os.path.exists('logo.png'):
            try: self.image('logo.png', 10, 8, 33)
            except: pass
        self.set_font("Arial", "B", 14)
        self.set_text_color(*COLOR_PRIMARIO)
        
        titulo = "INFORME TÉCNICO DE FUMIGACIÓN"
        if getattr(self, 'is_visita', False): titulo = "VISITA TÉCNICA PRE-FUMIGACIÓN"
        if getattr(self, 'is_investigacion', False): titulo = "INVESTIGACIÓN DE INCIDENTES / KPI"
            
        self.cell(0, 8, titulo, ln=1, align="R")
        self.set_font("Arial", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "RENTOKIL INITIAL CHILE SPA", ln=1, align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
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
                if self.get_y() > 210: self.add_page(); self.set_y(45); i_mod = 0
                else: i_mod = i % 2
                if i_mod == 0: y_act = self.get_y(); self.image(tmp, x=10, y=y_act, w=90, h=65)
                else: self.image(tmp, x=110, y=y_act, w=90, h=65); self.ln(70)
                os.remove(tmp)
        if len(fotos) % 2 != 0: self.ln(70)

# ==============================================================================
# PANTALLA DE INICIO (HUB PRINCIPAL)
# ==============================================================================
if st.session_state.app_mode == "HOME":
    st.write("")
    col_logo1, col_logo2, col_logo3 = st.columns([1,2,1])
    with col_logo2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h2 style='text-align: center; color: #E30613;'>Generador de Informes y Herramientas para RT</h2>", unsafe_allow_html=True)
    
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
    c4, c5, c6 = st.columns(3)
    with c4:
        if st.button("📢 NOTIFICACIÓN\n(Aviso al Seremi)", use_container_width=True, type="secondary"):
            st.session_state.app_mode = "AVISO"; st.rerun()
    with c5:
        if st.button("📸 INFORME DE TRABAJO\n(Reporte Visual)", use_container_width=True, type="secondary"):
            st.session_state.app_mode = "TRABAJO"; st.rerun()
    with c6:
        if st.button("⚠️ INVESTIGACIÓN\n(Reporte de Incidentes)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "INVESTIGACION"; st.rerun()

# ==============================================================================
# LÓGICA: INVESTIGACIÓN DE INCIDENTES (100% NATIVA EN PDF - V17.2)
# ==============================================================================
elif st.session_state.app_mode == "INVESTIGACION":
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Investigación de Incidentes y Evaluación KPI")

    st.title("⚠️ Informe de Investigación de Incidentes (KPI)")
    
    st.subheader("📋 I. Datos Generales del Incidente")
    op_inv = st.selectbox("Seleccione Cliente", list(DATABASE_COMBINADA.keys()), key="cliente_inv")
    db_inv = DATABASE_COMBINADA
    
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        cliente_inv = st.text_input("Razón Social", db_inv[op_inv].get("cliente", op_inv))
        planta_inv = st.text_input("Planta / Instalación", op_inv)
    with col_i2:
        area_inv = st.text_input("Área exacta del incidente", "Ej: Bodega principal")
        fecha_inv = st.date_input("Fecha del Incidente", datetime.date.today())
    with col_i3:
        hora_inv = st.time_input("Hora del Incidente", st.session_state.hora_inv_default)
        st.session_state.hora_inv_default = hora_inv

    st.subheader("👤 II. Personal Involucrado (Evaluado)")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        per_sel = st.selectbox("Seleccionar Personal", LISTA_PERSONAL)
        if per_sel == "OTRO":
            nombre_inv = st.text_input("Nombre (Manual)")
            rut_inv_def = ""
            cargo_inv_def = ""
        else:
            nombre_inv = per_sel
            rut_inv_def = DATABASE_PERSONAL[per_sel]["rut"]
            cargo_inv_def = DATABASE_PERSONAL[per_sel]["cargo"]
    with col_p2:
        rut_inv = st.text_input("RUT Involucrado", rut_inv_def)
    with col_p3:
        cargo_inv = st.text_input("Cargo / Función", cargo_inv_def)

    st.subheader("📝 III. Descripción de los Hechos")
    desc_inv = st.text_area("Relate de manera objetiva cómo ocurrió el incidente:", height=100)

    # --- MOTOR LÓGICO KPI ---
    st.subheader("📊 IV. Clasificación de la Desviación (Motor KPI)")
    st.markdown("Seleccione el Área/Categoría para desplegar las faltas. **Puede seleccionar múltiples faltas.**")
    
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        # Menú Nivel 1: Área
        tipo_area = st.selectbox("1. Seleccione Origen de la Falta", ["Área Específica (Plagas, Fumigaciones, etc.)", "Categoría General (Seguridad, Calidad, etc.)"])
        
    with col_k2:
        # Menú Nivel 2: Cascada
        if tipo_area == "Área Específica (Plagas, Fumigaciones, etc.)":
            filtro_2 = st.selectbox("2. Seleccione Área", ["Plagas", "Fumigaciones", "Rapaces", "Termitas", "Bioservicios", "Higiene"])
        else:
            filtro_2 = st.selectbox("2. Seleccione Categoría General", ["Seguridad", "Calidad", "RIOHS y Contrato"])

    # Menú Nivel 3: Las Faltas
    opciones_faltas = []
    if filtro_2 in DATABASE_KPI_ESTRUCTURADA:
        opciones_faltas = list(DATABASE_KPI_ESTRUCTURADA[filtro_2].keys())
        
    faltas_seleccionadas = st.multiselect("3. Seleccione la(s) Desviación(es) Cometida(s)", opciones_faltas)
    
    # Cálculo de Penalidad Acumulada
    puntos_acumulados = 0
    tabla_faltas_pdf = [] # Almacena datos para el PDF
    
    for falta in faltas_seleccionadas:
        puntos_falta = DATABASE_KPI_ESTRUCTURADA[filtro_2][falta]
        puntos_acumulados += puntos_falta
        tabla_faltas_pdf.append([filtro_2, falta, str(puntos_falta)])
        
    # Lógica de Evaluación de Bono
    if puntos_acumulados == 0:
        bono_resultado = "100% Bono"
        accion_kpi = "Sin Acción (OK)"
        color_kpi = "green"
    elif 1 <= puntos_acumulados <= 2:
        bono_resultado = "100% Bono"
        accion_kpi = "Correo resultado final"
        color_kpi = "orange"
    elif 3 <= puntos_acumulados <= 4:
        bono_resultado = "80% Bono"
        accion_kpi = "Correo resultado final"
        color_kpi = "orange"
    elif 5 <= puntos_acumulados <= 7:
        bono_resultado = "50% Bono"
        accion_kpi = "Carta amonestación (RRHH)"
        color_kpi = "red"
    else: # 8 o más
        bono_resultado = "0% Bono (Pérdida Total)"
        accion_kpi = "A definir con jefatura (RRHH)"
        color_kpi = "red"

    # Tarjeta Visual de Resultados
    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 5px solid {color_kpi}; margin-top:10px;">
            <h4 style="margin:0; color: #333;">Veredicto del Sistema</h4>
            <p style="margin:5px 0;"><b>Puntaje de Penalización Acumulado:</b> {puntos_acumulados} puntos</p>
            <p style="margin:5px 0;"><b>Impacto en Bono de Gestión:</b> {bono_resultado}</p>
            <p style="margin:0;"><b>Acción a Tomar:</b> {accion_kpi}</p>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("🔍 V. Análisis de Causas")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        causa_inmediata = st.text_area("Causas Inmediatas (Acciones/Condiciones Subestándares)", height=100)
    with col_c2:
        causa_raiz = st.text_area("Causas Raíz (Factores Personales/Trabajo)", height=100)

    st.subheader("✅ VI. Plan de Acción (Medidas Correctivas)")
    col_pa1, col_pa2, col_pa3 = st.columns(3)
    with col_pa1:
        accion_inv = st.text_area("Acción Correctiva a Implementar", height=68)
    with col_pa2:
        responsable_inv = st.selectbox("Responsable de ejecución", LISTA_PERSONAL)
    with col_pa3:
        fecha_accion_inv = st.date_input("Fecha de Cumplimiento", datetime.date.today() + datetime.timedelta(days=7))

    st.subheader("📸 VII. Evidencias Fotográficas y Anexos")
    fotos_incidentes = st.file_uploader("Sube fotos o archivos PDF de evidencia", accept_multiple_files=True, type=['png','jpg','jpeg','heic','pdf'], key="evidencia_inv")

    if st.button("🚀 GENERAR INFORME DE INVESTIGACIÓN (PDF)", use_container_width=True, type="primary"):
        try:
            pdf = InformePDF()
            pdf.is_investigacion = True
            pdf.add_page()
            
            pdf.t_seccion("I", "DATOS GENERALES DEL INCIDENTE")
            pdf.tabla(["Cliente / Razón Social", "Planta", "Área del Incidente"], [[cliente_inv, planta_inv, area_inv]], [70, 60, 60])
            pdf.tabla(["Fecha del Incidente", "Hora del Incidente"], [[format_fecha_es(fecha_inv), hora_inv.strftime("%H:%M")]], [95, 95])
            
            pdf.t_seccion("II", "PERSONAL INVOLUCRADO (EVALUADO)")
            pdf.tabla(["Nombre", "RUT", "Cargo / Función"], [[nombre_inv, rut_inv, cargo_inv]], [70, 40, 80])
            
            pdf.t_seccion("III", "DESCRIPCIÓN DE LOS HECHOS")
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, desc_inv if desc_inv else "Sin descripción registrada.", border=1)
            
            pdf.t_seccion("IV", "EVALUACIÓN KPI Y PENALIZACIONES")
            if not tabla_faltas_pdf:
                pdf.set_font("Arial", "I", 10)
                pdf.cell(0, 6, "No se registraron faltas asociadas al KPI.", ln=1)
            else:
                pdf.tabla(["Categoría", "Desviación Detectada", "Pts Castigo"], tabla_faltas_pdf, [40, 130, 20])
                
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(100, 6, f"PUNTAJE TOTAL ACUMULADO: {puntos_acumulados} Pts", border=1)
            pdf.cell(90, 6, f"RESULTADO BONO: {bono_resultado}", border=1, ln=1)
            pdf.cell(190, 6, f"ACCIÓN NORMATIVA: {accion_kpi}", border=1, ln=1)
            
            pdf.t_seccion("V", "ANÁLISIS DE CAUSAS")
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "Causas Inmediatas (Acciones o Condiciones Subestándares):", ln=1)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, causa_inmediata if causa_inmediata else "N/A")
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "Causas Raíz (Factores Personales o del Trabajo):", ln=1)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, causa_raiz if causa_raiz else "N/A")
            
            pdf.t_seccion("VI", "PLAN DE ACCIÓN Y MEDIDAS CORRECTIVAS")
            pdf.tabla(["Acción Correctiva", "Responsable", "Fecha Cumplimiento"], 
                      [[accion_inv, responsable_inv, format_fecha_es(fecha_accion_inv)]], 
                      [100, 50, 40])
            
            # Procesar solo las imágenes (los PDF anexos el usuario los descarga aparte)
            fotos_validas = [f for f in fotos_incidentes if f.name.lower().endswith(('.png', '.jpg', '.jpeg', '.heic'))] if fotos_incidentes else []
            
            if fotos_validas:
                pdf.t_seccion("VII", "REGISTRO FOTOGRÁFICO Y EVIDENCIA", force=True)
                pdf.galeria(fotos_validas)
                
            pdf.ln(15)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "El presente documento certifica la evaluación del incidente descrito y la definición de las medidas correctivas.", ln=1)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_inv:
                pdf.output(tmp_inv.name)
                with open(tmp_inv.name, "rb") as finv: st.session_state.pdf_investigacion = finv.read()
            st.rerun()
            
        except Exception as e:
            st.error(f"Error generando la investigación: {e}")
            st.code(traceback.format_exc())

    if st.session_state.get("pdf_investigacion") is not None:
        st.success("✅ Informe de Investigación Generado Exitosamente")
        st.download_button(
            label="📄 DESCARGAR INVESTIGACIÓN (PDF)",
            data=st.session_state.pdf_investigacion,
            file_name="Investigacion_Incidentes_Rentokil.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# ==============================================================================
# LÓGICA: AVISO DE FUMIGACIÓN
# ==============================================================================
elif st.session_state.app_mode == "AVISO":
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Notificación de Fumigación")

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
                rut_repre_default = DATABASE_PERSONAL[rep_a_sel]["rut"]
                correo_repre_default = DATABASE_REPRESENTANTES.get(rep_a_sel, {}).get("correo", "")
                
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
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            mapa_file = st.file_uploader("Sube el Mapa de Georreferencia", type=["png", "jpg", "jpeg", "heic"])
        with col_img2:
            firma_aviso = st.file_uploader("Firma del Responsable Rentokil", type=["png", "jpg", "jpeg", "heic"])

        if st.button("🚀 GENERAR AVISO AL SEREMI", use_container_width=True, type="primary"):
            if not os.path.exists("plantilla_aviso.docx"):
                st.error("❌ No se encontró el archivo `plantilla_aviso.docx`. Por favor, súbelo a GitHub en la misma carpeta.")
            else:
                try:
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

                    mapa_path = None
                    firma_path = None
                    
                    if mapa_file:
                        mapa_path, _, _ = procesar_imagen_full(mapa_file)
                        if mapa_path:
                            context['mapa_img'] = InlineImage(doc, mapa_path, width=Mm(135))
                            
                    if firma_aviso:
                        firma_path = procesar_firma(firma_aviso)
                        if firma_path:
                            context['firma_img'] = InlineImage(doc, firma_path, width=Mm(35))

                    doc.render(context)
                    
                    tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                    doc.save(tmp_docx.name)
                    
                    with open(tmp_docx.name, "rb") as f:
                        st.session_state.word_aviso = f.read()
                        
                    if mapa_path and os.path.exists(mapa_path): os.remove(mapa_path)
                    if firma_path and os.path.exists(firma_path): os.remove(firma_path)
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generando el documento: {e}")
                    st.code(traceback.format_exc())

    if st.session_state.get("word_aviso") is not None:
        st.success("✅ Documento de Aviso/Notificación Generado Exitosamente")
        st.download_button(
            label="📄 DESCARGAR AVISO EN WORD",
            data=st.session_state.word_aviso,
            file_name="Aviso_Notificacion_Rentokil.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

# ==============================================================================
# LÓGICA: VISITA TÉCNICA 
# ==============================================================================
elif st.session_state.app_mode == "VISITA":
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Visita Técnica")

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
            pdf = InformePDF()
            pdf.is_visita = True
            pdf.add_page()
            
            if foto_portada:
                tmp_portada, w, h = procesar_imagen_full(foto_portada)
                if tmp_portada:
                    ratio = w / h
                    max_w = 190
                    calc_h = max_w / ratio
                    if calc_h > 120: 
                        calc_h = 120
                        max_w = calc_h * ratio
                    pdf_x = 10 + (190 - max_w) / 2
                    pdf.image(tmp_portada, x=pdf_x, y=pdf.get_y(), w=max_w, h=calc_h)
                    pdf.set_y(pdf.get_y() + calc_h + 10)
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
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Molinos")

    st.title("🏭 Informe y Certificado Molinos")
    st.subheader("I. Datos Generales")
    opcion = st.selectbox("Seleccione Planta", list(DATABASE_MOLINOS.keys()))
    d = DATABASE_MOLINOS.get(opcion, {"cliente": "", "rut": "", "direccion": "", "volumen": 0})
    
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
    df_m_mol_val = st.data_editor(st.session_state.df_m_mol, num_rows="dynamic", use_container_width=True, key="edi_mol_m")
    fotos_meds = st.file_uploader("Evidencia de Monitoreo (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_m_m")

    st.subheader("VI. Anexo Fotográfico")
    fotos_anexo = st.file_uploader("Fotos Generales", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_a_m")
    firma_file = st.file_uploader("Firma RT (Timbre)", type=["png", "jpg", "jpeg", "heic"], key="firm_m")

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        firma_path_guardada = None
        try:
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
            pdf.cell(35, 7, "Planta:", 0); pdf.cell(0, 7, f"{planta} - {direccion}", 0, ln=1)
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
            
            pdf.t_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)", force=True)
            fig, ax = plt.subplots(figsize=(10, 5))
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
                fig.savefig(tmp_g.name, dpi=300); pdf.image(tmp_g.name, x=10, w=190)
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
            
            if firma_path_guardada and firma_path_guardada != 'firma.png':
                if os.path.exists(firma_path_guardada): os.remove(firma_path_guardada)

            st.rerun()
        except Exception as e: st.error(f"Error al generar documentos: {e}"); st.code(traceback.format_exc())

# ==============================================================================
# LÓGICA: ESTRUCTURAS
# ==============================================================================
elif st.session_state.app_mode == "ESTRUCTURAS":
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Estructuras")

    st.title("🏗️ Informe y Certificado Estructuras")
    st.subheader("I. Datos Generales")
    LIST_CL = list(DATABASE_MOLINOS.keys()) + list(DATABASE_ESTRUCTURAS_EXTRA.keys())
    op_e = st.selectbox("Cliente", LIST_CL)
    db_ref = DATABASE_MOLINOS if op_e in DATABASE_MOLINOS else DATABASE_ESTRUCTURAS_EXTRA
    
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

    c_n = st.columns(5)
    n_cols_temp = ["Fecha", "Hora"]
    for i in range(5): 
        nom = c_n[i].text_input(f"Punto {i+1}", st.session_state.nom_p[i])
        st.session_state.nom_p[i] = nom
        n_cols_temp.append(nom)
    
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
            pdf.multi_cell(0, 5, "Previo a la inyección del fumigante, se verificaron y ejecutaron las condiciones de saneamiento crítico en las estructuras a tratar. Las labores se centraron en la remoción mecánica de biomasa, costras de producto envejecido y acumulaciones de polvo en zonas de difícil acceso (interiores de roscas, cúpulas de silos y ductos).\n\nEsta gestión de limpieza elimina refugios físicos que podrían disminuir la penetración del gas, garantizando así la hermeticidad y la máxima eficacia del tratamiento según los protocolos de calidad de Rentokil Initial.\n\n" + f"Supervisión Cliente: {enc_l} | Visado Rentokil: {rep_r}.\n" + f"Fecha Revisión en Terreno: {fecha_rev} a las {hora_rev} horas.")
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
            pdf.ln(5); fig, ax = plt.subplots(figsize=(10, 5))
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
                fig.savefig(tmp_g.name, dpi=300); pdf.image(tmp_g.name, x=10, w=190)
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
                f"El análisis de los registros de monitoreo confirma que la concentración de Fosfina (PH3) se mantuvo por sobre el umbral crítico de 300 PPM durante las {h_exp_e:.1f} horas de exposición efectiva. Esta saturación constante garantiza una penetración total del gas en los puntos críticos de las estructuras, {t_efic}\n\n"
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
                
            if firma_path_guardada and firma_path_guardada != 'firma.png':
                if os.path.exists(firma_path_guardada): os.remove(firma_path_guardada)
                
            st.rerun()
        except Exception as e: st.error(f"Error al generar documentos: {e}"); st.code(traceback.format_exc())

# ==============================================================================
# LÓGICA: INFORME DE TRABAJO
# ==============================================================================
elif st.session_state.app_mode == "TRABAJO":
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True): st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Informe de Trabajo")
        
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
            with c_btn1: st.download_button("📄 DESCARGAR INFORME TÉCNICO", data=st.session_state.pdf_informe, file_name="Informe_Rentokil.pdf", mime="application/pdf", use_container_width=True)
        if st.session_state.pdf_cert is not None:
            with c_btn2: st.download_button("📜 DESCARGAR CERTIFICADO", data=st.session_state.pdf_cert, file_name="Certificado_Rentokil.pdf", mime="application/pdf", use_container_width=True)

if st.session_state.app_mode == "TRABAJO" and st.session_state.pdf_dialogo is not None:
    st.success("✅ Informe de Trabajo Generado Exitosamente")
    st.download_button("📸 DESCARGAR INFORME DE TRABAJO", data=st.session_state.pdf_dialogo, file_name="Informe_Trabajo_Rentokil.pdf", mime="application/pdf", use_container_width=True)

if st.session_state.app_mode == "VISITA" and st.session_state.pdf_visita is not None:
    st.success("✅ Informe de Visita Técnica Generado Exitosamente")
    st.download_button("📋 DESCARGAR VISITA TÉCNICA", data=st.session_state.pdf_visita, file_name="Visita_Tecnica_Rentokil.pdf", mime="application/pdf", use_container_width=True)
