import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Coordenador - Batalha Naval",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Dashboard de Positivação e Cobertura")
st.caption("4 Elos Distribuidora Ltda. - Centro de Custo 622")

# ============================================================
# DATAS DE CONTROLE (MANUAL + FUSO BRASIL)
# ============================================================
COMPILATION_DATE = "22/07/2025 12:37"  # ⚠️ Atualize a cada deploy

# ============================================================
# CONEXÃO COM GOOGLE SHEETS
# ============================================================
SHEET_ID = "100LtVtmS76bT2CJd-EIb-bHTgX3F1BVm8Er5vUa-VYQ"

@st.cache_data(ttl=300)
def load_data():
    url_base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="

    df_base = pd.read_csv(url_base + "BASE")
    df_bi = pd.read_csv(url_base + "BI")
    df_fabricantes = pd.read_csv(url_base + "FABRICANTE")
    df_vendedores = pd.read_csv(url_base + "VENDEDORES")

    data_dados = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')

    # Padronizar colunas
    df_base = df_base.rename(columns={
        'cd_clien': 'codigo_cliente',
        'nome_cliente': 'nome_cliente',
        'nome_vendedor': 'nome_vendedor_base',
        'Cliente_Coligacao': 'Cliente_Coligacao',
        'Coordenador': 'Nome_Coordenador'
    })
    df_bi = df_bi.rename(columns={
        'Código Cliente': 'codigo_cliente',
        'Nome_Vendedor_Ajustado': 'nome_vendedor_bi',
        'Ano e Mês': 'Ano_e_Mes',
        'Nome Fabricante': 'Nome_Fabricante'
    })

    # Datas
    df_bi['Data'] = pd.to_datetime(df_bi['Ano_e_Mes'] + '-01', errors='coerce')
    df_bi['Mês'] = df_bi['Data'].dt.month
    df_bi['Ano'] = df_bi['Data'].dt.year
    df_bi['Mês_Ano'] = df_bi['Data'].dt.to_period('M').astype(str)

    # Merge
    df_merged = df_bi.merge(
        df_base[['codigo_cliente', 'nome_cliente', 'nome_vendedor_base', 'Cliente_Coligacao', 'Nome_Coordenador']],
        left_on=['codigo_cliente', 'nome_vendedor_bi'],
        right_on=['codigo_cliente', 'nome_vendedor_base'],
        how='left'
    )
    df_fallback = df_bi.merge(
        df_base[['codigo_cliente', 'nome_cliente', 'nome_vendedor_base', 'Cliente_Coligacao', 'Nome_Coordenador']],
        on='codigo_cliente',
        how='left',
        suffixes=('', '_fb')
    )
    for col in ['nome_cliente', 'Cliente_Coligacao', 'Nome_Coordenador']:
        if col in df_merged.columns and f'{col}_fb' in df_fallback.columns:
            df_merged[col] = df_merged[col].fillna(df_fallback[f'{col}_fb'])

    df_merged['nome_vendedor'] = df_merged['nome_vendedor_bi']

    # Dicionários de pastas
    fabricante_pasta = dict(zip(df_fabricantes['Nome Fabricante'], df_fabricantes['Pasta']))
    vendedor_pasta = dict(zip(df_vendedores['Vendedor'], df_vendedores['Pasta']))

    return df_base, df_bi, df_merged, data_dados, fabricante_pasta, vendedor_pasta

if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

df_base, df_bi, df_merged, data_dados, fabricante_pasta, vendedor_pasta = load_data()

# ============================================================
# LISTA DE INDÚSTRIAS (COMPLETA)
# ============================================================
TODAS_INDUSTRIAS = sorted(df_bi['Nome_Fabricante'].dropna().unique())
TODAS_INDUSTRIAS = [i for i in TODAS_INDUSTRIAS if i.strip() != '']
TOTAL_INDUSTRIAS_GERAL = len(TODAS_INDUSTRIAS)

# ============================================================
# FILTROS
# ============================================================
st.sidebar.header("🎯 Filtros")

# Limpar filtros
st.sidebar.markdown(
    """
    <form action="" method="get" style="margin-bottom: 10px;">
        <button type="submit" style="
            width: 100%; padding: 8px 12px; border-radius: 8px; 
            border: 1px solid #555; background-color: #333; color: #f0f0f0; 
            cursor: pointer; font-size: 14px; font-family: 'Source Sans Pro', sans-serif;
            display: flex; align-items: center; justify-content: center; gap: 8px;">
        🧹 Limpar Filtros
        </button>
    </form>
    """,
    unsafe_allow_html=True
)
if not st.query_params:
    for key in ['pasta', 'coordenador', 'vendedor', 'coligacao', 'ano', 'mes', 'industria_filtro', 'modo_gap']:
        st.session_state.pop(key, None)

# --- FILTRO DE PASTA (NOVO) ---
lista_pastas = ["Todas", "PA", "PV", "PVA"]
if 'pasta' not in st.session_state:
    st.session_state['pasta'] = 'Todas'
pasta_selecionada = st.sidebar.selectbox(
    "Pasta",
    lista_pastas,
    index=lista_pastas.index(st.session_state['pasta']) if st.session_state['pasta'] in lista_pastas else 0,
    key='pasta_select'
)
st.session_state['pasta'] = pasta_selecionada

# --- COORDENADOR ---
lista_coordenadores = ["Todos"] + sorted(df_base['Nome_Coordenador'].dropna().unique().tolist())
if 'coordenador' not in st.session_state: st.session_state['coordenador'] = 'Todos'
coordenador_selecionado = st.sidebar.selectbox("Coordenador", lista_coordenadores, index=lista_coordenadores.index(st.session_state['coordenador']), key='coordenador_select')
st.session_state['coordenador'] = coordenador_selecionado

# --- VENDEDOR (filtrado por coordenador e pasta) ---
if coordenador_selecionado != "Todos":
    vendedores_filtrados = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].dropna().unique()
else:
    vendedores_filtrados = df_base['nome_vendedor_base'].dropna().unique()

# Aplicar filtro de pasta à lista de vendedores
if pasta_selecionada != "Todas":
    vendedores_filtrados = [v for v in vendedores_filtrados if vendedor_pasta.get(v) == pasta_selecionada]

lista_vendedores = ["Todos"] + sorted(vendedores_filtrados)
if 'vendedor' not in st.session_state: st.session_state['vendedor'] = 'Todos'
if st.session_state['vendedor'] not in lista_vendedores: st.session_state['vendedor'] = 'Todos'
vendedor_selecionado = st.sidebar.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(st.session_state['vendedor']), key='vendedor_select')
st.session_state['vendedor'] = vendedor_selecionado

# --- COLIGAÇÃO, ANO, MÊS, INDÚSTRIA, GAP ---
# (Mantidos como no código anterior, sem alterações)
# ... (código dos filtros restantes)

# ============================================================
# APLICAR FILTROS
# ============================================================
df_filtrado = df_merged.copy()

# Filtro de pasta (afeta indústrias visíveis)
if pasta_selecionada != "Todas":
    INDUSTRIAS_PERMITIDAS = [ind for ind in TODAS_INDUSTRIAS if fabricante_pasta.get(ind) == pasta_selecionada]
else:
    INDUSTRIAS_PERMITIDAS = TODAS_INDUSTRIAS.copy()

if coordenador_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Nome_Coordenador'] == coordenador_selecionado]
if vendedor_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['nome_vendedor'] == vendedor_selecionado]

# Restrição de indústrias pela pasta
df_filtrado = df_filtrado[df_filtrado['Nome_Fabricante'].isin(INDUSTRIAS_PERMITIDAS)]

# ... (demais filtros de coligação, ano, mês, indústria multiselect, modo gap)

# ============================================================
# CARDS DE PASTA (NOVO)
# ============================================================
st.subheader("📅 Visão por Pasta")

# Calcular métricas por pasta
pastas_unicas = ["PA", "PV", "PVA"]
cards_pasta = []
for p in pastas_unicas:
    df_pasta = df_filtrado[df_filtrado['Nome_Fabricante'].isin(
        [ind for ind in TODAS_INDUSTRIAS if fabricante_pasta.get(ind) == p]
    )]
    ativos = df_pasta[df_pasta['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
    total_carteira = df_base[df_base['nome_vendedor_base'].isin(
        df_pasta['nome_vendedor'].unique()
    )]['codigo_cliente'].nunique() if not df_pasta.empty else 0
    pct = (ativos / total_carteira * 100) if total_carteira > 0 else 0
    cards_pasta.append({"Pasta": p, "Ativos": ativos, "Carteira": total_carteira, "% Positivação": pct})

# Exibir cards lado a lado
cols = st.columns(len(cards_pasta))
for i, card in enumerate(cards_pasta):
    with cols[i]:
        st.metric(f"Pasta {card['Pasta']}", f"{card['Ativos']} clientes")
        st.metric("Carteira", card['Carteira'])
        st.metric("% Positivação", f"{card['% Positivação']:.1f}%")

st.divider()

# ============================================================
# PERFORMANCE POR VENDEDOR (COM INDICADOR DE PASTA)
# ============================================================
st.subheader("👥 Performance por Vendedor")

# ... (código da performance, adicionando coluna 'Pasta' e aplicando meta de 70%)
# ...

# ============================================================
# EVOLUÇÃO MENSAL POR PASTA (COM LINHA DE META)
# ============================================================
st.subheader("📅 Evolução Mensal por Pasta")

# ... (gráfico de linhas com uma linha por pasta, mais linha tracejada em 70%)
# ...

# ============================================================
# ANÁLISE DE GAP POR PASTA
# ============================================================
st.subheader("🔍 Análise de GAP por Pasta")

# ... (lista de clientes sem compra em cada pasta)
# ...

# ============================================================
# DEMAIS SEÇÕES (BATALHA NAVAL, FICHA DO CLIENTE)
# ============================================================
# ... (mantidas conforme versão anterior)
