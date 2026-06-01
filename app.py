import streamlit as st
import httpx
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import time

st.set_page_config(page_title="Sistema Elétrico Profissional", layout="wide")

# --- CONFIGURAÇÃO SUPABASE VIA SECRETS ---
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]

headers = {
    "apikey": KEY_SUPABASE,
    "Authorization": f"Bearer {KEY_SUPABASE}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- CACHE DE CONSULTAS PARA EVITAR LOOPS ---
@st.cache_data(ttl=3)
def supabase_get(tabela, params=None):
    try:
        url = f"{URL_SUPABASE}/rest/v1/{tabela}"
        r = httpx.get(url, headers=headers, params=params, timeout=5.0)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception:
        return []

def supabase_post(tabela, dado):
    try:
        url = f"{URL_SUPABASE}/rest/v1/{tabela}"
        httpx.post(url, headers=headers, json=dado, timeout=5.0)
        st.cache_data.clear()
    except Exception:
        pass

def supabase_upsert(tabela, dados):
    try:
        url = f"{URL_SUPABASE}/rest/v1/{tabela}"
        headers_upsert = headers.copy()
        headers_upsert["Prefer"] = "resolution=merge-duplicates,return=representation"
        httpx.post(url, headers=headers_upsert, json=dados, timeout=5.0)
        st.cache_data.clear()
    except Exception:
        pass

def supabase_delete(tabela, filtros):
    try:
        url = f"{URL_SUPABASE}/rest/v1/{tabela}"
        httpx.delete(url, headers=headers, params=filtros, timeout=5.0)
        st.cache_data.clear()
    except Exception:
        pass

# --- CARREGAMENTO INICIAL DO BANCO ---
servicos_padrao_local = [
    {"nome": "Pontos Altos de Força", "tipo_categoria": "Predial", "valor": 20.0, "tipo_input": "quantidade", "deletavel": False},
    {"nome": "Pontos Baixos e Médios de Força", "tipo_categoria": "Predial", "valor": 15.0, "tipo_input": "quantidade", "deletavel": False},
    {"nome": "Luminárias em Teto/Gesso/PVC", "tipo_categoria": "Predial", "valor": 35.0, "tipo_input": "quantidade", "deletavel": False},
    {"nome": "Perfil LED em Teto/Gesso/PVC", "tipo_categoria": "Predial", "valor": 25.0, "tipo_input": "metragem", "deletavel": False},
    {"nome": "Fiação de Distribuição", "tipo_categoria": "Predial", "valor": 15.0, "tipo_input": "metragem", "deletavel": False},
    {"nome": "Fiação do Padrão ao Quadro de Disjuntores", "tipo_categoria": "Predial", "valor": 25.0, "tipo_input": "metragem", "deletavel": False},
    {"nome": "Instalações sobre Laje/Telhados", "tipo_categoria": "Predial", "valor": 10.0, "tipo_input": "metragem", "deletavel": False},
    {"nome": "Instalação de Eletrodutos/Canaletas Sobrepostas", "tipo_categoria": "Predial", "valor": 15.0, "tipo_input": "metragem", "deletavel": False},
    {"nome": "Quadro de Disjuntores", "tipo_categoria": "Predial", "valor": 15.0, "tipo_input": "quantidade", "deletavel": False},
    {"nome": "Instalação do Padrão", "tipo_categoria": "Predial", "valor": 400.0, "tipo_input": "padrao", "deletavel": False},
    {"nome": "Projeto e ART", "tipo_categoria": "Predial", "valor": 800.0, "tipo_input": "art", "deletavel": False},
    {"nome": "Parametrização de Soft Starter", "tipo_categoria": "Industrial", "valor": 150.0, "tipo_input": "quantidade", "deletavel": True},
    {"nome": "Parametrização de Inversor", "tipo_categoria": "Industrial", "valor": 150.0, "tipo_input": "quantidade", "deletavel": True},
    {"nome": "Instalação de Soft Starter", "tipo_categoria": "Industrial", "valor": 200.0, "tipo_input": "quantidade", "deletavel": True},
    {"nome": "Instalação de Inversor", "tipo_categoria": "Industrial", "valor": 200.0, "tipo_input": "quantidade", "deletavel": True},
    {"nome": "Montagem de Comandos", "tipo_categoria": "Industrial", "valor": 50.0, "tipo_input": "componentes", "deletavel": True}
]

servicos_db = supabase_get("precif_servicos")
if not servicos_db:
    servicos_db = servicos_padrao_local

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {}

# Suporte a rótulos customizados na edição final
if 'labels_customizados' not in st.session_state:
    st.session_state.labels_customizados = {}

if 'unidades_materiais' not in st.session_state:
    st.session_state.unidades_materiais = {}

for s in servicos_db:
    if s["nome"] not in st.session_state.dados_servicos:
        if s["tipo_input"] == "padrao":
            st.session_state.dados_servicos[s["nome"]] = {"incluir": False, "tipo": "Monofásico"}
        elif s["tipo_input"] == "art":
            st.session_state.dados_servicos[s["nome"]] = False
        else:
            st.session_state.dados_servicos[s["nome"]] = 0.0

if 'lista_materiais' not in st.session_state:
    st.session_state.lista_materiais = []

# --- MAPA DE PREÇOS ANTI-KEYERROR ---
precos = {}
for s in servicos_db:
    precos[s["nome"]] = float(s["valor"])
# --- SIDEBAR REESTRUTURADA ---
with st.sidebar:
    st.header("⚙️ Painel de Controle Global")
    modo_config = st.radio("Selecione o que deseja gerenciar:", ["Predial", "Industrial", "Material"], key="radio_modo_global")
    st.divider()
    
    if modo_config in ["Predial", "Industrial"]:
        st.subheader(f"Mão de Obra - {modo_config}")
        servicos_filtrados = [s for s in servicos_db if s["tipo_categoria"] == modo_config]
        valores_novos = {}
        
        for s in servicos_filtrados:
            valores_novos[s["nome"]] = st.number_input(
                f"Valor: {s['nome']}", value=float(s["valor"]), key=f"p_input_{s['nome']}"
            )
            precos[s["nome"]] = valores_novos[s["nome"]]
            
        if st.button("💾 Confirmar Novos Valores M.O.", type="primary", use_container_width=True):
            for s in servicos_filtrados:
                supabase_upsert("precif_servicos", {
                    "nome": s["nome"], "tipo_categoria": s["tipo_categoria"],
                    "valor": valores_novos[s["nome"]], "tipo_input": s["tipo_input"], "deletavel": s["deletavel"]
                })
            st.success("Valores salvos!")
            time.sleep(0.4)
            st.rerun()
            
        st.divider()
        st.subheader("➕ Nova Mão de Obra")
        novo_nome = st.text_input("Nome do Serviço:", key="add_nome_serv")
        novo_tipo_in = st.selectbox("Tipo de Cobrança:", ["quantidade", "metragem", "componentes"], key="add_tipo_serv")
        novo_valor = st.number_input("Valor Inicial (R$):", min_value=0.0, value=50.0, key="add_val_serv")
        
        if st.button("Confirmar Lançamento M.O.", use_container_width=True):
            if novo_nome.strip():
                if not any(s['nome'].lower() == novo_nome.strip().lower() for s in servicos_db):
                    supabase_post("precif_servicos", {
                        "nome": novo_nome.strip(), "tipo_categoria": modo_config,
                        "valor": novo_valor, "tipo_input": novo_tipo_in, "deletavel": True
                    })
                    st.success("Serviço adicionado!")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("Serviço já existe!")
                
        servicos_deletaveis = [s for s in servicos_filtrados if s["deletavel"]]
        if servicos_deletaveis:
            st.divider()
            st.subheader("🗑️ Excluir Mão de Obra")
            serv_del = st.selectbox("Escolha para remover:", [s["nome"] for s in servicos_deletaveis])
            if st.button("Confirmar Exclusão de M.O.", type="secondary", use_container_width=True):
                supabase_delete("precif_servicos", {"nome": f"eq.{serv_del}"})
                st.session_state.dados_servicos.pop(serv_del, None)
                st.success("Removido!")
                time.sleep(0.4)
                st.rerun()

    else:
        # --- PAINEL EXCLUSIVO DE MATERIAIS NA SIDEBAR ---
        st.subheader("📦 + Lançar Material para o Serviço")
        nome_mat_base = st.text_input("Nome do Material Base:", placeholder="Ex: Disjuntor DR, Cabo, Tomada", key="mat_add_sidebar").strip()
        uni_mat_base = st.selectbox("Unidade de Medida Geral:", ["un", "m", "kg", "pç", "cx"], key="mat_uni_sidebar")
        
        st.markdown("**Selecione as Variantes deste Material:**")
        opcoes_variantes = ["Quantidade", "Metros", "Kg", "Corrente (Amperagem)", "Polos", "Curva", "Seção", "Cor", "Bitola", "Descrição"]
        vars_selecionadas = st.multiselect("Marque quais deseja aplicar:", opcoes_variantes, key="multiselect_vars_mat")
        
        partes_nome_mat = [nome_mat_base] if nome_mat_base else []
        custo_total_material = 0.0
        
        if vars_selecionadas:
            st.markdown("---")
            for v in vars_selecionadas:
                with st.container():
                    c_label, c_val = st.columns([0.6, 0.4])
                    if v == "Quantidade":
                        v_qtd = c_label.number_input("Quantidade Final:", min_value=1, value=1, key="v_mat_qtd")
                        v_val = c_val.number_input("Valor Unitário (R$):", min_value=0.0, value=0.0, key="v_mat_qtd_val")
                        custo_total_material += (v_qtd * v_val)
                    elif v == "Metros":
                        v_met = c_label.number_input("Metragem (m):", min_value=0.0, value=0.0, key="v_mat_met")
                        v_val = c_val.number_input("Valor por Metro (R$):", min_value=0.0, value=0.0, key="v_mat_met_val")
                        if v_met > 0: partes_nome_mat.append(f"{v_met}m")
                        custo_total_material += (v_met * v_val)
                    elif v == "Kg":
                        v_kg = c_label.number_input("Peso (Kg):", min_value=0.0, value=0.0, key="v_mat_kg")
                        v_val = c_val.number_input("Valor por Kg (R$):", min_value=0.0, value=0.0, key="v_mat_kg_val")
                        if v_kg > 0: partes_nome_mat.append(f"{v_kg}kg")
                        custo_total_material += (v_kg * v_val)
def formatar_qtd(qtd, unidade):
    if unidade.lower() == "m":
        return f"{float(qtd):.1f}"
    return f"{int(qtd)}"

# --- ABAS PRINCIPAIS ---
tab_predial, tab_industrial, tab_conf_serv = st.tabs([
    "🏢 Predial", "🏭 Industrial", "🔍 Conferência e Fechamento"
])

# --- FUNÇÃO DE CONTAGEM AUXILIAR ---
def contar_confirmados(categoria):
    contagem = 0
    for k, v in st.session_state.dados_servicos.items():
        info = next((s for s in servicos_db if s["nome"] == k and s["tipo_categoria"] == categoria), None)
        if info:
            if info["tipo_input"] == "padrao" and v.get("incluir"):
                contagem += 1
            elif info["tipo_input"] == "art" and v:
                contagem += 1
            elif info["tipo_input"] not in ["padrao", "art"] and isinstance(v, (int, float)) and v > 0:
                contagem += 1
    return contagem

# --- ABA 1: PREDIAL (MÃO DE OBRA) ---
with tab_predial:
    st.subheader("Lançamento de Mão de Obra - Predial")
    
    # Marcador visual de quantidade
    qtd_predial_conf = contar_confirmados("Predial")
    st.info(f"📊 Serviços Prediais Confirmados no Orçamento: **{qtd_predial_conf}**")
    
    servicos_prediais = [s for s in servicos_db if s["tipo_categoria"] == "Predial"]
    nomes_prediais = [s["nome"] for s in servicos_prediais]
    
    if nomes_prediais:
        opcoes_com_placeholder = ["Clique aqui para selecionar serviço."] + nomes_prediais
        
        if "reset_predial_select" not in st.session_state:
            st.session_state.reset_predial_select = 0
            
        escolha_placeholder = st.selectbox(
            "Selecione o serviço predial para lançar/editar:", 
            opcoes_com_placeholder, 
            index=0, 
            key=f"sel_predial_aba_pl_{st.session_state.reset_predial_select}"
        )
        
        if escolha_placeholder != "Clique aqui para selecionar serviço.":
            escolha_serv = escolha_placeholder
            dados_serv_escolhido = next(s for s in servicos_prediais if s["nome"] == escolha_serv)
            
            valor_temporario = None
            inc_temporario = False
            tipo_temporario = "Monofásico"
            
            if dados_serv_escolhido["tipo_input"] == "quantidade":
                valor_temporario = st.number_input(
                    "Quantidade (unidades/peças):", min_value=0.0, step=1.0, 
                    value=None, placeholder="Digite a quantidade...", key=f"in_aba_pr_temp_{escolha_serv}"
                )
            elif dados_serv_escolhido["tipo_input"] == "metragem":
                valor_temporario = st.number_input(
                    "Metragem (m):", min_value=0.0, step=0.5, 
                    value=None, placeholder="Digite a metragem...", key=f"in_aba_pr_temp_{escolha_serv}"
                )
            elif dados_serv_escolhido["tipo_input"] == "padrao":
                d = st.session_state.dados_servicos.get(escolha_serv, {"incluir": False, "tipo": "Monofásico"})
                inc_temporario = st.checkbox("Incluir Padrão no Orçamento?", value=d["incluir"], key="chk_aba_padrao_pr_temp")
                tipo_temporario = st.selectbox("Fase do Padrão:", ["Monofásico", "Bifásico", "Trifásico"], index=["Monofásico", "Bifásico", "Trifásico"].index(d["tipo"]), key="sel_aba_fase_pr_temp")
            elif dados_serv_escolhido["tipo_input"] == "art":
                inc_temporario = st.checkbox(
                    "Incluir Projeto e taxa de ART?", value=bool(st.session_state.dados_servicos.get(escolha_serv, False)), key="chk_aba_art_pr_temp"
                )
            
            if st.button("Confirmar Serviço", type="primary", key=f"btn_confirmar_predial_{escolha_serv}"):
                if dados_serv_escolhido["tipo_input"] in ["quantidade", "metragem"]:
                    st.session_state.dados_servicos[escolha_serv] = float(valor_temporario) if valor_temporario is not None else 0.0
                elif dados_serv_escolhido["tipo_input"] == "padrao":
                    st.session_state.dados_servicos[escolha_serv] = {"incluir": inc_temporario, "tipo": tipo_temporario}
                elif dados_serv_escolhido["tipo_input"] == "art":
                    st.session_state.dados_servicos[escolha_serv] = inc_temporario
                st.success(f"Serviço '{escolha_serv}' confirmado com sucesso!")
                st.session_state.reset_predial_select += 1
                time.sleep(0.5)
                st.rerun()
    else:
        st.info("Nenhum serviço predial configurado no banco de dados.")

# --- ABA 2: INDUSTRIAL (MÃO DE OBRA) ---
with tab_industrial:
    st.subheader("Lançamento de Mão de Obra - Industrial")
    
    # Marcador visual de quantidade
    qtd_ind_conf = contar_confirmados("Industrial")
    st.info(f"📊 Serviços Industriais Confirmados no Orçamento: **{qtd_ind_conf}**")
    
    servicos_industriais = [s for s in servicos_db if s["tipo_categoria"] == "Industrial"]
    nomes_industriais = [s["nome"] for s in servicos_industriais]
    
    if nomes_industriais:
        opcoes_ind_placeholder = ["Clique aqui para selecionar serviço."] + nomes_industriais
        
        if "reset_industrial_select" not in st.session_state:
            st.session_state.reset_industrial_select = 0
            
        escolha_ind_placeholder = st.selectbox(
            "Selecione o serviço industrial para lançar/editar:", 
            opcoes_ind_placeholder, 
            index=0, 
            key=f"sel_ind_aba_pl_{st.session_state.reset_industrial_select}"
        )
        
        if escolha_ind_placeholder != "Clique aqui para selecionar serviço.":
            escolha_serv_ind = escolha_ind_placeholder
            dados_serv_ind_escolhido = next(s for s in servicos_industriais if s["nome"] == escolha_serv_ind)
            
            valor_ind_temporario = None
            
            if dados_serv_ind_escolhido["tipo_input"] == "componentes":
                valor_ind_temporario = st.number_input(
                    "Quantidade de Componentes (R$ 50,00 por componente):", min_value=0.0, step=1.0, 
                    value=None, placeholder="Digite a quantidade de componentes...", key=f"in_aba_ind_temp_{escolha_serv_ind}"
                )
            elif dados_serv_ind_escolhido["tipo_input"] == "quantidade":
                valor_ind_temporario = st.number_input(
                    "Quantidade:", min_value=0.0, step=1.0, 
                    value=None, placeholder="Digite a quantidade...", key=f"in_aba_ind_temp_{escolha_serv_ind}"
                )
            elif dados_serv_ind_escolhido["tipo_input"] == "metragem":
                valor_ind_temporario = st.number_input(
                    "Metragem (m):", min_value=0.0, step=0.5, 
                    value=None, placeholder="Digite a metragem...", key=f"in_aba_ind_temp_{escolha_serv_ind}"
                )
                
            if st.button("Confirmar Serviço Industrial", type="primary", key=f"btn_confirmar_ind_{escolha_serv_ind}"):
                st.session_state.dados_servicos[escolha_serv_ind] = float(valor_ind_temporario) if valor_ind_temporario is not None else 0.0
                st.success(f"Serviço Industrial '{escolha_serv_ind}' confirmado!")
                st.session_state.reset_industrial_select += 1
                time.sleep(0.5)
                st.rerun()
    else:
        st.info("Nenhum serviço industrial configurado no banco de dados.")
    # --- PROCESSAMENTO ESPECÍFICO PARA PROJETOS/ART (Fixo + 55%) ---
    for servico, dado in st.session_state.dados_servicos.items():
        serv_info = next((s for s in servicos_db if s["nome"] == servico), None)
        if serv_info and serv_info["tipo_input"] == "art" and dado:
            servicos_ativos = True
            v_art = precos[servico] + (soma_base_para_art * 0.55)
            itens_orc[servico] = v_art
            
            with st.container(border=True):
                cl1, cl2, cl3, cl4 = st.columns([0.4, 0.2, 0.2, 0.2])
                cl1.write(servico)
                cl2.write("Fixo + 55%")
                cl3.write(f"R$ {v_art:.2f}")
                if cl4.button("🗑️", key=f"del_aba_art_{servico}"):
                    st.session_state.dados_servicos[servico] = False
                    st.rerun()

    if not servicos_ativos:
        st.info("Nenhum serviço lançado até o momento.")

    # --- TABELA DE REVISÃO DE MATERIAIS (EDITÁVEL) ---
    st.divider()
    st.markdown("### 📦 Materiais Lançados pela Barra Lateral")
    
    if not st.session_state.lista_materiais:
        st.info("Nenhum material adicionado através da barra lateral.")
    else:
        cm_h1, cm_h2, cm_h3, cm_h4 = st.columns([0.4, 0.2, 0.2, 0.2])
        cm_h1.write("**Especificação Completa do Material**")
        cm_h2.write("**Quantidade / Unidade**")
        cm_h3.write("**Custo Informado**")
        cm_h4.write("**Remover**")
        
        for i, item in enumerate(st.session_state.lista_materiais):
            with st.container(border=True):
                m1, m2, m3, m4 = st.columns([0.4, 0.2, 0.2, 0.2])
                
                # Permite edição do nome
                st.session_state.lista_materiais[i]['nome'] = m1.text_input(
                    "Nome:", item['nome'], key=f"ed_aba_n_{i}", label_visibility="collapsed"
                )
                
                # Permite edição da quantidade e unidade em colunas internas
                sub_c1, sub_c2 = m2.columns([0.5, 0.5])
                st.session_state.lista_materiais[i]['qtd'] = sub_c1.number_input(
                    "Qtd:", value=float(item['qtd']), step=1.0, key=f"ed_aba_q_{i}", label_visibility="collapsed"
                )
                
                # Inicializa chave de unidade caso não exista para evitar falhas
                if 'unidade' not in st.session_state.lista_materiais[i]:
                    st.session_state.lista_materiais[i]['unidade'] = "un"
                    
                lista_unidades_mat = ["un", "m", "kg", "pç", "cx"]
                idx_uni_mat = lista_unidades_mat.index(item['unidade']) if item['unidade'] in lista_unidades_mat else 0
                
                st.session_state.lista_materiais[i]['unidade'] = sub_c2.selectbox(
                    "Und:", lista_unidades_mat, index=idx_uni_mat, key=f"ed_aba_u_mat_{i}", label_visibility="collapsed"
                )
                
                m3.write(f"R$ {item.get('preco_calculado', 0.0):.2f}")
                
                if m4.button("🗑️", key=f"del_aba_m_{i}"):
                    st.session_state.lista_materiais.pop(i)
                    st.rerun()

    # --- RESUMO GERAL DOS VALORES ---
    st.divider()
    total_mo_calculado = sum(itens_orc.values())
    total_mats_calculado = sum([m.get("preco_calculado", 0.0) for m in st.session_state.lista_materiais])
    valor_geral_proposta = total_mo_calculado + total_mats_calculado
    
    st.write(f"### Valor Total da Mão de Obra: R$ {total_mo_calculado:.2f}")
    if total_mats_calculado > 0:
        st.write(f"### Valor Total de Materiais Informados: R$ {total_mats_calculado:.2f}")
    st.write(f"## 💰 Valor Geral da Proposta: R$ {valor_geral_proposta:.2f}")

    # --- CENTRAL DE DOWNLOADS VIA GERAÇÃO DE PDF ---
    st.markdown("### 📄 Central de Exportação em PDF")
    col_d1, col_d2, col_d3 = st.columns(3)
    
    if servicos_ativos:
        pdf_mo_dados = f"========================================\n" \
                       f"        RELATORIO DE MAO DE OBRA        \n" \
                       f"========================================\n\n"
        for serv, val in itens_orc.items():
            pdf_mo_dados += f"- {serv}: R$ {val:.2f}\n"
        pdf_mo_dados += f"\n----------------------------------------\n" \
                        f"VALOR TOTAL DA MAO DE OBRA: R$ {total_mo_calculado:.2f}\n" \
                        f"========================================\n"
                        
        col_d1.download_button(
            label="📥 Baixar Mão de Obra (PDF)",
            data=pdf_mo_dados,
            file_name="mao_de_obra.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
    if st.session_state.lista_materiais:
        # Relatório 1: Materiais completos com valores
        pdf_mat_com_preco = f"========================================\n" \
                            f"   RELATORIO DE MATERIAIS (COM PRECOS)  \n" \
                            f"========================================\n\n"
        for item in st.session_state.lista_materiais:
            pdf_mat_com_preco += f"- {item['nome']} | Qtd: {item['qtd']} {item['unidade']} | Valor: R$ {item.get('preco_calculado', 0.0):.2f}\n"
        pdf_mat_com_preco += f"\n----------------------------------------\n" \
                             f"VALOR TOTAL DOS MATERIAIS: R$ {total_mats_calculado:.2f}\n" \
                             f"========================================\n"
                             
        col_d2.download_button(
            label="📥 Baixar Materiais com Preço (PDF)",
            data=pdf_mat_com_preco,
            file_name="materiais_com_precos.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        # Relatório 2: Apenas quantitativo inibindo todos os valores
        pdf_mat_sem_preco = f"========================================\n" \
                            f"  LISTA DE MATERIAIS (QUANTITATIVO)     \n" \
                            f"========================================\n\n"
        for item in st.session_state.lista_materiais:
            pdf_mat_sem_preco += f"- {item['nome']} | Qtd: {item['qtd']} {item['unidade']}\n"
        pdf_mat_sem_preco += f"========================================\n"
        
        col_d3.download_button(
            label="📥 Baixar Lista de Materiais Sem Preço (PDF)",
            data=pdf_mat_sem_preco,
            file_name="materiais_sem_precos.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # --- CLÁUSULA DO WORD (MANTIDA ORIGINALMENTE) ---
    def gerar_word_proposicao(orc, mats, tot):
        doc = Document()
        for s in doc.sections:
            s.top_margin = Pt(72)
