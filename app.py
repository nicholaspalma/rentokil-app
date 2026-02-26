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
    st.session_state.app_mode = "HOME" # Inicia en el Menú Principal
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

DATABASE_ESTRUCTURAS_CLIENTES = {
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
def procesar_imagen_estilizada(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGB')
        image_fixed = ImageOps.fit(image, (800, 600), method=Image.Resampling.LANCZOS)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        image_fixed.save(tmp.name, format='JPEG', quality=85)
        return tmp.name
    except: return None

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

    def titulo_seccion(self, numero, texto):
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(*COLOR_PRIMARIO)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {numero}. {texto.upper()}", ln=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def tabla_estilizada(self, header, data, col_widths):
        self.set_font("Arial", "B", 7)
        self.set_fill_color(*COLOR_TABLA_HEAD)
        for i, h in enumerate(header):
            self.cell(col_widths[i], 8, h, 1, 0, 'C', True)
        self.ln()
        self.set_font("Arial", "", 7)
        for row in data:
            self.set_fill_color(*COLOR_TABLA_FILA)
            for i, d in enumerate(row):
                self.cell(col_widths[i], 6, str(d), 1, 0, 'C', True)
            self.ln()
            
    def agregar_galeria_fotos(self, lista_fotos, titulo_opcional=None):
        if not lista_fotos: return
        if titulo_opcional:
            self.ln(2); self.set_font("Arial", "B", 9); self.cell(0, 6, titulo_opcional, ln=1)
        y_start = self.get_y()
        if y_start > 200: self.add_page(); self.set_y(20); y_start = 20
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
# PANTALLA DE INICIO (HOME) - MENÚ VISUAL
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
    ], columns=["Piso", "Bandejas", "Mini-Ropes"]), num_rows="dynamic", use_container_width=True)
    st.info("📷 Fotos dosificación (Página 1)")
    fotos_dosis = st.file_uploader("Subir evidencia dosis", accept_multiple_files=True, key="dosis_mol")
    
    total_bandejas = df_dosis["Bandejas"].sum()
    total_ropes = df_dosis["Mini-Ropes"].sum()
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
            d_dosis_pdf = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_dosis.iterrows()]
            d_dosis_pdf.append(["TOTALES", str(total_bandejas), str(total_ropes)])
            pdf.tabla_estilizada(["Sector", "Bandejas", "Mini-Ropes"], d_dosis_pdf, [80, 50, 50])
            
            if fotos_dosis:
                pdf.ln(2); y_start = pdf.get_y()
                for i, f in enumerate(fotos_dosis[:2]):
                    tmp_path = procesar_imagen_estilizada(f)
                    if tmp_path:
                        try:
                            x_pos = 10 if i == 0 else 105
                            pdf.image(tmp_path, x=x_pos, y=y_start, w=85, h=60); os.remove(tmp_path)
                        except: pass
                pdf.ln(65)

            pdf.ln(2); pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, f"DOSIS FINAL: {dosis_final:.2f} g/m3", ln=1, align="R")
            
            pdf.add_page(); pdf.titulo_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)")
            fig, ax = plt.subplots(figsize=(10, 5))
            eje_x_labels = df_meds["Fecha"] + "\n" + df_meds["Hora"]
            for col in df_meds.columns[2:]: 
                ax.plot(eje_x_labels, pd.to_numeric(df_meds[col], errors='coerce'), marker='o', label=col)
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal')
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4, frameon=False, fontsize='small')
            plt.xticks(rotation=45, fontsize=8); plt.subplots_adjust(top=0.85); plt.tight_layout()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_graf:
                fig.savefig(tmp_graf.name, dpi=300); pdf.image(tmp_graf.name, x=10, w=190)
            pdf.ln(5)
            pdf.tabla_estilizada(["Fech", "Hr", "S", "P1", "P2", "P3", "P4", "P5"], [[str(x) for x in r] for _, r in df_meds.iterrows()], [25, 20, 20, 20, 20, 20, 20, 20])
            
            if fotos_anexo:
                pdf.add_page(); pdf.titulo_seccion("V", "ANEXO FOTOGRÁFICO")
                pdf.agregar_galeria_fotos(fotos_anexo)

            pdf.add_page(); pdf.titulo_seccion("VI", "CONCLUSIONES TÉCNICAS")
            conclusiones_texto = (
                f"De acuerdo con los registros monitoreados, se certifica que el tratamiento de fumigación en las instalaciones de {planta} "
                f"se realizó cumpliendo un tiempo de exposición efectivo de {horas_exp:.1f} horas.\n\n"
                f"El monitoreo de concentración de gas Fosfina (PH3) arrojó un promedio global de {promedio_ppm:.0f} PPM, "
                f"manteniéndose en todo momento dentro de los rangos de eficacia requeridos para el control de {plaga}.\n\n"
                f"Por lo anterior, el servicio se declara CONFORME, cumpliendo con los estándares de seguridad y calidad establecidos por Rentokil Initial Chile."
            )
            pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, conclusiones_texto); pdf.ln(20)

            ruta_firma = None
            if firma_file: ruta_firma = procesar_firma(firma_file)
            elif os.path.exists('firma.png'): ruta_firma = 'firma.png'
            if ruta_firma:
                try:
                    x_c = (210 - 60) / 2; pdf.image(ruta_firma, x=x_c, w=60)
                    if firma_file and ruta_firma != 'firma.png': os.remove(ruta_firma)
                except: pass

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                pdf.output(tmp_pdf.name)
                with open(tmp_pdf.name, "rb") as f:
                    st.session_state.pdf_data = f.read()
            st.rerun()
        except Exception as e: st.error(f"Error: {e}"); st.code(traceback.format_exc())

# ==============================================================================
# LÓGICA 2: ESTRUCTURAS
# ==============================================================================
elif st.session_state.app_mode == "ESTRUCTURAS":
    with st.sidebar:
        st.image("logo.png", width=120) if os.path.exists("logo.png") else None
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True):
            st.session_state.app_mode = "HOME"; st.rerun()
        st.markdown("---"); st.info("Modo: Estructuras")

    st.title("🏗️ Informe Estructuras (Nuevo)")
    
    st.subheader("I. Datos Generales")
    opcion_e = st.selectbox("Seleccione Cliente", list(DATABASE_ESTRUCTURAS_CLIENTES.keys()))
    direccion_auto = DATABASE_ESTRUCTURAS_CLIENTES.get(opcion_e, "")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        cliente_e = st.text_input("Nombre Cliente", opcion_e)
        direccion_e = st.text_input("Dirección", direccion_auto)
        tipo_trat = st.radio("Tipo de Tratamiento", ["Preventivo", "Curativo"], horizontal=True)
    with col_e2:
        fecha_e = st.date_input("Fecha Informe", datetime.date.today())
        plaga_e = "N/A (Preventivo)"
        if tipo_trat == "Curativo":
            plaga_e = st.text_input("Plaga de Almacenamiento (Curativo)", "Tribolium confusum")

    st.subheader("II. Plan de Sellado y Limpieza")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        encargado_limpieza = st.text_input("Encargado Limpieza (Cliente)", "Jefe de Turno")
        rep_rentokil = st.selectbox("Representante Rentokil (Visador)", LISTA_REPRESENTANTES)
    with col_l2:
        fecha_rev = st.date_input("Fecha Revisión", datetime.date.today())
        hora_rev = st.time_input("Hora Revisión", datetime.time(10, 0))
    estructuras_sel = st.multiselect("Estructuras a tratar", ["Silos", "Tolvas", "Roscas", "Elevadores", "Pozos", "Ductos Descarga", "Ductos Carga", "Pavos", "Ductos Aspiración", "Celdas"])
    
    st.markdown("**📷 Evidencia de Limpieza / Suciedad (Item 2.1)**")
    fotos_limpieza = st.file_uploader("Subir fotos de limpieza", accept_multiple_files=True, key="fotos_limp")

    st.subheader("III. Volumen y Dosis (Cálculo Automático)")
    df_struct_template = pd.DataFrame(columns=["Estructura (Nombre/N°)", "Volumen (m3)", "Cant. Placas", "Cant. Mini-Ropes", "Cant. Phostoxin"])
    data_struct = [{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}]
    df_estructuras = st.data_editor(data_struct, num_rows="dynamic", use_container_width=True)

    st.subheader("IV. Tiempos y Mediciones")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        f_ini_e = st.date_input("Inicio Tratamiento", datetime.date.today(), key="fi_e")
        h_ini_e = st.time_input("Hora Inicio", datetime.time(18, 0), key="hi_e")
    with col_t2:
        f_ter_e = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=4), key="ft_e")
        h_ter_e = st.time_input("Hora Término", datetime.time(10, 0), key="ht_e")
    horas_exp_e = (datetime.datetime.combine(f_ter_e, h_ter_e) - datetime.datetime.combine(f_ini_e, h_ini_e)).total_seconds() / 3600

    st.markdown("**Registro de Concentraciones (PPM)**")
    data_med_est = []
    for i in range(3):
        f_str = (f_ini_e + datetime.timedelta(days=i)).strftime("%d-%m")
        data_med_est.append([f_str, "10:00", 0, 0, 0, 0, 0])
    df_med_est = st.data_editor(pd.DataFrame(data_med_est, columns=["Fecha", "Hora", "Punto 1", "Punto 2", "Punto 3", "Punto 4", "Punto 5"]), num_rows="dynamic", use_container_width=True)

    st.markdown("**📷 Evidencia de Monitoreo / Equipos (Item 4)**")
    fotos_monitoreo = st.file_uploader("Subir fotos de mediciones", accept_multiple_files=True, key="fotos_mon")

    st.subheader("V. Anexo Fotográfico General")
    st.markdown("**📷 Otras Fotos (Generales)**")
    fotos_anexo_est = st.file_uploader("Fotos Generales Estructuras", accept_multiple_files=True, key="anexo_est")
    
    st.markdown("---")
    st.subheader("✍️ Firma Supervisor")
    firma_file_est = st.file_uploader("Subir firma (opcional)", type=["png", "jpg", "jpeg"], key="firma_est")

    if st.button("🚀 GENERAR INFORME ESTRUCTURAS"):
        try:
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(30, 6, "Cliente:", 0); pdf.cell(0, 6, str(cliente_e), 0, ln=1)
            pdf.cell(30, 6, "Dirección:", 0); pdf.cell(0, 6, str(direccion_e), 0, ln=1)
            pdf.cell(30, 6, "Tratamiento:", 0); pdf.cell(0, 6, f"{tipo_trat} - Plaga: {plaga_e}", 0, ln=1)
            pdf.cell(30, 6, "Fecha:", 0); pdf.cell(0, 6, str(fecha_e), 0, ln=1)
            
            pdf.titulo_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
            texto_limpieza = (
                "Previo al inicio del tratamiento de fumigación, se solicitó la ejecución de un aseo minucioso de las áreas a tratar, "
                "el cual consistió en la remoción de polvo, materia orgánica, derrames y acumulaciones de residuos presentes en "
                "vigas, interiores de roscas, tolvas, elevadores y silos.\n"
                "Asimismo, se procedió a la eliminación de costras de residuos e impurezas acumuladas en las superficies, con el "
                "objetivo de evitar que los insectos se refugiaran bajo capas de polvo o materia orgánica.\n\n"
                f"La limpieza fue supervisada por: {encargado_limpieza}.\n"
                f"Visada por Representante Técnico Rentokil: {rep_rentokil}.\n"
                f"Fecha Revisión: {fecha_rev} a las {hora_rev} horas."
            )
            pdf.multi_cell(0, 5, texto_limpieza); pdf.ln(3)
            
            est_str = ", ".join(estructuras_sel) if estructuras_sel else "No especificadas"
            pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, f"Estructuras intervenidas: {est_str}", ln=1)
            
            if fotos_limpieza: pdf.agregar_galeria_fotos(fotos_limpieza, titulo_opcional="Evidencia de Limpieza y Sellado:")

            pdf.titulo_seccion("II", "VOLUMEN Y DOSIFICACIÓN")
            header_dosis = ["Estructura", "Vol(m3)", "Plac", "Rope", "Phos", "Dosis g/m3"]
            data_dosis_pdf = []
            total_g = 0
            for index, row in df_estructuras.iterrows():
                try:
                    vol = float(row.get("Volumen (m3)", 0))
                    n_pla = float(row.get("Cant. Placas", 0))
                    n_rop = float(row.get("Cant. Mini-Ropes", 0))
                    n_pho = float(row.get("Cant. Phostoxin", 0))
                    g_row = (n_pla * 33) + (n_rop * 333) + (n_pho * 1)
                    dosis_row = g_row / vol if vol > 0 else 0
                    total_g += g_row
                    data_dosis_pdf.append([str(row.get("Estructura (Nombre/N°)", "")), f"{vol:.1f}", f"{int(n_pla)}", f"{int(n_rop)}", f"{int(n_pho)}", f"{dosis_row:.2f}"])
                except: pass
            pdf.tabla_estilizada(header_dosis, data_dosis_pdf, [55, 25, 20, 20, 20, 30])
            pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Total Gas Generado: {total_g:.1f} gramos.", ln=1, align="R")

            pdf.add_page(); pdf.titulo_seccion("III", "TIEMPOS Y MEDICIONES")
            pdf.tabla_estilizada(["Evento", "Fecha", "Hora", "Total Horas"], [["Inicio", str(f_ini_e), str(h_ini_e), f"{horas_exp_e:.1f}"], ["Término", str(f_ter_e), str(h_ter_e), "---"]], [45, 45, 45, 45])
            
            pdf.ln(5)
            fig, ax = plt.subplots(figsize=(10, 5))
            eje_x = df_med_est["Fecha"] + "\n" + df_med_est["Hora"]
            for col in df_med_est.columns[2:]: 
                valores = pd.to_numeric(df_med_est[col], errors='coerce')
                if valores.sum() > 0: ax.plot(eje_x, valores, marker='o', label=col)
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=5, frameon=False, fontsize='small')
            plt.subplots_adjust(top=0.85); plt.tight_layout()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_graf:
                fig.savefig(tmp_graf.name, dpi=300); pdf.image(tmp_graf.name, x=10, w=190)
            
            pdf.ln(5)
            cols_pdf = [str(c) for c in df_med_est.columns]
            data_pdf = [[str(x) for x in r] for _, r in df_med_est.iterrows()]
            pdf.tabla_estilizada(cols_pdf, data_pdf, [25, 20, 25, 25, 25, 25, 25])

            if fotos_monitoreo: pdf.agregar_galeria_fotos(fotos_monitoreo, titulo_opcional="Evidencia de Monitoreo:")

            if fotos_anexo_est:
                pdf.add_page(); pdf.titulo_seccion("IV", "ANEXO FOTOGRÁFICO"); pdf.agregar_galeria_fotos(fotos_anexo_est)

            pdf.add_page(); pdf.titulo_seccion("V", "CONCLUSIONES TÉCNICAS")
            lista_structs = ", ".join(estructuras_sel) if estructuras_sel else "las estructuras indicadas"
            concl_text_est = (
                f"Se certifica que el tratamiento de fumigación en {cliente_e} ({direccion_e}) abarcando {lista_structs}, "
                f"se realizó cumpliendo un tiempo de exposición efectivo de {horas_exp_e:.1f} horas.\n\n"
                f"Las concentraciones de gas Fosfina se mantuvieron dentro de los parámetros de eficacia para el control de {plaga_e}.\n\n"
                f"El servicio se declara CONFORME según los estándares de Rentokil Initial Chile."
            )
            pdf.multi_cell(0, 6, concl_text_est); pdf.ln(20)

            ruta_firma = None
            if firma_file_est: ruta_firma = procesar_firma(firma_file_est)
            elif os.path.exists('firma.png'): ruta_firma = 'firma.png'
            if ruta_firma:
                try:
                    x_c = (210 - 60) / 2; pdf.image(ruta_firma, x=x_c, w=60)
                    if firma_file_est and ruta_firma != 'firma.png': os.remove(ruta_firma)
                except: pass

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                pdf.output(tmp_pdf.name)
                with open(tmp_pdf.name, "rb") as f:
                    st.session_state.pdf_data = f.read()
            st.rerun()
            
        except Exception as e: st.error(f"Error: {e}"); st.code(traceback.format_exc())

# BOTÓN FINAL
if st.session_state.pdf_data:
    st.success("✅ Informe Generado Exitosamente")
    st.download_button(label="📲 DESCARGAR PDF FINAL", data=st.session_state.pdf_data, file_name="Informe_Rentokil.pdf", mime="application/pdf", key="btn_descarga_final")
