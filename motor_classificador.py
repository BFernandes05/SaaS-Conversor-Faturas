import os
import json
import pdfplumber
from groq import Groq
from typing import Dict, Any

# Instancia o cliente da Groq (a chave de API fica armazenada em variáveis de ambiente)
# Para testes locais basta definir: os.environ["GROQ_API_KEY"] = "sua_chave_aqui"
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

def classificar_itens_com_ia(texto_fatura: str) -> Dict[str, Any]:
    prompt_sistema = """
    Você é um Despachante Alfandegário Especialista em Classificação Fiscal Internacional (Sistema Harmonizado - HS Code e NCM/Taric).
    Sua tarefa é analisar o texto de uma Commercial Invoice, extrair a lista de produtos e determinar a classificação fiscal mais adequada para cada item.

    Regras Importantes:
    - Responda EXCLUSIVAMENTE em formato JSON válido, sem textos antes ou depois.
    - Estrutura JSON exata esperada:
    {
      "fatura_num": "número da fatura aqui",
      "fornecedor": "nome do fornecedor aqui",
      "itens_classificados": [
        {
          "item_num": 1,
          "descricao_original": "descrição completa do produto",
          "hs_code_6dig": "código de 6 dígitos ex: 7318.15",
          "ncm_code_8dig": "código de 8 dígitos ex: 7318.15.00",
          "grau_confianca": 95,
          "justificativa_legal": "motivo técnico da classificação",
          "alerta_duvida": null
        }
      ]
    }
    """

    try:
        # Chamada à API da Groq (Executa Llama 3.1 na nuvem em tempo real)
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Analise esta fatura e devolva APENAS o JSON:\n\n{texto_fatura}"}
            ],
            response_format={"type": "json_object"}
        )
        
        resultado_json = json.loads(response.choices[0].message.content)
        return resultado_json

    except Exception as e:
        print(f"\n[ERRO GROQ API] Falha no processamento: {e}")
        return {}