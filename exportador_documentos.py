"""
Módulo de Exportação de Dados e Geração de Relatórios Oficiais de Conformidade
Gera XML/CSV estruturados para ERPs e Relatórios PDF via WeasyPrint.
"""

import io
import json
import xml.etree.ElementTree as ET
import pandas as pd
from weasyprint import HTML


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
    ET.SubElement(header, "TransportMode").text = str(dados.get("modal_transporte", "AÉREO"))
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
    """Gera o PDF do Certificado de Auditoria de Compliance usando HTML + WeasyPrint."""
    fatura = dados.get("fatura_num", "N/A")
    fornecedor = dados.get("fornecedor", "N/A")
    modal = dados.get("modal_transporte", "AÉREO")
    status = dados.get("status_aprovacao", "N/A")
    status_cor = "#2e7d32" if "APROVADO" in status else "#c62828"
    
    itens = dados.get("itens_classificados", [])
    alertas = dados.get("alertas_criticos_codigo", [])
    
    rows_html = ""
    for item in itens:
        rows_html += f"""
        <tr>
            <td style="text-align: center;">{item.get('item_num', '-')}</td>
            <td>{item.get('descricao_original', '-')}</td>
            <td style="text-align: center; font-weight: bold;">{item.get('hs_code_6dig', '-')}</td>
            <td style="text-align: center;">{item.get('ncm_code_8dig', '-')}</td>
            <td style="text-align: center;">{item.get('un_number', 'N/A')}</td>
            <td style="text-align: center;">{item.get('classe_risco', 'N/A')}</td>
            <td style="text-align: center;">{item.get('grau_confianca', 0)}%</td>
        </tr>
        """
        
    alertas_html = ""
    if alertas:
        alertas_items = "".join([f"<li style='color: #c62828; font-weight: bold;'>{a}</li>" for a in alertas])
        alertas_html = f"""
        <div style="background-color: #ffebee; border-left: 4px solid #c62828; padding: 12px; margin-top: 15px; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #c62828; font-size: 13pt;">⚠️ Bloqueios e Alertas Críticos de Regulação:</h3>
            <ul style="margin-bottom: 0; padding-left: 20px;">
                {alertas_items}
            </ul>
        </div>
        """
    else:
        alertas_html = """
        <div style="background-color: #e8f5e9; border-left: 4px solid #2e7d32; padding: 12px; margin-top: 15px; border-radius: 4px;">
            <p style="margin: 0; color: #2e7d32; font-weight: bold;">🟢 Nenhuma incompatibilidade regulatória ou infração detetada.</p>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 15mm 12mm;
                background-color: #ffffff;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 10pt;
                color: #2c3e50;
                margin: 0;
                padding: 0;
            }}
            .header {{
                background-color: #1a252f;
                color: white;
                padding: 20px;
                margin: -15mm -12mm 20px -12mm;
            }}
            .header h1 {{
                margin: 0;
                font-size: 18pt;
                letter-spacing: 0.5px;
            }}
            .header p {{
                margin: 5px 0 0 0;
                font-size: 9pt;
                color: #bdc3c7;
            }}
            .info-grid {{
                width: 100%;
                margin-bottom: 20px;
                border-collapse: collapse;
            }}
            .info-grid td {{
                padding: 8px;
                border: 1px solid #e2e8f0;
                background-color: #f8fafc;
            }}
            .info-label {{
                font-weight: bold;
                color: #64748b;
                font-size: 8.5pt;
                text-transform: uppercase;
            }}
            .info-val {{
                font-size: 10pt;
                color: #0f172a;
                font-weight: bold;
            }}
            .status-badge {{
                display: inline-block;
                padding: 6px 12px;
                color: white;
                background-color: {status_cor};
                font-weight: bold;
                border-radius: 4px;
                font-size: 11pt;
            }}
            table.data-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            table.data-table th {{
                background-color: #334155;
                color: white;
                padding: 8px;
                font-size: 9pt;
                text-align: left;
            }}
            table.data-table td {{
                padding: 8px;
                border-bottom: 1px solid #e2e8f0;
                font-size: 9pt;
            }}
            table.data-table tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            .footer {{
                margin-top: 30px;
                border-top: 1px solid #cbd5e1;
                padding-top: 10px;
                font-size: 8pt;
                color: #94a3b8;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CERTIFICADO DE AUDITORIA DE COMPLIANCE</h1>
            <p>HS-Code Automator | Middleware Aduaneiro & Multimodal Enterprise</p>
        </div>

        <table class="info-grid">
            <tr>
                <td width="33%">
                    <div class="info-label">Nº de Fatura</div>
                    <div class="info-val">{fatura}</div>
                </td>
                <td width="33%">
                    <div class="info-label">Fornecedor</div>
                    <div class="info-val">{fornecedor}</div>
                </td>
                <td width="33%">
                    <div class="info-label">Modal de Transporte</div>
                    <div class="info-val">{modal}</div>
                </td>
            </tr>
            <tr>
                <td>
                    <div class="info-label">Auditado Por</div>
                    <div class="info-val">{user_email}</div>
                </td>
                <td colspan="2">
                    <div class="info-label">Resultado da Validação Estrita</div>
                    <div style="margin-top: 4px;"><span class="status-badge">{status}</span></div>
                </td>
            </tr>
        </table>

        {alertas_html}

        <h3 style="margin-top: 25px; color: #1e293b; border-bottom: 2px solid #cbd5e1; padding-bottom: 5px;">
            Itens Classificados & Regulação Perigosa
        </h3>

        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 6%;">#</th>
                    <th>Descrição do Produto</th>
                    <th style="width: 14%; text-align: center;">HS Code</th>
                    <th style="width: 14%; text-align: center;">NCM/Taric</th>
                    <th style="width: 12%; text-align: center;">UN Number</th>
                    <th style="width: 12%; text-align: center;">Classe</th>
                    <th style="width: 10%; text-align: center;">Conf.</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            Relatório gerado automaticamente por algoritmo determinístico HS-Code Automator.<br>
            A conformidade foi checada com base nos regulamentos vigentes IATA DGR, IMDG Code e ADR.
        </div>
    </body>
    </html>
    """
    
    return HTML(string=html_content).write_pdf()