"""
Módulo Determinístico de Compliance Logístico Multimodal
Aplica regras matematicamente estritas sem depender de Inteligência Artificial.
"""

from typing import Dict, Any, List

# Matriz de Incompatibilidade de Segregação IMDG (Simplificada para Regras Críticas)
# Chave: Classe de Risco -> Valor: Lista de Classes Incompatíveis no mesmo contentor
IMDG_INCOMPATIBILIDADES = {
    "1": ["2", "3", "4", "5", "8"],  # Explosivos são incompatíveis com quase tudo
    "3": ["5.1", "5.2"],             # Líquidos Inflamáveis não misturam com Oxidantes/Peróxidos
    "5.1": ["3", "4.1", "8"],        # Oxidantes reagem violentamente com Combustíveis e Ácidos
    "8": ["1", "5.1"]                # Corrosivos
}

# Fatores de Multiplicação do ADR (Regra dos 1000 Pontos - Isenção 1.1.3.6)
ADR_FATORES_CATEGORIA = {
    "1": 50,   # Categoria de Transporte 1 (Risco Alto) -> Multiplica por 50
    "2": 3,    # Categoria de Transporte 2 (Risco Médio) -> Multiplica por 3
    "3": 1,    # Categoria de Transporte 3 (Risco Baixo) -> Multiplica por 1
    "4": 0     # Categoria de Transporte 4 (Sem Limite de Pontos)
}


def validar_iata_aereo(item: Dict[str, Any]) -> List[str]:
    """Validações estritas para o Modal Aéreo (IATA DGR)."""
    alertas = []
    un = str(item.get("un_number", "")).upper()
    
    # Exemplo Determinístico: Baterias de Lítio (UN 3480 / UN 3481)
    if "3480" in un:
        alertas.append("🛑 [IATA CRÍTICO] UN 3480 (Lithium Ion Batteries) é estritamente PROIBIDO em aeronaves de passageiros (PAX). Deve ser despachado como Cargo Aircraft Only (CAO).")
    
    return alertas


def validar_imdg_maritimo(itens: List[Dict[str, Any]]) -> List[str]:
    """Validações de Segregação de Contentor para o Modal Marítimo (IMDG Code)."""
    alertas = []
    classes_presentes = set()

    for item in itens:
        classe = str(item.get("classe_risco", "")).replace("Classe", "").strip()
        if classe and classe != "N/A":
            classes_presentes.add(classe)

    # Verificar incompatibilidade cruzada no mesmo lote/contentor
    for c1 in classes_presentes:
        if c1 in IMDG_INCOMPATIBILIDADES:
            incomp = IMDG_INCOMPATIBILIDADES[c1]
            for c2 in classes_presentes:
                if c2 in incomp:
                    alertas.append(f"💥 [IMDG BLOQUEIO DE SEGREGAÇÃO] Incompatibilidade detetada no contentor: Classe {c1} não pode ser embalada juntamente com a Classe {c2}!")
    
    return list(set(alertas))


def validar_adr_rodoviario(itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cálculo da Regra dos 1000 Pontos para Isenção Parcial ADR (1.1.3.6)."""
    pontos_totais = 0
    
    for item in itens:
        cat = str(item.get("categoria_transporte", "3")).strip()
        fator = ADR_FATORES_CATEGORIA.get(cat, 1)
        
        # Tenta extrair quantidade estimada (padrão 10 se não informada)
        qtd = item.get("quantidade_kg_l", 10)
        pontos_totais += (qtd * fator)

    isento = pontos_totais <= 1000
    msg = f"Pontuação Total ADR: {pontos_totais}/1000 pontos."
    
    if isento:
        msg += " 🟢 Isenção Parcial Aplicável (Não exige painel laranja nem licença completa de motorista)."
    else:
        msg += " 🔴 LIMITE EXCEDIDO: Veículo DEVE ter sinalização ADR (Placa Laranja) e motorista certificado!"

    return {
        "pontos_totais": pontos_totais,
        "isento": isento,
        "mensagem": msg
    }


def executar_auditoria_compliance(dados_ia: Dict[str, Any], modal: str) -> Dict[str, Any]:
    """
    Função Principal que recebe a resposta da IA e aplica os filtros de código duro.
    """
    itens = dados_ia.get("itens_classificados", [])
    alertas_bloqueio = []
    
    # 1. Auditoria Aérea
    if "AÉREO" in modal.upper():
        for item in itens:
            err = validar_iata_aereo(item)
            alertas_bloqueio.extend(err)

    # 2. Auditoria Marítima (Segregação)
    elif "MARÍTIMO" in modal.upper():
        err = validar_imdg_maritimo(itens)
        alertas_bloqueio.extend(err)

    # 3. Auditoria Rodoviária (1000 Pontos)
    elif "RODOVIÁRIO" in modal.upper():
        res_adr = validar_adr_rodoviario(itens)
        dados_ia["resumo_adr_pontos"] = res_adr["mensagem"]
        if not res_adr["isento"]:
            alertas_bloqueio.append("⚠️ [ADR ALERTA] Transporte requer veículo 100% equipado com sinalização ADR.")

    # Status de Aprovado / Bloqueado
    dados_ia["auditado_por_codigo"] = True
    dados_ia["status_aprovacao"] = "🔴 BLOQUEADO (RISCO REGULATÓRIO)" if alertas_bloqueio else "🟢 APROVADO COMPLIANCE"
    dados_ia["alertas_criticos_codigo"] = alertas_bloqueio

    return dados_ia