import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from datetime import date, timedelta
from fpdf import FPDF
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.backend.db_connection import get_connection

# Ruta relativa
RUTA_REPORTES = "app/static/reportes"

# --- FUNCIÓN AUXILIAR PARA LIMPIAR TEXTO ---
def limpiar_texto(texto):
    """
    Permite tildes y ñ, pero elimina emojis y caracteres raros 
    que rompen FPDF (latin-1).
    """
    if not texto:
        return ""
    try:
        # Esto mantiene 'áéíóúñ' pero reemplaza emojis por '?'
        return str(texto).encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return str(texto)

# --- CLASE PDF ---
class PDF(FPDF):
    def __init__(self, nombre_usuario):
        super().__init__()
        self.nombre_usuario = limpiar_texto(nombre_usuario)

    def header(self):
        self.set_text_color(234, 88, 12) # Naranja Racheros
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, limpiar_texto("Reporte semanal de Racheros"), ln=True, align="C")
        
        self.set_text_color(50, 50, 50)
        self.set_font("Arial", "", 12)
        self.cell(0, 8, f"Usuario: {self.nombre_usuario}", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128)
        # Tilde en Página
        texto_pag = limpiar_texto(f'Página {self.page_no()}')
        self.cell(0, 10, texto_pag, 0, 0, 'C')

# --- GENERADOR DE GRÁFICO ---
def generar_grafico_temp(datos, etiquetas, ruta_img):
    plt.figure(figsize=(10, 4))
    plt.plot(etiquetas, datos, marker='o', linestyle='-', color='#ea580c', linewidth=2, markersize=8)
    plt.fill_between(etiquetas, datos, color='#ea580c', alpha=0.1)
    
    # Título con tildes para la imagen
    plt.title('Progreso de hábitos - Últimos 7 días', fontsize=12, color='#333333')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.yticks(range(0, max(datos) + 2))
    plt.savefig(ruta_img, bbox_inches='tight', dpi=100)
    plt.close()

# --- ESTILIZAR EXCEL ---
def estilizar_excel(ruta_excel, ruta_imagen, usuario, stats, rango_fechas):
    wb = load_workbook(ruta_excel)
    ws = wb.active
    ws.title = "Reporte semanal"

    # Estilos
    fuente_titulo = Font(name='Arial', size=18, bold=True, color="EA580C")
    fuente_subtitulo = Font(name='Arial', size=12, bold=True, color="555555")
    fuente_negrita = Font(name='Arial', bold=True)
    borde_delgado = Border(left=Side(style='thin'), right=Side(style='thin'), 
                           top=Side(style='thin'), bottom=Side(style='thin'))
    relleno_naranja = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
    relleno_gris = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    # Encabezado
    ws.merge_cells('B2:H2')
    ws['B2'] = "Reporte semanal de Racheros"
    ws['B2'].font = fuente_titulo
    ws['B2'].alignment = Alignment(horizontal='center')

    ws.merge_cells('B3:H3')
    ws['B3'] = f"Usuario: {usuario} | Periodo: {rango_fechas}"
    ws['B3'].font = fuente_subtitulo
    ws['B3'].alignment = Alignment(horizontal='center')

    # Dashboard Estadísticas (Izquierda)
    ws['B5'] = "Resumen semanal"
    ws['B5'].font = fuente_negrita
    
    metricas = [
        ("Hábitos completados", stats['completados']),
        ("Porcentaje total", f"{stats['porcentaje']}%"),
        ("Racha actual", f"{stats['racha']} días")
    ]

    fila_inicio = 6
    for titulo, valor in metricas:
        ws[f'B{fila_inicio}'] = titulo
        ws[f'C{fila_inicio}'] = valor
        
        ws[f'B{fila_inicio}'].fill = relleno_gris
        ws[f'B{fila_inicio}'].border = borde_delgado
        ws[f'C{fila_inicio}'].border = borde_delgado
        ws[f'C{fila_inicio}'].alignment = Alignment(horizontal='center')
        fila_inicio += 1

    # Insertar Imagen
    img = OpenpyxlImage(ruta_imagen)
    img.width = 450 
    img.height = 220
    ws.add_image(img, 'E5')

    # Estilo Tabla de Datos (Fila 14)
    encabezados = ["Fecha", "Hábito", "Estado"]
    ws['B14'] = encabezados[0]
    ws['C14'] = encabezados[1]
    ws['D14'] = encabezados[2]

    for celda in ws[14]:
        if celda.col_idx >= 2 and celda.col_idx <= 4: # Solo columnas B, C, D
            celda.fill = relleno_naranja
            celda.font = Font(color="FFFFFF", bold=True)
            celda.alignment = Alignment(horizontal='center')
            celda.border = borde_delgado

    # Ajustar anchos
    ws.column_dimensions['B'].width = 20 
    ws.column_dimensions['C'].width = 35 
    ws.column_dimensions['D'].width = 15 

    wb.save(ruta_excel)


def generar_reporte_semanal(id_usuario):
    conn = get_connection()

    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    # Formato de fecha con tildes si es necesario, aquí usamos numérico para evitar problemas de locales
    rango_fechas = f"{inicio_semana} al {fin_semana}"

    # 1. OBTENER NOMBRE
    nombre_usuario = "Usuario"
    with conn.cursor() as cursor:
        cursor.execute("SELECT nombre FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        user_data = cursor.fetchone()
        if user_data and user_data['nombre']:
            nombre_usuario = user_data['nombre'].title()

    # 2. DATOS GRÁFICO (Matplotlib maneja tildes bien si se configuran, aquí usamos sin tildes en etiquetas cortas)
    datos_grafico = []
    etiquetas_dias = []
    dias_semana_txt = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"] # Con tildes para el gráfico

    for i in range(6, -1, -1):
        fecha_calculo = hoy - timedelta(days=i)
        fecha_str = fecha_calculo.isoformat()
        dia_idx = int(fecha_calculo.strftime("%w"))
        etiquetas_dias.append(dias_semana_txt[dia_idx])

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total FROM registro_progreso r
                INNER JOIN habitos h ON r.id_habito = h.id_habito
                WHERE h.id_usuario = %s AND r.fecha = %s AND r.completado = 1
            """, (id_usuario, fecha_str))
            datos_grafico.append(cursor.fetchone()['total'])

    # 3. DATOS TABLA
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT h.nombre_habito, r.completado, r.fecha
            FROM habitos h
            LEFT JOIN registro_progreso r ON h.id_habito = r.id_habito
            WHERE h.id_usuario = %s AND r.fecha BETWEEN %s AND %s
            ORDER BY r.fecha DESC
        """, (id_usuario, inicio_semana, fin_semana))
        datos_detalle = cursor.fetchall()

    if sum(datos_grafico) == 0 and not datos_detalle:
         return {"hay_reporte": False}

    total_regs = len(datos_detalle)
    completados = sum(1 for d in datos_detalle if d["completado"])
    porcentaje = int((completados / total_regs) * 100) if total_regs > 0 else 0
    racha = 1 if datos_grafico[-1] > 0 else 0
    
    stats = {
        "completados": completados,
        "porcentaje": porcentaje,
        "racha": racha
    }

    # --- ARCHIVOS ---
    os.makedirs(RUTA_REPORTES, exist_ok=True)
    nombre_base = f"reporte_{id_usuario}_{inicio_semana}"
    
    ruta_pdf = os.path.join(RUTA_REPORTES, f"{nombre_base}.pdf")
    ruta_excel = os.path.join(RUTA_REPORTES, f"{nombre_base}.xlsx")
    ruta_img_temp = os.path.join(RUTA_REPORTES, f"chart_temp_{id_usuario}.png")

    generar_grafico_temp(datos_grafico, etiquetas_dias, ruta_img_temp)

    # --- A. EXCEL ---
    datos_excel = []
    for d in datos_detalle:
        # Excel soporta unicode nativo, no necesitamos limpiar_texto
        datos_excel.append({
            "Fecha": str(d["fecha"]),
            "Hábito": d["nombre_habito"].title(),
            "Estado": "Completado" if d["completado"] else "Pendiente"
        })
    
    df = pd.DataFrame(datos_excel)
    
    with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, startrow=13, startcol=1, sheet_name='Reporte Semanal')
    
    estilizar_excel(ruta_excel, ruta_img_temp, nombre_usuario, stats, rango_fechas)

    # --- B. PDF ---
    pdf = PDF(nombre_usuario)
    pdf.add_page()
    pdf.set_text_color(0)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, limpiar_texto(f"Periodo: {rango_fechas}"), ln=True)
    pdf.ln(2)
    
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Arial", "B", 11)
    
    # Etiquetas con tildes limpias para FPDF
    lbl_comp = limpiar_texto(f"Hábitos completados: {completados}")
    lbl_porc = limpiar_texto(f"Porcentaje: {porcentaje}%")
    lbl_racha = limpiar_texto(f"Racha actual: {racha}")

    pdf.cell(60, 10, lbl_comp, border=1, fill=True, align="C")
    pdf.cell(60, 10, lbl_porc, border=1, fill=True, align="C")
    pdf.cell(60, 10, lbl_racha, border=1, fill=True, align="C", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, limpiar_texto("Tu rendimiento gráfico"), ln=True)
    pdf.image(ruta_img_temp, x=10, w=190)
    pdf.ln(5)

    # Tabla PDF
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, limpiar_texto("Detalle de hábitos"), ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(234, 88, 12)
    pdf.set_text_color(255, 255, 255)
    
    # Encabezados tabla PDF
    pdf.cell(40, 8, "Fecha", 1, 0, 'C', True)
    pdf.cell(110, 8, limpiar_texto("Hábito"), 1, 0, 'L', True)
    pdf.cell(40, 8, "Estado", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0)
    
    for d in datos_detalle:
        estado = "Sí" if d["completado"] else "No" # Tilde en Sí
        
        # Limpieza crucial para el nombre del hábito en el PDF
        nombre_limpio = limpiar_texto(d["nombre_habito"].title())
        estado_limpio = limpiar_texto(estado)
        
        pdf.cell(40, 8, str(d["fecha"]), 1, 0, 'C')
        pdf.cell(110, 8, nombre_limpio, 1, 0, 'L')
        
        if d["completado"]:
            pdf.set_text_color(0, 120, 0)
        else:
            pdf.set_text_color(200, 0, 0)
        pdf.cell(40, 8, estado_limpio, 1, 1, 'C')
        pdf.set_text_color(0)

    pdf.output(ruta_pdf)

    if os.path.exists(ruta_img_temp):
        os.remove(ruta_img_temp)

    return {
        "hay_reporte": True,
        "semana": rango_fechas,
        "completados": completados,
        "total": total_regs,
        "porcentaje": porcentaje,
        "racha": racha,
        "ruta_pdf": ruta_pdf,
        "archivo_pdf": f"{nombre_base}.pdf",
        "archivo_excel": f"{nombre_base}.xlsx"
    }