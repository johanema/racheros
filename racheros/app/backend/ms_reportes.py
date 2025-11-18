import os
from fpdf import FPDF
from datetime import date, timedelta
from app.backend.db_connection import get_connection

RUTA_REPORTES = "app/static/reportes"


class PDF(FPDF):
    """FPDF configurado para soportar UTF-8."""
    def __init__(self):
        super().__init__()
        self.add_page()
        # Fuente DejaVu Sans compatible con acentos y emojis
        self.add_font('DejaVu', '', 'app/static/fonts/DejaVuSans.ttf', uni=True)
        self.set_font('DejaVu', '', 12)


def generar_reporte_semanal(id_usuario):
    conn = get_connection()

    # 1. Calcular semana actual
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)

    # 2. Obtener datos
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT u.nombre, h.nombre_habito, r.completado, r.fecha
            FROM usuarios u
            LEFT JOIN habitos h ON u.id_usuario = h.id_usuario
            LEFT JOIN registro_progreso r ON h.id_habito = r.id_habito
            WHERE u.id_usuario = %s AND r.fecha BETWEEN %s AND %s
            ORDER BY r.fecha ASC
        """, (id_usuario, inicio_semana, fin_semana))
        datos = cursor.fetchall()

    # 3. Verificar datos
    if not datos:
        return {
            "hay_reporte": False,
            "mensaje": "No hay información suficiente",
            "archivo": None
        }

    # 4. Crear carpeta si no existe
    os.makedirs(RUTA_REPORTES, exist_ok=True)

    # 5. Ruta del PDF
    nombre_pdf = f"reporte_{id_usuario}_{inicio_semana}.pdf"
    ruta_pdf = os.path.join(RUTA_REPORTES, nombre_pdf)

    # 6. Crear PDF UTF-8
    pdf = PDF()

    # Título
    pdf.set_font("DejaVu", "", 18)
    pdf.cell(0, 10, "Reporte semanal de hábitos", ln=1, align="C")
    pdf.ln(4)

    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 10, f"Semana del {inicio_semana} al {fin_semana}", ln=1)
    pdf.ln(6)

    # 7. Agregar registros
    for fila in datos:
        texto = (
            f"{fila['fecha']} - {fila['nombre_habito']} : "
            f"{'✔️ Completado' if fila['completado'] else '❌ No completado'}"
        )
        pdf.multi_cell(0, 8, texto)

    # 8. Guardar archivo
    pdf.output(ruta_pdf)

    return {
        "hay_reporte": True,
        "archivo": nombre_pdf,
        "ruta": ruta_pdf
    }
