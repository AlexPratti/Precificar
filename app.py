import streamlit as st
from supabase import create_client, Client
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Sistema de Orçamento Elétrico Profissional", layout="wide")

# --- CONEXÃO SUPABASE (AJUSTADA PARA SEUS SECRETS) ---
@st.cache_resource
def init_connection():
    try:
        # Nomes alterados para bater com sua imagem (Secrets)
        url = st.secrets["URL_SUPABASE"]
        key = st.secrets["KEY_SUPABASE"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique os nomes no Secrets. Detalhe: {e}")
        return None

supabase = init_connection()

if supabase is None:
    st.stop()

# --- INICIALIZAÇÃO DO ESTADO DE MÃO DE OBRA ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0, "Pontos Baixos e Médios de Força": 0,
        "Luminárias em Teto/Gesso/PVC": 0, "Perfil LED em Teto/Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Instalações sobre Laje/Telhados": 0.0, "Instalação de Eletrodutos/Canaletas Sobrepostas": 0.0,
        "Quadro de Disjuntores": 0, "Instalação do Padrão": {"incluir": False, "tipo": "Monofásico"},
        "Projeto e ART": False
    }

# --- FUNÇÕES AUXILIARES ---
def formatar_qtd(qtd, unidade):
    return f"{float(qtd):.1f}" if unidade.lower() == "m" else f"{int(qtd)}"

# --- FUNÇÕES DO BANCO DE DADOS (SUPABASE) ---
def adicionar_ou_somar_material(nome, qtd, uni):
    nome_chave = nome.strip().lower()
    try:
        res = supabase.table("orc_eletrico_itens").select("*").eq("orc_item_nome_chave", nome_chave).eq("orc_item_unidade", uni).execute()
        
        if res.data:
            item = res.data[0]
            nova_qtd = item['orc_item_quantidade'] + qtd
            supabase.table("orc_eletrico_itens").update({"orc_item_quantidade": nova_qtd}).eq("id", item['id']).execute()
        else:
            supabase.table("orc_eletrico_itens").insert({
                "orc_item_nome_chave": nome_chave,
                "orc_item_nome_visual": nome.strip(),
                "orc_item_quantidade": qtd,
                "orc_item_unidade": uni
            }).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")
        return False

def buscar_materiais():
    try:
        res = supabase.table("orc_eletrico_itens").select("*").order("created_at").execute()
        return res.data
    except:
        return []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Preços Mão de Obra")
    precos = {k: st.number_input(k, value=20.0 if "m" in k else 30.0) for k in st.session_state.dados_servicos.keys() if k not in ["Instalação do Padrão", "Projeto e ART"]}
    precos["Instalação do Padrão"] = st.number_input("Instalação do Padrão", value=400.0)
    precos["Projeto e ART"] = st.number_input("Projeto e ART", value=800.0)

tab1, tab2, tab_conf, tab3 = st.tabs(["📋 Serviços", "📦 Materiais", "🔍 Conferência", "📄 Gerar Orçamento"])

# --- ABA 1: SERVIÇOS ---
with tab1:
    escolha_serv = st.selectbox("Selecione o serviço para editar:", list(st.session_state.dados_servicos.keys()))
    if escolha_serv in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Teto/Gesso/PVC", "Quadro de Disjuntores"]:
        st.session_state.dados_servicos[escolha_serv] = st.number_input("Quantidade:", min_value=0, step=1, value=int(st.session_state.dados_servicos[escolha_serv]))
    elif escolha_serv in ["Perfil LED em Teto/Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores", "Instalações sobre Laje/Telhados", "Instalação de Eletrodutos/Canaletas Sobrepostas"]:
        st.session_state.dados_servicos[escolha_serv] = st.number_input("Metragem (m):", min_value=0.0, step=0.5, value=float(st.session_state.dados_servicos[escolha_serv]))
    elif escolha_serv == "Instalação do Padrão":
        d = st.session_state.dados_servicos[escolha_serv]
        inc = st.checkbox("Incluir Padrão?", value=d["incluir"])
        tipo = st.selectbox("Fase:", ["Monofásico", "Bifásico", "Trifásico"], index=["Monofásico", "Bifásico", "Trifásico"].index(d["tipo"]))
        st.session_state.dados_servicos[escolha_serv] = {"incluir": inc, "tipo": tipo}
    elif escolha_serv == "Projeto e ART":
        st.session_state.dados_servicos[escolha_serv] = st.checkbox("Incluir Projeto/ART?", value=st.session_state.dados_servicos[escolha_serv])

# --- ABA 2: MATERIAIS ---
with tab2:
    st.subheader("📦 Lançamento de Materiais")
    cat = st.selectbox("Categoria:", ["CABOS", "DISJUNTORES", "MÓDULOS, TOMADAS E PLACAS", "CONDUÍTES", "CONDULETES", "OUTROS"])
    
    with st.container(border=True):
        nome_f, uni_f, qtd_f = "", "", 0.0
        
        if cat == "CABOS":
            c1, c2, c3 = st.columns(3)
            sec = c1.selectbox("Seção:", ["1,0 mm²", "1,5 mm²", "2,5 mm²", "4,0 mm²", "6,0 mm²", "10 mm²", "16 mm²", "25 mm²", "35 mm²"])
            cor = c2.selectbox("Cor:", ["azul", "preto", "branco", "vermelho", "amarelo", "verde", "verde e amarelo", "cinza", "marrom"])
            qtd_f = c3.number_input("Metros:", min_value=0.0, step=1.0)
            nome_f, uni_f = f"Cabo Flexível {sec} {cor}", "m"

        elif cat == "DISJUNTORES":
            c1, c2, c3, c4 = st.columns(4)
            amperagens = [f"{a} A" for a in [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]]
            corr = c1.selectbox("Corrente Nominal:", amperagens)
            fase = c2.selectbox("Polos:", ["Unipolar", "Bipolar", "Tripolar"])
            curva = c3.selectbox("Curva:", ["B", "C", "D"], index=1)
            qtd_f = c4.number_input("Qtde:", min_value=0, step=1)
            nome_f, uni_f = f"Disjuntor {fase} {curva}{corr.replace(' A', '')}", "un"

        elif cat == "CONDUÍTES" or cat == "CONDULETES":
            c1, c2, c3 = st.columns(3)
            bits = ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"', '2 1/2"', '3"', '4"']
            sec = c1.selectbox("Bitola:", bits)
            if cat == "CONDUÍTES":
                tipo = c2.text_input("Tipo (ex: Corrugado):")
                uni_f = "m"
            else:
                tipo = c2.selectbox("Tipo:", ["C", "E", "X", "T", "LR", "LL", "LB", "TB", "B"])
                uni_f = "un"
            qtd_f = c3.number_input("Qtd:", min_value=0.0)
            nome_f = f"{cat.title()[:-1]} {sec} {tipo}"

        elif cat == "MÓDULOS, TOMADAS E PLACAS":
            c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
            tipo = c1.selectbox("Tipo:", ["Placa 4x2", "Placa 4x4", "Módulo Tomada", "Módulo Interruptor", "Three Way"])
            desc = c2.text_input("Descrição (ex: 3 postos):")
            qtd_f = c3.number_input("Qtde:", min_value=0)
            nome_f, uni_f = f"{tipo} {desc}", "pç"

        elif cat == "OUTROS":
            c1, c2, c3 = st.columns([0.5, 0.2, 0.3])
            nome_f = c1.text_input("Descrição:")
            uni_f = c2.selectbox("Unid:", ["un", "m", "Pç", "kg"])
            qtd_f = c3.number_input("Qtd:", min_value=0.0)

        if st.button("➕ Adicionar à Lista"):
            if nome_f and qtd_f > 0:
                if adicionar_ou_somar_material(nome_f, qtd_f, uni_f):
                    st.success(f"{nome_f} processado!")
                    st.rerun()

# --- ABA DE CONFERÊNCIA ---
with tab_conf:
    st.subheader("🔍 Conferência e Edição")
    mats_db = buscar_materiais()
    
    if not mats_db:
        st.info("Nenhum material no banco de dados.")
    else:
        if st.button("🚨 Limpar Lista Completa"):
            try:
                supabase.table("orc_eletrico_itens").delete().neq("id", 0).execute()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao limpar: {e}")
        
        for item in mats_db:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.5, 0.15, 0.15, 0.2])
                novo_n = c1.text_input("Nome:", item['orc_item_nome_visual'], key=f"n_{item['id']}")
                nova_q = c2.number_input("Qtd:", value=float(item['orc_item_quantidade']), key=f"q_{item['id']}")
                nova_u = c3.text_input("Uni:", item['orc_item_unidade'], key=f"u_{item['id']}")
                
                if c4.button("🗑️", key=f"del_{item['id']}"):
                    supabase.table("orc_eletrico_itens").delete().eq("id", item['id']).execute()
                    st.rerun()
                
                if novo_n != item['orc_item_nome_visual'] or nova_q != item['orc_item_quantidade'] or nova_u != item['orc_item_unidade']:
                    supabase.table("orc_eletrico_itens").update({
                        "orc_item_nome_visual": novo_n, "orc_item_quantidade": nova_q, "orc_item_unidade": nova_u,
                        "orc_item_nome_chave": novo_n.lower()
                    }).eq("id", item['id']).execute()

# --- ABA 3: EXPORTAÇÃO ---
with tab3:
    itens_orc, soma_serv = {}, 0.0
    for k, v in st.session_state.dados_servicos.items():
        if k == "Instalação do Padrão" and v["incluir"]:
            val = precos[k] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[v["tipo"]]
            itens_orc[k], soma_serv = val, soma_serv + val
        elif k != "Projeto e ART" and k != "Instalação do Padrão" and v > 0:
            val = v * precos[k]
            itens_orc[k], soma_serv = val, soma_serv + val
    if st.session_state.dados_servicos["Projeto e ART"]:
        itens_orc["Projeto e ART"] = precos["Projeto e ART"] + (soma_serv * 0.55)
    
    total_mo = sum(itens_orc.values())
    st.write(f"### Total Mão de Obra: R$ {total_mo:.2f}")

    def gerar_word(orc, total_mo_val):
        doc = Document()
        for s in doc.sections: s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Pt(72)
        style = doc.styles['Normal']
        style.font.name, style.font.size, style.paragraph_format.line_spacing = 'Arial', Pt(12), 1.5
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if orc:
            doc.add_heading('ORÇAMENTO DE MÃO DE OBRA', 1)
            for k, v in orc.items():
                p = doc.add_paragraph()
                p.add_run(f"• {k}: ").bold = True
                p.add_run(f"R$ {v:.2f}")
            p_t = doc.add_paragraph()
            p_t.add_run(f"\nVALOR TOTAL DO ORÇAMENTO: R$ {total_mo_val:.2f}").bold = True
            
        mats = buscar_materiais()
        if mats:
            doc.add_page_break()
            doc.add_heading('LISTA DE MATERIAIS', 1)
            for m in mats:
                q_f = formatar_qtd(m['orc_item_quantidade'], m['orc_item_unidade'])
                doc.add_paragraph(f"• {m['orc_item_nome_visual']}: {q_f} {m['orc_item_unidade']}")
        
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    if total_mo > 0 or buscar_materiais():
        st.download_button("📥 Baixar Documento Completo", gerar_word(itens_orc, total_mo), "orcamento.docx", type="primary")
