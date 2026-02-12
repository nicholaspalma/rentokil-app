import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os
import tempfile  # <--- NUEVA HERRAMIENTA CLAVE

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="Rentokil Mobile")
COLOR_PRIMARIO = (227, 6, 19)
COLOR_TABLA_HEAD = (220, 220, 220)
COLOR_TABLA_FILA = (255, 255, 255)

# --- BASE DE DATOS ---
DATABASE_MOLINOS = {
    "MOLINO CASABLANCA": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Alejandro Galaz N° 500, Casablanca", "volumen": 4850},
    "MOLINO LA ESTAMPA": {"cliente": "MOLINO LA ESTAMPA S.A.", "direccion": "Fermin Vivaceta 1053, Independencia", "volumen": 5500},
    "MOLINO FERRER": {"cliente": "MOLINO FERRER HERMANOS S.A.", "direccion": "Baquedano N° 647, San Bernardo", "volumen": 8127},
    "MOLINO EXPOSICIÓN": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Exposición N° 1657, Estación Central", "volumen": 7502},
    "MOLINO LINDEROS": {"cliente": "MOLINO LINDEROS S.A.", "direccion": "Villaseca Nº 1195, Buin", "volumen": 4800},
    "MOLINO MAIPÚ": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Avenida Pajarito N° 1046, Maipú", "volumen": 4059}
}

LISTA_PLAGAS = ["Tribolium confusum", "Cryptolestes ferrugineus", "Gnathocerus cornutus", "Ephestia kuehniella", "Psócidos", "OTRA / MANUAL"]

class PDF(FPDF):
    def header(self):
        # Logo: Verificación robusta para la nube
        if os.path.exists("logo.png"):
            self.image('logo.png', 10, 8, 33)
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

st.title("🛡️ Generador Rentokil v6.2 (Cloud)")

# --- I. DATOS GENERALES ---
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

# --- II. DETALLES TÉCNICOS ---
st.subheader("II. Detalles Técnicos")
col_t1, col_t2 = st.columns(2)
with col_t1:
    plaga = st.selectbox("Plaga Objetivo", LISTA_PLAGAS)
    sellado_ok = st.checkbox("Sellado Conforme", value=True)
with col_t2:
    f_ini = st.date_input("Inicio Inyección", datetime.date.today())
    h_ini = st.time_input("Hora Inicio", datetime.time(19, 0))
    f_ter = st.date_input("Fin Ventilación", datetime.date.today() + datetime.timedelta(days=3))
    h_ter = st.time_input("Hora Término", datetime.time(19, 0))

dt_ini = datetime.datetime.combine(f_ini, h_ini)
dt_ter = datetime.datetime.combine(f_ter, h_ter)
horas_exp = (dt_ter - dt_ini).total_seconds() / 3600

# --- III. DOSIFICACIÓN ---
st.subheader("III. Distribución y Dosificación")
df_dosis = st.data_editor(
    pd.DataFrame([
        {"Piso": "Subterráneo", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 1", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 2", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 3", "Bandejas": 10, "Mini-Ropes": 2},
        {"Piso": "Piso 4", "Bandejas": 8, "Mini-Ropes": 1},
        {"Piso": "Piso 5", "Bandejas": 5, "Mini-Ropes": 0},
    ], columns=["Piso", "Bandejas", "Mini-Ropes"]), 
    num_rows="dynamic",
    use_container_width=True
)

total_bandejas = df_dosis["Bandejas"].sum()
total_ropes = df_dosis["Mini-Ropes"].sum()
gramos_totales = (total_bandejas * 500) + (total_ropes * 333)
dosis_final = gramos_totales / volumen_total if volumen_total > 0 else 0

# --- IV. MEDICIONES ---
st.subheader("IV. Mediciones de Gas (PPM)")
cols_meds = ["Fecha", "Hora", "Hrs Exp", "Subt.", "Piso 1", "Piso 2", "Piso 3", "Piso 4", "Piso 5"]

data_inicial = []
horas_std = ["19:00", "00:00", "07:00", "13:00"]
fecha_cursor = f_ini

for i in range(3):
    f_str = (fecha_cursor + datetime.timedelta(days=i)).strftime("%d-%m")
    for h in horas_std:
        h_exp = (i * 24) + int(h.split(":")[0]) 
        if h_exp < 0: h_exp = 0
        data_inicial.append([f_str, h, h_exp, 300, 310, 320, 305, 300, 290])

df_meds = st.data_editor(
    pd.DataFrame(data_inicial, columns=cols_meds), 
    num_rows="dynamic",
    use_container_width=True
)

for col in cols_meds[3:]:
    df_meds[col] = pd.to_numeric(df_meds[col], errors='coerce').fillna(0)
promedio_ppm = df_meds.iloc[:, 3:].values.flatten().mean()

# --- V. FOTOS ---
st.subheader("V. Registro Fotográfico")
fotos = st.file_uploader("Cargar evidencia", accept_multiple_files=True)

# --- PDF ---
if st.button("🚀 GENERAR INFORME OFICIAL"):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 1. INFO
    pdf.set_font("Arial", "", 10)
    pdf.cell(30, 6, "Cliente:", 0); pdf.cell(0, 6, cliente, 0, ln=1)
    pdf.cell(30, 6, "Planta:", 0); pdf.cell(0, 6, f"{planta} - {direccion}", 0, ln=1)
    pdf.cell(30, 6, "Atención:", 0); pdf.cell(0, 6, atencion, 0, ln=1)
    pdf.cell(30, 6, "Fecha:", 0); pdf.cell(0, 6, str(fecha_inf), 0, ln=1)
    
    # 2. TÉCNICA
    pdf.titulo_seccion("I", "SELLADO Y PLAGAS")
    estado = "CONFORME" if sellado_ok else "OBSERVADO"
    pdf.multi_cell(0, 6, f"Inspección de sellado: {estado}. Plaga objetivo: {plaga}.")
    
    pdf.titulo_seccion("II", "VOLÚMENES Y TIEMPOS")
    pdf.multi_cell(0, 6, f"Volumen tratado: {volumen_total} m3. Tiempo de exposición: {horas_exp:.1f} horas.")
    pdf.ln(2)
    
    h_tiempos = ["Evento", "Fecha", "Hora", "Total Horas"]
    d_tiempos = [["Inyección", str(f_ini), str(h_ini), f"{horas_exp:.1f}"], ["Ventilación", str(f_ter), str(h_ter), "---"]]
    pdf.tabla_estilizada(h_tiempos, d_tiempos, [45, 45, 45, 45])

    # 3. DOSIS
    pdf.titulo_seccion("III", "DOSIFICACIÓN Y DISTRIBUCIÓN")
    data_dosis_pdf = []
    for _, row in df_dosis.iterrows():
        data_dosis_pdf.append([str(row['Piso']), str(row['Bandejas']), str(row['Mini-Ropes'])])
    data_dosis_pdf.append(["TOTALES", str(total_bandejas), str(total_ropes)])
    pdf.tabla_estilizada(["Piso / Sector", "Bandejas", "Mini-Ropes"], data_dosis_pdf, [80, 50, 50])
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, f"DOSIS FINAL: {dosis_final:.2f} g/m3", ln=1, align="R")

    # 4. GRÁFICO (CON ARCHIVO TEMPORAL)
    pdf.add_page()
    pdf.titulo_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    eje_x = df_meds["Hrs Exp"]
    for col in cols_meds[3:]:
        ax.plot(eje_x, df_meds[col], marker='o', label=col)
    ax.axhline(300, color='red', linestyle='--')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize='small')
    ax.set_title("Curva de Gas por Piso")
    plt.tight_layout()
    
    # Guardado seguro en la nube
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_graf:
        fig.savefig(tmp_graf.name, dpi=300)
        tmp_graf_path = tmp_graf.name
    
    pdf.image(tmp_graf_path, x=10, w=190)
    pdf.ln(5)
    os.remove(tmp_graf_path) # Limpieza
    
    # Tabla Mediciones
    headers_pdf = ["Fecha", "Hora", "Hrs", "Sub", "P1", "P2", "P3", "P4", "P5"]
    vals_pdf = []
    for _, row in df_meds.iterrows():
        vals_pdf.append([str(x) for x in row])
    anchos = [20, 15, 12] + [20]*6
    pdf.tabla_estilizada(headers_pdf, vals_pdf, anchos)

    # 5. CONCLUSIONES
    pdf.titulo_seccion("V", "CONCLUSIONES")
    txt_concl = (f"1. Tiempo de exposición: {horas_exp:.1f} horas.\n2. Promedio concentración global: {promedio_ppm:.0f} PPM.\n3. Tratamiento aprobado.")
    pdf.multi_cell(0, 6, txt_concl)

    # 6. FOTOS (ARREGLO DE CARGA DE IMÁGENES)
    if fotos:
        pdf.add_page()
        pdf.titulo_seccion("VI", "ANEXO FOTOGRÁFICO")
        for i, f in enumerate(fotos):
            # Guardamos la foto en un lugar seguro del servidor temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(f.getvalue())
                tmp_path = tmp_file.name
            
            try:
                if i % 2 == 0: 
                    y_act = pdf.get_y()
                    pdf.image(tmp_path, x=10, y=y_act, w=90)
                else: 
                    pdf.image(tmp_path, x=110, y=y_act, w=90)
                    pdf.ln(70)
            except Exception as e:
                st.error(f"Error con la foto {i+1}: {e}")
            finally:
                os.remove(tmp_path) # Borramos la foto temporal para no llenar el servidor

    # Firma
    if os.path.exists('firma.png'):
        try:
            pdf.set_y(-40); pdf.image('firma.png', x=140, w=40); pdf.ln(5)
            pdf.cell(0, 5, "Nicholas Palma Carvajal", align="R", ln=1)
            pdf.cell(0, 5, "Supervisor Técnico", align="R", ln=1)
        except: pass

    # --- DESCARGA ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            pdf_data = f.read()
    
    st.success("✅ Informe Generado Exitosamente!")
    st.download_button(
        label="📲 DESCARGAR PDF FINAL",
        data=pdf_data,
        file_name="Informe_Rentokil_Final.pdf",
        mime="application/pdf"
    )
