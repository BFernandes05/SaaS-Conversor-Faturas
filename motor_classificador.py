import os
import json
import pdfplumber
from groq import Groq
from typing import Dict, Any

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extrair_texto_fatura(caminho_pdf: str) -> str:
    if not os.path.exists(caminho_pdf):
        raise FileNotFoundError(f"O ficheiro {caminho_pdf} não foi encontrado.")
        
    texto_completo = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages):
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto_completo += f"\n--- PÁGINA {i+1} ---\n" + texto_pagina
                
    return texto_completo

def classificar_itens_com_ia(texto_fatura: str, modal: str = "AÉREO") -> Dict[str, Any]:
    prompt_sistema = f"""
    Você é um Despachante e Especialista Logístico Multimodal em Classificação Fiscal (HS Code/NCM) e Compliance de Carga Perigosa.
    O modal de transporte selecionado para este embarque é: **{modal}**.

    Sua missão é analisar o texto da Commercial Invoice / Packing List e retornar as classificações fiscais e alertas de compliance.

    Regras de Análise por Modal:
    - Se Modal == "AÉREO (IATA DGR)": Identifique UN Numbers, Packing Instructions (PI) e restrições de aeronave de passageiros.
    - Se Modal == "MARÍTIMO (IMDG)": Identifique a Classe de Risco, UN Number e alertas de SEGREGAÇÃO (se produtos incompatíveis estão no mesmo lote).
    - Se Modal == "RODOVIÁRIO (ADR)": Identifique UN Number, quantidade líquida e aplique a estimativa da Regra dos 1000 Pontos (Isenção ADR 1.1.3.6).

    Responda EXCLUSIVAMENTE em formato JSON válido, seguindo estritamente esta estrutura:
    {{
      "fatura_num": "número da fatura",
      "fornecedor": "nome do fornecedor",
      "modal_analisado": "{modal}",
      "itens_classificados": [
        {{
          "item_num": 1,
          "descricao_original": "descrição do produto",
          "hs_code_6dig": "código 6 dígitos ex: 8507.60",
          "ncm_code_8dig": "código 8 dígitos ex: 8507.60.00",
          "grau_confianca": 95,
          "un_number": "ex: UN 3481 ou N/A",
          "classe_risco": "ex: Classe 9 ou N/A",
          "justificativa_legal": "fundamentação da classificação",
          "alerta_duvida": "alerta específico do modal {modal} ou null se seguro"
        }}
      ],
      "resumo_compliance_modal": "Resumo geral do risco para o transporte {modal} (ex: Carga Aprovada, Alerta de Segregação, Exige Licença Especial)"
    }}
    """

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Analise esta fatura para o modal {modal} e devolva APENAS o JSON:\n\n{texto_fatura}"}
            ],
            response_format={"type": "json_object"}
        )
        
        resultado_json = json.loads(response.choices[0].message.content)
        return resultado_json

    except Exception as e:
        print(f"\n[ERRO GROQ API] Falha no processamento: {e}")
        return {}