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
COLOR_CELESTE_CLARO = (0, 160, 224) # Celeste Rentokil moderno
COLOR_TABLA_HEAD = (220, 220, 220)
COLOR_TABLA_FILA = (255, 255, 255)

# --- GESTIÓN DE ESTADO (MEMORIA PROFUNDA) ---
if "app_mode" not in st.session_state: st.session_state.app_mode = "HOME"
if "pdf_informe" not in st.session_state: st.session_state.pdf_informe = None
if "pdf_cert" not in st.session_state: st.session_state.pdf_cert = None

# Memoria Tablas Molinos
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

# Memoria Tablas Estructuras
if "df_d_est" not in st.session_state:
    st.session_state.df_d_est = pd.DataFrame([{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}])
if "nom_p" not in st.session_state: st.session_state.nom_p = ["Punto 1", "Punto 2", "Punto 3", "Punto 4", "Punto 5"]
if "df_m_est" not in st.session_state:
    d_me = []
    for i in range(3): d_me.append([(datetime.date.today() + datetime.timedelta(days=i)).strftime("%d-%m"), "10:00", 0, 0, 0, 0, 0])
    st.session_state.df_m_est = pd.DataFrame(d_me, columns=["Fecha", "Hora"] + st.session_state.nom_p)

# --- BASES DE DATOS ---
DATABASE_MOLINOS = {
    "MOLINO CASABLANCA": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "rut": "76.000.000-1", "direccion": "Alejandro Galaz N° 500, Casablanca", "volumen": 4850},
    "MOLINO LA ESTAMPA": {"cliente": "MOLINO LA ESTAMPA S.A.", "rut": "90.828.000-8", "direccion": "Fermin Vivaceta 1053, Independencia", "volumen": 5500},
    "MOLINO FERRER": {"cliente": "MOLINO FERRER HERMANOS S.A.", "rut": "76.000.000-3", "direccion": "Baquedano N° 647, San Bernardo", "volumen": 8127},
    "MOLINO EXPOSICIÓN": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "rut": "76.000.000-1", "direccion": "Exposición N° 1657, Estación Central", "volumen": 7502},
    "MOLINO LINDEROS": {"cliente": "MOLINO LINDEROS S.A.", "rut": "76.000.000-5", "direccion": "Villaseca Nº 1195, Buin", "volumen": 4800},
    "MOLINO MAIPÚ": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "rut": "76.000.000-1", "direccion": "Avenida Pajarito N° 1046, Maipú", "volumen": 4059}
}

DATABASE_ESTRUCTURAS_EXTRA = {
    "MOLINO PUENTE ALTO": {"rut": "76.000.000-7", "direccion": "Calle Balmaceda 27, Puente Alto, Santiago RM."},
    "CV TRADING": {"rut": "76.000.000-8", "direccion": "Camino Valdivia de Paine S/N, Buin"},
    "LDA SPA": {"rut": "76.000.000-9", "direccion": "Ruta 5 sur Km 53, N°19200 Paine"},
    "TUCAPEL": {"rut": "76.000.000-0", "direccion": "Planta Lo Boza - Santiago"},
    "EMPRESAS CAROZZI S.A": {"rut": "76.000.000-K", "direccion": "Longitudinal sur Km 21, San Bernardo."},
    "AGROCOMMERCE": {"rut": "76.000.000-1", "direccion": "Jose Miguel Infante 8745, Renca"},
    "OTRO": {"rut": "", "direccion": ""}
}

LISTA_REPRESENTANTES = ["Nicholas Palma", "Vicente Madariaga", "Sebastián Carrillo", "Stefano Pernigotti", "Herbert Diaz", "Juan Callofa", "Maximiliano Caro"]

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
        if image.width > 1200:
            ratio = 1200 / float(image.width)
            image = image.resize((1200, int(float(image.height) * float(ratio))), Image.Resampling.LANCZOS)
        image_fixed = ImageOps.fit(image, (800, 600), method=Image.Resampling.LANCZOS)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        image_fixed.save(tmp.name, format='JPEG', quality=85, optimize=True)
        return tmp.name
    except: return None

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
        return tmp.name
    except: return None

# ==============================================================================
# CLASE PDF: INFORME
# ==============================================================================
class InformePDF(FPDF):
    def header(self):
        if os.path.exists('logo.png'):
            try: self.image('logo.png', 10, 8, 33)
            except: pass
        self.set_font("Arial", "B", 14)
        self.set_text_color(*COLOR_PRIMARIO)
        self.cell(0, 8, "INFORME TÉCNICO DE FUMIGACIÓN", ln=1, align="R")
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
        y_start = self.get_y()
        for i, f in enumerate(fotos):
            tmp = procesar_imagen(f)
            if tmp:
                if self.get_y() > 210: self.add_page(); self.set_y(45); y_start = 45; i_mod = 0
                else: i_mod = i % 2
                
                if i_mod == 0: y_act = self.get_y(); self.image(tmp, x=10, y=y_act, w=90, h=65)
                else: self.image(tmp, x=110, y=y_act, w=90, h=65); self.ln(70)
        if len(fotos) % 2 != 0: self.ln(70)

# ==============================================================================
# CLASE PDF: CERTIFICADO (Diseño Moderno)
# ==============================================================================
class CertificadoPDF(FPDF):
    def rounded_rect(self, x, y, w, h, r, style=''):
        """Dibuja un rectángulo con bordes curvos (Diseño Moderno)"""
        k = self.k
        hp = self.h
        op = 'f' if style == 'F' else 'B' if style in ['FD', 'DF'] else 'S'
        MyArc = 4/3 * (math.sqrt(2) - 1)
        self._out(f'{(x+r)*k:.2f} {(hp-y)*k:.2f} m')
        xc, yc = x+w-r, y+r
        self._out(f'{xc*k:.2f} {(hp-y)*k:.2f} l')
        self._out(f'{(xc+r*MyArc)*k:.2f} {(hp-y)*k:.2f} {(x+w)*k:.2f} {(hp-(yc-r*MyArc))*k:.2f} {(x+w)*k:.2f} {(hp-yc)*k:.2f} c')
        xc, yc = x+w-r, y+h-r
        self._out(f'{(x+w)*k:.2f} {(hp-yc)*k:.2f} l')
        self._out(f'{(x+w)*k:.2f} {(hp-(yc+r*MyArc))*k:.2f} {(xc+r*MyArc)*k:.2f} {(hp-(y+h))*k:.2f} {xc*k:.2f} {(hp-(y+h))*k:.2f} c')
        xc, yc = x+r, y+h-r
        self._out(f'{xc*k:.2f} {(hp-(y+h))*k:.2f} l')
        self._out(f'{(xc-r*MyArc)*k:.2f} {(hp-(y+h))*k:.2f} {x*k:.2f} {(hp-(yc+r*MyArc))*k:.2f} {x*k:.2f} {(hp-yc)*k:.2f} c')
        xc, yc = x+r, y+r
        self._out(f'{x*k:.2f} {(hp-yc)*k:.2f} l')
        self._out(f'{x*k:.2f} {(hp-(yc-r*MyArc))*k:.2f} {(xc-r*MyArc)*k:.2f} {(hp-y)*k:.2f} {xc*k:.2f} {(hp-y)*k:.2f} c')
        self._out(op)

    def header(self):
        if os.path.exists('logo.png'):
            try: self.image('logo.png', 10, 8, 33)
            except: pass
        self.set_font("Arial", "B", 10)
        self.set_text_color(100, 100, 100)
        self.set_y(10)
        self.cell(0, 5, "Rentokil Initial Chile SpA | RUT 76.360.903-0", ln=1, align="R")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, "Resolución Seremi de Salud N 372/16 del 20-06-2016", ln=1, align="R")
        self.ln(10)
        self.set_draw_color(*COLOR_CELESTE_CLARO)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "Documento Oficial Rentokil Initial Chile SpA", align="C")

    def t_rojo(self, texto):
        self.ln(3); self.set_font("Arial", "B", 10); self.set_fill_color(*COLOR_PRIMARIO); self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {texto.upper()}", ln=1, fill=True); self.set_text_color(0, 0, 0); self.ln(2)

    def t_cert(self, header, data, widths):
        """Diseño de tabla moderno y redondeado"""
        self.set_font("Arial", "B", 8)
        self.set_fill_color(*COLOR_CELESTE_CLARO)
        self.set_text_color(255, 255, 255)
        
        # Dibuja el fondo del encabezado redondeado
        x_start = self.get_x()
        y_start = self.get_y()
        self.rounded_rect(x_start, y_start, sum(widths), 7, 2, 'F')
        
        # Textos del encabezado
        for i, h in enumerate(header):
            self.cell(widths[i], 7, h, border=0, align='C', fill=False)
        self.ln()
        
        # Textos del cuerpo (Borde limpio inferior)
        self.set_font("Arial", "", 8)
        self.set_text_color(0, 0, 0)
        for row in data:
            for i, d in enumerate(row):
                self.cell(widths[i], 8, str(d), border='B', align='C', fill=False)
            self.ln()
        self.ln(4)

# ==============================================================================
# NAVEGACIÓN
# ==============================================================================
if st.session_state.app_mode == "HOME":
    st.write(""); st.write("")
    col_logo1, col_logo2, col_logo3 = st.columns([1,2,1])
    with col_logo2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Generador Informes y Certificados</h2>", unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏭 MODO MOLINOS\n(Clic para iniciar)", use_container_width=True, type="primary"): st.session_state.app_mode = "MOLINOS"; st.rerun()
    with c2:
        if st.button("🏗️ MODO ESTRUCTURAS\n(Clic para iniciar)", use_container_width=True, type="primary"): st.session_state.app_mode = "ESTRUCTURAS"; st.rerun()

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
    opcion = st.selectbox("Seleccione Planta", list(DATABASE_MOLINOS.keys()) + ["OTRO"])
    d = DATABASE_MOLINOS.get(opcion, {"cliente": "", "rut": "", "direccion": "", "volumen": 0})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        cliente = st.text_input("Razón Social", d["cliente"])
        planta = st.text_input("Nombre Planta", opcion)
    with col2:
        rut_cli = st.text_input("RUT Cliente", d["rut"])
        direccion = st.text_input("Dirección", d["direccion"])
    with col3:
        fecha_inf = st.date_input("Fecha Informe/Emisión", datetime.date.today())
        volumen_total = st.number_input("Volumen Total (m³)", value=d["volumen"])
        
    st.markdown("**Datos para Certificado:**")
    cc1, cc2, cc3 = st.columns(3)
    with cc1: num_cert = st.text_input("N° Certificado", "28251")
    with cc2: ingrediente = st.selectbox("Fumigante a Declarar", ["Fosfuro de Aluminio (AIP) 56%", "Fosfuro de Magnesio", "Mixto"])
    with cc3: inf_ref_mol = st.text_input("Informe Ref.", f"2026-{num_cert} NP")

    st.subheader("II. Detalles Técnicos")
    c3, c4 = st.columns(2)
    with c3:
        tipo_trat = st.radio("Tipo de Tratamiento", ["Preventivo", "Curativo"], horizontal=True, key="tr_m")
        plaga = "N/A"
        if tipo_trat == "Curativo": plaga = st.selectbox("Plaga Objetivo", ["Tribolium confusum", "Cryptolestes ferrugineus", "Gnathocerus cornutus", "Ephestia kuehniella", "Psócidos", "OTRA"])
        sellado_ok = st.checkbox("Sellado Conforme", value=True)
    with c4:
        rep_r = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES)
        f_ini = st.date_input("Inicio Inyección", datetime.date.today(), key="i_m")
        h_ini = st.time_input("Hora Inicio", datetime.time(19, 0), key="h_i_m")
        f_ter = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=3), key="f_m")
        h_ter = st.time_input("Hora Término", datetime.time(19, 0), key="h_t_m")
    horas_exp = (datetime.datetime.combine(f_ter, h_ter) - datetime.datetime.combine(f_ini, h_ini)).total_seconds() / 3600
    
    # NUEVO UPLOADER MOLINOS ITEM 1
    st.markdown("**📷 Evidencia de Limpieza / Sellado**")
    fotos_sellado_mol = st.file_uploader("Subir fotos sellado (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="fs_mol")

    st.subheader("III. Distribución y Dosis")
    st.session_state.df_d_mol = st.data_editor(st.session_state.df_d_mol, num_rows="dynamic", use_container_width=True)
    fotos_dosis = st.file_uploader("Evidencia dosis (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_d_m")
    
    total_g = (st.session_state.df_d_mol["Bandejas"].apply(clean_number).sum() * 500) + (st.session_state.df_d_mol["Mini-Ropes"].apply(clean_number).sum() * 333)
    dosis_final = total_g / volumen_total if volumen_total > 0 else 0

    st.subheader("IV. Mediciones")
    st.session_state.df_m_mol = st.data_editor(st.session_state.df_m_mol, num_rows="dynamic", use_container_width=True)
    fotos_meds = st.file_uploader("Evidencia de Monitoreo (Opcional)", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_m_m")
    promedio_ppm = st.session_state.df_m_mol.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0).values.flatten().mean()

    st.subheader("V. Anexo Fotográfico")
    fotos_anexo = st.file_uploader("Fotos Generales", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="f_a_m")
    firma_file = st.file_uploader("Firma RT (Aparece al final de los docs)", type=["png", "jpg", "jpeg", "heic"], key="firm_m")

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        df_d_val = st.session_state.df_d_mol
        df_m_val = st.session_state.df_m_mol

        try:
            # 1. INFORME MOLINOS
            pdf = InformePDF()
            pdf.add_page()
            pdf.set_font("Arial", "", 11)
            pdf.cell(35, 7, "Cliente:", 0); pdf.cell(0, 7, str(cliente), 0, ln=1)
            pdf.cell(35, 7, "Planta:", 0); pdf.cell(0, 7, f"{planta} - {direccion}", 0, ln=1)
            pdf.cell(35, 7, "Tratamiento:", 0); pdf.cell(0, 7, f"{tipo_trat} - Plaga: {plaga}", 0, ln=1)
            pdf.cell(35, 7, "Fecha:", 0); pdf.cell(0, 7, format_fecha_es(fecha_inf), 0, ln=1)
            
            pdf.t_seccion("I", "SELLADO Y PLAGAS")
            pdf.set_font("Arial", "", 10)
            status_sellado = 'CONFORME' if sellado_ok else 'OBSERVADO'
            pdf.multi_cell(0, 6, f"Inspección de sellado en planta: {status_sellado}.\nSupervisión Cliente: Jefe de Planta | Visado Rentokil: {rep_r}.")
            if fotos_sellado_mol: pdf.galeria(fotos_sellado_mol, "Evidencia de Sellado:")
            
            # Item 2 y 3 juntos (sin force=True en el 3)
            pdf.t_seccion("II", "VOLÚMENES Y TIEMPOS")
            pdf.multi_cell(0, 6, f"Volumen total tratado: {volumen_total} m3.\nTiempo de exposición efectivo: {horas_exp:.1f} horas.")
            pdf.ln(2)
            pdf.tabla(["Evento", "Fecha", "Hora", "Total Horas"], [["Inyección", str(f_ini), str(h_ini), f"{horas_exp:.1f}"], ["Ventilación", str(f_ter), str(h_ter), "---"]], [45, 45, 45, 45])
            
            pdf.t_seccion("III", "DOSIFICACIÓN") # SIN SALTO FORZADO
            d_p = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_d_val.iterrows()]
            d_p.append(["TOTALES", str(int(df_d_val["Bandejas"].apply(clean_number).sum())), str(int(df_d_val["Mini-Ropes"].apply(clean_number).sum()))])
            pdf.tabla(["Sector", "Bandejas", "Mini-Ropes"], d_p, [80, 50, 50], bold_last=True)
            
            if fotos_dosis: pdf.galeria(fotos_dosis, "Evidencia de Dosificación:")
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, f"DOSIS FINAL: {dosis_final:.2f} g/m3", ln=1, align="R")
            
            pdf.t_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)", force=True)
            fig, ax = plt.subplots(figsize=(10, 5))
            e_x = df_m_val["Fecha"].astype(str) + "\n" + df_m_val["Hora"].astype(str)
            for col in df_m_val.columns[2:]: ax.plot(e_x, pd.to_numeric(df_m_val[col], errors='coerce'), marker='o', label=col)
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4, frameon=False); plt.tight_layout()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                fig.savefig(tmp_g.name, dpi=300); pdf.image(tmp_g.name, x=10, w=190)
            pdf.ln(5); pdf.tabla(list(df_m_val.columns), [[str(x) for x in r] for _, r in df_m_val.iterrows()], [25, 20, 20, 20, 20, 20, 20, 20])
            
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
            
            firma_path = procesar_firma(firma_file) if firma_file else ('firma.png' if os.path.exists('firma.png') else None)
            if firma_path:
                if pdf.get_y() > 240: pdf.add_page()
                pdf.image(firma_path, x=75, w=60)

            # 2. CERTIFICADO MOLINOS
            cert = CertificadoPDF()
            cert.add_page()
            cert.set_font("Arial", "B", 10)
            cert.cell(0, 6, "El profesional que suscribe certifica que Rentokil Initial Chile SpA, ha procedido a fumigar lo siguiente:", ln=1)
            cert.t_rojo("I. ANTECEDENTES DE LA EMPRESA MANDANTE")
            cert.t_cert(["RAZÓN SOCIAL", "RUT", "DIRECCIÓN"], [[cliente, rut_cli, direccion]], [60, 40, 90])
            
            cert.t_rojo("II. ANTECEDENTES SOBRE LA APLICACIÓN")
            cert.t_cert(["Área Tratada", "Volumen (m3)", "Fecha y Hora Fumigación / Ventilación"], [[planta, f"{volumen_total} m3", f"Inicio: {f_ini.strftime('%d-%m-%Y')} - {h_ini} Hrs\nTérmino: {f_ter.strftime('%d-%m-%Y')} - {h_ter} Hrs"]], [50, 30, 110])
            
            # Tabla reducida para certificado moderno
            cert.t_cert(["Tiempo Exp.", "Fumigante Usado", "Lugar Fumigación"], [[f"{horas_exp:.0f} Horas", ingrediente, direccion]], [40, 60, 90])
            cert.t_cert(["Dosis (g/m3)", "Concentración Promedio", "Informe Ref."], [[f"{dosis_final:.2f}", f"{promedio_ppm:.0f} PPM", inf_ref_mol]], [63, 63, 64])
            
            cert.ln(10); cert.set_font("Arial", "", 10)
            cert.multi_cell(0, 6, f"Se extiende el presente certificado N° {num_cert}, con fecha {format_fecha_es(fecha_inf)}, al interesado para los efectos que estime conveniente.")
            cert.ln(20)
            if firma_path:
                if cert.get_y() > 240: cert.add_page()
                cert.image(firma_path, x=75, w=60)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1, tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
                pdf.output(t1.name); cert.output(t2.name)
                with open(t1.name, "rb") as f1: st.session_state.pdf_informe = f1.read()
                with open(t2.name, "rb") as f2: st.session_state.pdf_cert = f2.read()
            st.rerun()
        except Exception as e: st.error(f"Error al generar documentos: {e}"); st.code(traceback.format_exc())

# --- ESTRUCTURAS ---
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
        cliente_e = st.text_input("Nombre Cliente", op_e)
        direccion_e = st.text_input("Dirección", db_ref[op_e]["direccion"])
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
    with cc3: inf_ref_est = st.text_input("Informe Ref.", f"2026-{num_cert} NP")

    st.subheader("II. Plan de Sellado y Limpieza")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        enc_l = st.text_input("Encargado Limpieza", "Jefe de Turno")
        rep_r = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES)
    with col_l2:
        fecha_rev = st.date_input("Fecha Revisión", datetime.date.today())
        hora_rev = st.time_input("Hora Revisión", datetime.time(10, 0))
    est_sel = st.multiselect("Estructuras a tratar", ["Silos", "Tolvas", "Roscas", "Elevadores", "Pozos", "Ductos Descarga", "Ductos Carga", "Pavos", "Ductos Aspiración", "Celdas"])
    
    hay_obs = st.checkbox("⚠️ ¿Agregar observaciones de limpieza?")
    txt_obs = st.text_area("Hallazgos:", height=80) if hay_obs else ""
    fotos_l = st.file_uploader("Fotos sellado/limpieza", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="fl")

    st.subheader("III. Volumen y Dosis")
    st.session_state.df_d_est = st.data_editor(st.session_state.df_d_est, num_rows="dynamic", use_container_width=True)
    fotos_d = st.file_uploader("Fotos dosificación", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="fd")

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
    for i in range(5): st.session_state.nom_p[i] = c_n[i].text_input(f"Punto {i+1}", st.session_state.nom_p[i], key=f"np_{i}")
    
    c_cols = list(st.session_state.df_m_est.columns)
    n_cols = ["Fecha", "Hora"] + st.session_state.nom_p
    if c_cols != n_cols: st.session_state.df_m_est.columns = n_cols
    
    st.session_state.df_m_est = st.data_editor(st.session_state.df_m_est, num_rows="dynamic", use_container_width=True)
    fotos_m = st.file_uploader("Fotos mediciones", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="fm")

    st.subheader("V. Anexo Fotográfico")
    fotos_a = st.file_uploader("Otras fotos", accept_multiple_files=True, type=['png','jpg','jpeg','heic'], key="fa")
    firma_e = st.file_uploader("Firma RT (Aparece al final de los docs)", type=["png", "jpg", "jpeg", "heic"], key="fe")

    if st.button("🚀 GENERAR INFORME Y CERTIFICADO", use_container_width=True, type="primary"):
        df_est_val = st.session_state.df_d_est
        df_m_val = st.session_state.df_m_est

        try:
            # 1. INFORME ESTRUCTURAS
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
            
            # Sin salto forzado para Item II
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
            pdf.tabla(["Estructura", "Vol(m3)", "Plac", "Rope", "Phos", "Dosis g/m3"], d_d_pdf, [55, 25, 20, 20, 20, 30], bold_last=True)
            pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Total Gas Generado: {t_g:.1f} gramos.", ln=1, align="R")
            dosis_promedio = t_g / t_v if t_v > 0 else 0
            
            if fotos_d: pdf.galeria(fotos_d, "Evidencia de Dosificación:")

            pdf.t_seccion("III", "TIEMPOS Y MEDICIONES", force=True)
            pdf.tabla(["Evento", "Fecha", "Hora", "Total Horas"], [["Inicio", str(f_ini_e), str(h_ini_e), f"{h_exp_e:.1f}"], ["Término", str(f_ter_e), str(h_ter_e), "---"]], [45, 45, 45, 45])
            pdf.ln(5); fig, ax = plt.subplots(figsize=(10, 5))
            e_x = df_m_val["Fecha"].astype(str) + "\n" + df_m_val["Hora"].astype(str)
            h_g = False
            for col in df_m_val.columns[2:]:
                val = pd.to_numeric(df_m_val[col], errors='coerce').fillna(0)
                if val.sum() > 0: ax.plot(e_x, val, marker='o', label=col); h_g = True
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
            if h_g: ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=5, frameon=False)
            plt.tight_layout()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                fig.savefig(tmp_g.name, dpi=300); pdf.image(tmp_g.name, x=10, w=190)
            pdf.ln(5); pdf.tabla([str(c) for c in df_m_val.columns], [[str(x) for x in r] for _, r in df_m_val.iterrows()], [25, 20, 25, 25, 25, 25, 25])
            
            if fotos_m: pdf.galeria(fotos_m, "Evidencia de Monitoreo:")
            promedio_ppm = df_m_val.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0).values.flatten().mean()
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

            firma_path = procesar_firma(firma_e) if firma_e else ('firma.png' if os.path.exists('firma.png') else None)
            if firma_path:
                if pdf.get_y() > 240: pdf.add_page()
                pdf.image(firma_path, x=75, w=60)

            # 2. CERTIFICADO ESTRUCTURAS
            cert = CertificadoPDF()
            cert.add_page()
            cert.set_font("Arial", "B", 10)
            cert.cell(0, 6, "El profesional que suscribe certifica que Rentokil Initial Chile SpA, ha procedido a fumigar lo siguiente:", ln=1)
            cert.t_rojo("I. ANTECEDENTES DE LA EMPRESA MANDANTE")
            cert.t_cert(["RAZÓN SOCIAL", "RUT", "DIRECCIÓN"], [[cliente_e, rut_cli_e, direccion_e]], [60, 40, 90])
            
            cert.t_rojo("II. ANTECEDENTES SOBRE LA APLICACIÓN")
            p_limpio = p_sel[:30]+"..." if len(p_sel)>30 else p_sel
            cert.t_cert(["Área Tratada", "Volumen (m3)", "Fecha y Hora Fumigación / Ventilación"], [[p_limpio, f"{t_v:.1f} m3", f"Inicio: {f_ini_e.strftime('%d-%m-%Y')} - {h_ini_e} Hrs\nTérmino: {f_ter_e.strftime('%d-%m-%Y')} - {h_ter_e} Hrs"]], [50, 30, 110])
            
            cert.t_cert(["Tiempo Exp.", "Fumigante Usado", "Lugar Fumigación"], [[f"{h_exp_e:.0f} Horas", ingrediente, direccion_e]], [40, 60, 90])
            cert.t_cert(["Dosis (g/m3)", "Concentración Promedio", "Informe Ref."], [[f"{dosis_promedio:.2f}", f"{promedio_ppm:.0f} PPM", inf_ref_est]], [63, 63, 64])
            
            cert.ln(10); cert.set_font("Arial", "", 10)
            cert.multi_cell(0, 6, f"Se extiende el presente certificado N° {num_cert}, con fecha {format_fecha_es(fecha_e)}, al interesado para los efectos que estime conveniente.")
            cert.ln(20)
            if firma_path:
                if cert.get_y() > 240: cert.add_page()
                cert.image(firma_path, x=75, w=60)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1, tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
                pdf.output(t1.name); cert.output(t2.name)
                with open(t1.name, "rb") as f1: st.session_state.pdf_informe = f1.read()
                with open(t2.name, "rb") as f2: st.session_state.pdf_cert = f2.read()
            st.rerun()
        except Exception as e: st.error(f"Error al generar documentos: {e}"); st.code(traceback.format_exc())

# ==============================================================================
# BOTONES DE DESCARGA GLOBALES
# ==============================================================================
if st.session_state.pdf_informe is not None or st.session_state.pdf_cert is not None:
    st.success("✅ Documentos Generados Exitosamente")
    c_btn1, c_btn2 = st.columns(2)
    if st.session_state.pdf_informe is not None:
        with c_btn1: st.download_button("📄 DESCARGAR INFORME TÉCNICO", data=st.session_state.pdf_informe, file_name="Informe_Rentokil.pdf", mime="application/pdf", use_container_width=True)
    if st.session_state.pdf_cert is not None:
        with c_btn2: st.download_button("📜 DESCARGAR CERTIFICADO", data=st.session_state.pdf_cert, file_name="Certificado_Rentokil.pdf", mime="application/pdf", use_container_width=True)
