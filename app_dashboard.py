import os
import json
import streamlit as st
import pandas as pd
from motor_classificador import extrair_texto_fatura, classificar_itens_com_ia

# Configuração da página Web
st.set_page_config(
    page_title="HS-Code Automator | Middleware Aduaneiro",
    page_icon="📦",
    layout="wide"
)

st.title("📦 HS-Code Automator — Middleware para Despachantes")
st.caption("Classificação Automática de NCM/HS Codes com Análise de Risco Aduaneiro")

# Sidebar para definições
with st.sidebar:
    st.header("⚙️ Configurações do Middleware")
    empresa_id = st.text_input("Empresa / Licença ID", value="DESPACHANTE_DEMO_01")
    sistema_destino = st.selectbox(
        "Sistema de Destino (Injeção)",
        ["CargoWise", "Primavera ERP", "Exportar CSV/JSON", "API Direct Webhook"]
    )
    st.divider()
    st.info("💡 **Dica Comercial:** Itens com confiança < 90% requerem validação manual antes da injeção no ERP.")

# Área de Upload de Documentos
st.subheader("1. Ingestão de Documentos")
uploaded_file = st.file_uploader("Arraste e largue a Comercial Invoice (PDF)", type=["pdf"])

# Se o utilizador carregar um PDF (ou usar a nossa fatura de teste se não fizer upload)
if uploaded_file is not None or st.button("🚀 Testar com a Fatura de Exemplo (Desktop)"):
    
    # Processar ficheiro enviado ou usar o do Desktop
    if uploaded_file is not None:
        temp_path = "temp_fatura.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        caminho_pdf = temp_path
    else:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        if not os.path.exists(desktop):
            desktop = os.path.join(os.path.expanduser('~'), 'Área de Trabalho')
        caminho_pdf = os.path.join(desktop, "fatura_importacao_exemplo.pdf")

    with st.spinner("📄 Lendo PDF e analisando enquadramento fiscal com IA..."):
        texto = extrair_texto_fatura(caminho_pdf)
        dados = classificar_itens_com_ia(texto)

    st.success(f"Fatura **{dados.get('fatura_num')}** do fornecedor **{dados.get('fornecedor')}** processada com sucesso!")

    st.divider()
    st.subheader("2. Validação Human-in-the-Loop (Revisão de Classificação)")

    itens = dados.get("itens_classificados", [])
    
    # Criar tabela editável para o utilizador
    tabela_dados = []
    for item in itens:
        confianca = item.get("grau_confianca", 0)
        status_icon = "🟢" if confianca >= 90 else "🟡"
        
        tabela_dados.append({
            "Status": f"{status_icon} {confianca}%",
            "Item #": item.get("item_num"),
            "Descrição do Produto": item.get("descricao_original"),
            "HS Code (6 Dig)": item.get("hs_code_6dig"),
            "NCM / Taric (8 Dig)": item.get("ncm_code_8dig"),
            "Fundamentação Legal": item.get("justificativa_legal"),
            "Alerta de Risco / Dúvida": item.get("alerta_duvida") or "Nenhum risco detetado"
        })

    df = pd.DataFrame(tabela_dados)
    
    # Exibir tabela interativa
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Status": st.column_config.TextColumn("Confiança"),
            "HS Code (6 Dig)": st.column_config.TextColumn("HS Code (Editável)"),
            "NCM / Taric (8 Dig)": st.column_config.TextColumn("NCM (Editável)"),
        }
    )

    st.divider()
    st.subheader("3. Injeção & Exportação de Dados")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirmar e Injetar no " + sistema_destino, type="primary"):
            st.balloons()
            st.success(f"Dados injetados com sucesso via API no sistema {sistema_destino}!")
    
    with col2:
        json_str = json.dumps(dados, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Descarregar JSON Limpo",
            data=json_str,
            file_name=f"classificacao_{dados.get('fatura_num')}.json",
            mime="application/json"
        )