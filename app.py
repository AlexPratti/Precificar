import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Precificador Elétrico Profissional", layout="centered")

# --- ESTADO DA SESSÃO PARA MANTER VALORES ---
if 'dados_servicos' not in st.session_state:
    # Inicializa o dicionário para guardar as quantidades/metragens de cada item
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0, "Pontos Baixos e Médios de Força": 0,
        "Luminárias em Gesso/PVC": 0, "Perfil LED em Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Quadro de Disjuntores": 0, "Instalação do Padrão": "Monofásico", "Projeto e ART": False
    }

# --- SIDEBAR: VALORES UNITÁRIOS ---
with st.sidebar:
    st.header("⚙️ Ajustar Preços Base")
    precos = {
        "Pontos Altos de Força": st.number_input("Ponto Alto (un)", value=80.0),
        "Pontos Baixos e Médios de Força": st.number_input("Ponto Baixo/Médio (un)", value=60.0),
        "Luminárias em Gesso/PVC": st.number_input("Luminária (un)", value=45.0),
        "Perfil LED em Gesso/PVC": st.number_input("Perfil LED (m)", value=120.0),
        "Fiação de Distribuição": st.number_input("Fiação Distr. (m)", value=15.0),
        "Fiação do Padrão ao Quadro de Disjuntores": st.number_input("Fiação Padrão (m)", value=25.0),
        "Quadro de Disjuntores": st.number_input("Disjuntor (un)", value=40.0),
        "Instalação do Padrão": st.number_input("Base Padrão", value=500.0),
        "Projeto e ART": st.number_input("Base Projeto/ART", value=800.0)
    }

tab1, tab2, tab3 = st.tabs(["📋 Lançar Itens", "💰 Tabela de Preços", "📄 Gerar Orçamento"])

# --- ABA 2: VISUALIZAÇÃO ---
with tab2:
    st.table([{"Serviço": k, "Valor Unitário": f"R$ {v:.2f}"} for k, v in precos.items()])

# --- ABA 1: ENTRADA DINÂMICA (UM POR VEZ) ---
with tab1:
    st.subheader("Configuração por Item")
    
    # Seletor que define QUAL entrada aparece na tela
    escolha = st.selectbox("Selecione o serviço para editar a quantidade/metragem:", list(precos.keys()))

    st.info(f"Editando agora: **{escolha}**")
    
    # Renderiza APENAS o input da opção selecionada
    if escolha in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Gesso/PVC"]:
        val = st.number_input("Digite a quantidade de pontos:", min_value=0, step=1, value=int(st.session_state.dados_servicos[escolha]))
        st.session_state.dados_servicos[escolha] = val
        
    elif escolha in ["Perfil LED em Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores"]:
        val = st.number_input("Digite a metragem (m):", min_value=0.0, step=0.5, value=float(st.session_state.dados_servicos[escolha]))
        st.session_state.dados_servicos[escolha] = val
        
    elif escolha == "Quadro de Disjuntores":
        val = st.number_input("Quantidade de disjuntores:", min_value=0, step=1, value=int(st.session_state.dados_servicos[escolha]))
        st.session_state.dados_servicos[escolha] = val
        
    elif escolha == "Instalação do Padrão":
        # Busca o index atual para o selectbox
        opcoes_padrao = ["Monofásico", "Bifásico", "Trifásico"]
        idx = opcoes_padrao.index(st.session_state.dados_servicos[escolha])
        val = st.selectbox("Tipo de ligação:", opcoes_padrao, index=idx)
        st.session_state.dados_servicos[escolha] = val
        
    elif escolha == "Projeto e ART":
        val = st.checkbox("Incluir Projeto e ART no orçamento?", value=st.session_state.dados_servicos[escolha])
        st.session_state.dados_servicos[escolha] = val

    st.success(f"Valor registrado para {escolha}!")

# --- ABA 3: CÁLCULOS FINAIS E WORD ---
with tab3:
    st.subheader("Resumo Final do Orçamento")
    
    itens_com_valor = {}
    soma_servicos_para_art = 0.0

    # Lógica de Cálculo
    for item, input_val in st.session_state.dados_servicos.items():
        subtotal = 0.0
        if input_val == 0 or input_val == 0.0 or input_val is False: continue
        
        if item in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Gesso/PVC", "Quadro de Disjuntores"]:
            subtotal = input_val * precos[item]
        elif item in ["Perfil LED em Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores"]:
            subtotal = input_val * precos[item]
        elif item == "Instalação do Padrão":
            mult = {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}
            subtotal = precos[item] * mult[input_val]
        
        if item != "Projeto e ART":
            itens_com_valor[item] = subtotal
            soma_servicos_para_art += subtotal

    # Cálculo da ART (Fixo + 55% dos outros)
    if st.session_state.dados_servicos["Projeto e ART"]:
        valor_art = precos["Projeto e ART"] + (soma_servicos_para_art * 0.55)
        itens_com_valor["Projeto e ART"] = valor_art

    if not itens_com_valor:
        st.warning("Nenhum valor lançado na Aba 1.")
    else:
        total_geral = sum(itens_com_valor.values())
        for s, v in itens_com_valor.items():
            st.write(f"✅ {s}: **R$ {v:.2f}**")
        
        st.markdown(f"## Total: R$ {total_geral:.2f}")

        # Função de exportação para Word
        def gerar_docx(dados, total):
            doc = Document()
            for sec in doc.sections:
                sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Pt(72)
            
            style = doc.styles['Normal']
            style.font.name, style.font.size = 'Arial', Pt(12)
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            doc.add_heading('ORÇAMENTO DE PRESTAÇÃO DE SERVIÇOS', 0)
            doc.add_paragraph("Apresentamos abaixo o detalhamento dos serviços elétricos:")
            
            for s, v in dados.items():
                p = doc.add_paragraph(style='Normal')
                p.add_run(f"• {s}: ").bold = True
                p.add_run(f"R$ {v:.2f}")
            
            p_total = doc.add_paragraph()
            p_total.add_run(f"\nVALOR TOTAL DO ORÇAMENTO: R$ {total:.2f}").bold = True
            
            buf = BytesIO()
            doc.save(buf)
            return buf.getvalue()

        st.download_button("📥 Baixar Orçamento em Word", gerar_docx(itens_com_valor, total_geral), "orcamento.docx")
