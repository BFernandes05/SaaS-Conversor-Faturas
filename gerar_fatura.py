import os
import platform
import subprocess
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def obter_caminho_desktop():
    # Encontra o caminho exato da Área de Trabalho (Desktop) no Windows/Mac/Linux
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    if not os.path.exists(desktop):
        # Caso o sistema esteja em Português
        desktop = os.path.join(os.path.expanduser('~'), 'Área de Trabalho')
    return desktop

def abrir_ficheiro(caminho_ficheiro):
    # Abre o PDF automaticamente no leitor padrão do sistema operativo
    if platform.system() == 'Windows':
        os.startfile(caminho_ficheiro)
    elif platform.system() == 'Darwin': # macOS
        subprocess.call(['open', caminho_ficheiro])
    else: # Linux
        subprocess.call(['xdg-open', caminho_ficheiro])

def criar_fatura_comercial_importacao():
    # Guardar diretamente no Desktop
    desktop_path = obter_caminho_desktop()
    filepath = os.path.join(desktop_path, "fatura_importacao_exemplo.pdf")

    # 1. Configuração do Documento PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=20, leading=24,
        textColor=colors.HexColor('#1E293B'), spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle', parent=styles['Normal'], fontSize=9, leading=12,
        textColor=colors.HexColor('#334155')
    )
    
    bold_style = ParagraphStyle('BoldStyle', parent=normal_style, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('CellStyle', parent=normal_style, fontSize=8, leading=10)

    elements = []

    # 2. Cabeçalho
    elements.append(Paragraph("COMMERCIAL INVOICE / 商业发票", title_style))
    elements.append(Spacer(1, 10))

    header_data = [
        [
            Paragraph("<b>EXPORTER / SHIPPER:</b><br/>Shenzhen Precision Metal Parts Co., Ltd.<br/>Building 4, Industrial Zone, Bao'an District<br/>Shenzhen, Guangdong, China<br/>TAX ID: CN91440300MA5***", normal_style),
            Paragraph("<b>INVOICE NO:</b> SZ-2026-89412<br/><b>DATE:</b> 2026-08-10<br/><b>INCOTERM:</b> FOB Shenzhen<br/><b>CURRENCY:</b> USD", normal_style)
        ],
        [
            Paragraph("<b>IMPORTER / CONSIGNEE:</b><br/>Global Tech Solutions Lda.<br/>Zona Industrial de Maia, Lote 12<br/>4470-000 Maia, Portugal<br/>VAT: PT501234567", normal_style),
            Paragraph("<b>PORT OF LOADING:</b> Shenzhen, China<br/><b>PORT OF DISCHARGE:</b> Leixões, Portugal<br/><b>PAYMENT TERMS:</b> T/T 30 days", normal_style)
        ]
    ]

    header_table = Table(header_data, colWidths=[3.75 * inch, 3.75 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # 3. Tabela de Produtos
    table_data = [
        [
            Paragraph("<b>Item</b>", bold_style),
            Paragraph("<b>Description of Goods</b>", bold_style),
            Paragraph("<b>Qty</b>", bold_style),
            Paragraph("<b>Unit Price (USD)</b>", bold_style),
            Paragraph("<b>Total (USD)</b>", bold_style)
        ],
        [
            Paragraph("1", cell_style),
            Paragraph("Stainless Steel Hex Head Screws (Grade 316) - M8x40mm for industrial machine assembly.", cell_style),
            Paragraph("50,000 pcs", cell_style),
            Paragraph("$0.12", cell_style),
            Paragraph("$6,000.00", cell_style)
        ],
        [
            Paragraph("2", cell_style),
            Paragraph("Multi-layer Printed Circuit Boards (Rigid PCB, populated with passive components, for telecommunication devices).", cell_style),
            Paragraph("2,500 pcs", cell_style),
            Paragraph("$14.50", cell_style),
            Paragraph("$36,250.00", cell_style)
        ],
        [
            Paragraph("3", cell_style),
            Paragraph("Brushless DC Electric Motor, Output: 450W, Single-Phase, 24V, used for automated conveyor belts.", cell_style),
            Paragraph("120 pcs", cell_style),
            Paragraph("$85.00", cell_style),
            Paragraph("$10,200.00", cell_style)
        ],
        [
            Paragraph("4", cell_style),
            Paragraph("Rigid PVC Plastic Pipes for fluid transport, outer diameter 50mm, non-reinforced.", cell_style),
            Paragraph("1,000 meters", cell_style),
            Paragraph("$3.20", cell_style),
            Paragraph("$3,200.00", cell_style)
        ],
        [
            Paragraph("5", cell_style),
            Paragraph("Optical Photoelectric Sensors with LED indicator for industrial position detection.", cell_style),
            Paragraph("500 pcs", cell_style),
            Paragraph("$18.00", cell_style),
            Paragraph("$9,000.00", cell_style)
        ]
    ]

    product_table = Table(table_data, colWidths=[0.5 * inch, 4.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(product_table)
    elements.append(Spacer(1, 15))

    # 4. Totais
    total_data = [
        [Paragraph("<b>TOTAL FOB VALUE:</b>", bold_style), Paragraph("<b>$64,650.00 USD</b>", bold_style)],
        [Paragraph("<b>TOTAL NET WEIGHT:</b>", normal_style), Paragraph("1,840.00 KGS", normal_style)],
        [Paragraph("<b>TOTAL GROSS WEIGHT:</b>", normal_style), Paragraph("2,050.00 KGS", normal_style)]
    ]
    
    total_table = Table(total_data, colWidths=[5.5 * inch, 2.0 * inch])
    total_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(total_table)
    elements.append(Spacer(1, 20))

    declaration_text = "We hereby certify that this invoice is true and correct, and that the goods originating from China are as described above."
    elements.append(Paragraph(f"<i>{declaration_text}</i>", normal_style))

    # Construir PDF
    doc.build(elements)
    
    print(f"\n[SUCESSO] Fatura guardada em:\n{filepath}")
    
    # Abrir automaticamente
    abrir_ficheiro(filepath)

if __name__ == "__main__":
    criar_fatura_comercial_importacao()