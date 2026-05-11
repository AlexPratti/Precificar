import streamlit as st
from supabase import create_client, Client
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Sistema de Orçamento Elétrico Profissional", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["URL_SUPABASE"]
        key = st.secrets["KEY_SUPABASE"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro nos Secrets: {e}")
        return None

supabase = init_connection()
if supabase is None: st.stop()

# --- ESTADO DE MÃO DE OBRA ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0, "Pontos Baixos e Médios de Força": 0,
        "Luminárias em Teto/Gesso/PVC": 0, "Perfil LED em Teto/Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Instalações sobre Laje/Telhados": 0.0, "Instalação de Eletrodutos/Canaletas Sobrepostas": 0.0,
        "Quadro de Disjuntores": 0, "Instalação do Padrão": {"incluir": False, "tipo": "Monofásico"},
        "Projeto e ART": False
    }

# --- FUNÇÕES DE BANCO DE DADOS ---
def adicionar_ou_somar_material(nome, qtd, uni):
    nome_chave = nome.strip().lower()
    try:
        # Busca EXATA para verificar se já existe
        res = supabase.table("orc_eletrico_itens").select("*").eq("orc_item_nome_chave", nome_chave).eq("orc_item_unidade", uni).execute()
        
        if res.data and len(res.data) > 0:
            # SE EXISTE: Soma
            item = res.data[0]
            nova_qtd = float(item['orc_item_quantidade']) + float(qtd)
            supabase.table("orc_eletrico_itens").update({"orc_item_quantidade": nova_qtd}).eq("id", item['id']).execute()
            st.success(f"✓ Quantidade atualizada: {nome} (+{qtd})")
        else:
            # SE NÃO EXISTE: Cria novo
            supabase.table("orc_eletrico_itens").insert({
                "orc_item_nome_chave": nome_chave,
                "orc_item_nome_visual": nome.strip(),
                "orc_item_quantidade": float(qtd),
                "orc_item_unidade": uni
            }).execute()
            st.success(f"✓ {nome} adicionado!")
        return True
    except Exception as e:
        st.error(f"Erro ao processar no banco: {e}")
        return False

def buscar_materiais():
    try:
        return supabase.table("orc_eletrico_itens").select("*").order("created_at").execute().data
    except:
        return []

# --- INTERFACE ---
tab1, tab2, tab_conf, tab3 = st.tabs(["📋 Serviços", "📦 Materiais", "🔍 Conferência", "📄 Gerar Orçamento"])

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
            qtd_f = c3.number_input("Metros:", min_value=0.0, step=1.0, key="qtd_cabo")
            nome_f, uni_f = f"Cabo Flexível {sec} {cor}", "m"

        elif cat == "DISJUNTORES":
            c1, c2, c3, c4 = st.columns(4)
            amperagens = [f"{a} A" for a in [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]]
            corr = c1.selectbox("Corrente:", amperagens)
            fase = c2.selectbox("Polos:", ["Unipolar", "Bipolar", "Tripolar"])
            curva = c3.selectbox("Curva:", ["B", "C", "D"], index=1)
            qtd_f = c4.number_input("Qtde:", min_value=0, step=1, key="qtd_disj")
            nome_f, uni_f = f"Disjuntor {fase} {curva}{corr.replace(' A', '')}", "un"

        elif cat == "CONDUÍTES" or cat == "CONDULETES":
            c1, c2, c3 = st.columns(3)
            bits = ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"', '2 1/2"', '3"', '4"']
            sec = c1.selectbox("Bitola:", bits)
            if cat == "CONDUÍTES":
                tipo = st.text_input("Tipo (ex: Corrugado):", key="tp_cond")
                uni_f = "m"
            else:
                tipo = st.selectbox("Tipo:", ["C", "E", "X", "T", "LR", "LL", "LB", "TB", "B"], key="tp_let")
                uni_f = "un"
            qtd_f = c3.number_input("Qtd:", min_value=0.0, key="qtd_tubo")
            nome_f = f"{cat.title()[:-1]} {sec} {tipo}"

        elif cat == "MÓDULOS, TOMADAS E PLACAS":
            c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
            tipo = c1.selectbox("Tipo:", ["Placa 4x2", "Placa 4x4", "Módulo Tomada", "Módulo Interruptor", "Three Way"])
            desc = c2.text_input("Descrição (ex: 3 postos):", key="desc_mod")
            qtd_f = c3.number_input("Qtde:", min_value=0, key="qtd_mod")
            nome_f, uni_f = f"{tipo} {desc}", "pç"

        elif cat == "OUTROS":
            c1, c2, c3 = st.columns([0.5, 0.2, 0.3])
            nome_f = c1.text_input("Descrição:", key="desc_out")
            uni_f = c2.selectbox("Unid:", ["un", "m", "Pç", "kg"], key="uni_out")
            qtd_f = c3.number_input("Qtd:", min_value=0.0, key="qtd_out")

        if st.button("➕ Adicionar Material"):
            if nome_f and qtd_f > 0:
                adicionar_ou_somar_material(nome_f, qtd_f, uni_f)
                st.rerun()

# --- ABA DE CONFERÊNCIA ---
with tab_conf:
    mats_db = buscar_materiais()
    if mats_db:
        if st.button("🚨 Limpar Lista Completa"):
            supabase.table("orc_eletrico_itens").delete().neq("id", 0).execute()
            st.rerun()
        
        for item in mats_db:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.5, 0.15, 0.15, 0.2])
                n = c1.text_input("Nome:", item['orc_item_nome_visual'], key=f"n_{item['id']}")
                q = c2.number_input("Qtd:", value=float(item['orc_item_quantidade']), key=f"q_{item['id']}")
                u = c3.text_input("Uni:", item['orc_item_unidade'], key=f"u_{item['id']}")
                
                if c4.button("🗑️", key=f"del_{item['id']}"):
                    supabase.table("orc_eletrico_itens").delete().eq("id", item['id']).execute()
                    st.rerun()
                
                if n != item['orc_item_nome_visual'] or q != item['orc_item_quantidade'] or u != item['orc_item_unidade']:
                    supabase.table("orc_eletrico_itens").update({
                        "orc_item_nome_visual": n, "orc_item_quantidade": q, "orc_item_unidade": u,
                        "orc_item_nome_chave": n.lower()
                    }).eq("id", item['id']).execute()

# --- ABA 3: EXPORTAÇÃO (Com total MO) ---
with tab3:
    with st.sidebar:
        st.header("⚙️ Ajuste de Preços")
        precos = {k: st.number_input(k, value=20.0 if "m" in k else 30.0) for k in st.session_state.dados_servicos.keys() if k not in ["Instalação do Padrão", "Projeto e ART"]}
        precos["Instalação do Padrão"] = st.number_input("Instalação do Padrão", value=400.0)
        precos["Projeto e ART"] = st.number_input("Projeto e ART", value=800.0)

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

    def gerar_word(orc, tot):
        doc = Document()
        for s in doc.sections: s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Pt(72)
        style = doc.styles['Normal']
        style.font.name, style.font.size, style.paragraph_format.line_spacing = 'Arial', Pt(12), 1.5
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        doc.add_heading('ORÇAMENTO DE MÃO DE OBRA', 1)
        for k, v in orc.items():
            p = doc.add_paragraph()
            p.add_run(f"• {k}: ").bold = True
            p.add_run(f"R$ {v:.2f}")
        p_t = doc.add_paragraph()
        p_t.add_run(f"\nVALOR TOTAL DO ORÇAMENTO: R$ {tot:.2f}").bold = True
        
        mats = buscar_materiais()
        if mats:
            doc.add_page_break()
            doc.add_heading('LISTA DE MATERIAIS', 1)
            for m in mats:
                q_txt = f"{float(m['orc_item_quantidade']):.1f}" if m['orc_item_unidade'] == "m" else f"{int(m['orc_item_quantidade'])}"
                doc.add_paragraph(f"• {m['orc_item_nome_visual']}: {q_txt} {m['orc_item_unidade']}")
        
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    if total_mo > 0 or mats_db:
        st.download_button("📥 Baixar Documento Completo", gerar_word(itens_orc, total_mo), "orcamento.docx", type="primary")
