import os
import json
import tempfile
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Imports dos Módulos da Aplicação
from motor_classificador import extrair_texto_fatura, classificar_itens_com_ia
from validador_compliance import executar_auditoria_compliance
from exportador_documentos import gerar_csv_erp, gerar_xml_cargowise, gerar_pdf_relatorio_compliance

# Configuração do Supabase via Secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

# CONFIGURAÇÕES DE SEGURANÇA, FINOPS E LEGAL
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # Limite de Tamanho do Ficheiro: 10 MB
LIMITE_DIARIO_FATURAS = 10              # Quota de Rate Limiting por utilizador/dia

@st.cache_resource
def iniciar_supabase() -> Client:
    if SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

supabase = iniciar_supabase()

def verificar_quota_diaria(user_id: str, limite: int = LIMITE_DIARIO_FATURAS) -> tuple[bool, int]:
    """Verifica se o utilizador atingiu o limite diário de faturas processadas."""
    if not supabase:
        return True, 0
    try:
        hoje_inicio = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
        resposta = supabase.table("faturas_processadas") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .gte("created_at", hoje_inicio) \
            .execute()
            
        total_hoje = resposta.count or 0
        return total_hoje < limite, total_hoje
    except Exception:
        return True, 0

st.set_page_config(
    page_title="HS-Code Automator | SaaS Enterprise",
    page_icon="📦",
    layout="wide"
)

# Inicializar Estado de Sessão
if "user" not in st.session_state:
    st.session_state.user = None

# =====================================================================
# TELA DE AUTENTICAÇÃO & ACEITAÇÃO DE TERMOS (LOGIN / REGISTO)
# =====================================================================
def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📦 HS-Code Automator")
        st.subheader("Acesso Restrito ao Middleware Aduaneiro")
        
        aba_login, aba_registo = st.tabs(["🔒 Iniciar Sessão", "📝 Criar Conta"])
        
        with aba_login:
            with st.form("form_login"):
                email = st.text_input("Email Corporativo").strip().lower()
                password = st.text_input("Palavra-passe", type="password")
                btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
                
                if btn_entrar:
                    if not email or not password:
                        st.warning("Por favor, preencha o email e a palavra-passe.")
                    else:
                        try:
                            resposta = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = resposta.user
                            st.success("Autenticado com sucesso!")
                            st.rerun()
                        except Exception:
                            st.error("Falha na autenticação: Credenciais inválidas ou limite de tentativas excedido.")

        with aba_registo:
            with st.form("form_registo"):
                novo_email = st.text_input("Email Corporativo").strip().lower()
                nova_password = st.text_input("Palavra-passe (mínimo 6 caracteres)", type="password")
                
                # ⚖️ PILAR 4: Consentimento RGPD e Termos de Serviço
                aceita_termos = st.checkbox("Li e aceito os Termos de Serviço, Política de Privacidade e Isenção de Responsabilidade Aduaneira/DGR.")
                
                btn_registrar = st.form_submit_button("Criar Conta Enterprise", use_container_width=True)
                
                if btn_registrar:
                    if not aceita_termos:
                        st.warning("⚠️ Deve aceitar os Termos de Serviço para criar conta.")
                    elif len(nova_password) < 6:
                        st.warning("A palavra-passe deve ter pelo menos 6 caracteres.")
                    else:
                        try:
                            resposta = supabase.auth.sign_up({"email": novo_email, "password": nova_password})
                            st.success("Conta criada com sucesso! Já pode efetuar login.")
                        except Exception:
                            st.error("Erro ao criar conta. Verifique se o email é válido.")

# Bloqueia a execução se não estiver logado
if not st.session_state.user:
    tela_login()
    st.stop()

# =====================================================================
# PAINEL PRINCIPAL (DADOS DO UTILIZADOR AUTENTICADO)
# =====================================================================
user_email = st.session_state.user.email
user_id = st.session_state.user.id

# CHECAGEM DE QUOTA FINOPS
dentro_da_quota, usadashoje = verificar_quota_diaria(user_id)

# --- SIDEBAR UNIFICADA ---
with st.sidebar:
    st.header("👤 Sessão Ativa")
    st.caption(f"Conectado como:\n**{user_email}**")
    
    # Exibição do consumo de quota
    st.divider()
    st.markdown("### 📊 Quota Diária (FinOps)")
    progresso_pct = min(1.0, usadashoje / LIMITE_DIARIO_FATURAS)
    st.progress(progresso_pct)
    st.caption(f"Processadas hoje: **{usadashoje} / {LIMITE_DIARIO_FATURAS} faturas**")
    
    if not dentro_da_quota:
        st.error("🚨 Limite diário atingido. Contacte o suporte para subscrição ilimitada.")
    
    st.divider()
    if st.button("🚪 Terminar Sessão (Logout)", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # ⚖️ PILAR 4: Gestão do RGPD / Direito ao Esquecimento
    st.divider()
    with st.expander("🛡️ Privacidade & Dados (RGPD)"):
        st.caption("Conforme o Artigo 17.º do RGPD, pode solicitar a eliminação imediata de todo o seu histórico de faturas do nosso servidor.")
        if st.button("🗑️ Apagar Todo o Meu Histórico", type="secondary", use_container_width=True):
            try:
                supabase.table("faturas_processadas").delete().eq("user_id", user_id).execute()
                st.success("Histórico eliminado com sucesso!")
                st.rerun()
            except Exception:
                st.error("Erro ao apagar o histórico.")

    st.divider()
    st.header("⚙️ Configurações do Embarque")
    
    modal_transporte = st.selectbox(
        "🚢 Modal de Transporte",
        ["AÉREO (IATA DGR)", "MARÍTIMO (IMDG)", "RODOVIÁRIO (ADR)"],
        key="sb_modal_transporte"
    )
    
    sistema_destino = st.selectbox(
        "Sistema de Destino (ERP)",
        ["CargoWise", "Primavera ERP", "Exportar CSV/JSON", "API Direct Webhook"],
        key="sb_sistema_destino"
    )

st.title("📦 HS-Code Automator — Dashboard Enterprise")

# DEFINIÇÃO DAS TABS
tab_processar, tab_historico, tab_legal = st.tabs(["📄 Processar Nova Fatura", "🗄️ Histórico Protegido", "⚖️ Termos & Conformidade Legal"])

# =====================================================================
# TAB 1: PROCESSAR FATURA
# =====================================================================
with tab_processar:
    st.subheader("1. Ingestão de Documentos")
    
    if not dentro_da_quota:
        st.error(f"🛑 **Atingiu a sua quota diária de {LIMITE_DIARIO_FATURAS} faturas/dia.** Para continuar a processar em volume ilimitado, solicite a atualização para o plano Pro Enterprise.")
    else:
        uploaded_file = st.file_uploader("Arraste e largue a Commercial Invoice (PDF - Máx 10MB)", type=["pdf"])

        if uploaded_file is not None:
            # 🛡️ SEGURANÇA: Validação de Tamanho do Ficheiro (DoS Protection)
            if uploaded_file.size > MAX_FILE_SIZE_BYTES:
                st.error("🚨 Ficheiro demasiado grande! O limite máximo permitido é de 10 MB.")
                st.stop()

            temp_file_path = None
            try:
                # 🛡️ SEGURANÇA: Ficheiro temporário isolado
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    temp_file_path = tmp.name

                with st.spinner(f"📄 Analisando fatura e auditando regras de compliance ({modal_transporte})..."):
                    texto = extrair_texto_fatura(temp_file_path)
                    dados_brutos = classificar_itens_com_ia(texto, modal=modal_transporte)
                    
                    # AUDITORIA DETERMINÍSTICA
                    dados = executar_auditoria_compliance(dados_brutos, modal=modal_transporte)

            except Exception:
                st.error("Erro ao processar o documento. Verifique se o PDF contém texto legível.")
                st.stop()
            finally:
                # 🛡️ SEGURANÇA: Apaga o ficheiro temporário imediatamente
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except Exception:
                        pass

            st.success(f"Fatura **{dados.get('fatura_num', 'N/A')}** processada e auditada com sucesso!")

            # EXIBIÇÃO DO STATUS DA AUDITORIA
            st.divider()
            if dados.get("status_aprovacao") == "🟢 APROVADO COMPLIANCE":
                st.success(f"### Status da Auditoria: {dados.get('status_aprovacao')}")
            else:
                st.error(f"### Status da Auditoria: {dados.get('status_aprovacao')}")
                for alerta in dados.get("alertas_criticos_codigo", []):
                    st.warning(alerta)

            if dados.get("resumo_adr_pontos"):
                st.info(f"📊 **Cálculo ADR:** {dados.get('resumo_adr_pontos')}")

            if dados.get("resumo_compliance_modal"):
                st.info(f"💡 **Resumo de Compliance ({modal_transporte}):** {dados.get('resumo_compliance_modal')}")

            # GUARDAR NO SUPABASE
            try:
                registro = {
                    "user_id": user_id,
                    "empresa_id": user_email,
                    "fatura_num": dados.get("fatura_num"),
                    "fornecedor": dados.get("fornecedor"),
                    "modal_transporte": modal_transporte,
                    "dados_json": dados
                }
                supabase.table("faturas_processadas").insert(registro).execute()
                st.toast("✅ Fatura guardada com segurança no histórico!")
            except Exception:
                st.warning("Aviso ao gravar registo no histórico remoto.")

            # PASSO 2: VALIDAÇÃO HUMAN-IN-THE-LOOP
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
                    "UN Number": item.get("un_number", "N/A"),
                    "Classe Risco": item.get("classe_risco", "N/A"),
                    "Alerta Modal": item.get("alerta_duvida") or "Sem risco"
                })

            df = pd.DataFrame(tabela_dados)
            st.dataframe(df, use_container_width=True)

            bloqueado = dados.get("status_aprovacao") != "🟢 APROVADO COMPLIANCE"

            st.divider()
            st.subheader("3. Exportação & Integração de Dados")

            # GERAR DOCUMENTOS PARA DOWNLOAD
            pdf_bytes = gerar_pdf_relatorio_compliance(dados, user_email)
            xml_data = gerar_xml_cargowise(dados)
            csv_data = gerar_csv_erp(dados)
            json_str = json.dumps(dados, indent=2, ensure_ascii=False)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.download_button(
                    label="📄 Relatório PDF de Compliance",
                    data=pdf_bytes,
                    file_name=f"Relatorio_Compliance_{dados.get('fatura_num', 'export')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            with col2:
                st.download_button(
                    label="🏢 Exportar XML (CargoWise)",
                    data=xml_data,
                    file_name=f"cargowise_{dados.get('fatura_num', 'export')}.xml",
                    mime="application/xml",
                    use_container_width=True,
                    disabled=bloqueado
                )

            with col3:
                st.download_button(
                    label="📊 Exportar CSV (Primavera/ERP)",
                    data=csv_data,
                    file_name=f"erp_import_{dados.get('fatura_num', 'export')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    disabled=bloqueado
                )

            with col4:
                st.download_button(
                    label="📥 JSON Limpo (API)",
                    data=json_str,
                    file_name=f"classificacao_{dados.get('fatura_num', 'export')}.json",
                    mime="application/json",
                    use_container_width=True
                )

            if bloqueado:
                st.warning("⚠️ Os ficheiros de integração com ERP (XML e CSV) estão bloqueados até que os alertas de compliance sejam resolvidos.")

# =====================================================================
# TAB 2: HISTÓRICO PROTEGIDO
# =====================================================================
with tab_historico:
    st.subheader("🗄️ O seu Histórico de Faturas")
    try:
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
                    "Modal": f.get("modal_transporte", "AÉREO"),
                    "Qtd Itens": len(f.get("dados_json", {}).get("itens_classificados", []))
                })
            
            st.dataframe(pd.DataFrame(lista_historico), use_container_width=True)
            
    except Exception:
        st.error("Erro ao carregar o histórico. Tente novamente mais tarde.")

# =====================================================================
# TAB 3: TERMOS & CONFORMIDADE LEGAL (PILAR 4)
# =====================================================================
with tab_legal:
    st.subheader("⚖️ Declaração de Responsabilidade Legal & RGPD")
    st.markdown("""
    ### 1. Isenção de Responsabilidade Aduaneira e DGR
    * O **HS-Code Automator** é um *middleware* de apoio técnico baseado em inteligência artificial e tabelas determinísticas.
    * A sugestão de **HS Code / NCM / Taric** e a verificação de regras **IATA DGR, IMDG e ADR** servem como suporte de pré-auditoria e **não substituem a validação final por um Despachante Oficial ou Agente de Carga Certificado**.
    * A responsabilidade legal pela submissão do documento às Autoridades Aduaneiras e Marítimas/Aéreas é inteiramente do Utilizador/Declarante.

    ### 2. Política de Proteção de Dados (RGPD)
    * **Confidencialidade:** Os dados das faturas submetidas são processados exclusivamente para fins de auditoria e classificação.
    * **Retenção:** Os dados permanecem na sua conta até que solicite a sua eliminação através do menu lateral (**Direito ao Esquecimento**).
    * **Ficheiros Temporários:** Ficheiros PDF carregados são removidos da memória volátil do servidor imediatamente após o processamento.
    """)