import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

# Configuração inicial da página
st.set_page_config(page_title="Calculadora de Orçamento Elétrico", layout="centered")

# Inicialização do estado para armazenar os itens selecionados
if 'itens_orcamento' not in st.session_state:
    st.session_state.itens_orcamento = {}

# --- ABA 2: CONFIGURAÇÃO DE PREÇOS BASE ---
# Definimos primeiro para que a Aba 1 possa ler os valores
with st.sidebar:
    st.header("⚙️ Configuração de Preços Unitários")
    precos = {
        "Pontos Altos de Força": st.number_input("Preço Ponto Alto (un)", value=80.0),
        "Pontos Baixos e Médios de Força": st.number_input("Preço Ponto Baixo/Médio (un)", value=60.0),
        "Luminárias em Gesso/PVC": st.number_input("Preço Luminária (un)", value=45.0),
        "Perfil LED em Gesso/PVC": st.number_input("Preço Perfil LED (metro)", value=120.0),
        "Fiação de Distribuição": st.number_input("Preço Fiação Distr. (metro)", value=15.0),
        "Fiação do Padrão ao Quadro": st.number_input("Preço Fiação Padrão (metro)", value=25.0),
        "Quadro de Disjuntores": st.number_input("Preço por Disjuntor (un)", value=40.0),
        "Instalação do Padrão": st.number_input("Preço Base Padrão", value=500.0),
        "Projeto e ART": st.number_input("Preço Fixo Projeto/ART", value=800.0)
    }

tab1, tab2, tab3 = st.tabs(["📋 Seleção de Serviços", "💰 Tabela de Preços", "📄 Resumo e Exportação"])

# Aba 2 apenas mostra o que foi definido no sidebar para conferência
with tab2:
    st.subheader("Tabela de Referência Atual")
    st.table([{"Serviço": k, "Valor Unitário (R$)": v} for k, v in precos.items()])

# --- ABA 1: SELEÇÃO E CÁLCULO ---
with tab1:
    st.subheader("Selecione os serviços prestados")
    
    opcoes = list(precos.keys())
    selecionados = st.multiselect("Serviços executados:", opcoes)

    temp_itens = {}
    valor_acumulado_servicos = 0.0

    for item in selecionados:
        st.write(f"---")
        st.markdown(f"**{item}**")
        
        # Lógica de entrada baseada no tipo de serviço
        if item in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Gesso/PVC"]:
            qtd = st.number_input(f"Quantidade de pontos para {item}:", min_value=0, step=1, key=f"q_{item}")
            subtotal = qtd * precos[item]
            
        elif item in ["Perfil LED em Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores"]:
            metragem = st.number_input(f"Metragem (m) para {item}:", min_value=0.0, step=0.5, key=f"m_{item}")
            subtotal = metragem * precos[item]
            
        elif item == "Quadro de Disjuntores":
            qtd_disj = st.number_input(f"Quantidade de disjuntores:", min_value=0, step=1, key=f"d_{item}")
            subtotal = qtd_disj * precos[item]
            
        elif item == "Instalação do Padrão":
            tipo = st.selectbox("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"], key=f"t_{item}")
            multiplicadores = {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}
            subtotal = precos[item] * multiplicadores[tipo]
            
        elif item == "Projeto e ART":
            # O cálculo do Projeto e ART depende do somatório dos outros itens selecionados
            subtotal = 0 # Calculado ao final
            
        if item != "Projeto e ART":
            temp_itens[item] = subtotal
            valor_acumulado_servicos += subtotal
            st.info(f"Subtotal: R$ {subtotal:.2f}")

    # Cálculo especial para Projeto e ART
    if "Projeto e ART" in selecionados:
        valor_art = precos["Projeto e ART"] + (valor_acumulado_servicos * 0.55)
        temp_itens["Projeto e ART"] = valor_art
        st.markdown(f"**Projeto e ART**")
        st.info(f"Subtotal (Fixo + 55% sobre serviços): R$ {valor_art:.2f}")

    if st.button("Atualizar Orçamento"):
        st.session_state.itens_orcamento = temp_itens
        st.success("Itens adicionados ao resumo!")

# --- ABA 3: RESUMO E WORD ---
with tab3:
    st.subheader("Resumo Final")
    
    if not st.session_state.itens_orcamento:
        st.warning("Nenhum item selecionado ou calculado.")
    else:
        total_geral = 0
        for servico, valor in st.session_state.itens_orcamento.items():
            st.write(f"✅ {servico}: **R$ {valor:.2f}**")
            total_geral += valor
        
        st.divider()
        st.markdown(f"### Total do Orçamento: R$ {total_geral:.2f}")

        # Função para gerar o Word
        def gerar_word(dados, total):
            doc = Document()
            
            # Configuração de Margens (Moderada aprox. 2.5cm)
            sections = doc.sections
            for section in sections:
                section.top_margin = Pt(72)
                section.bottom_margin = Pt(72)
                section.left_margin = Pt(72)
                section.right_margin = Pt(72)

            # Estilo de Fonte
            style = doc.styles['Normal']
            font = style.font
            font.name = 'Arial'
            font.size = Pt(12)
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            doc.add_heading('Orçamento de Serviços Elétricos', 0)
            
            p = doc.add_paragraph("Abaixo seguem os valores detalhados para a execução dos serviços solicitados:")
            
            for servico, valor in dados.items():
                doc.add_paragraph(f"• {servico}: R$ {valor:.2f}", style='Normal')
            
            doc.add_paragraph("")
            total_p = doc.add_paragraph()
            run = total_p.add_run(f"VALOR TOTAL DO SERVIÇO: R$ {total:.2f}")
            run.bold = True
            
            target = BytesIO()
            doc.save(target)
            return target.getvalue()

        # Botão de Download
        btn_word = gerar_word(st.session_state.itens_orcamento, total_geral)
        st.download_button(
            label="📥 Baixar Orçamento em Word",
            data=btn_word,
            file_name="orcamento_eletrico.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

