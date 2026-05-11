import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

st.set_page_config(page_title="Sistema Elétrico Profissional", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0, "Pontos Baixos e Médios de Força": 0,
        "Luminárias em Teto/Gesso/PVC": 0, "Perfil LED em Teto/Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Instalações sobre Laje/Telhados": 0.0, "Instalação de Eletrodutos/Canaletas Sobrepostas": 0.0,
        "Quadro de Disjuntores": 0, "Instalação do Padrão": {"incluir": False, "tipo": "Monofásico"},
        "Projeto e ART": False
    }
if 'mats_selecionados' not in st.session_state:
    st.session_state.mats_selecionados = {}

# --- FUNÇÕES AUXILIARES ---
def extrair_unidade(texto):
    texto_limpo = re.sub(r'^\d+\.\s*', '', texto)
    match = re.search(r'\[(.*?)\]', texto_limpo)
    if match:
        unidade = match.group(1)
        descricao = texto_limpo.replace(f'[{unidade}]', '').strip()
        return unidade, descricao
    return "un", texto_limpo

def formatar_qtd(qtd, unidade):
    return f"{float(qtd):.1f}" if unidade.lower() == "m" else f"{int(qtd)}"

def processar_arquivo_materiais(arquivo):
    doc = Document(arquivo)
    categorias = {}
    categoria_atual = "GERAL"
    for p in doc.paragraphs:
        texto = p.text.strip()
        if not texto: continue
        if texto.isupper() and "[" not in texto:
            categoria_atual = texto
            categorias[categoria_atual] = []
        else:
            if categoria_atual not in categorias: categorias[categoria_atual] = []
            categorias[categoria_atual].append(texto)
    return categorias

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Preços Mão de Obra")
    precos = {k: st.number_input(k, value=20.0 if "m" in k else 30.0) for k in st.session_state.dados_servicos.keys() if k not in ["Instalação do Padrão", "Projeto e ART"]}
    precos["Instalação do Padrão"] = st.number_input("Instalação do Padrão", value=400.0)
    precos["Projeto e ART"] = st.number_input("Projeto e ART", value=800.0)

tab1, tab2, tab3 = st.tabs(["📋 Serviços", "📦 Materiais", "📄 Gerar Orçamento"])

# --- ABA 1: SERVIÇOS (MANTIDA) ---
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

# --- ABA 2: MATERIAIS (LÓGICA DE NOMENCLATURA LIMPA) ---
with tab2:
    st.subheader("📦 Lista de Materiais")
    up_mats = st.file_uploader("Upload da listagem (.docx)", type=["docx"])
    if up_mats:
        dict_cat = processar_arquivo_materiais(up_mats)
        cat_sel = st.selectbox("Escolha a Categoria:", list(dict_cat.keys()))
        
        for i, item_bruto in enumerate(dict_cat[cat_sel]):
            uni_base, nome_base = extrair_unidade(item_bruto)
            with st.expander(f"➕ {nome_base}"):
                c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
                if c1.checkbox("Selecionar", key=f"ch_{cat_sel}_{i}"):
                    qtd = c2.number_input("Qtd:", min_value=0.0, key=f"q_{cat_sel}_{i}")
                    uni = c3.selectbox("Unid:", ["un", "m", "pç", "rl"], index=0 if uni_base not in ["un", "m", "pç", "rl"] else ["un", "m", "pç", "rl"].index(uni_base), key=f"u_{cat_sel}_{i}")
                    
                    nome_final = nome_base # Padrão
                    
                    if "CABO" in cat_sel:
                        # Extrai a palavra principal (ex: Cabinho ou Cabo)
                        prefixo = nome_base.split()[0]
                        col_a, col_b = st.columns(2)
                        sec = col_a.text_input("Seção (ex: 1,5 mm²):", key=f"s_{i}")
                        cor = col_b.text_input("Cor:", key=f"c_{i}")
                        nome_final = f"{prefixo} {sec} {cor}".strip()
                        
                    elif "DISJUNTOR" in cat_sel:
                        col_a, col_b, col_c = st.columns(3)
                        polo = col_a.selectbox("Tipo:", ["Monopolar", "Bipolar", "Tripolar"], key=f"p_{i}")
                        curva = col_b.selectbox("Curva:", ["B", "C", "D"], index=1, key=f"cv_{i}")
                        corr = col_c.text_input("Amperagem (A):", key=f"amp_{i}")
                        nome_final = f"Disjuntor {polo} {curva}{corr}".strip()
                        
                    elif "TOMADA" in cat_sel or "INTERRUPTOR" in cat_sel or "PLACA" in cat_sel:
                        prefixo = nome_base.split()[0]
                        col_a, col_b = st.columns(2)
                        tam = col_a.selectbox("Tam:", ["4x2", "4x4"], key=f"t_{i}")
                        pos = col_b.text_input("Postos:", key=f"ps_{i}")
                        nome_final = f"{prefixo} {tam} {pos} postos".strip()

                    elif "CONDUITE" in cat_sel:
                        prefixo = nome_base.split()[0]
                        col_a, col_b = st.columns(2)
                        sec_c = col_a.text_input("Seção:", key=f"sc_{i}")
                        tp_c = col_b.text_input("Tipo:", key=f"tc_{i}")
                        nome_final = f"{prefixo} {sec_c} {tp_c}".strip()

                    st.session_state.mats_selecionados[f"ID_{cat_sel}_{i}"] = {"nome": nome_final, "qtd": qtd, "uni": uni}
                else:
                    st.session_state.mats_selecionados.pop(f"ID_{cat_sel}_{i}", None)

# --- ABA 3: EXPORTAÇÃO ---
with tab3:
    itens_orc = {}
    soma_serv = 0.0
    for k, v in st.session_state.dados_servicos.items():
        if k == "Instalação do Padrão" and v["incluir"]:
            val = precos[k] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[v["tipo"]]
            itens_orc[k], soma_serv = val, soma_serv + val
        elif k != "Projeto e ART" and k != "Instalação do Padrão" and v > 0:
            val = v * precos[k]
            itens_orc[k], soma_serv = val, soma_serv + val
    if st.session_state.dados_servicos["Projeto e ART"]:
        itens_orc["Projeto e ART"] = precos["Projeto e ART"] + (soma_serv * 0.55)

    def gerar_word(orc, mats):
        doc = Document()
        for sec in doc.sections: sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Pt(72)
        style = doc.styles['Normal']
        style.font.name, style.font.size = 'Arial', Pt(12)
        style.paragraph_format.line_spacing, style.paragraph_format.alignment = 1.5, WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if orc:
            doc.add_heading('ORÇAMENTO DE MÃO DE OBRA', 1)
            for s, v in orc.items():
                p = doc.add_paragraph(style='Normal')
                p.add_run(f"• {s}: ").bold = True
                p.add_run(f"R$ {v:.2f}")
            doc.add_page_break()
            
        if mats:
            doc.add_heading('LISTA DE MATERIAIS', 1)
            for info in mats.values():
                doc.add_paragraph(f"• {info['nome']}: {formatar_qtd(info['qtd'], info['uni'])} {info['uni']}", style='Normal')
        
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    if itens_orc or st.session_state.mats_selecionados:
        st.download_button("📥 Baixar Orçamento Completo", gerar_word(itens_orc, st.session_state.mats_selecionados), "orcamento.docx", type="primary")

