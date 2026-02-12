import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os
import tempfile
from PIL import Image

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="Rentokil Mobile PRO")
COLOR_PRIMARIO = (227, 6, 19)
COLOR_TABLA_HEAD = (220, 220, 220)
COLOR_TABLA_FILA = (255, 255, 255)

class PDF(FPDF):
    def header(self):
        logo_path = 'logo.png'
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, 10, 8, 33)
            except:
                self.set_font("Arial", "B", 12)
                self.set_text_color(*COLOR_PRIMARIO)
                self.cell(40, 10, "RENTOKIL", ln=0)
        
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

# --- INTERFAZ ---
st.title("🛡️ Generador Rentokil v6.7")

# ... SECCIONES DE DATOS ...
st.subheader("I. Datos Generales")
DATABASE_MOLINOS = {
    "MOLINO CASABLANCA": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Alejandro Galaz N° 500, Casablanca", "volumen": 4850},
    "MOLINO LA ESTAMPA": {"cliente": "MOLINO LA ESTAMPA S.A.", "direccion": "Fermin Vivaceta 1053, Independencia", "volumen": 5500},
    "MOLINO FERRER": {"cliente": "MOLINO FERRER HERMANOS S.A.", "direccion": "Baquedano N° 647, San Bernardo", "volumen": 8127},
    "MOLINO EXPOSICIÓN": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Exposición N° 1657, Estación Central", "volumen": 7502},
    "MOLINO LINDEROS": {"cliente": "MOLINO LINDEROS S.A.", "direccion": "Villaseca Nº 1195, Buin", "volumen": 4800},
    "MOLINO MAIPÚ": {"cliente": "COMPAÑÍA MOLINERA SAN CRISTOBAL S.A.", "direccion": "Avenida Pajarito N° 1046, Maipú", "volumen": 4059}
}
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

st.markdown("**📸 Evidencia de Dosificación (Aparecerá en Página 1)**")
fotos_dosis = st.file_uploader("Subir fotos de bandejas/ropes instalados", accept_multiple_files=True, key="dosis")

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

st.subheader("V. Anexo Fotográfico (Fotos Generales)")
fotos_anexo = st.file_uploader("Cargar resto de evidencia", accept_multiple_files=True, key="anexo")

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
    
    # 2. TECNICA
    pdf.titulo_seccion("I", "SELLADO Y PLAGAS")
    pdf.multi_cell(0, 6, f"Inspección de sellado: {'CONFORME' if sellado_ok else 'OBSERVADO'}. Plaga objetivo: {plaga}.")
    pdf.titulo_seccion("II", "VOLÚMENES Y TIEMPOS")
    pdf.multi_cell(0, 6, f"Volumen tratado: {volumen_total} m3. Tiempo de exposición: {horas_exp:.1f} horas.")
    pdf.ln(2)
    pdf.tabla_estilizada(["Evento", "Fecha", "Hora", "Total Horas"], [["Inyección", str(f_ini), str(h_ini), f"{horas_exp:.1f}"], ["Ventilación", str(f_ter), str(h_ter), "---"]], [45, 45, 45, 45])
    
    # 3. DOSIS (PORTADA)
    pdf.titulo_seccion("III", "DOSIFICACIÓN")
    d_dosis = [[str(r['Piso']), str(r['Bandejas']), str(r['Mini-Ropes'])] for _, r in df_dosis.iterrows()]
    d_dosis.append(["TOTALES", str(total_bandejas), str(total_ropes)])
    pdf.tabla_estilizada(["Sector", "Bandejas", "Mini-Ropes"], d_dosis, [80, 50, 50])
    
    # FOTOS DOSIS PAGINA 1
    if fotos_dosis:
        pdf.ln(2)
        y_start = pdf.get_y()
        for i, f in enumerate(fotos_dosis[:2]):
            try:
                img = Image.open(f).convert('RGB')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                    img.save(tmp_img.name, format='JPEG', quality=80)
                    tmp_path = tmp_img.name
                x_pos = 10 if i == 0 else 105
                pdf.image(tmp_path, x=x_pos, y=y_start, w=85, h=45) 
                os.remove(tmp_path)
            except: pass
        pdf.ln(48) 

    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, f"DOSIS FINAL: {dosis_final:.2f} g/m3", ln=1, align="R")
    
    # 4. GRAFICO
    pdf.add_page()
    pdf.titulo_seccion("IV", "CONTROL DE CONCENTRACIÓN (PPM)")
    fig, ax = plt.subplots(figsize=(10, 4))
    eje_x_labels = df_meds["Fecha"] + "\n" + df_meds["Hora"]
    for col in df_meds.columns[2:]: 
        ax.plot(eje_x_labels, pd.to_numeric(df_meds[col], errors='coerce'), marker='o', label=col)
    ax.axhline(300, color='red', linestyle='--')
    ax.legend(fontsize='small')
    plt.xticks(rotation=45, fontsize=8)
    plt.tight_layout()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_graf:
        fig.savefig(tmp_graf.name, dpi=300)
        pdf.image(tmp_graf.name, x=10, w=190)
    pdf.ln(5)
    pdf.tabla_estilizada(["Fech", "Hr", "S", "P1", "P2", "P3", "P4", "P5"], [[str(x) for x in r] for _, r in df_meds.iterrows()], [25, 20, 20, 20, 20, 20, 20, 20])
    
    # --- CAMBIO DE ORDEN AQUI ---

    # 5. ITEM V: ANEXO FOTOGRÁFICO (ANTES DE CONCLUSIONES)
    if fotos_anexo:
        pdf.add_page()
        pdf.titulo_seccion("V", "ANEXO FOTOGRÁFICO")
        for i, f in enumerate(fotos_anexo):
            try:
                img = Image.open(f).convert('RGB')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                    img.save(tmp_img.name, format='JPEG', quality=85)
                    tmp_path = tmp_img.name
                
                # Control de posición
                if i % 2 == 0:
                    # Si queda poco espacio en la página, saltamos
                    if pdf.get_y() > 200: pdf.add_page()
                    y_act = pdf.get_y()
                    pdf.image(tmp_path, x=10, y=y_act, w=90)
                else: 
                    # La segunda foto va al lado
                    pdf.image(tmp_path, x=110, y=y_act, w=90)
                    pdf.ln(70) # Bajamos después de poner las dos
                
                os.remove(tmp_path)
            except: pass

    # 6. ITEM VI: CONCLUSIONES TÉCNICAS (AL FINAL)
    # Verificamos espacio. Si queda poco, pasamos a nueva página para que no se corte firma
    if pdf.get_y() > 220:
        pdf.add_page()
    else:
        pdf.ln(10) # Separación si viene de las fotos

    pdf.titulo_seccion("VI", "CONCLUSIONES TÉCNICAS")
    
    conclusiones_texto = (
        f"De acuerdo con los registros monitoreados, se certifica que el tratamiento de fumigación "
        f"en las instalaciones de {planta} se realizó cumpliendo un tiempo de exposición efectivo de "
        f"{horas_exp:.1f} horas.\n\n"
        f"El monitoreo de concentración de gas Fosfina (PH3) arrojó un promedio global de {promedio_ppm:.0f} PPM, "
        f"manteniéndose en todo momento dentro de los rangos de eficacia requeridos para el control de "
        f"{plaga}.\n\n"
        f"Por lo anterior, el servicio se declara CONFORME, cumpliendo con los estándares de seguridad y "
        f"calidad establecidos por Rentokil Initial Chile."
    )
    
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, conclusiones_texto)
    pdf.ln(15) # Espacio antes de la firma

    # FIRMA CENTRADA Y MAS GRANDE
    if os.path.exists('firma.png'):
        try:
            # Calculamos el centro de la pagina (ancho A4 ~210mm)
            # Queremos la firma de 60mm de ancho (más alargada)
            ancho_firma = 60
            x_centro = (210 - ancho_firma) / 2
            
            # Verificamos que no se salga de la hoja
            if pdf.get_y() > 240: pdf.add_page()
            
            # Ponemos la imagen centrada
            pdf.image('firma.png', x=x_centro, w=ancho_firma)
            
            # Texto debajo, también centrado
            pdf.ln(5)
            pdf.cell(0, 5, "Nicholas Palma Carvajal", align="C", ln=1)
            pdf.cell(0, 5, "Supervisor Técnico", align="C", ln=1)
        except: pass

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📲 DESCARGAR PDF FINAL", f.read(), "Informe_Rentokil.pdf", "application/pdf")
