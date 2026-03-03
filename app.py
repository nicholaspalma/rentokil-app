import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os
import tempfile
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
COLOR_TABLA_HEAD = (220, 220, 220)
COLOR_TABLA_FILA = (255, 255, 255)

# --- GESTIÓN DE ESTADO ---
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

# --- FUNCIONES ---
def format_fecha_es(fecha):
    """Convierte un objeto date a string en español: 02 de Marzo de 2026"""
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    return f"{fecha.day:02d} de {meses[fecha.month]} de {fecha.year}"

def clean_number(value):
    if value is None: return 0.0
    if isinstance(value, (int, float)): return float(value)
    if isinstance(value, str):
        val_clean = value.replace(',', '.').strip()
        if val_clean == "": return 0.0
        try: return float(val_clean)
        except ValueError: return 0.0
    return 0.0

def procesar_imagen_estilizada(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        if image.width > 1200:
            ratio = 1200 / float(image.width)
            new_height = int((float(image.height) * float(ratio)))
            image = image.resize((1200, new_height), Image.Resampling.LANCZOS)
        image_fixed = ImageOps.fit(image, (800, 600), method=Image.Resampling.LANCZOS)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        image_fixed.save(tmp.name, format='JPEG', quality=85, optimize=True)
        image.close()
        del image
        gc.collect()
        return tmp.name
    except Exception: return None

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

    def titulo_seccion(self, numero, texto, force_page=False):
        if force_page:
            self.add_page()
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(*COLOR_PRIMARIO)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {numero}. {texto.upper()}", ln=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def tabla_estilizada(self, header, data, col_widths, bold_last_row=False):
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
        if titulo_opcional:
            self.ln(2)
            self.set_font("Arial", "B", 9)
            self.cell(0, 6, titulo_opcional, ln=1)
        for i, f in enumerate(lista_fotos):
            tmp_path = procesar_imagen_estilizada(f)
            if tmp_path:
                try:
                    if self.get_y() > 210:
                        self.add_page()
                        self.set_y(45)
                    if i % 2 == 0:
                        y_act = self.get_y()
                        self.image(tmp_path, x=10, y=y_act, w=90, h=65)
                    else:
                        self.image(tmp_path, x=110, y=y_act, w=90, h=65)
                        self.ln(70)
                    os.remove(tmp_path)
                except: pass
        if len(lista_fotos) % 2 != 0: self.ln(70)

# --- HOME ---
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

# --- MOLINOS ---
elif st.session_state.app_mode == "MOLINOS":
    with st.sidebar:
        st.image("logo.png", width=120) if os.path.exists("logo.png") else None
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True):
            st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Molinos")

    st.title("🏭 Informe Molinos")
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
    fotos_dosis = st.file_uploader("Evidencia dosis", accept_multiple_files=True, key="d_mol")
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
    fotos_anexo = st.file_uploader("Fotos Generales", accept_multiple_files=True, key="a_mol")
    firma_file = st.file_uploader("Firma Supervisor", type=["png", "jpg", "jpeg"], key="f_mol")

    if st.button("🚀 GENERAR INFORME MOLINOS"):
        try:
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", "", 10)
            pdf.cell(30, 6, "Cliente:", 0); pdf.cell(0, 6, str(cliente), 0, ln=1)
            pdf.cell(30, 6, "Planta:", 0); pdf.cell(0, 6, f"{planta} - {direccion}", 0, ln=1)
            pdf.cell(30, 6, "Atención:", 0); pdf.cell(0, 6, str(atencion), 0, ln=1)
            pdf.cell(30, 6, "Fecha:", 0); pdf.cell(0, 6, format_fecha_es(fecha_inf), 0, ln=1)
            
            pdf.titulo_seccion("I", "SELLADO Y PLAGAS")
            pdf.multi_cell(0, 6, f"Inspección de sellado: {'CONFORME' if sellado_ok else 'OBSERVADO'}. Plaga objetivo: {plaga}.")
            pdf.titulo_seccion("II", "VOLÚMENES Y TIEMPOS")
            pdf.multi_cell(0, 6, f"Volumen tratado: {volumen_total} m3. Tiempo de exposición: {horas_exp:.1f} horas.")
            pdf.ln(2)
            pdf.tabla_estilizada(["Evento", "Fecha", "Hora", "Total Horas"], [["Inyección", str(f_ini), str(h_ini), f"{horas_exp:.1f}"], ["Ventilación", str(f_ter), str(h_ter), "---"]], [45, 45, 45, 45])
            
            pdf.titulo_seccion("III", "DOSIFICACIÓN")
            d_dosis_pdf = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_dosis.iterrows()]
            d_dosis_pdf.append(["TOTALES", str(int(total_bandejas)), str(int(total_ropes))])
            pdf.tabla_estilizada(["Sector", "Bandejas", "Mini-Ropes"], d_dosis_pdf, [80, 50, 50], bold_last_row=True)
            if fotos_dosis:
                pdf.ln(2); y_start = pdf.get_y()
                for i, f in enumerate(fotos_dosis[:2]):
                    tmp_p = procesar_imagen_estilizada(f)
                    if tmp_p:
                        x_pos = 10 if i == 0 else 105
                        pdf.image(tmp_p, x=x_pos, y=y_start, w=85, h=60); os.remove(tmp_p)
                pdf.ln(65)
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, f"DOSIS FINAL: {dosis_final:.2f} g/m3", ln=1, align="R")
            
            pdf.add_page(); pdf.titulo_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)")
            fig, ax = plt.subplots(figsize=(10, 5))
            e_x = df_meds["Fecha"].astype(str) + "\n" + df_meds["Hora"].astype(str)
            for col in df_meds.columns[2:]: ax.plot(e_x, pd.to_numeric(df_meds[col], errors='coerce'), marker='o', label=col)
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal'); ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4, frameon=False)
            plt.xticks(rotation=45); plt.tight_layout()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                fig.savefig(tmp_g.name, dpi=300); pdf.image(tmp_g.name, x=10, w=190)
            pdf.ln(5); pdf.tabla_estilizada(["Fech", "Hr", "S", "P1", "P2", "P3", "P4", "P5"], [[str(x) for x in r] for _, r in df_meds.iterrows()], [25, 20, 20, 20, 20, 20, 20, 20])
            
            if fotos_anexo: pdf.add_page(); pdf.titulo_seccion("V", "ANEXO FOTOGRÁFICO"); pdf.agregar_galeria_fotos(fotos_anexo)
            pdf.add_page(); pdf.titulo_seccion("VI", "CONCLUSIONES TÉCNICAS")
            pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, "Servicio declarado CONFORME cumpliendo estándares Rentokil Initial Chile."); pdf.ln(20)
            
            r_f = None
            if firma_file: r_f = procesar_firma(firma_file)
            elif os.path.exists('firma.png'): r_f = 'firma.png'
            if r_f:
                pdf.image(r_f, x=75, w=60)
                if firma_file and r_f != 'firma.png': os.remove(r_f)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_p:
                pdf.output(tmp_p.name)
                with open(tmp_p.name, "rb") as f: st.session_state.pdf_data = f.read()
            st.rerun()
        except Exception as e: st.error(f"Error: {e}"); st.code(traceback.format_exc())

# --- ESTRUCTURAS ---
elif st.session_state.app_mode == "ESTRUCTURAS":
    with st.sidebar:
        st.image("logo.png", width=120) if os.path.exists("logo.png") else None
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True):
            st.session_state.app_mode = "HOME"; st.rerun()
        st.info("Modo: Estructuras")

    st.title("🏗️ Informe Estructuras")
    st.subheader("I. Datos Generales")
    LIST_CL = list(DATABASE_MOLINOS.keys()) + list(DATABASE_ESTRUCTURAS_EXTRA.keys())
    op_e = st.selectbox("Cliente", LIST_CL)
    dir_e = DATABASE_MOLINOS[op_e]["direccion"] if op_e in DATABASE_MOLINOS else DATABASE_ESTRUCTURAS_EXTRA[op_e]
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        cliente_e = st.text_input("Nombre Cliente", op_e)
        direccion_e = st.text_input("Dirección", dir_e)
        tipo_trat = st.radio("Tipo de Tratamiento", ["Preventivo", "Curativo"], horizontal=True)
    with col_e2:
        fecha_e = st.date_input("Fecha Informe", datetime.date.today())
        plaga_e = "N/A"
        if tipo_trat == "Curativo": plaga_e = st.text_input("Plaga Objetivo", "Tribolium confusum")

    st.subheader("II. Plan de Sellado y Limpieza")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        enc_l = st.text_input("Encargado Limpieza", "Jefe de Turno")
        rep_r = st.selectbox("Representante Rentokil", LISTA_REPRESENTANTES)
    with col_l2:
        fecha_rev = st.date_input("Fecha Revisión", datetime.date.today())
        hora_rev = st.time_input("Hora Revisión", datetime.time(10, 0))
    est_sel = st.multiselect("Estructuras", ["Silos", "Tolvas", "Roscas", "Elevadores", "Pozos", "Ductos Descarga", "Ductos Carga", "Pavos", "Ductos Aspiración", "Celdas"])
    
    hay_obs = st.checkbox("⚠️ ¿Agregar observaciones de limpieza?")
    txt_obs = st.text_area("Hallazgos:", height=80) if hay_obs else ""
    fotos_l = st.file_uploader("Fotos sellado/limpieza", accept_multiple_files=True, key="f_l")

    st.subheader("III. Volumen y Dosis")
    df_est = st.data_editor(pd.DataFrame([{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}]), num_rows="dynamic", use_container_width=True)
    fotos_d = st.file_uploader("Fotos dosificación", accept_multiple_files=True, key="f_d")

    st.subheader("IV. Tiempos y Mediciones")
    col_t1, col_t2 = st.columns(2)
    with col_t1: f_ini_e = st.date_input("Inicio", datetime.date.today()); h_ini_e = st.time_input("Hora Inicio", datetime.time(18, 0))
    with col_t2: f_ter_e = st.date_input("Término", datetime.date.today() + datetime.timedelta(days=4)); h_ter_e = st.time_input("Hora Término", datetime.time(10, 0))
    h_exp_e = (datetime.datetime.combine(f_ter_e, h_ter_e) - datetime.datetime.combine(f_ini_e, h_ini_e)).total_seconds() / 3600

    c_n = st.columns(5); nom_p = []
    for i in range(5): nom_p.append(c_n[i].text_input(f"Nombre Punto {i+1}", f"Punto {i+1}", key=f"np_{i}"))
    
    data_med_est = []
    for i in range(3): data_med_est.append([(f_ini_e + datetime.timedelta(days=i)).strftime("%d-%m"), "10:00", 0, 0, 0, 0, 0])
    df_med_est = st.data_editor(pd.DataFrame(data_med_est, columns=["Fecha", "Hora"] + nom_p), num_rows="dynamic", use_container_width=True)
    fotos_m = st.file_uploader("Fotos mediciones", accept_multiple_files=True, key="f_m")

    st.subheader("V. Anexo Fotográfico")
    fotos_anexo_est = st.file_uploader("Otras fotos", accept_multiple_files=True, key="a_est")
    firma_e = st.file_uploader("Firma Supervisor", type=["png", "jpg", "jpeg"], key="f_est")

    if st.button("🚀 GENERAR INFORME ESTRUCTURAS"):
        try:
            pdf = PDF()
            pdf.add_page()
            
            # --- INFO CLIENTE (LETRA 11 - MEJORA VISUAL) ---
            pdf.set_font("Arial", "", 11)
            pdf.cell(35, 7, "Cliente:", 0); pdf.cell(0, 7, str(cliente_e), 0, ln=1)
            pdf.cell(35, 7, "Dirección:", 0); pdf.cell(0, 7, str(direccion_e), 0, ln=1)
            pdf.cell(35, 7, "Tratamiento:", 0); pdf.cell(0, 7, f"{tipo_trat} - Plaga: {plaga_e}", 0, ln=1)
            pdf.cell(35, 7, "Fecha:", 0); pdf.cell(0, 7, format_fecha_es(fecha_e), 0, ln=1)
            
            # 1. LIMPIEZA
            pdf.titulo_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, "Previo a la inyección del fumigante, se verificaron y ejecutaron las condiciones de saneamiento crítico en las estructuras a tratar. Las labores se centraron en la remoción mecánica de biomasa, costras de producto envejecido y acumulaciones de polvo en zonas de difícil acceso (interiores de roscas, cúpulas de silos y ductos).\n\nEsta gestión de limpieza elimina refugios físicos que podrían disminuir la penetración del gas, garantizando así la hermeticidad y la máxima eficacia del tratamiento según los protocolos de calidad de Rentokil Initial.\n\n" + f"Supervisión Cliente: {enc_l} | Visado Rentokil: {rep_r}.\n" + f"Fecha Revisión en Terreno: {fecha_rev} a las {hora_rev} horas.")
            pdf.ln(3)
            
            # --- OBSERVACIONES (LETRA 11 ROJA) ---
            if hay_obs and txt_obs:
                pdf.set_font("Arial", "B", 11)
                pdf.set_text_color(200, 0, 0)
                pdf.cell(0, 7, "OBSERVACIONES / OPORTUNIDADES DE MEJORA DETECTADAS:", ln=1)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 6, txt_obs); pdf.ln(3)

            p_sel = ", ".join(est_sel) if est_sel else "No especificadas"
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Estructuras intervenidas: {p_sel}", ln=1)
            if fotos_l: pdf.agregar_galeria_fotos(fotos_l, "Evidencia de Limpieza y Sellado:")
            
            # 2. DOSIS (SALTO PÁGINA)
            pdf.titulo_seccion("II", "VOLUMEN Y DOSIFICACIÓN", force_page=True)
            h_dosis = ["Estructura", "Vol(m3)", "Plac", "Rope", "Phos", "Dosis g/m3"]
            d_d_pdf = []; t_g = 0; t_v = 0
            for _, row in df_est.iterrows():
                try:
                    v = clean_number(row.get("Volumen (m3)", 0))
                    n_pl = clean_number(row.get("Cant. Placas", 0)); n_ro = clean_number(row.get("Cant. Mini-Ropes", 0)); n_ph = clean_number(row.get("Cant. Phostoxin", 0))
                    if v > 0 or n_pl > 0 or n_ro > 0 or n_ph > 0:
                        g_r = (n_pl * 33) + (n_ro * 333) + (n_ph * 1); d_r = g_r / v if v > 0 else 0
                        t_g += g_r; t_v += v
                        d_d_pdf.append([str(row.get("Estructura (Nombre/N°)", "")), f"{v:.1f}", f"{int(n_pl)}", f"{int(n_ro)}", f"{int(n_ph)}", f"{d_r:.2f}"])
                except: pass
            d_d_pdf.append(["TOTALES", f"{t_v:.1f}", "", "", "", ""])
            pdf.tabla_estilizada(h_dosis, d_d_pdf, [55, 25, 20, 20, 20, 30], bold_last_row=True)
            pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Total Gas Generado: {t_g:.1f} gramos.", ln=1, align="R")
            if fotos_d: pdf.agregar_galeria_fotos(fotos_d, "Evidencia de Dosificación:")

            # 3. MEDICIONES (SALTO PÁGINA)
            pdf.titulo_seccion("III", "TIEMPOS Y MEDICIONES", force_page=True)
            pdf.tabla_estilizada(["Evento", "Fecha", "Hora", "Total Horas"], [["Inicio", str(f_ini_e), str(h_ini_e), f"{h_exp_e:.1f}"], ["Término", str(f_ter_e), str(h_ter_e), "---"]], [45, 45, 45, 45])
            pdf.ln(5); fig, ax = plt.subplots(figsize=(10, 5))
            e_x = df_med_est["Fecha"].astype(str) + "\n" + df_med_est["Hora"].astype(str)
            h_g = False
            for col in df_med_est.columns[2:]:
                val = pd.to_numeric(df_med_est[col], errors='coerce').fillna(0)
                if val.sum() > 0: ax.plot(e_x, val, marker='o', label=col); h_g = True
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
            if h_g: ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=5, frameon=False)
            plt.subplots_adjust(top=0.85); plt.tight_layout()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_g:
                fig.savefig(tmp_g.name, dpi=300); pdf.image(tmp_g.name, x=10, w=190)
            pdf.ln(5); pdf.tabla_estilizada([str(c) for c in df_med_est.columns], [[str(x) for x in r] for _, r in df_med_est.iterrows()], [25, 20, 25, 25, 25, 25, 25])
            if fotos_m: pdf.agregar_galeria_fotos(fotos_m, "Evidencia de Monitoreo:")

            # 4. ANEXO (SALTO PÁGINA)
            if fotos_anexo_est: pdf.titulo_seccion("IV", "ANEXO FOTOGRÁFICO", force_page=True); pdf.agregar_galeria_fotos(fotos_anexo_est)

            # 5. CONCLUSIONES (SALTO PÁGINA + TEXTO REFINADO v9.8)
            pdf.titulo_seccion("V", "CONCLUSIONES TÉCNICAS", force_page=True)
            t_efic = f"asegurando el control biológico de {plaga_e} en todos sus estadios de desarrollo."
            if tipo_trat == "Preventivo":
                t_efic = "logrando establecer una barrera sanitaria efectiva que elimina reservorios biológicos latentes y mitiga riesgos de contaminación cruzada, garantizando así la integridad higiénica de las instalaciones."

            c_text = (
                "EVALUACIÓN DE EFICACIA:\n"
                f"El análisis de los registros de monitoreo confirma que la concentración de Fosfina (PH3) se mantuvo por sobre el umbral crítico de 300 PPM durante las {h_exp_e:.1f} horas de exposición efectiva. Esta saturación constante garantiza una penetración total del gas en los puntos críticos de las estructuras, {t_efic}\n\n"
                "CERTIFICACIÓN:\n"
                "En consecuencia, el servicio se declara CONFORME, validando la bio-disponibilidad del ingrediente activo y el cumplimiento de los estándares técnicos de Rentokil Initial Chile."
            )
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, c_text); pdf.ln(20)

            r_f_e = None
            if firma_e: r_f_e = procesar_firma(firma_e)
            elif os.path.exists('firma.png'): r_f_e = 'firma.png'
            if r_f_e:
                pdf.image(r_f_e, x=75, w=60)
                if firma_e and r_f_e != 'firma.png': os.remove(r_f_e)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_p:
                pdf.output(tmp_p.name)
                with open(tmp_p.name, "rb") as f: st.session_state.pdf_data = f.read()
            st.rerun()
        except Exception as e: st.error(f"Error: {e}"); st.code(traceback.format_exc())

# BOTÓN DESCARGA
if st.session_state.pdf_data:
    st.success("✅ Informe Generado")
    st.download_button("📲 DESCARGAR PDF FINAL", data=st.session_state.pdf_data, file_name="Informe_Rentokil.pdf", mime="application/pdf")
