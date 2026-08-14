import os
import json
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from motor_classificador import extrair_texto_fatura, classificar_itens_com_ia

# Configuração do Supabase via Secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def iniciar_supabase() -> Client:
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

supabase = iniciar_supabase()

st.set_page_config(
    page_title="HS-Code Automator | SaaS Enterprise",
    page_icon="📦",
    layout="wide"
)

# Inicializar Estado de Sessão de Autenticação
if "user" not in st.session_state:
    st.session_state.user = None

# =====================================================================
# TELA DE AUTENTICAÇÃO (LOGIN / REGISTO)
# =====================================================================
def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📦 HS-Code Automator")
        st.subheader("Acesso Restrito ao Middleware Aduaneiro")
        
        aba_login, aba_registo = st.tabs(["🔒 Iniciar Sessão", "📝 Criar Conta"])
        
        with aba_login:
            with st.form("form_login"):
                email = st.text_input("Email Corporativo")
                password = st.text_input("Palavra-passe", type="password")
                btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
                
                if btn_entrar:
                    try:
                        resposta = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = resposta.user
                        st.success("Autenticado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error("Falha na autenticação: Credenciais inválidas ou limite de tentativas excedido.")

        with aba_registo:
            with st.form("form_registo"):
                novo_email = st.text_input("Email Corporativo")
                nova_password = st.text_input("Palavra-passe (mínimo 6 caracteres)", type="password")
                btn_registrar = st.form_submit_button("Criar Conta Enterprise", use_container_width=True)
                
                if btn_registrar:
                    try:
                        resposta = supabase.auth.sign_up({"email": novo_email, "password": nova_password})
                        st.success("Conta criada com sucesso! Já pode efetuar login.")
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")

# Se o utilizador não estiver logado, exibe a tela de login e para a execução
if not st.session_state.user:
    tela_login()
    st.stop()

# =====================================================================
# PAINEL PRINCIPAL (APENAS PARA UTILIZADORES AUTENTICADOS)
# =====================================================================

user_email = st.session_state.user.email
user_id = st.session_state.user.id

# Sidebar com perfil do utilizador
with st.sidebar:
    st.header("👤 Sessão Ativa")
    st.caption(f"Conectado como:\n**{user_email}**")
    
    if st.button("🚪 Terminar Sessão (Logout)", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.divider()
    st.header("⚙️ Configurações")
    sistema_destino = st.selectbox(
        "Sistema de Destino (ERP)",
        ["CargoWise", "Primavera ERP", "Exportar CSV/JSON", "API Direct Webhook"]
    )

st.title("📦 HS-Code Automator — Dashboard Enterprise")
tab_processar, tab_historico = st.tabs(["📄 Processar Nova Fatura", "🗄️ Histórico Protegido"])

# --- TAB 1: PROCESSAR FATURA ---
with tab_processar:
    st.subheader("1. Ingestão de Documentos")
    uploaded_file = st.file_uploader("Arraste e largue a Commercial Invoice (PDF)", type=["pdf"])

    if uploaded_file is not None:
        temp_path = "temp_fatura.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("📄 Lendo PDF e analisando enquadramento fiscal..."):
            texto = extrair_texto_fatura(temp_path)
            dados = classificar_itens_com_ia(texto)

        st.success(f"Fatura **{dados.get('fatura_num')}** processada com sucesso!")

        # GUARDAR NO SUPABASE COM O USER_ID
        try:
            registro = {
                "user_id": user_id,
                "empresa_id": user_email,
                "fatura_num": dados.get("fatura_num"),
                "fornecedor": dados.get("fornecedor"),
                "dados_json": dados
            }
            supabase.table("faturas_processadas").insert(registro).execute()
            st.toast("✅ Fatura guardada com segurança na sua conta!")
        except Exception as e:
            st.warning(f"Erro ao salvar registro: {e}")

        st.divider()
        st.subheader("2. Validação Human-in-the-Loop")

        itens = dados.get("itens_classificados", [])
        tabela_dados = []
        for item in itens:
            confianca = item.get("grau_confianca", 0)
            status_icon = "🟢" if confianca >= 90 else "🟡"
            
            tabela_dados.append({
                "Status": f"{status_icon} {confianca}%",
                "Item #": item.get("item_num"),
                "Descrição do Produto": item.get("descricao_original"),
                "HS Code": item.get("hs_code_6dig"),
                "NCM / Taric": item.get("ncm_code_8dig"),
                "Justificativa Legal": item.get("justificativa_legal"),
                "Alerta de Risco": item.get("alerta_duvida") or "Sem risco"
            })

        df = pd.DataFrame(tabela_dados)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar e Injetar no " + sistema_destino, type="primary"):
                st.balloons()
                st.success(f"Dados enviados para o {sistema_destino}!")
        with col2:
            json_str = json.dumps(dados, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Descarregar JSON Limpo",
                data=json_str,
                file_name=f"classificacao_{dados.get('fatura_num')}.json",
                mime="application/json"
            )

# --- TAB 2: HISTÓRICO PROTEGIDO ---
with tab_historico:
    st.subheader("🗄️ O seu Histórico de Faturas")
    try:
        # A consulta só retorna os dados pertencentes ao user_id logado
        resposta = supabase.table("faturas_processadas").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        faturas_db = resposta.data

        if not faturas_db:
            st.info("Ainda não processou nenhuma fatura na sua conta.")
        else:
            lista_historico = []
            for f in faturas_db:
                lista_historico.append({
                    "Data": f.get("created_at")[:19].replace("T", " "),
                    "Nº Fatura": f.get("fatura_num"),
                    "Fornecedor": f.get("fornecedor"),
                    "Qtd Itens": len(f.get("dados_json", {}).get("itens_classificados", []))
                })
            
            st.dataframe(pd.DataFrame(lista_historico), use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")