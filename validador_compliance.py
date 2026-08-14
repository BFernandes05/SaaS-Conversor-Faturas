"""
Módulo Determinístico de Compliance Logístico Multimodal Enterprise (DGR / IMDG / ADR)
Aplica regras matematicamente estritas sem depender de Inteligência Artificial.
"""

from typing import Dict, Any, List

# =====================================================================
# BASE DE DADOS DETERMINÍSTICA DE CÓDIGOS UN E REGRAS ESTRITAS (DGR/IMDG/ADR)
# =====================================================================
UN_DATABASE = {
    "UN 3480": {
        "nome": "LITHIUM ION BATTERIES (including lithium ion polymer batteries)",
        "classe": "9",
        "subrisco": None,
        "pi_pax": "PROIBIDO",  # Banido em voos de passageiros (IATA)
        "pi_cao": "PI 965",    # Cargo Aircraft Only
        "limite_pax_kg": 0,
        "limite_cao_kg": 35.0,
        "grupo_embalagem": "N/A",
        "adr_categoria": "2",
        "alerta_especial": "🛑 [IATA DGR] UN 3480 é estritamente PROIBIDO em aeronaves de passageiros (PAX). Deve ser despachado obrigatoriamente como Cargo Aircraft Only (CAO) com SOC <= 30%."
    },
    "UN 3481": {
        "nome": "LITHIUM ION BATTERIES CONTAINED IN EQUIPMENT or PACKED WITH EQUIPMENT",
        "classe": "9",
        "subrisco": None,
        "pi_pax": "PI 966 / PI 967",
        "pi_cao": "PI 966 / PI 967",
        "limite_pax_kg": 5.0,
        "limite_cao_kg": 35.0,
        "grupo_embalagem": "N/A",
        "adr_categoria": "2",
        "alerta_especial": "⚠️ Exige rotulagem de Bateria de Lítio e documento de acompanhamento se exceder o número de células/baterias por volume."
    },
    "UN 1263": {
        "nome": "PAINT or PAINT RELATED MATERIAL",
        "classe": "3",
        "subrisco": None,
        "pi_pax": "PI 355",
        "pi_cao": "PI 366",
        "limite_pax_kg": 5.0,
        "limite_cao_kg": 60.0,
        "grupo_embalagem": "II",
        "adr_categoria": "2",
        "alerta_especial": "🔥 Líquido Inflamável. Manter afastado de fontes de ignição e oxidantes (Classe 5.1)."
    },
    "UN 1950": {
        "nome": "AEROSOLS, flammable",
        "classe": "2.1",
        "subrisco": None,
        "pi_pax": "PI 203",
        "pi_cao": "PI 203",
        "limite_pax_kg": 75.0,
        "limite_cao_kg": 150.0,
        "grupo_embalagem": "N/A",
        "adr_categoria": "2",
        "alerta_especial": "💥 Vaso sob pressão. Risco de explosão sob calor intenso."
    },
    "UN 1090": {
        "nome": "ACETONE",
        "classe": "3",
        "subrisco": None,
        "pi_pax": "PI 353",
        "pi_cao": "PI 364",
        "limite_pax_kg": 5.0,
        "limite_cao_kg": 60.0,
        "grupo_embalagem": "II",
        "adr_categoria": "2",
        "alerta_especial": "🔥 Solvente altamente inflamável."
    },
    "UN 1830": {
        "nome": "SULPHURIC ACID with more than 51% acid",
        "classe": "8",
        "subrisco": None,
        "pi_pax": "PI 851",
        "pi_cao": "PI 855",
        "limite_pax_kg": 1.0,
        "limite_cao_kg": 30.0,
        "grupo_embalagem": "II",
        "adr_categoria": "2",
        "alerta_especial": "🧪 Corrosivo Forte. Incompatível com bases e substâncias orgânicas."
    },
    "UN 2031": {
        "nome": "NITRIC ACID, other than red fuming, with more than 70% acid",
        "classe": "8",
        "subrisco": "5.1",
        "pi_pax": "PROIBIDO",
        "pi_cao": "PI 855",
        "limite_pax_kg": 0,
        "limite_cao_kg": 30.0,
        "grupo_embalagem": "I",
        "adr_categoria": "1",
        "alerta_especial": "🛑 Corrosivo e Oxidante. Proibido em PAX. Altamente reativo."
    },
    "UN 3082": {
        "nome": "ENVIRONMENTALLY HAZARDOUS SUBSTANCE, LIQUID, N.O.S.",
        "classe": "9",
        "subrisco": None,
        "pi_pax": "PI 964",
        "pi_cao": "PI 964",
        "limite_pax_kg": 450.0,
        "limite_cao_kg": 450.0,
        "grupo_embalagem": "III",
        "adr_categoria": "3",
        "alerta_especial": "🐟 Perigoso para o Ambiente Aquático (Poluente Marinho no IMDG)."
    }
}

# MATRIZ DE INCOMPATIBILIDADE DE SEGREGAÇÃO IMDG (MARÍTIMO - CAPÍTULO 7.2)
IMDG_INCOMPATIBILIDADES = {
    "1": ["2", "3", "4", "5.1", "5.2", "8"],  # Explosivos são incompatíveis com quase tudo
    "2.1": ["5.1", "5.2"],                   # Gases inflamáveis
    "3": ["5.1", "5.2"],                     # Líquidos Inflamáveis
    "5.1": ["1", "2.1", "3", "4.1", "8"],    # Oxidantes
    "8": ["1", "5.1", "5.2"]                 # Corrosivos
}

# FATORES DE MULTIPLICAÇÃO ADR (RODOVIÁRIO - ISENÇÃO 1.1.3.6)
ADR_FATORES_CATEGORIA = {
    "0": 0,     # Categoria 0 -> Sem limite
    "1": 50,    # Categoria 1 -> Multiplica por 50 (Muito Perigoso)
    "2": 3,     # Categoria 2 -> Multiplica por 3 (Médio Risco)
    "3": 1,     # Categoria 3 -> Multiplica por 1 (Baixo Risco)
    "4": 0      # Categoria 4 -> Isento de limiar de pontos
}


def validar_iata_aereo(item: Dict[str, Any]) -> List[str]:
    """Validações estritas para o Modal Aéreo (IATA DGR)."""
    alertas = []
    un_raw = str(item.get("un_number", "")).upper().strip()
    qtd = item.get("quantidade_kg_l", 0)
    
    # Normalização de string para busca de UN
    un_key = None
    for k in UN_DATABASE.keys():
        if k in un_raw or k.replace(" ", "") in un_raw.replace(" ", ""):
            un_key = k
            break
            
    if un_key:
        info = UN_DATABASE[un_key]
        
        # 1. Checagem de Proibição em Avião de Passageiros
        if info["pi_pax"] == "PROIBIDO":
            alertas.append(f"🛑 [IATA CRÍTICO - {un_key}] Proibido em Avião de Passageiros (PAX). {info['alerta_especial']}")
            
        # 2. Checagem de Limite de Quantidade por Carga (CAO)
        limite_cao = info["limite_cao_kg"]
        if qtd > limite_cao:
            alertas.append(f"🚨 [IATA LIMITE DE CARGA - {un_key}] Quantidade informada ({qtd} kg/L) excede o limite máximo permitido de Cargo Aircraft Only ({limite_cao} kg/L - {info['pi_cao']}).")

        # 3. Injeção de Informação de Embalagem (Packing Instruction)
        item["packing_instruction_pax"] = info["pi_pax"]
        item["packing_instruction_cao"] = info["pi_cao"]
        item["grupo_embalagem_oficial"] = info["grupo_embalagem"]
    elif "UN" in un_raw and un_raw != "N/A":
        alertas.append(f"⚠️ [IATA AVISO] {un_raw} detetado. Verificar Packing Instruction e Declaração de Mercadorias Perigosas (DGD) do expedidor.")

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
                    alertas.append(f"💥 [IMDG BLOQUEIO DE SEGREGAÇÃO] Incompatibilidade grave detetada no mesmo contentor: Classe {c1} não pode ser estivada juntamente com Classe {c2} (Capítulo 7.2 IMDG)!")
    
    return list(set(alertas))


def validar_adr_rodoviario(itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cálculo exato da Regra dos 1000 Pontos para Isenção Parcial ADR (1.1.3.6)."""
    pontos_totais = 0
    
    for item in itens:
        un_raw = str(item.get("un_number", "")).upper().strip()
        cat = "3"  # Categoria padrão baixa caso não encontrada
        
        # Tenta obter a categoria ADR da base determinística
        for k, info in UN_DATABASE.items():
            if k in un_raw or k.replace(" ", "") in un_raw.replace(" ", ""):
                cat = info["adr_categoria"]
                break
                
        fator = ADR_FATORES_CATEGORIA.get(cat, 1)
        qtd = item.get("quantidade_kg_l", 10)  # Padrão 10 se não indicado
        
        pontos_totais += (qtd * fator)

    isento = pontos_totais <= 1000
    msg = f"Pontuação Total ADR: {pontos_totais}/1000 pontos."
    
    if isento:
        msg += " 🟢 Isenção Parcial Aplicável (Isento de Painel Laranja no Veículo e Carta ADR do Condutor)."
    else:
        msg += " 🔴 LIMITE EXCEDIDO: Transporte Obriga a Veículo Equipado com Sinalização ADR (Placas Laranjas) e Condutor com Certificado Formação ADR!"

    return {
        "pontos_totais": pontos_totais,
        "isento": isento,
        "mensagem": msg
    }


def executar_auditoria_compliance(dados_ia: Dict[str, Any], modal: str) -> Dict[str, Any]:
    """
    Função Principal: Recebe o JSON da IA, cruza com a Base Determinística e valida DGR/IMDG/ADR.
    """
    itens = dados_ia.get("itens_classificados", [])
    alertas_bloqueio = []
    
    # 1. Enriquecimento e Auditoria Aérea (IATA DGR)
    if "AÉREO" in modal.upper():
        for item in itens:
            err = validar_iata_aereo(item)
            alertas_bloqueio.extend(err)

    # 2. Auditoria Marítima (IMDG Code - Segregação)
    elif "MARÍTIMO" in modal.upper():
        err = validar_imdg_maritimo(itens)
        alertas_bloqueio.extend(err)

    # 3. Auditoria Rodoviária (ADR - Isenção 1.1.3.6)
    elif "RODOVIÁRIO" in modal.upper():
        res_adr = validar_adr_rodoviario(itens)
        dados_ia["resumo_adr_pontos"] = res_adr["mensagem"]
        if not res_adr["isento"]:
            alertas_bloqueio.append("⚠️ [ADR ALERTA DE TRANSPORTE] Veículo obrigado a portar equipamento de proteção individual (EPI) e placas refletoras laranjas.")

    # Estado Final de Auditoria Estrita
    dados_ia["auditado_por_codigo"] = True
    dados_ia["status_aprovacao"] = "🔴 BLOQUEADO (RISCO REGULATÓRIO)" if alertas_bloqueio else "🟢 APROVADO COMPLIANCE"
    dados_ia["alertas_criticos_codigo"] = alertas_bloqueio

    return dados_ia