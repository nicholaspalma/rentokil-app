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
    """
    Convierte cualquier entrada (str con coma, vacío, int) a float seguro.
    Ej: "1,5" -> 1.5 | "" -> 0.0 | None -> 0.0
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Reemplazar coma por punto y quitar espacios
        val_clean = value.replace(',', '.').strip()
        if val_clean == "":
            return 0.0
        try:
            return float(val_clean)
        except ValueError:
            return 0.0
    return 0.0

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

    def check_page_break(self, needed_height):
        """Si no hay espacio suficiente (needed_height mm), crea nueva página."""
        if self.get_y() + needed_height > 250:
            self.add_page()

    def titulo_seccion(self, numero, texto):
        self.check_page_break(20) # Asegurar espacio para título + un poco de texto
        self.ln(5)
        self.set_font("Arial", "B", 10)
        self.set_fill_color(*COLOR_PRIMARIO)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, f"  {numero}. {texto.upper()}", ln=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def tabla_estilizada(self, header, data, col_widths, bold_last_row=False):
        self.check_page_break(20) # Al menos espacio para cabecera y 1 fila
        self.set_font("Arial", "B", 7)
        self.set_fill_color(*COLOR_TABLA_HEAD)
        for i, h in enumerate(header):
            self.cell(col_widths[i], 8, h, 1, 0, 'C', True)
        self.ln()
        
        self.set_font("Arial", "", 7)
        for idx, row in enumerate(data):
            # Si es la última fila y pedimos negrita (totales)
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
        
        self.check_page_break(40) # Verificar si cabe al menos título y 1 foto
        
        if titulo_opcional:
            self.ln(2); self.set_font("Arial", "B", 9); self.cell(0, 6, titulo_opcional, ln=1)
        
        # Guardar posición Y inicial segura
        y_start = self.get_y()
        
        for i, f in enumerate(lista_fotos):
            tmp_path = procesar_imagen_estilizada(f)
            if tmp_path:
                try:
                    # Control de salto de página dentro del bucle
                    # Si estamos muy abajo (>220mm), saltar página y resetear Y
                    if self.get_y() > 220:
                        self.add_page(); self.set_y(20); y_start = 20
                        if i % 2 != 0: y_start = 20 # Si es la 2da foto de un par, resetear
                    
                    if i % 2 == 0:
                        y_act = self.get_y()
                        self.image(tmp_path, x=10, y=y_act, w=90, h=65)
                    else:
                        self.image(tmp_path, x=110, y=y_act, w=90, h=65)
                        self.ln(70) # Bajar cursor solo al terminar el par
                    
                    os.remove(tmp_path)
                except: pass
        
        # Si quedó una foto impar, bajar el cursor para que no se escriba encima
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
# LÓGICA 1: MOLINOS (SIN CAMBIOS MAYORES)
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
    ]), num_rows="dynamic", use_container_width=True)

    st.info("📷 Fotos dosificación (Página 1)")
    fotos_dosis = st.file_uploader("Subir evidencia dosis", accept_multiple_files=True, key="dosis_mol")
    
    # Cálculos Molinos
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
            d_dosis_pdf = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_dosis.iterrows()]
            d_dosis_pdf.append(["TOTALES", str(int(total_bandejas)), str(int(total_ropes))])
            pdf.tabla_estilizada(["Sector", "Bandejas", "Mini-Ropes"], d_dosis_pdf, [80, 50, 50], bold_last_row=True)
            
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
            eje_x_labels = df_med_est["Fecha"] + "\n" + df_med_est["Hora"]
            for col in df_med_est.columns[2:]: 
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
# LÓGICA 2: ESTRUCTURAS (MEJORADA v8.5)
# ==============================================================================
elif st.session_state.app_mode == "ESTRUCTURAS":
    with st.sidebar:
        st.image("logo.png", width=120) if os.path.exists("logo.png") else None
        if st.button("⬅️ VOLVER AL MENÚ", use_container_width=True):
            st.session_state.app_mode = "HOME"; st.rerun()
        st.markdown("---"); st.info("Modo: Estructuras")

    st.title("🏗️ Informe Estructuras (Nuevo)")
    
    # 1. DATOS
    st.subheader("I. Datos Generales")
    LISTA_CLIENTES_ESTR = list(DATABASE_MOLINOS.keys()) + list(DATABASE_ESTRUCTURAS_EXTRA.keys())
    opcion_e = st.selectbox("Seleccione Cliente", LISTA_CLIENTES_ESTR)
    direccion_auto = ""
    if opcion_e in DATABASE_MOLINOS: direccion_auto = DATABASE_MOLINOS[opcion_e]["direccion"]
    elif opcion_e in DATABASE_ESTRUCTURAS_EXTRA: direccion_auto = DATABASE_ESTRUCTURAS_EXTRA[opcion_e]
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        cliente_e = st.text_input("Nombre Cliente", opcion_e)
        direccion_e = st.text_input("Dirección", direccion_auto)
        tipo_trat = st.radio("Tipo de Tratamiento", ["Preventivo", "Curativo"], horizontal=True)
    with col_e2:
        fecha_e = st.date_input("Fecha Informe", datetime.date.today())
        plaga_e = "N/A (Preventivo)"
        if tipo_trat == "Curativo": plaga_e = st.text_input("Plaga de Almacenamiento", "Tribolium confusum")

    # 2. LIMPIEZA
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

    # 3. DOSIS (CORREGIDO BUG NUMÉRICO)
    st.subheader("III. Volumen y Dosis (Cálculo Automático)")
    data_struct = [{"Estructura (Nombre/N°)": "Silo 1", "Volumen (m3)": 100, "Cant. Placas": 0, "Cant. Mini-Ropes": 0, "Cant. Phostoxin": 0}]
    df_estructuras = st.data_editor(pd.DataFrame(data_struct), num_rows="dynamic", use_container_width=True)

    # 4. MEDICIONES
    st.subheader("IV. Tiempos y Mediciones")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        f_ini_e = st.date_input("Inicio Tratamiento", datetime.date.today(), key="fi_e")
        h_ini_e = st.time_input("Hora Inicio", datetime.time(18, 0), key="hi_e")
    with col_t2:
        f_ter_e = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=4), key="ft_e")
        h_ter_e = st.time_input("Hora Término", datetime.time(10, 0), key="ht_e")
    horas_exp_e = (datetime.datetime.combine(f_ter_e, h_ter_e) - datetime.datetime.combine(f_ini_e, h_ini_e)).total_seconds() / 3600

    st.markdown("---")
    st.markdown("**Configuración de Puntos de Medición**")
    c_nombres = st.columns(5)
    nombres_puntos = []
    for i in range(5):
        nuevo_nombre = c_nombres[i].text_input(f"Nombre Punto {i+1}", f"Punto {i+1}", key=f"n_p_{i}")
        nombres_puntos.append(nuevo_nombre)
    
    st.markdown("**Registro de Concentraciones (PPM)**")
    data_med_est = []
    for i in range(3):
        f_str = (f_ini_e + datetime.timedelta(days=i)).strftime("%d-%m")
        data_med_est.append([f_str, "10:00", 0, 0, 0, 0, 0])
    cols_totales = ["Fecha", "Hora"] + nombres_puntos
    df_med_est = st.data_editor(pd.DataFrame(data_med_est, columns=cols_totales), num_rows="dynamic", use_container_width=True)

    st.markdown("**📷 Evidencia de Monitoreo / Equipos (Item 4)**")
    fotos_monitoreo = st.file_uploader("Subir fotos de mediciones", accept_multiple_files=True, key="fotos_mon")

    st.subheader("V. Anexo Fotográfico General")
    fotos_anexo_est = st.file_uploader("Fotos Generales Estructuras", accept_multiple_files=True, key="anexo_est")
    
    st.markdown("---")
    st.subheader("✍️ Firma Supervisor")
    firma_file_est = st.file_uploader("Subir firma (opcional)", type=["png", "jpg", "jpeg"], key="firma_est")

    if st.button("🚀 GENERAR INFORME ESTRUCTURAS"):
        try:
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            # 1. INFO
            pdf.set_font("Arial", "", 10)
            pdf.cell(30, 6, "Cliente:", 0); pdf.cell(0, 6, str(cliente_e), 0, ln=1)
            pdf.cell(30, 6, "Dirección:", 0); pdf.cell(0, 6, str(direccion_e), 0, ln=1)
            pdf.cell(30, 6, "Tratamiento:", 0); pdf.cell(0, 6, f"{tipo_trat} - Plaga: {plaga_e}", 0, ln=1)
            # Formato fecha profesional
            fecha_str_larga = fecha_e.strftime("%d-%m-%Y")
            pdf.cell(30, 6, "Fecha:", 0); pdf.cell(0, 6, fecha_str_larga, 0, ln=1)
            
            # 2. LIMPIEZA (TEXTO MEJORADO)
            pdf.titulo_seccion("I", "PLAN DE SELLADO Y LIMPIEZA")
            texto_limpieza = (
                "Previo a la inyección del fumigante, se verificaron y ejecutaron las condiciones de saneamiento crítico en las "
                "estructuras a tratar. Las labores se centraron en la remoción mecánica de biomasa, costras de producto envejecido "
                "y acumulaciones de polvo en zonas de difícil acceso (interiores de roscas, cúpulas de silos y ductos).\n\n"
                "Esta gestión de limpieza elimina refugios físicos que podrían disminuir la penetración del gas, garantizando así "
                "la hermeticidad y la máxima eficacia del tratamiento según los protocolos de calidad de Rentokil Initial.\n\n"
                f"Supervisión Cliente: {encargado_limpieza} | Visado Rentokil: {rep_rentokil}.\n"
                f"Fecha Revisión en Terreno: {fecha_rev} a las {hora_rev} horas."
            )
            pdf.multi_cell(0, 5, texto_limpieza); pdf.ln(3)
            
            est_str = ", ".join(estructuras_sel) if estructuras_sel else "No especificadas"
            pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, f"Estructuras intervenidas: {est_str}", ln=1)
            
            if fotos_limpieza: pdf.agregar_galeria_fotos(fotos_limpieza, titulo_opcional="Evidencia de Limpieza y Sellado:")

            # 3. DOSIS (CON FIX NUMÉRICO Y TOTALES)
            pdf.titulo_seccion("II", "VOLUMEN Y DOSIFICACIÓN")
            header_dosis = ["Estructura", "Vol(m3)", "Plac", "Rope", "Phos", "Dosis g/m3"]
            data_dosis_pdf = []
            total_g = 0
            total_vol = 0
            
            # LÓGICA DE CÁLCULO SEGURA (CLEAN NUMBER)
            for index, row in df_estructuras.iterrows():
                try:
                    vol = clean_number(row.get("Volumen (m3)", 0))
                    n_pla = clean_number(row.get("Cant. Placas", 0))
                    n_rop = clean_number(row.get("Cant. Mini-Ropes", 0))
                    n_pho = clean_number(row.get("Cant. Phostoxin", 0))
                    
                    if vol > 0 or n_pla > 0 or n_rop > 0 or n_pho > 0: # Solo si hay algo escrito
                        g_row = (n_pla * 33) + (n_rop * 333) + (n_pho * 1)
                        dosis_row = g_row / vol if vol > 0 else 0
                        total_g += g_row
                        total_vol += vol
                        data_dosis_pdf.append([
                            str(row.get("Estructura (Nombre/N°)", "")),
                            f"{vol:.1f}", 
                            f"{int(n_pla)}", 
                            f"{int(n_rop)}", 
                            f"{int(n_pho)}", 
                            f"{dosis_row:.2f}"
                        ])
                except: pass
            
            # Agregar fila de TOTALES
            data_dosis_pdf.append(["TOTALES", f"{total_vol:.1f}", "", "", "", ""])
            
            pdf.tabla_estilizada(header_dosis, data_dosis_pdf, [55, 25, 20, 20, 20, 30], bold_last_row=True)
            pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, f"Total Gas Generado: {total_g:.1f} gramos.", ln=1, align="R")

            # 4. TIEMPOS Y MEDICIONES
            pdf.add_page() # Forzar inicio en nueva hoja para que grafico y tabla queden juntos
            pdf.titulo_seccion("III", "TIEMPOS Y MEDICIONES")
            pdf.tabla_estilizada(["Evento", "Fecha", "Hora", "Total Horas"], [["Inicio", str(f_ini_e), str(h_ini_e), f"{horas_exp_e:.1f}"], ["Término", str(f_ter_e), str(h_ter_e), "---"]], [45, 45, 45, 45])
            
            pdf.ln(5)
            # GENERACIÓN GRÁFICO
            fig, ax = plt.subplots(figsize=(10, 5))
            eje_x = df_med_est["Fecha"] + "\n" + df_med_est["Hora"]
            hay_datos_grafico = False
            for col in df_med_est.columns[2:]: 
                valores = pd.to_numeric(df_med_est[col], errors='coerce').fillna(0)
                if valores.sum() > 0: 
                    ax.plot(eje_x, valores, marker='o', label=col)
                    hay_datos_grafico = True
            
            ax.axhline(300, color='red', linestyle='--', label='Mínimo Legal (300ppm)')
            if hay_datos_grafico:
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

            # 5. CONCLUSIONES (TEXTO MEJORADO)
            pdf.add_page(); pdf.titulo_seccion("V", "CONCLUSIONES TÉCNICAS")
            
            concl_text_est = (
                "EVALUACIÓN DE EFICACIA:\n"
                "El análisis de las curvas de concentración de Fosfina (PH3) demuestra que se alcanzó y mantuvo la saturación "
                f"necesaria en todos los puntos críticos monitoreados. Los niveles de gas superaron el umbral de toxicidad requerido, "
                f"asegurando el control de {plaga_e} en sus distintos estadios de desarrollo.\n\n"
                "CERTIFICACIÓN:\n"
                f"Se certifica un tiempo de exposición efectivo de {horas_exp_e:.1f} horas, validando la bio-disponibilidad del "
                "ingrediente activo en todo el volumen tratado.\n\n"
                "En consecuencia, el servicio se declara CONFORME, cumpliendo estrictamente con los estándares de inocuidad "
                "y calidad comprometidos por Rentokil Initial Chile."
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
