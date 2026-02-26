import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os
import tempfile
from PIL import Image, ImageOps
import traceback

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(layout="wide", page_title="Rentokil Mobile PRO")
COLOR_PRIMARIO = (227, 6, 19)
COLOR_TABLA_HEAD = (220, 220, 220)
COLOR_TABLA_FILA = (255, 255, 255)

# --- GESTIÓN DE ESTADO (MEMORIA) ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "HOME"
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None

# --- BASES DE DATOS ---
DATABASE_MOLINOS = {
    "MOLINO CASABLANCA": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Alejandro Galaz N° 500, Casablanca", "volumen": 4850},
    "MOLINO LA ESTAMPA": {"cliente": "MOLINO LA ESTAMPA S.A.", "direccion": "Fermin Vivaceta 1053, Independencia", "volumen": 5500},
    "MOLINO FERRER": {"cliente": "MOLINO FERRER HERMANOS S.A.", "direccion": "Baquedano N° 647, San Bernardo", "volumen": 8127},
    "MOLINO EXPOSICIÓN": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Exposición N° 1657, Estación Central", "volumen": 7502},
    "MOLINO LINDEROS": {"cliente": "MOLINO LINDEROS S.A.", "direccion": "Villaseca Nº 1195, Buin", "volumen": 4800},
    "MOLINO MAIPÚ": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Avenida Pajarito N° 1046, Maipú", "volumen": 4059}
}

DATABASE_ESTRUCTURAS_EXTRA = {
    "MOLINO PUENTE ALTO": "Calle Balmaceda 27, Puente Alto, Santiago RM.",
    "CV TRADING": "Camino Valdivia de Paine S/N, Buin",
    "LDA SPA": "Ruta 5 sur Km 53, N°19200 Paine",
    "TUCAPEL": "Planta Lo Boza - Santiago",
    "EMPRESAS CAROZZI S.A": "Longitudinal sur Km 21, San Bernardo.",
    "AGROCOMMERCE": "Jose Miguel Infante 8745, Renca",
    "OTRO": ""
}

LISTA_REPRESENTANTES = [
    "Nicholas Palma", "Vicente Madariaga", "Sebastián Carrillo", 
    "Stefano Pernigotti", "Herbert Diaz", "Juan Callofa", "Maximiliano Caro"
]

# --- FUNCIONES UTILITARIAS ---
def clean_number(value):
    """Convierte entradas numéricas sucias (con comas o vacíos) a float seguro."""
    if value is None: return 0.0
    if isinstance(value, (int, float)): return float(value)
    if isinstance(value, str):
        val_clean = value.replace(',', '.').strip()
        if val_clean == "": return 0.0
        try: return float(val_clean)
        except ValueError: return 0.0
    return 0.0

def procesar_imagen_estilizada(uploaded_file):
    """Procesamiento robusto de imagen: Arregla rotación, color y tamaño (4:3)"""
    try:
        image = Image.open(uploaded_file)
        # 1. Corregir rotación (EXIF) para fotos de celular
        image = ImageOps.exif_transpose(image)
        # 2. Convertir a RGB (Evita errores con PNG transparentes o modos raros)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        # 3. Ajuste de tamaño y recorte (800x600)
        image_fixed = ImageOps.fit(image, (800, 600), method=Image.Resampling.LANCZOS)
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        image_fixed.save(tmp.name, format='JPEG', quality=90)
        return tmp.name
    except Exception:
        return None

def procesar_firma(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGBA')
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        background.save(tmp.name, format='JPEG', quality=90)
        return tmp.name
    except: return None

class PDF(FPDF):
    def header(self):
        logo_path = 'logo.png'
        if os.path.exists(logo_path):
            try: self.image(logo_path, 10, 8, 33)
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

    def check_page_break(self, needed_height):
        if self.get_y() + needed_height > 250:
            self.add_page()

    def titulo_seccion(self, numero, texto):
        self.check_page_break(20)
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(*COLOR_PRIMARIO)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {numero}. {texto.upper()}", ln=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def tabla_estilizada(self, header, data, col_widths, bold_last_row=False):
        self.check_page_break(20)
        self.set_font("Arial", "B", 7)
        self.set_fill_color(*COLOR_TABLA_HEAD)
        for i, h in enumerate(header):
            self.cell(col_widths[i], 8, h, 1, 0, 'C', True)
        self.ln()
        
        self.set_font("Arial", "", 7)
        for idx, row in enumerate(data):
            if bold_last_row and idx == len(data) - 1:
                self.set_font("Arial", "B", 7)
            else:
                self.set_font("Arial", "", 7)
                
            self.set_fill_color(*COLOR_TABLA_FILA)
            for i, d in enumerate(row):
                self.cell(col_widths[i], 6, str(d), 1, 0, 'C', True)
            self.ln()
            
    def agregar_galeria_fotos(self, lista_fotos, titulo_opcional=None):
        if not lista_fotos: return
        self.check_page_break(50)
        
        if titulo_opcional:
            self.ln(2); self.set_font("Arial", "B", 9); self.cell(0, 6, titulo_opcional, ln=1)
        
        y_start = self.get_y()
        for i, f in enumerate(lista_fotos):
            tmp_path = procesar_imagen_estilizada(f)
            if tmp_path:
                try:
                    if self.get_y() > 220:
                        self.add_page(); self.set_y(20); y_start = 20
                        if i % 2 != 0: y_start = 20 
                    
                    if i % 2 == 0:
                        y_act = self.get_y()
                        self.image(tmp_path, x=10, y=y_act, w=90, h=65)
                    else:
                        self.image(tmp_path, x=110, y=y_act, w=90, h=65)
                        self.ln(70)
                    os.remove(tmp_path)
                except: pass
        if len(lista_fotos) % 2 != 0: self.ln(70)


# ==============================================================================
# PANTALLA DE INICIO (HOME)
# ==============================================================================
if st.session_state.app_mode == "HOME":
    st.write(""); st.write("")
    col_logo1, col_logo2, col_logo3 = st.columns([1,2,1])
    with col_logo2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Seleccione Tipo de Informe</h2>", unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏭 FUMIGACIÓN MOLINOS\n(Clic para iniciar)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "MOLINOS"; st.rerun()
    with c2:
        if st.button("🏗️ FUMIGACIÓN ESTRUCTURAS\n(Clic para iniciar)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "ESTRUCTURAS"; st.rerun()

# ==============================================================================
# LÓGICA 1: MOLINOS
# ==============================================================================
elif st.session_state.app_mode == "MOLINOS":
    with st.sidebar:
        st.image("logo.png", width=120) if os.path.exists("logo.png") else None
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True):
            st.session_state.app_mode = "HOME"; st.rerun()
        st.markdown("---"); st.info("Modo: Molinos")

    st.title("🏭 Informe Molinos (Tradicional)")
    # ... (Código Molinos sin cambios en lógica visual) ...
    st.subheader("I. Datos Generales")
    opcion = st.selectbox("Seleccione Planta", list(DATABASE_MOLINOS.keys()) + ["OTRO"])
    d = DATABASE_MOLINOS.get(opcion, {"cliente": "", "direccion": "", "volumen": 0})
    c1, c2 = st.columns(2)
    with c1:
        cliente = st.text_input("Razón Social", d["cliente"])
        planta = st.text_input("Nombre Planta", opcion)
        volumen_total = st.number_input("Volumen Total (m³)", value=d["volumen"])
    with c2:
        direccion = st.text_input("Dirección", d["direccion"])
        fecha_inf = st.date_input("Fecha Informe", datetime.date.today())
        atencion = st.text_input("Atención", "Jefe de Planta")

    st.subheader("II. Detalles Técnicos")
    c3, c4 = st.columns(2)
    with c3:
        plaga = st.selectbox("Plaga Objetivo", ["Tribolium confusum", "Cryptolestes ferrugineus", "Gnathocerus cornutus", "Ephestia kuehniella", "Psócidos", "OTRA / MANUAL"])
        sellado_ok = st.checkbox("Sellado Conforme", value=True)
    with c4:
        f_ini = st.date_input("Inicio Inyección", datetime.date.today())
        h_ini = st.time_input("Hora Inicio", datetime.time(19, 0))
        f_ter = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=3))
        h_ter = st.time_input("Hora Término", datetime.time(19, 0))
    horas_exp = (datetime.datetime.combine(f_ter, h_ter) - datetime.datetime.combine(f_ini, h_ini)).total_seconds() / 3600

    st.subheader("III. Distribución y Dosis")
    df_dosis = st.data_editor(pd.DataFrame([
        {"Piso": "Subterráneo", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 1", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 2", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 3", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 4", "Bandejas": 8, "Mini-Ropes": 1},
        {"Piso": "Piso 5", "Bandejas": 5, "Mini-Ropes": 0},
    ]), num_rows="dynamic", use_container_width=True)

    st.info("📷 Fotos dosificación (Página 1)")
    fotos_dosis = st.file_uploader("Subir evidencia dosis", accept_multiple_files=True, key="dosis_mol")
    
    total_bandejas = df_dosis["Bandejas"].apply(clean_number).sum()
    total_ropes = df_dosis["Mini-Ropes"].apply(clean_number).sum()
    gramos_totales = (total_bandejas * 500) + (total_ropes * 333)
    dosis_final = gramos_totales / volumen_total if volumen_total > 0 else 0

    st.subheader("IV. Mediciones")
    data_inicial = []
    for i in range(3):
        f_str = (f_ini + datetime.timedelta(days=i)).strftime("%d-%m")
        for h in ["19:00", "00:00", "07:00", "13:00"]:
            data_inicial.append([f_str, h, 300, 310, 320, 305, 300, 290])
    cols_meds = ["Fecha", "Hora", "Subt.", "Piso 1", "Piso 2", "Piso 3", "Piso 4", "Piso 5"]
    df_meds = st.data_editor(pd.DataFrame(data_inicial, columns=cols_meds), num_rows="dynamic", use_container_width=True)
    promedio_ppm = df_meds.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0).values.flatten().mean()

    st.subheader("V. Anexo Fotográfico")
    fotos_anexo = st.file_uploader("Fotos Generales", accept_multiple_files=True, key="anexo_mol")
    st.markdown("---")
    st.subheader("✍️ Firma Supervisor")
    firma_file = st.file_uploader("Subir firma (opcional)", type=["png", "jpg", "jpeg"], key="firma_mol")

    if st.button("🚀 GENERAR INFORME MOLINOS"):
        try:
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(30, 6, "Cliente:", 0); pdf.cell(0, 6, str(cliente), 0, ln=1)
            pdf.cell(30, 6, "Planta:", 0); pdf.cell(0, 6, f"{planta} - {direccion}", 0, ln=1)
            pdf.cell(30, 6, "Atención:", 0); pdf.cell(0, 6, str(atencion), 0, ln=1)
            pdf.cell(30, 6, "Fecha:", 0); pdf.cell(0, 6, str(fecha_inf), 0, ln=1)
            
            pdf.titulo_seccion("I", "SELLADO Y PLAGAS")
            pdf.multi_cell(0, 6, f"Inspección de sellado: {'CONFORME' if sellado_ok else 'OBSERVADO'}. Plaga objetivo: {plaga}.")
            pdf.titulo_seccion("II", "VOLÚMENES Y TIEMPOS")
            pdf.multi_cell(0, 6, f"Volumen tratado: {volumen_total} m3. Tiempo de exposición: {horas_exp:.1f} horas.")
            pdf.ln(2)
            pdf.tabla_estilizada(["Evento", "Fecha", "Hora", "Total Horas"], [["Inyección", str(f_ini), str(h_ini), f"{horas_exp:.1f}"], ["Ventilación", str(f_ter), str(h_ter), "---"]], [45, 45, 45, 45])
            
            pdf.titulo_seccion("III", "DOSIFICACIÓN")
            d_dosis_pdf = [[str(r['Piso']), str(
