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
# --- CONTINUAÇÃO DO CÓDIGO (PARTE 2 DE 2) ---

def formatar_qtd(qtd, unidade):
    if unidade.lower() == "m":
        return f"{float(qtd):.1f}"
    return f"{int(qtd)}"

# --- ABAS PRINCIPAIS ---
tab_predial, tab_industrial, tab_conf_serv = st.tabs([
    "🏢 Predial", "🏭 Industrial", "🔍 Conferência e Fechamento"
])

# --- ABA 1: PREDIAL (MÃO DE OBRA) ---
with tab_predial:
    st.subheader("Lançamento de Mão de Obra - Predial")
    servicos_prediais = [s for s in servicos_db if s["tipo_categoria"] == "Predial"]
    nomes_prediais = [s["nome"] for s in servicos_prediais]
    
    if nomes_prediais:
        escolha_serv = st.selectbox("Selecione o serviço predial para lançar/editar:", nomes_prediais, key="sel_predial_aba")
        dados_serv_escolhido = next(s for s in servicos_prediais if s["nome"] == escolha_serv)
        
        if dados_serv_escolhido["tipo_input"] == "quantidade":
            st.session_state.dados_servicos[escolha_serv] = st.number_input(
                "Quantidade (unidades/peças):", min_value=0.0, step=1.0, 
                value=float(st.session_state.dados_servicos.get(escolha_serv, 0.0)), key=f"in_aba_pr_{escolha_serv}"
            )
        elif dados_serv_escolhido["tipo_input"] == "metragem":
            st.session_state.dados_servicos[escolha_serv] = st.number_input(
                "Metragem (m):", min_value=0.0, step=0.5, 
                value=float(st.session_state.dados_servicos.get(escolha_serv, 0.0)), key=f"in_aba_pr_{escolha_serv}"
            )
        elif dados_serv_escolhido["tipo_input"] == "padrao":
            d = st.session_state.dados_servicos.get(escolha_serv, {"incluir": False, "tipo": "Monofásico"})
            inc = st.checkbox("Incluir Padrão no Orçamento?", value=d["incluir"], key="chk_aba_padrao_pr")
            tipo = st.selectbox("Fase do Padrão:", ["Monofásico", "Bifásico", "Trifásico"], index=["Monofásico", "Bifásico", "Trifásico"].index(d["tipo"]), key="sel_aba_fase_pr")
            st.session_state.dados_servicos[escolha_serv] = {"incluir": inc, "tipo": tipo}
        elif dados_serv_escolhido["tipo_input"] == "art":
            st.session_state.dados_servicos[escolha_serv] = st.checkbox(
                "Incluir Projeto e taxa de ART?", value=bool(st.session_state.dados_servicos.get(escolha_serv, False)), key="chk_aba_art_pr"
            )
    else:
        st.info("Nenhum serviço predial configurado no banco de dados.")

# --- ABA 2: INDUSTRIAL (MÃO DE OBRA) ---
with tab_industrial:
    st.subheader("Lançamento de Mão de Obra - Industrial")
    servicos_industriais = [s for s in servicos_db if s["tipo_categoria"] == "Industrial"]
    nomes_industriais = [s["nome"] for s in servicos_industriais]
    
    if nomes_industriais:
        escolha_serv_ind = st.selectbox("Selecione o serviço industrial para lançar/editar:", nomes_industriais, key="sel_ind_aba")
        dados_serv_ind_escolhido = next(s for s in servicos_industriais if s["nome"] == escolha_serv_ind)
        
        if dados_serv_ind_escolhido["tipo_input"] == "componentes":
            st.session_state.dados_servicos[escolha_serv_ind] = st.number_input(
                "Quantidade de Componentes (R$ 50,00 por componente):", min_value=0.0, step=1.0, 
                value=float(st.session_state.dados_servicos.get(escolha_serv_ind, 0.0)), key=f"in_aba_ind_{escolha_serv_ind}"
            )
        elif dados_serv_ind_escolhido["tipo_input"] == "quantidade":
            st.session_state.dados_servicos[escolha_serv_ind] = st.number_input(
                "Quantidade:", min_value=0.0, step=1.0, 
                value=float(st.session_state.dados_servicos.get(escolha_serv_ind, 0.0)), key=f"in_aba_ind_{escolha_serv_ind}"
            )
        elif dados_serv_ind_escolhido["tipo_input"] == "metragem":
            st.session_state.dados_servicos[escolha_serv_ind] = st.number_input(
                "Metragem (m):", min_value=0.0, step=0.5, 
                value=float(st.session_state.dados_servicos.get(escolha_serv_ind, 0.0)), key=f"in_aba_ind_{escolha_serv_ind}"
            )
    else:
        st.info("Nenhum serviço industrial configurado no banco de dados.")

# --- ABA 3: CONFERÊNCIA E FECHAMENTO GERAL ---
with tab_conf_serv:
    st.subheader("🔍 Revisão de Serviços Lançados")
    soma_base_para_art = 0.0
    servicos_ativos = False
    
    col_z1, col_z2 = st.columns([0.5, 0.5])
    if col_z1.button("🚨 Zerar Todos os Serviços Lançados", key="btn_clear_all_srv"):
        for k in st.session_state.dados_servicos.keys():
            serv_info = next((s for s in servicos_db if s["nome"] == k), None)
            if serv_info and serv_info["tipo_input"] == "padrao":
                st.session_state.dados_servicos[k] = {"incluir": False, "tipo": "Monofásico"}
            elif serv_info and serv_info["tipo_input"] == "art":
                st.session_state.dados_servicos[k] = False
            else:
                st.session_state.dados_servicos[k] = 0.0
        st.rerun()
        
    if col_z2.button("🚨 Limpar Lista de Materiais Atual", key="btn_clear_all_mat"):
        st.session_state.lista_materiais = []
        st.rerun()
        
    st.divider()
    
    # --- TABELA DE REVISÃO DE MÃO DE OBRA ---
    st.markdown("### 📋 Serviços de Mão de Obra Incluídos")
    c_h1, c_h2, c_h3, c_h4 = st.columns([0.4, 0.2, 0.2, 0.2])
    c_h1.write("**Serviço / Item**"); c_h2.write("**Qtd / Tipo**"); c_h3.write("**Subtotal M.O.**"); c_h4.write("**Remover**")

    itens_orc = {}
    
    for servico, dado in st.session_state.dados_servicos.items():
        serv_info = next((s for s in servicos_db if s["nome"] == servico), None)
        if not serv_info:
            continue
            
        v_item, exibir, label = 0.0, False, ""
        
        if serv_info["tipo_input"] == "padrao":
            if dado["incluir"]:
                v_item = precos[servico] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[dado["tipo"]]
                exibir, label = True, dado["tipo"]
        elif serv_info["tipo_input"] == "art":
            continue
        else:
            if dado > 0:
                v_item = dado * precos[servico]
                exibir = True
                if serv_info["tipo_input"] == "metragem":
                    label = f"{dado:.1f} m"
                elif serv_info["tipo_input"] == "componentes":
                    label = f"{int(dado)} comp"
                else:
                    label = f"{int(dado)} un"
        
        if exibir:
            servicos_ativos = True
            soma_base_para_art += v_item
            itens_orc[servico] = v_item
            with st.container(border=True):
                cl1, cl2, cl3, cl4 = st.columns([0.4, 0.2, 0.2, 0.2])
                cl1.write(servico); cl2.write(label); cl3.write(f"R$ {v_item:.2f}")
                if cl4.button("🗑️", key=f"del_aba_srv_{servico}"):
                    if serv_info["tipo_input"] == "padrao":
                        st.session_state.dados_servicos[servico]["incluir"] = False
                    else:
                        st.session_state.dados_servicos[servico] = 0.0
                    st.rerun()

    # Processamento específico para Projetos/ART (Fixo + 55%)
    for servico, dado in st.session_state.dados_servicos.items():
        serv_info = next((s for s in servicos_db if s["nome"] == servico), None)
        if serv_info and serv_info["tipo_input"] == "art" and dado:
            servicos_ativos = True
            v_art = precos[servico] + (soma_base_para_art * 0.55)
            itens_orc[servico] = v_art
            with st.container(border=True):
                cl1, cl2, cl3, cl4 = st.columns([0.4, 0.2, 0.2, 0.2])
                cl1.write(servico); cl2.write("Fixo + 55%"); cl3.write(f"R$ {v_art:.2f}")
                if cl4.button("🗑️", key=f"del_aba_art_{servico}"):
                    st.session_state.dados_servicos[servico] = False
                    st.rerun()

    if not servicos_ativos:
        st.info("Nenhum serviço lançado até o momento.")

    # --- TABELA DE REVISÃO DE MATERIAIS ---
    st.divider()
    st.markdown("### 📦 Materiais Lançados pela Barra Lateral")
    
    if not st.session_state.lista_materiais:
        st.info("Nenhum material adicionado através da barra lateral.")
    else:
        cm_h1, cm_h2, cm_h3, cm_h4 = st.columns([0.4, 0.2, 0.2, 0.2])
        cm_h1.write("**Especificação Completa do Material**"); cm_h2.write("**Quantidade**"); cm_h3.write("**Custo Informado**"); cm_h4.write("**Remover**")
        
        for i, item in enumerate(st.session_state.lista_materiais):
            with st.container(border=True):
                m1, m2, m3, m4 = st.columns([0.4, 0.2, 0.2, 0.2])
                st.session_state.lista_materiais[i]['nome'] = m1.text_input("Nome:", item['nome'], key=f"ed_aba_n_{i}", label_visibility="collapsed")
                st.session_state.lista_materiais[i]['qtd'] = m2.number_input("Qtd:", value=float(item['qtd']), key=f"ed_aba_q_{i}", label_visibility="collapsed")
                m3.write(f"R$ {item.get('preco_calculado', 0.0):.2f}")
                
                if m4.button("🗑️", key=f"del_aba_m_{i}"):
                    st.session_state.lista_materiais.pop(i)
                    st.rerun()

    # --- RESUMO GERAL E GERADOR DO ARQUIVO DOCX ---
    st.divider()
    total_mo_calculado = sum(itens_orc.values())
    total_mats_calculado = sum([m.get("preco_calculado", 0.0) for m in st.session_state.lista_materiais])
    valor_geral_proposta = total_mo_calculado + total_mats_calculado
    
    st.write(f"### Valor Total da Mão de Obra: R$ {total_mo_calculado:.2f}")
    if total_mats_calculado > 0:
        st.write(f"### Valor Total de Materiais Informados: R$ {total_mats_calculado:.2f}")
    st.write(f"## 💰 Valor Geral da Proposta: R$ {valor_geral_proposta:.2f}")

    def gerar_word_proposicao(orc, mats, tot):
        doc = Document()
        for s in doc.sections:
            s.top_margin = Pt(72)
