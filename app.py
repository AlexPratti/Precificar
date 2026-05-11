import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

st.set_page_config(page_title="Sistema de Orçamento Elétrico", layout="wide")

# --- PADRONIZAÇÃO DE NOMES DO ORÇAMENTO ---
N_P_ALTO = "Pontos Altos de Força"
N_P_BAIXO = "Pontos Baixos e Médios de Força"
N_LUMI = "Luminárias em Teto/Gesso/PVC"
N_LED = "Perfil LED em Teto/Gesso/PVC"
N_DIST = "Fiação de Distribuição"
N_PADRAO_FIA = "Fiação do Padrão ao Quadro de Disjuntores"
N_LAJE = "Instalações sobre Laje/Telhados"
N_SOBREPOSTA = "Instalação de Eletrodutos/Canaletas Sobrepostas"
N_QUADRO = "Quadro de Disjuntores"
N_PADRAO_INST = "Instalação do Padrão"
N_ART = "Projeto e ART"

# --- INICIALIZAÇÃO DO ESTADO ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        N_P_ALTO: 0, N_P_BAIXO: 0, N_LUMI: 0, N_LED: 0.0, N_DIST: 0.0, 
        N_PADRAO_FIA: 0.0, N_LAJE: 0.0, N_SOBREPOSTA: 0.0, N_QUADRO: 0, 
        N_PADRAO_INST: {"incluir": False, "tipo": "Monofásico"}, N_ART: False
    }
if 'mats_selecionados' not in st.session_state:
    st.session_state.mats_selecionados = {}

# --- FUNÇÕES AUXILIARES ---
def extrair_unidade(texto):
    match = re.search(r'\[(.*?)\]', texto)
    if match:
        unidade = match.group(1)
        descricao = texto.replace(f'[{unidade}]', '').strip()
        return unidade, descricao
    return "un", texto

def configurar_estilo_base(doc):
    for sec in doc.sections:
        sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Pt(72)
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Arial', Pt(12)
    style.paragraph_format.line_spacing = 1.5
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# --- SIDEBAR: PREÇOS ---
with st.sidebar:
    st.header("⚙️ Preços de Mão de Obra")
    precos = {
        N_P_ALTO: st.number_input(N_P_ALTO, value=30.0),
        N_P_BAIXO: st.number_input(N_P_BAIXO, value=20.0),
        N_LUMI: st.number_input(N_LUMI, value=50.0),
        N_LED: st.number_input(N_LED, value=20.0),
        N_DIST: st.number_input(N_DIST, value=10.0),
        N_PADRAO_FIA: st.number_input(N_PADRAO_FIA, value=20.0),
        N_LAJE: st.number_input(N_LAJE, value=25.0),
        N_SOBREPOSTA: st.number_input(N_SOBREPOSTA, value=20.0),
        N_QUADRO: st.number_input(N_QUADRO, value=20.0),
        N_PADRAO_INST: st.number_input(N_PADRAO_INST, value=400.0),
        N_ART: st.number_input(N_ART, value=800.0)
    }

tab1, tab2, tab3, tab4 = st.tabs(["📋 Serviços", "📦 Materiais", "💰 Tabela de Preços", "📄 Gerar Documentos"])

# --- ABA 1: SERVIÇOS ---
with tab1:
    st.subheader("Configuração de Mão de Obra")
    escolha = st.selectbox("Selecione o serviço para editar:", list(precos.keys()))
    st.divider()

    if escolha in [N_P_ALTO, N_P_BAIXO, N_LUMI, N_QUADRO]:
        st.session_state.dados_servicos[escolha] = st.number_input("Quantidade:", min_value=0, step=1, value=int(st.session_state.dados_servicos.get(escolha, 0)))
    elif escolha in [N_LED, N_DIST, N_PADRAO_FIA, N_LAJE, N_SOBREPOSTA]:
        st.session_state.dados_servicos[escolha] = st.number_input("Metragem (m):", min_value=0.0, step=0.5, value=float(st.session_state.dados_servicos.get(escolha, 0.0)))
    elif escolha == N_PADRAO_INST:
        dado = st.session_state.dados_servicos[N_PADRAO_INST]
        inc = st.checkbox("Incluir Instalação do Padrão?", value=dado["incluir"])
        tipo = st.selectbox("Fase:", ["Monofásico", "Bifásico", "Trifásico"], index=["Monofásico", "Bifásico", "Trifásico"].index(dado["tipo"]))
        st.session_state.dados_servicos[N_PADRAO_INST] = {"incluir": inc, "tipo": tipo}
    elif escolha == N_ART:
        st.session_state.dados_servicos[N_ART] = st.checkbox("Incluir Projeto e ART?", value=st.session_state.dados_servicos[N_ART])
    st.success(f"Registrado: {escolha}")

# --- ABA 2: MATERIAIS ---
with tab2:
    st.subheader("Seleção de Materiais")
    up_mats = st.file_uploader("Upload da lista ampla (.docx)", type=["docx"])
    if up_mats:
        doc_ref = Document(up_mats)
        linhas = [p.text.strip() for p in doc_ref.paragraphs if p.text.strip()]
        busca = st.text_input("🔍 Filtrar materiais...")
        for i, linha in enumerate([l for l in linhas if busca.lower() in l.lower()]):
            uni_base, nome_limpo = extrair_unidade(linha)
            c1, c2, c3 = st.columns([0.5, 0.25, 0.25])
            if c1.checkbox(nome_limpo, key=f"c_{i}"):
                qtd = c2.number_input("Qtd:", min_value=0.0, step=1.0, key=f"q_{i}")
                uni = c3.selectbox("Unidade:", ["un", "m", "pç", "rl", "cj", "kg", uni_base], index=0, key=f"u_{i}")
                st.session_state.mats_selecionados[nome_limpo] = {"qtd": qtd, "uni": uni}
            else:
                st.session_state.mats_selecionados.pop(nome_limpo, None)

# --- ABA 3: TABELA ---
with tab2: # Note: tab2 was reused in your request context, but let's point to tab3
    pass
with tab3:
    st.table([{"Serviço": k, "Preço": f"R$ {v:.2f}"} for k, v in precos.items()])

# --- ABA 4: GERAR DOCUMENTOS ---
with tab4:
    st.subheader("Resumo e Exportação")
    
    # Cálculo Orçamento
    itens_orc = {}
    soma_base = 0.0
    for it, val in st.session_state.dados_servicos.items():
        v = 0.0
        if it == N_PADRAO_INST and val["incluir"]:
            v = precos[it] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[val["tipo"]]
        elif it != N_ART and it != N_PADRAO_INST and val > 0:
            v = val * precos[it]
        if v > 0:
            itens_orc[it] = v
            soma_base += v
    if st.session_state.dados_servicos[N_ART]:
        itens_orc[N_ART] = precos[N_ART] + (soma_base * 0.55)
    
    # Exibição
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Mão de Obra:**")
        for s, v in itens_orc.items():
            st.write(f"• {s}: R$ {v:.2f}")
        st.write(f"**Total Mão de Obra: R$ {sum(itens_orc.values()):.2f}**")
    with col_b:
        st.write("**Materiais:**")
        for m, info in st.session_state.mats_selecionados.items():
            st.write(f"• {m}: {info['qtd']} {info['uni']}")

    # Gerador Word
    def gerar_completo(dados_o, dados_m):
        doc = Document()
        configurar_estilo_base(doc)
        if dados_o:
            doc.add_heading('ORÇAMENTO DE MÃO DE OBRA', 0)
            for s, v in dados_o.items():
                p = doc.add_paragraph(style='Normal')
                p.add_run(f"• {s}: ").bold = True
                p.add_run(f"R$ {v:.2f}")
            p_tot = doc.add_paragraph()
            p_tot.add_run(f"\nTOTAL MÃO DE OBRA: R$ {sum(dados_o.values()):.2f}").bold = True
        if dados_o and dados_m: doc.add_page_break()
        if dados_m:
            doc.add_heading('LISTA DE MATERIAIS', 0)
            for m, info in dados_m.items():
                doc.add_paragraph(f"• {m}: {info['qtd']} {info['uni']}", style='Normal')
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    st.divider()
    st.download_button("📥 Baixar Documento Completo (.docx)", gerar_completo(itens_orc, st.session_state.mats_selecionados), "orcamento_e_materiais.docx", type="primary")
