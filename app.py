import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Sistema Elétrico Profissional", layout="wide")

# --- INICIALIZAÇÃO DO ESTADO ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0, "Pontos Baixos e Médios de Força": 0,
        "Luminárias em Teto/Gesso/PVC": 0, "Perfil LED em Teto/Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Instalações sobre Laje/Telhados": 0.0, "Instalação de Eletrodutos/Canaletas Sobrepostas": 0.0,
        "Quadro de Disjuntores": 0, "Instalação do Padrão": {"incluir": False, "tipo": "Monofásico"},
        "Projeto e ART": False
    }
if 'lista_materiais' not in st.session_state:
    st.session_state.lista_materiais = []

# --- FUNÇÕES AUXILIARES ---
def formatar_qtd(qtd, unidade):
    return f"{float(qtd):.1f}" if unidade.lower() == "m" else f"{int(qtd)}"

# --- SIDEBAR: PREÇOS MÃO DE OBRA ---
with st.sidebar:
    st.header("⚙️ Preços Mão de Obra")
    precos = {k: st.number_input(k, value=20.0 if "m" in k else 30.0) for k in st.session_state.dados_servicos.keys() if k not in ["Instalação do Padrão", "Projeto e ART"]}
    precos["Instalação do Padrão"] = st.number_input("Instalação do Padrão", value=400.0)
    precos["Projeto e ART"] = st.number_input("Projeto e ART", value=800.0)

tab1, tab2, tab3 = st.tabs(["📋 Serviços", "📦 Materiais", "📄 Gerar Orçamento"])

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
    categoria = st.selectbox("Categoria:", ["CABOS", "DISJUNTORES", "MÓDULOS, TOMADAS E PLACAS", "CONDUÍTES", "CONDULETES", "OUTROS"])
    
    with st.container(border=True):
        if categoria == "CABOS":
            c1, c2, c3 = st.columns(3)
            sec = c1.selectbox("Seção:", ["1,0 mm²", "1,5 mm²", "2,5 mm²", "4,0 mm²", "6,0 mm²", "10 mm²", "16 mm²", "25 mm²", "35 mm²"])
            cor = c2.selectbox("Cor:", ["azul", "preto", "branco", "vermelho", "amarelo", "verde", "verde e amarelo", "cinza", "marrom"])
            qtd = c3.number_input("Metros:", min_value=0.0, step=1.0)
            nome_final, unidade = f"Cabo Flexível {sec} {cor}", "m"

        elif categoria == "DISJUNTORES":
            c1, c2, c3, c4 = st.columns(4)
            correntes = [f"{a} A" for a in [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]]
            corr = c1.selectbox("Corrente Nominal:", correntes)
            fase = c2.selectbox("Polos:", ["Unipolar", "Bipolar", "Tripolar"])
            curva = c3.selectbox("Curva:", ["B", "C", "D"], index=1)
            qtd = c4.number_input("Qtde:", min_value=0, step=1)
            nome_final, unidade = f"Disjuntor {fase} {curva}{corr.replace(' A', '')}", "un"

        elif categoria == "MÓDULOS, TOMADAS E PLACAS":
            c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
            tipo = c1.selectbox("Tipo:", ["Placa 4x2", "Placa 4x4", "Módulo Tomada", "Módulo Interruptor", "Three Way", "For Way"])
            desc = c2.text_input("Descrição (ex: 3 postos / 20A):")
            qtd = c3.number_input("Qtde:", min_value=0, step=1)
            nome_final, unidade = f"{tipo} {desc}", "pç"

        elif categoria == "CONDUÍTES" or categoria == "CONDULETES":
            c1, c2, c3 = st.columns(3)
            bitolas = ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"', '2 1/2"', '3"', '4"']
            sec = c1.selectbox("Seção/Bitola:", bitolas)
            if categoria == "CONDUÍTES":
                tipo = c2.text_input("Tipo (ex: Corrugado):")
                unidade = "m"
            else:
                tipo = c2.selectbox("Tipo/Modelo:", ["C", "E", "X", "T", "LR", "LL", "LB", "TB", "B"])
                unidade = "un"
            qtd = c3.number_input("Qtde/Metros:", min_value=0.0, step=1.0)
            nome_final = f"{categoria.title()[:-1]} {sec} {tipo}"

        elif categoria == "OUTROS":
            c1, c2, c3 = st.columns([0.5, 0.2, 0.3])
            desc = c1.text_input("Descrição:")
            uni = c2.selectbox("Unid:", ["un", "m", "Pç", "kg"], index=0)
            # Permite alteração manual se necessário
            uni_final = st.text_input("Alterar Unid (opcional):", value=uni)
            qtd = c3.number_input("Qtde:", min_value=0.0)
            nome_final, unidade = desc, uni_final

        if st.button("➕ Adicionar à Lista"):
            if nome_final and qtd > 0:
                # Lógica de Soma para Itens Idênticos
                existe = False
                for item in st.session_state.lista_materiais:
                    if item['nome'] == nome_final and item['uni'] == unidade:
                        item['qtd'] += qtd
                        existe = True
                        break
                if not existe:
                    st.session_state.lista_materiais.append({"nome": nome_final, "qtd": qtd, "uni": unidade})
                st.rerun()

    # Exibição
    st.divider()
    st.write("### Itens Lançados:")
    for i, item in enumerate(st.session_state.lista_materiais):
        col_txt, col_del = st.columns([0.9, 0.1])
        col_txt.write(f"• {item['nome']} - {formatar_qtd(item['qtd'], item['uni'])} {item['uni']}")
        if col_del.button("🗑️", key=f"del_mat_{i}"):
            st.session_state.lista_materiais.pop(i)
            st.rerun()

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
    
    total_mao_obra = sum(itens_orc.values())
    
    st.write(f"### Valor Total Mão de Obra: R$ {total_mao_obra:.2f}")

    def gerar_word(orc, mats, total_mo):
        doc = Document()
        for sec in doc.sections: sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Pt(72)
        style = doc.styles['Normal']
        style.font.name, style.font.size, style.paragraph_format.line_spacing = 'Arial', Pt(12), 1.5
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if orc:
            doc.add_heading('ORÇAMENTO DE MÃO DE OBRA', 1)
            for s, v in orc.items():
                p = doc.add_paragraph(style='Normal')
                p.add_run(f"• {s}: ").bold = True
                p.add_run(f"R$ {v:.2f}")
            p_tot = doc.add_paragraph()
            p_tot.add_run(f"\nVALOR TOTAL DO ORÇAMENTO: R$ {total_mo:.2f}").bold = True
            doc.add_page_break()
            
        if mats:
            doc.add_heading('LISTA DE MATERIAIS', 1)
            for item in mats:
                doc.add_paragraph(f"• {item['nome']}: {formatar_qtd(item['qtd'], item['uni'])} {item['uni']}", style='Normal')
        
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    if total_mao_obra > 0 or st.session_state.lista_materiais:
        st.download_button("📥 Baixar Orçamento e Lista", gerar_word(itens_orc, st.session_state.lista_materiais, total_mao_obra), "orcamento_eletrico.docx", type="primary")
