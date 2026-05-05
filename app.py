import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Precificador Elétrico", layout="centered")

# --- ESTADO DA SESSÃO ---
if 'itens_finalizados' not in st.session_state:
    st.session_state.itens_finalizados = {}

# --- ABA 2: PREÇOS (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Configurar Preços Base")
    precos_base = {
        "Pontos Altos de Força": st.number_input("Ponto Alto (un)", value=80.0),
        "Pontos Baixos e Médios de Força": st.number_input("Ponto Baixo/Médio (un)", value=60.0),
        "Luminárias em Gesso/PVC": st.number_input("Luminária (un)", value=45.0),
        "Perfil LED em Gesso/PVC": st.number_input("Perfil LED (m)", value=120.0),
        "Fiação de Distribuição": st.number_input("Fiação Distr. (m)", value=15.0),
        "Fiação do Padrão ao Quadro de Disjuntores": st.number_input("Fiação Padrão (m)", value=25.0),
        "Quadro de Disjuntores": st.number_input("Disjuntor (un)", value=40.0),
        "Instalação do Padrão": st.number_input("Base Padrão", value=500.0),
        "Projeto e ART": st.number_input("Fixo Projeto/ART", value=800.0)
    }

tab1, tab2, tab3 = st.tabs(["📋 Seleção e Entradas", "💰 Tabela de Preços", "📄 Orçamento Final"])

with tab2:
    st.subheader("Valores Unitários Cadastrados")
    st.table([{"Serviço": k, "Preço Unitário": f"R$ {v:.2f}"} for k, v in precos_base.items()])

# --- ABA 1: DINÂMICA DE ENTRADAS ---
with tab1:
    st.subheader("O que será cobrado neste serviço?")
    selecionados = st.multiselect("Selecione os itens para abrir as configurações:", list(precos_base.keys()))

    calculos_atuais = {}
    soma_servicos_para_art = 0.0

    # Exibe inputs apenas para o que está no multiselect
    for item in selecionados:
        st.write(f"### {item}")
        chave = item.replace(" ", "_").lower()
        
        if item in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Gesso/PVC"]:
            qtd = st.number_input(f"Quantidade de pontos:", min_value=0, step=1, key=f"q_{chave}")
            subtotal = qtd * precos_base[item]
            
        elif item in ["Perfil LED em Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores"]:
            metragem = st.number_input(f"Metragem total (m):", min_value=0.0, step=0.5, key=f"m_{chave}")
            subtotal = metragem * precos_base[item]
            
        elif item == "Quadro de Disjuntores":
            qtd_disj = st.number_input(f"Quantidade de disjuntores:", min_value=0, step=1, key=f"d_{chave}")
            subtotal = qtd_disj * precos_base[item]
            
        elif item == "Instalação do Padrão":
            tipo = st.radio("Selecione a fase:", ["Monofásico", "Bifásico", "Trifásico"], key=f"t_{chave}", horizontal=True)
            mult = {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}
            subtotal = precos_base[item] * mult[tipo]
            
        elif item == "Projeto e ART":
            st.info("O valor será calculado automaticamente (Fixo + 55% dos serviços selecionados).")
            subtotal = 0 # Placeholder

        if item != "Projeto e ART":
            calculos_atuais[item] = subtotal
            soma_servicos_para_art += subtotal
            st.write(f"**Subtotal de {item}: R$ {subtotal:.2f}**")
        st.divider()

    # Cálculo da ART após processar todos os outros itens
    if "Projeto e ART" in selecionados:
        valor_art = precos_base["Projeto e ART"] + (soma_servicos_para_art * 0.55)
        calculos_atuais["Projeto e ART"] = valor_art
        st.success(f"**Projeto e ART Total: R$ {valor_art:.2f}**")

    if st.button("Salvar Orçamento"):
        st.session_state.itens_finalizados = calculos_atuais
        st.toast("Dados salvos com sucesso!")

# --- ABA 3: RESUMO E DOCUMENTO ---
with tab3:
    if not st.session_state.itens_finalizados:
        st.info("Aguardando definição de valores na Aba 1.")
    else:
        st.subheader("Resumo do Orçamento")
        total_geral = sum(st.session_state.itens_finalizados.values())
        
        for serv, val in st.session_state.itens_finalizados.items():
            st.write(f"🔹 {serv}: **R$ {val:.2f}**")
        
        st.markdown(f"## Total: R$ {total_geral:.2f}")

        def criar_docx(dados, total):
            doc = Document()
            for s in doc.sections:
                s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Pt(72)
            
            style = doc.styles['Normal']
            style.font.name, style.font.size = 'Arial', Pt(12)
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            doc.add_heading('ORÇAMENTO DE SERVIÇOS', 0)
            doc.add_paragraph("Segue o descritivo dos serviços e valores:")
            
            for s, v in dados.items():
                p = doc.add_paragraph(f"{s}: ", style='Normal')
                p.add_run(f"R$ {v:.2f}").bold = True
            
            p_total = doc.add_paragraph()
            p_total.add_run(f"\nVALOR TOTAL: R$ {total:.2f}").bold = True
            
            buffer = BytesIO()
            doc.save(buffer)
            return buffer.getvalue()

        st.download_button(
            label="Gerar Documento Word",
            data=criar_docx(st.session_state.itens_finalizados, total_geral),
            file_name="orcamento_eletrico.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
