import os
import json
import pdfplumber
import ollama  # Biblioteca do Ollama Local
from typing import Dict, Any

def obter_caminho_desktop() -> str:
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    if not os.path.exists(desktop):
        desktop = os.path.join(os.path.expanduser('~'), 'Área de Trabalho')
    return desktop

# ---------------------------------------------------------------------
# 1. CAMADA DE INGESTÃO: EXTRAÇÃO DO TEXTO DO PDF
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# 2. CAMADA DE INTELIGÊNCIA: CLASSIFICAÇÃO COM LLAMA 3.1 LOCAL
# ---------------------------------------------------------------------
def classificar_itens_com_ia(texto_fatura: str) -> Dict[str, Any]:
    """
    Envia o texto da fatura para o Llama 3.1 a rodar LOCALMENTE no teu PC.
    """
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

    print("\n[LOCAL AI] Processando no teu Llama 3.1 local... Aguarde alguns segundos...")
    
    try:
        # Chamada direta para o teu modelo Local via Ollama
        response = ollama.chat(
            model='llama3.1',
            messages=[
                {'role': 'system', 'content': prompt_sistema},
                {'role': 'user', 'content': f"Analise esta fatura e devolva APENAS o JSON:\n\n{texto_fatura}"}
            ],
            format='json'  # Força o Llama a responder obrigatoriamente em formato JSON estruturado
        )
        
        # Converte a resposta em dicionário Python
        resultado_json = json.loads(response['message']['content'])
        return resultado_json

    except Exception as e:
        print(f"\n[ERRO LOCAL AI] Falha ao comunicar com o Ollama: {e}")
        print("Certifica-te de que o Ollama está a correr na tua máquina.")
        return {}

# ---------------------------------------------------------------------
# 3. PIPELINE DE EXECUÇÃO
# ---------------------------------------------------------------------
if __name__ == "__main__":
    desktop = obter_caminho_desktop()
    caminho_pdf = os.path.join(desktop, "fatura_importacao_exemplo.pdf")
    
    print("==========================================================")
    print("   MIDDLEWARE HS-CODE - MOTOR LOCAL LLAMA 3.1 (OFFLINE)")
    print("==========================================================")
    
    print(f"\n1. Lendo o ficheiro: {caminho_pdf}...")
    texto_extraido = extrair_texto_fatura(caminho_pdf)
    print("   [OK] Texto extraído com sucesso do PDF!")
    
    print("\n2. Processando com a tua IA Local...")
    resultado_classificacao = classificar_itens_com_ia(texto_extraido)
    
    if resultado_classificacao:
        print("\n3. RESULTADO PROCESSADO PELA TUA IA LOCAL:\n")
        print(json.dumps(resultado_classificacao, indent=2, ensure_ascii=False))
        
        caminho_json_saida = os.path.join(desktop, "resultado_classificacao.json")
        with open(caminho_json_saida, "w", encoding="utf-8") as f:
            json.dump(resultado_classificacao, f, indent=2, ensure_ascii=False)
            
        print(f"\n[SUCESSO] Ficheiro guardado em:\n{caminho_json_saida}")