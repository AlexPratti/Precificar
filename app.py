import streamlit as st
from supabase import create_client, Client
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Sistema Elétrico Profissional", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["URL_SUPABASE"]
        key = st.secrets["KEY_SUPABASE"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro Crítico de Conexão: {e}")
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

# --- FUNÇÕES DE BANCO DE DADOS (FORÇANDO ESCRITA REAL) ---
def adicionar_ou_somar_material(nome, qtd, uni):
    nome_chave = nome.strip().lower()
    try:
        # 1. Busca real no Supabase
        res = supabase.table("orc_eletrico_itens").select("*").eq("orc_item_nome_chave", nome_chave).eq("orc_item_unidade", uni).execute()
        
        if res.data and len(res.data) > 0:
            # SOMA NO REGISTRO EXISTENTE
            item_db = res.data[0]
            nova_qtd = float(item_db['orc_item_quantidade']) + float(qtd)
            supabase.table("orc_eletrico_itens").update({"orc_item_quantidade": nova_qtd}).eq("id", item_db['id']).execute()
        else:
            # INSERE NOVO REGISTRO
            supabase.table("orc_eletrico_itens").insert({
                "orc_item_nome_chave": nome_chave,
                "orc_item_nome_visual": nome.strip(),
                "orc_item_quantidade": float(qtd),
                "orc_item_unidade": uni
            }).execute()
        return True
    except Exception as e:
        st.error(f"Falha ao comunicar com Supabase: {e}")
        return False

def buscar_materiais():
    try:
        # Busca sempre do banco, nunca da memória do app
        res = supabase.table("orc_eletrico_itens").select("*").order("created_at").execute()
        return res.data
    except Exception as e:
        st.error(f"Erro ao ler banco: {e}")
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
            qtd_f = c3.number_input("Metros:", min_value=0.0, step=1.0, key="in_cabo")
            nome_f, uni_f = f"Cabo Flexível {sec} {cor}", "m"

        elif cat == "DISJUNTORES":
            c1, c2, c3, c4 = st.columns(4)
            amps = [f"{a} A" for a in [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]]
            corr = c1.selectbox("Amperagem:", amps)
            fase = c2.selectbox("Pólos:", ["Unipolar", "Bipolar", "Tripolar"])
            curva = c3.selectbox("Curva:", ["B", "C", "D"], index=1)
            qtd_f = c4.number_input("Qtd:", min_value=0, step=1, key="in_disj")
            nome_f, uni_f = f"Disjuntor {fase} {curva}{corr.replace(' A', '')}", "un"

        elif cat == "MÓDULOS, TOMADAS E PLACAS":
            c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
            tipo = c1.selectbox("Tipo:", ["Placa 4x2", "Placa 4x4", "Módulo Tomada", "Módulo Interruptor", "Three Way"])
            desc = c2.text_input("Descrição:", key="in_mod")
            qtd_f = c3.number_input("Qtd:", min_value=0, step=1, key="in_mod_q")
            nome_f, uni_f = f"{tipo} {desc}", "pç"

        elif cat == "CONDUÍTES" or cat == "CONDULETES":
            c1, c2, c3 = st.columns(3)
            bits = ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"', '2 1/2"', '3"', '4"']
            sec = c1.selectbox("Bitola:", bits)
            tipo = st.text_input("Tipo/Modelo:", key="in_tubo")
            uni_f = "m" if cat == "CONDUÍTES" else "un"
            qtd_f = c3.number_input("Quantidade:", min_value=0.0, key="in_tubo_q")
            nome_f = f"{cat.title()[:-1]} {sec} {tipo}"

        elif cat == "OUTROS":
            c1, c2, c3 = st.columns([0.5, 0.2, 0.3])
            nome_f = c1.text_input("Descrição:", key="in_out")
            uni_f = c2.selectbox("Unid:", ["un", "m", "Pç", "kg"])
            qtd_f = c3.number_input("Qtd:", min_value=0.0, key="in_out_q")

        if st.button("➕ Adicionar à Lista"):
            if nome_f and qtd_f > 0:
                if adicionar_ou_somar_material(nome_f, qtd_f, uni_f):
                    st.success("Salvo no Supabase!")
                    st.rerun()

# --- ABA 3: CONFERÊNCIA ---
with tab_conf:
    st.subheader("🔍 Conferência (Lendo do Supabase)")
    mats_db = buscar_materiais()
    
    if not mats_db:
        st.info("O banco de dados está vazio.")
    else:
        if st.button("🚨 Limpar Lista Completa"):
            supabase.table("orc_eletrico_itens").delete().neq("id", 0).execute()
            st.rerun()
        
        for item in mats_db:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([0.5, 0.15, 0.15, 0.2])
                n_up = col1.text_input("Item:", item['orc_item_nome_visual'], key=f"n_{item['id']}")
                q_up = col2.number_input("Qtd:", value=float(item['orc_item_quantidade']), key=f"q_{item['id']}")
                u_up = col3.text_input("Unid:", item['orc_item_unidade'], key=f"u_{item['id']}")
                
                if col4.button("🗑️", key=f"del_{item['id']}"):
                    supabase.table("orc_eletrico_itens").delete().eq("id", item['id']).execute()
                    st.rerun()
                
                if n_up != item['orc_item_nome_visual'] or q_up != item['orc_item_quantidade'] or u_up != item['orc_item_unidade']:
                    supabase.table("orc_eletrico_itens").update({
                        "orc_item_nome_visual": n_up, "orc_item_quantidade": q_up, "orc_item_unidade": u_up,
                        "orc_item_nome_chave": n_up.lower()
                    }).eq("id", item['id']).execute()

# --- ABA 4: EXPORTAÇÃO ---
with tab3:
    with st.sidebar:
        st.header("⚙️ Ajuste de Preços")
        precos = {k: st.number_input(k, value=20.0 if "m" in k else 30.0) for k in st.session_state.dados_servicos.keys() if k not in ["Instalação do Padrão", "Projeto e ART"]}
        precos["Instalação do Padrão"] = st.number_input("Instalação do Padrão", value=400.0)
        precos["Projeto e ART"] = st.number_input("Projeto e ART", value=800.0)

    itens_orc, soma_mo = {}, 0.0
    for k, v in st.session_state.dados_servicos.items():
        if k == "Instalação do Padrão" and v["incluir"]:
            val = precos[k] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[v["tipo"]]
            itens_orc[k], soma_mo = val, soma_mo + val
        elif k != "Projeto e ART" and k != "Instalação do Padrão" and v > 0:
            val = v * precos[k]
            itens_orc[k], soma_mo = val, soma_mo + val
    if st.session_state.dados_servicos["Projeto e ART"]:
        itens_orc["Projeto e ART"] = precos["Projeto e ART"] + (soma_mo * 0.55)
    
    total_final_mo = sum(itens_orc.values())
    st.write(f"### Total Mão de Obra: R$ {total_final_mo:.2f}")

    def gerar_doc(orc, tot_mo):
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
        p_t.add_run(f"\nVALOR TOTAL DO ORÇAMENTO: R$ {tot_mo:.2f}").bold = True
        
        mats = buscar_materiais()
        if mats:
            doc.add_page_break()
            doc.add_heading('LISTA DE MATERIAIS', 1)
            for m in mats:
                q_exib = f"{float(m['orc_item_quantidade']):.1f}" if m['orc_item_unidade'] == "m" else f"{int(m['orc_item_quantidade'])}"
                doc.add_paragraph(f"• {m['orc_item_nome_visual']}: {q_exib} {m['orc_item_unidade']}")
        
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    if total_final_mo > 0 or mats_db:
        st.download_button("📥 Baixar Documento Completo", gerar_doc(itens_orc, total_final_mo), "orcamento.docx", type="primary")
