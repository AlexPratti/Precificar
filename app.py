import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Precificador Elétrico", layout="centered")

# --- INICIALIZAÇÃO DO ESTADO ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0, 
        "Pontos Baixos e Médios de Força": 0,
        "Luminárias em Gesso/PVC": 0, 
        "Perfil LED em Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, 
        "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Quadro de Disjuntores": 0, 
        "Instalação do Padrão": {"incluir": False, "tipo": "Monofásico"},
        "Projeto e ART": False
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

with tab2:
    st.table([{"Serviço": k, "Valor Unitário": f"R$ {v:.2f}"} for k, v in precos.items()])

# --- ABA 1: ENTRADA DINÂMICA ---
with tab1:
    st.subheader("Configuração por Item")
    escolha = st.selectbox("Selecione o serviço para editar:", list(precos.keys()))
    st.divider()

    if escolha in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Gesso/PVC", "Quadro de Disjuntores"]:
        label = "Quantidade:" 
        val = st.number_input(label, min_value=0, step=1, value=int(st.session_state.dados_servicos[escolha]), key=f"inp_{escolha}")
        st.session_state.dados_servicos[escolha] = val
        
    elif escolha in ["Perfil LED em Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores"]:
        val = st.number_input("Metragem (m):", min_value=0.0, step=0.5, value=float(st.session_state.dados_servicos[escolha]), key=f"inp_{escolha}")
        st.session_state.dados_servicos[escolha] = val
        
    elif escolha == "Instalação do Padrão":
        dado_p = st.session_state.dados_servicos["Instalação do Padrão"]
        inc = st.checkbox("Incluir Instalação do Padrão?", value=dado_p["incluir"])
        tipo = st.selectbox("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"], 
                            index=["Monofásico", "Bifásico", "Trifásico"].index(dado_p["tipo"]))
        st.session_state.dados_servicos[escolha] = {"incluir": inc, "tipo": tipo}
        
    elif escolha == "Projeto e ART":
        val = st.checkbox("Incluir Projeto e ART?", value=st.session_state.dados_servicos[escolha])
        st.session_state.dados_servicos[escolha] = val

    st.success(f"Registrado: {escolha}")

# --- ABA 3: RESUMO E EXCLUSÃO ---
with tab3:
    st.subheader("Resumo Final")
    itens_finais = {}
    soma_base = 0.0

    # Lógica de processamento segura
    for item, dado in st.session_state.dados_servicos.items():
        v_item = 0.0
        if item == "Instalação do Padrão":
            if isinstance(dado, dict) and dado.get("incluir"):
                mult = {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}
                v_item = precos[item] * mult[dado["tipo"]]
        elif item == "Projeto e ART":
            continue
        else:
            if isinstance(dado, (int, float)) and dado > 0:
                v_item = dado * precos[item]
        
        if v_item > 0:
            itens_finais[item] = v_item
            soma_base += v_item

    if st.session_state.dados_servicos["Projeto e ART"]:
        itens_finais["Projeto e ART"] = precos["Projeto e ART"] + (soma_base * 0.55)

    if not itens_finais:
        st.info("Nenhum item selecionado.")
    else:
        for s, v in list(itens_finais.items()):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"✅ {s}: **R$ {v:.2f}**")
            if c2.button("🗑️", key=f"del_{s}"):
                if s == "Instalação do Padrão":
                    st.session_state.dados_servicos[s] = {"incluir": False, "tipo": "Monofásico"}
                elif s == "Projeto e ART":
                    st.session_state.dados_servicos[s] = False
                else:
                    st.session_state.dados_servicos[s] = 0
                st.rerun()
        
        total = sum(itens_finais.values())
        st.markdown(f"## Total: R$ {total:.2f}")

        def gerar_docx(dados, total_val):
            doc = Document()
            for sec in doc.sections:
                sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Pt(72)
            style = doc.styles['Normal']
            style.font.name, style.font.size = 'Arial', Pt(12)
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            doc.add_heading('ORÇAMENTO DE SERVIÇOS', 0)
            for s, v in dados.items():
                p = doc.add_paragraph(style='Normal')
                p.add_run(f"• {s}: ").bold = True
                p.add_run(f"R$ {v:.2f}")
            p_total = doc.add_paragraph()
            p_total.add_run(f"\nVALOR TOTAL: R$ {total_val:.2f}").bold = True
            buf = BytesIO()
            doc.save(buf)
            return buf.getvalue()

        st.download_button("📥 Baixar em Word", gerar_docx(itens_finais, total), "orcamento.docx")
