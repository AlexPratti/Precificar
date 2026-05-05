import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="Precificador Elétrico", layout="centered")

# --- PADRONIZAÇÃO DE NOMES (Para evitar erros de digitação) ---
N_P_ALTO = "Pontos Altos de Força"
N_P_BAIXO = "Pontos Baixos e Médios de Força"
N_LUMI = "Luminárias em Teto/Gesso/PVC"
N_LED = "Perfil LED em Teto/Gesso/PVC"
N_DIST = "Fiação de Distribuição"
N_PADRAO_FIA = "Fiação do Padrão ao Quadro de Disjuntores"
N_QUADRO = "Quadro de Disjuntores"
N_PADRAO_INST = "Instalação do Padrão"
N_ART = "Projeto e ART"

# --- INICIALIZAÇÃO DO ESTADO ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        N_P_ALTO: 0, 
        N_P_BAIXO: 0,
        N_LUMI: 0, 
        N_LED: 0.0,
        N_DIST: 0.0, 
        N_PADRAO_FIA: 0.0,
        N_QUADRO: 0, 
        N_PADRAO_INST: {"incluir": False, "tipo": "Monofásico"},
        N_ART: False
    }

# --- SIDEBAR: VALORES UNITÁRIOS ---
with st.sidebar:
    st.header("⚙️ Ajustar Preços Base")
    precos = {
        N_P_ALTO: st.number_input(f"{N_P_ALTO} (un)", value=30.0),
        N_P_BAIXO: st.number_input(f"{N_P_BAIXO} (un)", value=20.0),
        N_LUMI: st.number_input(f"{N_LUMI} (un)", value=50.0),
        N_LED: st.number_input(f"{N_LED} (m)", value=20.0),
        N_DIST: st.number_input(f"{N_DIST} (m)", value=10.0),
        N_PADRAO_FIA: st.number_input(f"{N_PADRAO_FIA} (m)", value=20.0),
        N_QUADRO: st.number_input(f"{N_QUADRO} (un)", value=20.0),
        N_PADRAO_INST: st.number_input(f"{N_PADRAO_INST} (Base)", value=400.0),
        N_ART: st.number_input(f"{N_ART} (Base)", value=800.0)
    }

tab1, tab2, tab3 = st.tabs(["📋 Lançar Itens", "💰 Tabela de Preços", "📄 Gerar Orçamento"])

with tab2:
    st.table([{"Serviço": k, "Valor Unitário": f"R$ {v:.2f}"} for k, v in precos.items()])

# --- ABA 1: ENTRADA DINÂMICA ---
with tab1:
    st.subheader("Configuração por Item")
    escolha = st.selectbox("Selecione o serviço para editar:", list(precos.keys()))
    st.divider()

    # Lógica de Quantidade (Unidades)
    if escolha in [N_P_ALTO, N_P_BAIXO, N_LUMI, N_QUADRO]:
        val = st.number_input("Quantidade:", min_value=0, step=1, 
                               value=int(st.session_state.dados_servicos[escolha]), key=f"inp_{escolha}")
        st.session_state.dados_servicos[escolha] = val
        
    # Lógica de Metragem (Metros)
    elif escolha in [N_LED, N_DIST, N_PADRAO_FIA]:
        val = st.number_input("Metragem (m):", min_value=0.0, step=0.5, 
                               value=float(st.session_state.dados_servicos[escolha]), key=f"inp_{escolha}")
        st.session_state.dados_servicos[escolha] = val
        
    # Lógica Especial: Instalação do Padrão
    elif escolha == N_PADRAO_INST:
        dado_p = st.session_state.dados_servicos[N_PADRAO_INST]
        inc = st.checkbox("Incluir Instalação do Padrão?", value=dado_p["incluir"])
        tipo = st.selectbox("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"], 
                            index=["Monofásico", "Bifásico", "Trifásico"].index(dado_p["tipo"]))
        st.session_state.dados_servicos[N_PADRAO_INST] = {"incluir": inc, "tipo": tipo}
        
    # Lógica Especial: Projeto e ART
    elif escolha == N_ART:
        val = st.checkbox("Incluir Projeto e ART?", value=st.session_state.dados_servicos[N_ART])
        st.session_state.dados_servicos[N_ART] = val

    st.success(f"Registrado: {escolha}")

# --- ABA 3: RESUMO E EXCLUSÃO ---
with tab3:
    st.subheader("Resumo Final")
    itens_finais = {}
    soma_base = 0.0

    for item, dado in st.session_state.dados_servicos.items():
        v_item = 0.0
        if item == N_PADRAO_INST:
            if isinstance(dado, dict) and dado.get("incluir"):
                mult = {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}
                v_item = precos[item] * mult[dado["tipo"]]
        elif item == N_ART:
            continue # Calcula no final
        else:
            if isinstance(dado, (int, float)) and dado > 0:
                v_item = dado * precos[item]
        
        if v_item > 0:
            itens_finais[item] = v_item
            soma_base += v_item

    # Cálculo da ART: Fixo + 55% da soma dos outros serviços
    if st.session_state.dados_servicos[N_ART]:
        valor_art_total = precos[N_ART] + (soma_base * 0.55)
        itens_finais[N_ART] = valor_art_total

    if not itens_finais:
        st.info("Nenhum item selecionado.")
    else:
        for s, v in list(itens_finais.items()):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"✅ {s}: **R$ {v:.2f}**")
            if c2.button("🗑️", key=f"del_{s}"):
                if s == N_PADRAO_INST:
                    st.session_state.dados_servicos[s] = {"incluir": False, "tipo": "Monofásico"}
                elif s == N_ART:
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
            doc.add_heading('ORÇAMENTO DE SERVIÇOS ELÉTRICOS', 0)
            doc.add_paragraph("Detalhamento de mão de obra:")
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
