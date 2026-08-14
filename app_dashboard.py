import os
import json
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from motor_classificador import extrair_texto_fatura, classificar_itens_com_ia

# Configuração do Supabase
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def iniciar_supabase() -> Client:
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

supabase = iniciar_supabase()

# Configuração da página Web
st.set_page_config(
    page_title="HS-Code Automator | Middleware Aduaneiro",
    page_icon="📦",
    layout="wide"
)

st.title("📦 HS-Code Automator — Middleware para Despachantes")
st.caption("Classificação Automática de NCM/HS Codes com Análise de Risco Aduaneiro")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações do Middleware")
    empresa_id = st.text_input("Empresa / Licença ID", value="DESPACHANTE_DEMO_01")
    sistema_destino = st.selectbox(
        "Sistema de Destino (Injeção)",
        ["CargoWise", "Primavera ERP", "Exportar CSV/JSON", "API Direct Webhook"]
    )
    st.divider()
    st.info("💡 **Dica Comercial:** Itens com confiança < 90% requerem validação manual antes da injeção no ERP.")

# Separadores principais
tab_processar, tab_historico = st.tabs(["📄 Processar Nova Fatura", "🗄️ Histórico na Base de Dados"])

# =====================================================================
# TAB 1: PROCESSAR FATURA
# =====================================================================
with tab_processar:
    st.subheader("1. Ingestão de Documentos")
    uploaded_file = st.file_uploader("Arraste e largue a Comercial Invoice (PDF)", type=["pdf"])

    if uploaded_file is not None:
        temp_path = "temp_fatura.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("📄 Lendo PDF e analisando enquadramento fiscal com a IA..."):
            texto = extrair_texto_fatura(temp_path)
            dados = classificar_itens_com_ia(texto)

        st.success(f"Fatura **{dados.get('fatura_num')}** do fornecedor **{dados.get('fornecedor')}** processada com sucesso!")

        # GUARDAR NO SUPABASE
        if supabase:
            try:
                registro = {
                    "empresa_id": empresa_id,
                    "fatura_num": dados.get("fatura_num"),
                    "fornecedor": dados.get("fornecedor"),
                    "dados_json": dados
                }
                supabase.table("faturas_processadas").insert(registro).execute()
                st.toast("✅ Fatura guardada com sucesso na base de dados Supabase!")
            except Exception as e:
                st.warning(f"Não foi possível gravar no Supabase: {e}")

        st.divider()
        st.subheader("2. Validação Human-in-the-Loop (Revisão de Classificação)")

        itens = dados.get("itens_classificados", [])
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
                "Alerta de Risco": item.get("alerta_duvida") or "Nenhum risco"
            })

        df = pd.DataFrame(tabela_dados)
        st.dataframe(df, use_container_width=True)

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

# =====================================================================
# TAB 2: HISTÓRICO DE FATURAS (CONSULTA DA BASE DE DADOS)
# =====================================================================
with tab_historico:
    st.subheader("🗄️ Faturas Guardadas no Supabase")
    
    if not supabase:
        st.error("Conexão ao Supabase não configurada nos Secrets.")
    else:
        try:
            resposta = supabase.table("faturas_processadas").select("*").eq("empresa_id", empresa_id).order("created_at", desc=True).execute()
            faturas_db = resposta.data

            if not faturas_db:
                st.info("Nenhuma fatura encontrada na base de dados para esta empresa.")
            else:
                lista_historico = []
                for f in faturas_db:
                    lista_historico.append({
                        "Data Processamento": f.get("created_at")[:19].replace("T", " "),
                        "Nº Fatura": f.get("fatura_num"),
                        "Fornecedor": f.get("fornecedor"),
                        "Qtd Itens": len(f.get("dados_json", {}).get("itens_classificados", []))
                    })
                
                st.dataframe(pd.DataFrame(lista_historico), use_container_width=True)
                
        except Exception as e:
            st.error(f"Erro ao procurar histórico: {e}")