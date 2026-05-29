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

# --- CACHE DE CONSULTAS PARA EVITAR LOOPS DE CARREGAMENTO ---
@st.cache_data(ttl=30)
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

# --- FALLBACK DE SEGURANÇA SE AS TABELAS NÃO EXISTIREM ---
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

# --- INICIALIZAÇÃO DE ESTADOS DA SESSÃO ---
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

# --- MENU DE SELEÇÃO DE AMBIENTE DA SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações do App")
    aba_selecionada = st.radio("Selecione o Ambiente de Trabalho:", ["Predial", "Industrial"], key="radio_ambiente_global")

    st.subheader(f"Mão de Obra: {aba_selecionada}")
    servicos_filtrados = [s for s in servicos_db if s["tipo_categoria"] == aba_selecionada]
    
    precos = {}
    valores_novos = {}
    
    for s in servicos_filtrados:
        label_exibicao = s["nome"]
        if s["tipo_input"] == "componentes":
            label_exibicao = f"{s['nome']} (por Componente)"
        
        valores_novos[s["nome"]] = st.number_input(
            f"Valor: {label_exibicao}", 
            value=float(s["valor"]), 
            key=f"p_{s['nome']}"
        )
        precos[s["nome"]] = valores_novos[s["nome"]]
    
    for s in servicos_db:
        if s["nome"] not in precos:
            precos[s["nome"]] = float(s["valor"])

    if st.button("💾 Confirmar Novos Valores", type="primary", use_container_width=True, key="btn_salvar_precos_side"):
        for s in servicos_filtrados:
            supabase_upsert("precif_servicos", {
                "nome": s["nome"],
                "tipo_categoria": s["tipo_categoria"],
                "valor": valores_novos[s["nome"]],
                "tipo_input": s["tipo_input"],
                "deletavel": s["deletavel"]
            })
        st.success("Preços salvos!")
        time.sleep(0.5)
        st.rerun()
        
    st.divider()
    st.subheader("➕ Nova Mão de Obra")
    novo_nome = st.text_input("Nome do Serviço:", key="add_nome_serv")
    novo_tipo_in = st.selectbox("Tipo de Cobrança:", ["quantidade", "metragem", "componentes"], key="add_tipo_serv")
    novo_valor = st.number_input("Valor Inicial (R$):", min_value=0.0, value=50.0, key="add_val_serv")
    
    if st.button("Adicionar Serviço", use_container_width=True, key="btn_add_serv_side"):
        if novo_nome.strip():
            if not any(s['nome'].lower() == novo_nome.strip().lower() for s in servicos_db):
                supabase_post("precif_servicos", {
                    "nome": novo_nome.strip(),
                    "tipo_categoria": aba_selecionada,
                    "valor": novo_valor,
                    "tipo_input": novo_tipo_in,
                    "deletavel": True
                })
                st.success("Serviço criado!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Serviço já existente!")
        else:
            st.error("Insira um nome válido.")

    servicos_deletaveis = [s for s in servicos_filtrados if s["deletavel"]]
    if servicos_deletaveis:
        st.divider()
        st.subheader("🗑️ Excluir Mão de Obra")
        serv_para_deletar = st.selectbox("Selecione para excluir:", [s["nome"] for s in servicos_deletaveis], key="sel_del_serv")
        if st.button("Remover Serviço Definitivamente", type="secondary", use_container_width=True, key="btn_remover_serv"):
            supabase_delete("precif_servicos", {"nome": f"eq.{serv_para_deletar}"})
            if serv_para_deletar in st.session_state.dados_servicos:
                st.session_state.dados_servicos.pop(serv_para_deletar)
            st.success("Serviço removido!")
            time.sleep(0.5)
            st.rerun()
# --- CONTINUAÇÃO DO CÓDIGO (PARTE 2 DE 2) ---

def formatar_qtd(qtd, unidade):
    if unidade.lower() == "m":
        return f"{float(qtd):.1f}"
    return f"{int(qtd)}"

# --- ABAS PRINCIPAIS ---
tab_predial, tab_industrial, tab_conf_serv, tab_mat, tab_conf_mat, tab_doc = st.tabs([
    "🏢 Predial", "🏭 Industrial", "🔍 Conferência Serviços", "📦 Materiais", "🔍 Conferência Materiais", "📄 Gerar Orçamento"
])

# --- ABA: PREDIAL (MÃO DE OBRA) ---
with tab_predial:
    st.subheader("Lançamento de Mão de Obra - Predial")
    servicos_prediais = [s for s in servicos_db if s["tipo_categoria"] == "Predial"]
    nomes_prediais = [s["nome"] for s in servicos_prediais]
    
    if nomes_prediais:
        escolha_serv = st.selectbox("Selecione o serviço predial para editar:", nomes_prediais, key="sel_predial")
        dados_serv_escolhido = next(s for s in servicos_prediais if s["nome"] == escolha_serv)
        
        if dados_serv_escolhido["tipo_input"] == "quantidade":
            st.session_state.dados_servicos[escolha_serv] = st.number_input(
                "Quantidade:", min_value=0.0, step=1.0, 
                value=float(st.session_state.dados_servicos.get(escolha_serv, 0.0)), key=f"in_pr_{escolha_serv}"
            )
        elif dados_serv_escolhido["tipo_input"] == "metragem":
            st.session_state.dados_servicos[escolha_serv] = st.number_input(
                "Metragem (m):", min_value=0.0, step=0.5, 
                value=float(st.session_state.dados_servicos.get(escolha_serv, 0.0)), key=f"in_pr_{escolha_serv}"
            )
        elif dados_serv_escolhido["tipo_input"] == "padrao":
            d = st.session_state.dados_servicos.get(escolha_serv, {"incluir": False, "tipo": "Monofásico"})
            inc = st.checkbox("Incluir Padrão?", value=d["incluir"], key="chk_padrao_pr")
            tipo = st.selectbox("Fase:", ["Monofásico", "Bifásico", "Trifásico"], index=["Monofásico", "Bifásico", "Trifásico"].index(d["tipo"]), key="sel_fase_pr")
            st.session_state.dados_servicos[escolha_serv] = {"incluir": inc, "tipo": tipo}
        elif dados_serv_escolhido["tipo_input"] == "art":
            st.session_state.dados_servicos[escolha_serv] = st.checkbox(
                "Incluir Projeto/ART?", value=bool(st.session_state.dados_servicos.get(escolha_serv, False)), key="chk_art_pr"
            )
    else:
        st.info("Nenhum serviço predial cadastrado.")

# --- ABA: INDUSTRIAL (MÃO DE OBRA) ---
with tab_industrial:
    st.subheader("Lançamento de Mão de Obra - Industrial")
    servicos_industriais = [s for s in servicos_db if s["tipo_categoria"] == "Industrial"]
    nomes_industriais = [s["nome"] for s in servicos_industriais]
    
    if nomes_industriais:
        escolha_serv_ind = st.selectbox("Selecione o serviço industrial para editar:", nomes_industriais, key="sel_ind")
        dados_serv_ind_escolhido = next(s for s in servicos_industriais if s["nome"] == escolha_serv_ind)
        
        if dados_serv_ind_escolhido["tipo_input"] in ["quantidade", "componentes"]:
            label_input = "Quantidade de Componentes:" if dados_serv_ind_escolhido["tipo_input"] == "componentes" else "Quantidade:"
            st.session_state.dados_servicos[escolha_serv_ind] = st.number_input(
                label_input, min_value=0.0, step=1.0, 
                value=float(st.session_state.dados_servicos.get(escolha_serv_ind, 0.0)), key=f"in_ind_{escolha_serv_ind}"
            )
        elif dados_serv_ind_escolhido["tipo_input"] == "metragem":
            st.session_state.dados_servicos[escolha_serv_ind] = st.number_input(
                "Metragem (m):", min_value=0.0, step=0.5, 
                value=float(st.session_state.dados_servicos.get(escolha_serv_ind, 0.0)), key=f"in_ind_{escolha_serv_ind}"
            )
    else:
        st.info("Nenhum serviço industrial cadastrado.")

# --- ABA: CONFERÊNCIA DE SERVIÇOS ---
with tab_conf_serv:
    st.subheader("🔍 Revisão de Serviços Lançados")
    soma_base_para_art = 0.0
    servicos_ativos = False
    
    if st.button("🚨 Zerar Todos os Serviços", key="btn_zerar_serv"):
        for k in st.session_state.dados_servicos.keys():
            serv_info = next((s for s in servicos_db if s["nome"] == k), None)
            if serv_info and serv_info["tipo_input"] == "padrao":
                st.session_state.dados_servicos[k] = {"incluir": False, "tipo": "Monofásico"}
            elif serv_info and serv_info["tipo_input"] == "art":
                st.session_state.dados_servicos[k] = False
            else:
                st.session_state.dados_servicos[k] = 0.0
        st.rerun()
    
    st.divider()
    col_h1, col_h2, col_h3, col_h4 = st.columns([0.4, 0.2, 0.2, 0.2])
    col_h1.write("**Serviço**"); col_h2.write("**Qtd/Fase**"); col_h3.write("**Subtotal**"); col_h4.write("**Ação**")

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
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.4, 0.2, 0.2, 0.2])
                c1.write(servico); c2.write(label); c3.write(f"R$ {v_item:.2f}")
                if c4.button("🗑️", key=f"del_srv_{servico}"):
                    if serv_info["tipo_input"] == "padrao":
                        st.session_state.dados_servicos[servico]["incluir"] = False
                    else:
                        st.session_state.dados_servicos[servico] = 0.0
                    st.rerun()

    for servico, dado in st.session_state.dados_servicos.items():
        serv_info = next((s for s in servicos_db if s["nome"] == servico), None)
        if serv_info and serv_info["tipo_input"] == "art" and dado:
            servicos_ativos = True
            v_art = precos[servico] + (soma_base_para_art * 0.55)
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.4, 0.2, 0.2, 0.2])
                c1.write(servico); c2.write("Fixo+55%"); c3.write(f"R$ {v_art:.2f}")
                if c4.button("🗑️", key=f"del_art_{servico}"):
                    st.session_state.dados_servicos[servico] = False
                    st.rerun()

    if not servicos_ativos:
        st.info("Nenhum serviço lançado.")

# --- ABA: MATERIAIS (CADASTRO E LANÇAMENTO) ---
with tab_mat:
    st.subheader("📦 Lançamento de Materiais")
    
    lista_db_materiais = supabase_get("precif_materiais_base")
    if lista_db_materiais is None:
        lista_db_materiais = []
        
    categorias_adicionais = sorted(list(set([m["categoria"] for m in lista_db_materiais])))
    categorias_base = ["CABOS", "DISJUNTORES", "MÓDULOS, TOMADAS E PLACAS", "CONDUÍTES", "CONDULETES", "OUTROS"]
    todas_categorias = categorias_base + [c for c in categorias_adicionais if c not in categorias_base]
    
    categoria = st.selectbox("Categoria:", todas_categorias, key="sel_cat_materiais")
    
    with st.container(border=True):
        nome_f, uni_f, qtd_f = "", "", 0.0
        
        if categoria == "CABOS":
            c1, c2, c3 = st.columns(3)
            sec = c1.selectbox("Seção:", ["1,0 mm²", "1,5 mm²", "2,5 mm²", "4,0 mm²", "6,0 mm²", "10 mm²", "16 mm²", "25 mm²", "35 mm²"])
            cor = c2.selectbox("Cor:", ["azul", "preto", "branco", "vermelho", "amarelo", "verde", "verde e amarelo", "cinza", "marrom"])
            qtd_f = c3.number_input("Metros:", min_value=0.0, step=1.0, key="in_q_cabo")
            nome_f, uni_f = f"Cabo Flexível {sec} {cor}", "m"

        elif categoria == "DISJUNTORES":
            c1, c2, c3, c4 = st.columns(4)
            amps = [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]
            corr = c1.selectbox("Corrente:", [f"{a} A" for a in amps])
            fase = c2.selectbox("Polos:", ["Unipolar", "Bipolar", "Tripolar"])
            curva = c3.selectbox("Curva:", ["B", "C", "D"], index=1)
            qtd_f = c4.number_input("Qtde:", min_value=0, step=1, key="in_q_disj")
            nome_f, uni_f = f"Disjuntor {fase} {curva}{corr.replace(' A', '')}", "un"

        elif categoria == "MÓDULOS, TOMADAS E PLACAS":
            c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
            tipo = c1.selectbox("Tipo:", ["Placa 4x2", "Placa 4x4", "Módulo Tomada", "Módulo Interruptor"])
            if tipo == "Módulo Interruptor":
                desc_op = ["Simples", "Three Way", "Four Way", "Simples com Tomada"]
            elif tipo == "Módulo Tomada":
                desc_op = ["10 A", "20 A", "USB", "RJ45", "TV"]
            else:
                desc_op = ["Cega", "1 posto", "2 postos", "3 postos", "4 postos", "6 postos"]
            desc = c2.selectbox("Descrição:", desc_op)
            qtd_f = c3.number_input("Qtde:", min_value=0, step=1, key="in_q_mod")
            nome_f, uni_f = f"{tipo} {desc}", "pç"

        elif categoria in ["CONDUÍTES", "CONDULETES"]:
            c1, c2, c3 = st.columns(3)
            bits = ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"', '2 1/2"', '3"', '4"']
            sec = c1.selectbox("Bitola:", bits)
