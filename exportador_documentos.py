"""
Módulo de Exportação de Dados e Geração de Relatórios Oficiais de Conformidade
Gera XML/CSV estruturados para ERPs e Relatórios PDF via FPDF2 (Python Puro).
"""

import io
import json
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF


class PDFComplianceReport(FPDF):
    def header(self):
        # Cabeçalho Escuro Corporativo
        self.set_fill_color(26, 37, 47)
        self.rect(0, 0, 210, 30, 'F')
        
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 8)
        self.cell(0, 8, "CERTIFICADO DE AUDITORIA DE COMPLIANCE", ln=True)
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(189, 195, 199)
        self.cell(0, 5, "HS-Code Automator | Middleware Aduaneiro & Multimodal Enterprise", ln=True)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, "Relatorio gerado automaticamente por algoritmo deterministico HS-Code Automator.", align="C")


def gerar_csv_erp(dados: dict) -> str:
    """Gera uma string CSV estruturada pronta para importação em ERPs/CargoWise."""
    itens = dados.get("itens_classificados", [])
    rows = []
    
    for item in itens:
        rows.append({
            "Fatura_Numero": dados.get("fatura_num", ""),
            "Fornecedor": dados.get("fornecedor", ""),
            "Item_Numero": item.get("item_num", ""),
            "Descricao_Original": item.get("descricao_original", ""),
            "HS_Code_6Dig": item.get("hs_code_6dig", ""),
            "NCM_Taric_8Dig": item.get("ncm_code_8dig", ""),
            "UN_Number": item.get("un_number", "N/A"),
            "Classe_Risco": item.get("classe_risco", "N/A"),
            "Grau_Confianca_Pct": item.get("grau_confianca", 0),
            "Status_Item": item.get("alerta_duvida") or "Aprovado"
        })
    
    df = pd.DataFrame(rows)
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig")


def gerar_xml_cargowise(dados: dict) -> str:
    """Gera um ficheiro XML compatível com esquemas de integração aduaneira (CargoWise / ERPs)."""
    root = ET.Element("Declaration", attrib={"version": "1.0", "system": "HS-Code-Automator"})
    
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "InvoiceNumber").text = str(dados.get("fatura_num", "N/A"))
    ET.SubElement(header, "Supplier").text = str(dados.get("fornecedor", "N/A"))
    ET.SubElement(header, "TransportMode").text = str(dados.get("modal_transporte", "AERO"))
    ET.SubElement(header, "AuditStatus").text = str(dados.get("status_aprovacao", "N/A"))
    
    items_node = ET.SubElement(root, "LineItems")
    for item in dados.get("itens_classificados", []):
        item_node = ET.SubElement(items_node, "Item")
        ET.SubElement(item_node, "LineNumber").text = str(item.get("item_num", ""))
        ET.SubElement(item_node, "Description").text = str(item.get("descricao_original", ""))
        ET.SubElement(item_node, "HSCode").text = str(item.get("hs_code_6dig", ""))
        ET.SubElement(item_node, "NCMCode").text = str(item.get("ncm_code_8dig", ""))
        ET.SubElement(item_node, "UNNumber").text = str(item.get("un_number", "N/A"))
        ET.SubElement(item_node, "HazardClass").text = str(item.get("classe_risco", "N/A"))
        ET.SubElement(item_node, "Confidence").text = f"{item.get('grau_confianca', 0)}%"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    
    out = io.BytesIO()
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out.getvalue().decode("utf-8")


def gerar_pdf_relatorio_compliance(dados: dict, user_email: str) -> bytes:
    """Gera o PDF do Certificado de Auditoria via FPDF2 de alta performance."""
    pdf = PDFComplianceReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    fatura = str(dados.get("fatura_num", "N/A"))
    fornecedor = str(dados.get("fornecedor", "N/A"))
    modal = str(dados.get("modal_transporte", "AERO"))
    status = str(dados.get("status_aprovacao", "N/A"))
    alertas = dados.get("alertas_criticos_codigo", [])
    
    # Cartão de Informações
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(10, 35, 190, 28, 'DF')
    
    pdf.set_xy(12, 37)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(60, 4, "FATURA", ln=False)
    pdf.cell(65, 4, "FORNECEDOR", ln=False)
    pdf.cell(60, 4, "MODAL", ln=True)
    
    pdf.set_xy(12, 42)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(60, 6, fatura, ln=False)
    pdf.cell(65, 6, fornecedor[:30], ln=False)
    pdf.cell(60, 6, modal, ln=True)
    
    pdf.set_xy(12, 50)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(60, 4, "UTILIZADOR", ln=False)
    pdf.cell(125, 4, "RESULTADO DA AUDITORIA", ln=True)
    
    pdf.set_xy(12, 55)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(60, 5, user_email, ln=False)
    
    if "APROVADO" in status:
        pdf.set_text_color(46, 125, 50)
    else:
        pdf.set_text_color(198, 40, 40)
    pdf.cell(125, 5, status, ln=True)
    
    # Caixa de Alertas
    pdf.ln(10)
    if alertas:
        pdf.set_fill_color(254, 242, 242)
        pdf.set_draw_color(239, 68, 68)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(185, 28, 28)
        
        pdf.cell(190, 7, "  ALERTAS CRITICOS DE COMPLIANCE DETETADOS:", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 8.5)
        for al in alertas:
            # Substitui carateres não-latin1 para evitar erro no PDF simples
            al_clean = al.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(190, 5, f"   - {al_clean}", border=0)
    else:
        pdf.set_fill_color(240, 253, 244)
        pdf.set_draw_color(34, 197, 94)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(21, 128, 61)
        pdf.cell(190, 7, "  Nenhuma incompatibilidade regulatoria ou infracao detetada.", ln=True, fill=True)
        
    # Tabela de Produtos
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, "Itens Classificados & Regulacao Perigosa", ln=True)
    pdf.ln(2)
    
    # Cabeçalho da Tabela
    pdf.set_fill_color(51, 65, 85)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    
    pdf.cell(10, 6, "#", border=1, align="C", fill=True)
    pdf.cell(75, 6, "Descricao do Produto", border=1, align="L", fill=True)
    pdf.cell(25, 6, "HS Code", border=1, align="C", fill=True)
    pdf.cell(25, 6, "NCM/Taric", border=1, align="C", fill=True)
    pdf.cell(25, 6, "UN Number", border=1, align="C", fill=True)
    pdf.cell(30, 6, "Classe", border=1, align="C", fill=True)
    pdf.ln()
    
    # Linhas da Tabela
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "", 8)
    fill = False
    
    for item in dados.get("itens_classificados", []):
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        
        num = str(item.get('item_num', '-'))
        desc = str(item.get('descricao_original', '-'))[:40].encode('latin-1', 'replace').decode('latin-1')
        hs = str(item.get('hs_code_6dig', '-'))
        ncm = str(item.get('ncm_code_8dig', '-'))
        un = str(item.get('un_number', 'N/A'))
        classe = str(item.get('classe_risco', 'N/A'))
        
        pdf.cell(10, 6, num, border=1, align="C", fill=fill)
        pdf.cell(75, 6, desc, border=1, align="L", fill=fill)
        pdf.cell(25, 6, hs, border=1, align="C", fill=fill)
        pdf.cell(25, 6, ncm, border=1, align="C", fill=fill)
        pdf.cell(25, 6, un, border=1, align="C", fill=fill)
        pdf.cell(30, 6, classe, border=1, align="C", fill=fill)
        pdf.ln()
        fill = not fill

    return bytes(pdf.output())