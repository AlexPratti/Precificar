import streamlit as st
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import time

st.set_page_config(page_title="Sistema Elétrico Profissional", layout="wide")

# --- INICIALIZAÇÃO DO ESTADO ---
if 'dados_servicos' not in st.session_state:
    st.session_state.dados_servicos = {
        "Pontos Altos de Força": 0.0, "Pontos Baixos e Médios de Força": 0.0,
        "Luminárias em Teto/Gesso/PVC": 0.0, "Perfil LED em Teto/Gesso/PVC": 0.0,
        "Fiação de Distribuição": 0.0, "Fiação do Padrão ao Quadro de Disjuntores": 0.0,
        "Instalações sobre Laje/Telhados": 0.0, "Instalação de Eletrodutos/Canaletas Sobrepostas": 0.0,
        "Quadro de Disjuntores": 0.0, "Instalação do Padrão": {"incluir": False, "tipo": "Monofásico"},
        "Projeto e ART": False
    }

if 'lista_materiais' not in st.session_state:
    st.session_state.lista_materiais = []

# --- FUNÇÕES AUXILIARES ---
def formatar_qtd(qtd, unidade):
    if unidade.lower() == "m":
        return f"{float(qtd):.1f}"
    return f"{int(qtd)}"

# --- SIDEBAR: PREÇOS MÃO DE OBRA ---
with st.sidebar:
    st.header("⚙️ Preços Mão de Obra")
    
    # EDITE OS VALORES ABAIXO PARA O SEU COMMIT:
    precos_fixos = {
        "Pontos Altos de Força": 20.0,
        "Pontos Baixos e Médios de Força": 15.0,
        "Luminárias em Teto/Gesso/PVC": 35.0,
        "Perfil LED em Teto/Gesso/PVC": 25.0,
        "Fiação de Distribuição": 15.0,
        "Fiação do Padrão ao Quadro de Disjuntores": 25.0,
        "Instalações sobre Laje/Telhados": 10.0,
        "Instalação de Eletrodutos/Canaletas Sobrepostas": 15.0,
        "Quadro de Disjuntores": 15.0,
        "Instalação do Padrão": 400.0,
        "Projeto e ART": 800.0
    }

    # Gerando os campos na sidebar automaticamente com base nos valores acima
    precos = {}
    for servico, valor_padrao in precos_fixos.items():
        precos[servico] = st.number_input(f"Valor: {servico}", value=valor_padrao, key=f"p_{servico}")


# --- ABAS ---
tab_serv, tab_conf_serv, tab_mat, tab_conf_mat, tab_doc = st.tabs([
    "📋 Serviços", "🔍 Conferência Serviços", "📦 Materiais", "🔍 Conferência Materiais", "📄 Gerar Orçamento"
])

# --- ABA 1: SERVIÇOS (LANÇAMENTO) ---
with tab_serv:
    st.subheader("Lançamento de Mão de Obra")
    escolha_serv = st.selectbox("Selecione o serviço para editar:", list(st.session_state.dados_servicos.keys()))
    
    if escolha_serv in ["Pontos Altos de Força", "Pontos Baixos e Médios de Força", "Luminárias em Teto/Gesso/PVC", "Quadro de Disjuntores"]:
        st.session_state.dados_servicos[escolha_serv] = st.number_input("Quantidade:", min_value=0.0, step=1.0, value=float(st.session_state.dados_servicos[escolha_serv]), key=f"in_{escolha_serv}")
    elif escolha_serv in ["Perfil LED em Teto/Gesso/PVC", "Fiação de Distribuição", "Fiação do Padrão ao Quadro de Disjuntores", "Instalações sobre Laje/Telhados", "Instalação de Eletrodutos/Canaletas Sobrepostas"]:
        st.session_state.dados_servicos[escolha_serv] = st.number_input("Metragem (m):", min_value=0.0, step=0.5, value=float(st.session_state.dados_servicos[escolha_serv]), key=f"in_{escolha_serv}")
    elif escolha_serv == "Instalação do Padrão":
        d = st.session_state.dados_servicos[escolha_serv]
        inc = st.checkbox("Incluir Padrão?", value=d["incluir"])
        tipo = st.selectbox("Fase:", ["Monofásico", "Bifásico", "Trifásico"], index=["Monofásico", "Bifásico", "Trifásico"].index(d["tipo"]))
        st.session_state.dados_servicos[escolha_serv] = {"incluir": inc, "tipo": tipo}
    elif escolha_serv == "Projeto e ART":
        st.session_state.dados_servicos[escolha_serv] = st.checkbox("Incluir Projeto/ART?", value=st.session_state.dados_servicos[escolha_serv])

# --- ABA 2: CONFERÊNCIA SERVIÇOS ---
with tab_conf_serv:
    st.subheader("🔍 Revisão de Serviços Lançados")
    soma_base_para_art = 0.0
    servicos_ativos = False
    
    if st.button("🚨 Zerar Todos os Serviços"):
        for k in st.session_state.dados_servicos.keys():
            if k == "Instalação do Padrão": st.session_state.dados_servicos[k] = {"incluir": False, "tipo": "Monofásico"}
            elif k == "Projeto e ART": st.session_state.dados_servicos[k] = False
            else: st.session_state.dados_servicos[k] = 0.0
        st.rerun()
    
    st.divider()
    col_h1, col_h2, col_h3, col_h4 = st.columns([0.4, 0.2, 0.2, 0.2])
    col_h1.write("**Serviço**"); col_h2.write("**Qtd/Fase**"); col_h3.write("**Subtotal**"); col_h4.write("**Ação**")

    for servico, dado in st.session_state.dados_servicos.items():
        v_item, exibir, label = 0.0, False, ""
        if servico == "Instalação do Padrão":
            if dado["incluir"]:
                v_item = precos[servico] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[dado["tipo"]]
                exibir, label = True, dado["tipo"]
        elif servico == "Projeto e ART": continue
        else:
            if dado > 0:
                v_item = dado * precos[servico]
                exibir, label = True, f"{dado:.1f} m" if "m" in servico or "Laje" in servico else f"{int(dado)} un"
        
        if exibir:
            servicos_ativos = True
            soma_base_para_art += v_item
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.4, 0.2, 0.2, 0.2])
                c1.write(servico); c2.write(label); c3.write(f"R$ {v_item:.2f}")
                if c4.button("🗑️", key=f"del_srv_{servico}"):
                    if servico == "Instalação do Padrão": st.session_state.dados_servicos[servico]["incluir"] = False
                    else: st.session_state.dados_servicos[servico] = 0.0
                    st.rerun()

    if st.session_state.dados_servicos["Projeto e ART"]:
        servicos_ativos = True
        v_art = precos["Projeto e ART"] + (soma_base_para_art * 0.55)
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.4, 0.2, 0.2, 0.2])
            c1.write("Projeto e ART"); c2.write("Fixo+55%"); c3.write(f"R$ {v_art:.2f}")
            if c4.button("🗑️", key="del_art_conf"):
                st.session_state.dados_servicos["Projeto e ART"] = False
                st.rerun()

    if not servicos_ativos: st.info("Nenhum serviço lançado.")

# --- ABA 3: MATERIAIS ---
with tab_mat:
    st.subheader("📦 Lançamento de Materiais")
    categoria = st.selectbox("Categoria:", ["CABOS", "DISJUNTORES", "MÓDULOS, TOMADAS E PLACAS", "CONDUÍTES", "CONDULETES", "OUTROS"])
    
    with st.container(border=True):
        nome_f, uni_f, qtd_f = "", "", 0.0
        
        if categoria == "CABOS":
            c1, c2, c3 = st.columns(3)
            sec = c1.selectbox("Seção:", ["1,0 mm²", "1,5 mm²", "2,5 mm²", "4,0 mm²", "6,0 mm²", "10 mm²", "16 mm²", "25 mm²", "35 mm²"])
            cor = c2.selectbox("Cor:", ["azul", "preto", "branco", "vermelho", "amarelo", "verde", "verde e amarelo", "cinza", "marrom"])
            qtd_f = c3.number_input("Metros:", min_value=0.0, step=1.0, key="in_q_cabo")
            nome_f, uni_f = f"Cabo Flexível {sec} {cor}", "m"

        elif categoria == "DISJUNTORES":
            c1, c2, c3, c4 = st.columns(4)
            amps = [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]
            corr = c1.selectbox("Corrente:", [f"{a} A" for a in amps])
            fase = c2.selectbox("Polos:", ["Unipolar", "Bipolar", "Tripolar"])
            curva = c3.selectbox("Curva:", ["B", "C", "D"], index=1)
            qtd_f = c4.number_input("Qtde:", min_value=0, step=1, key="in_q_disj")
            nome_f, uni_f = f"Disjuntor {fase} {curva}{corr.replace(' A', '')}", "un"

        elif categoria == "MÓDULOS, TOMADAS E PLACAS":
            c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
            tipo = c1.selectbox("Tipo:", ["Placa 4x2", "Placa 4x4", "Módulo Tomada", "Módulo Interruptor"])
            if tipo == "Módulo Interruptor":
                desc_op = ["Simples", "Three Way", "Four Way", "Simples com Tomada"]
            elif tipo == "Módulo Tomada":
                desc_op = ["10 A", "20 A", "USB", "RJ45", "TV"]
            else:
                desc_op = ["Cega", "1 posto", "2 postos", "3 postos", "4 postos", "6 postos"]
            desc = c2.selectbox("Descrição:", desc_op)
            qtd_f = c3.number_input("Qtde:", min_value=0, step=1, key="in_q_mod")
            nome_f, uni_f = f"{tipo} {desc}", "pç"

        elif categoria == "CONDUÍTES" or categoria == "CONDULETES":
            c1, c2, c3 = st.columns(3)
            bits = ['1/2"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"', '2 1/2"', '3"', '4"']
            sec = c1.selectbox("Bitola:", bits)
            if categoria == "CONDUÍTES":
                tipo_t = st.text_input("Tipo (ex: Corrugado):", key="t_cond")
                uni_f = "m"
            else:
                tipo_t = st.selectbox("Tipo:", ["C", "E", "X", "T", "LR", "LL", "LB", "TB", "B"])
                uni_f = "un"
            qtd_f = c3.number_input("Quantidade:", min_value=0.0, key="q_tubo")
            nome_f = f"{categoria.title()[:-1]} {sec} {tipo_t}"

        elif categoria == "OUTROS":
            c1, c2, c3 = st.columns([0.5, 0.2, 0.3])
            nome_f = c1.text_input("Descrição:", key="d_out")
            uni_f = c2.selectbox("Unid:", ["un", "m", "Pç", "kg"])
            qtd_f = c3.number_input("Qtde:", min_value=0.0, key="q_out")

        if st.button("➕ Adicionar à Lista"):
            if nome_f and qtd_f > 0:
                st.session_state.lista_materiais.append({"nome": nome_f.strip(), "qtd": qtd_f, "uni": uni_f})
                # Mensagem momentânea
                aviso = st.success("Material Lançado à Lista!")
                time.sleep(1)
                aviso.empty()
                st.rerun()

# --- ABA 4: CONFERÊNCIA MATERIAIS ---
with tab_conf_mat:
    st.subheader("🔍 Revisão de Materiais")
    if not st.session_state.lista_materiais: st.info("Nenhum material lançado.")
    else:
        if st.button("🚨 Limpar Todos os Materiais"): st.session_state.lista_materiais = []; st.rerun()
        for i, item in enumerate(st.session_state.lista_materiais):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.5, 0.15, 0.15, 0.2])
                st.session_state.lista_materiais[i]['nome'] = c1.text_input("Nome:", item['nome'], key=f"ed_n_{i}")
                st.session_state.lista_materiais[i]['qtd'] = c2.number_input("Qtd:", value=float(item['qtd']), key=f"ed_q_{i}")
                st.session_state.lista_materiais[i]['uni'] = c3.text_input("Unid:", item['uni'], key=f"ed_u_{i}")
                if c4.button("🗑️", key=f"del_m_{i}"): st.session_state.lista_materiais.pop(i); st.rerun()

# --- ABA 5: DOCUMENTO ---
with tab_doc:
    itens_orc, soma_mo = {}, 0.0
    for k, v in st.session_state.dados_servicos.items():
        if k == "Instalação do Padrão" and v["incluir"]:
            val = precos[k] * {"Monofásico": 1.0, "Bifásico": 1.4, "Trifásico": 1.7}[v["tipo"]]
            itens_orc[k], soma_mo = val, soma_mo + val
        elif k != "Projeto e ART" and k != "Instalação do Padrão" and v > 0:
            val = float(v) * precos[k]
            itens_orc[k], soma_mo = val, soma_mo + val
    if st.session_state.dados_servicos["Projeto e ART"]:
        itens_orc["Projeto e ART"] = precos["Projeto e ART"] + (soma_mo * 0.55)
    
    total_mo = sum(itens_orc.values())
    st.write(f"### Valor Total Geral: R$ {total_mo:.2f}")

    def gerar_word(orc, mats, tot):
        doc = Document()
        for s in doc.sections: s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Pt(72)
        style = doc.styles['Normal']
        style.font.name, style.font.size, style.paragraph_format.line_spacing = 'Arial', Pt(12), 1.5
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if orc:
            doc.add_heading('ORÇAMENTO DE MÃO DE OBRA', 1)
            for k, v in orc.items():
                p = doc.add_paragraph(); p.add_run(f"• {k}: ").bold = True; p.add_run(f"R$ {v:.2f}")
            p_t = doc.add_paragraph(); p_t.add_run(f"\nVALOR TOTAL DO ORÇAMENTO: R$ {tot:.2f}").bold = True
            if mats: doc.add_page_break()
        if mats:
            doc.add_heading('LISTA DE MATERIAIS', 1)
            for m in mats: doc.add_paragraph(f"• {m['nome']}: {formatar_qtd(m['qtd'], m['uni'])} {m['uni']}")
        buf = BytesIO(); doc.save(buf); return buf.getvalue()

    if total_mo > 0 or len(st.session_state.lista_materiais) > 0:
        st.download_button("📥 Baixar Documento Completo", gerar_word(itens_orc, st.session_state.lista_materiais, total_mo), "orcamento.docx", type="primary")
