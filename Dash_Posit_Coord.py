import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo
import unicodedata
import re
from urllib.parse import quote

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Coordenador - Batalha Naval",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    a[href*="/edit"] { display: none !important; }
    a[href*="github.com"] { display: none !important; }
    .stButton > button {
        width: 100%;
        min-height: 50px;
        white-space: normal;
        word-wrap: break-word;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
        padding: 8px 4px;
        text-align: center;
    }
    /* Alinhamento à direita nas tabelas */
    .dataframe th, .dataframe td {
        text-align: right !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Positivação e Cobertura")
st.caption("4 Elos Distribuidora Ltda. - Centro de Custo 622")

# ============================================================
# CARREGAR DADOS (Google Sheets)
# ============================================================
SHEET_ID = "100LtVtmS76bT2CJd-EIb-bHTgX3F1BVm8Er5vUa-VYQ"

@st.cache_data(ttl=300)
def load_data():
    url_base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="
    try:
        df_base = pd.read_csv(url_base + quote("BASE"))
        df_bi = pd.read_csv(url_base + quote("BI"))
        df_fabricantes = pd.read_csv(url_base + quote("FABRICANTE"))
        df_vendedores = pd.read_csv(url_base + quote("VENDEDORES"))
        df_meta_kenvue = pd.read_csv(url_base + quote("Meta Kenvue"))
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        st.stop()

    data_dados = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')

    def normalizar_texto(texto):
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ASCII', 'ignore').decode('ASCII')
        texto = texto.lower().strip()
        texto = re.sub(r'\s+', ' ', texto)
        return texto

    # BASE
    df_base.columns = [str(col).strip() for col in df_base.columns]
    base_rename = {}
    for col in df_base.columns:
        col_norm = normalizar_texto(col)
        if 'codigo cliente' in col_norm or ('codigo' in col_norm and 'cliente' in col_norm):
            base_rename[col] = 'codigo_cliente'
        elif col_norm == 'cliente' or ('cliente' in col_norm and 'nome' in col_norm):
            base_rename[col] = 'nome_cliente'
        elif 'vendedor' in col_norm:
            base_rename[col] = 'nome_vendedor_base'
        elif 'coligacao' in col_norm or 'coliga' in col_norm:
            base_rename[col] = 'Cliente_Coligacao'
        elif 'coordenador' in col_norm:
            base_rename[col] = 'Nome_Coordenador'
        elif 'municipio' in col_norm:
            base_rename[col] = 'Municipio'
        elif 'canal' in col_norm:
            base_rename[col] = 'Canal'
        elif 'segmento' in col_norm:
            base_rename[col] = 'Segmento'
    df_base = df_base.rename(columns=base_rename)

    if 'nome_cliente' not in df_base.columns:
        for col in df_base.columns:
            if normalizar_texto(col) == 'cliente':
                df_base.rename(columns={col: 'nome_cliente'}, inplace=True)
                break

    required_base_cols = ['codigo_cliente', 'nome_cliente', 'nome_vendedor_base',
                          'Cliente_Coligacao', 'Nome_Coordenador', 'Municipio', 'Canal', 'Segmento']
    missing_base = [c for c in required_base_cols if c not in df_base.columns]
    if missing_base:
        st.error(f"Colunas essenciais não encontradas no DataFrame BASE: {missing_base}")
        st.stop()

    # BI
    df_bi.columns = [str(col).strip() for col in df_bi.columns]
    bi_rename = {}
    for col in df_bi.columns:
        col_norm = normalizar_texto(col)
        if 'codigo cliente' in col_norm:
            bi_rename[col] = 'codigo_cliente'
        elif 'vendedor' in col_norm and 'ajustado' in col_norm:
            bi_rename[col] = 'nome_vendedor_bi'
        elif 'ano' in col_norm and 'mes' in col_norm:
            bi_rename[col] = 'Ano_e_Mes'
        elif 'fabricante' in col_norm:
            bi_rename[col] = 'Nome_Fabricante'
        elif 'linha de produto' in col_norm:
            bi_rename[col] = 'Linha_Produto'
        elif 'categoria' in col_norm:
            bi_rename[col] = 'Categoria'
        elif 'valor' in col_norm and ('venda' in col_norm or 'vendas' in col_norm):
            bi_rename[col] = 'Valor_Vendas'
    df_bi = df_bi.rename(columns=bi_rename)

    if 'Ano_e_Mes' not in df_bi.columns:
        for col in df_bi.columns:
            if 'ano' in col.lower() and 'mes' in col.lower():
                df_bi.rename(columns={col: 'Ano_e_Mes'}, inplace=True)
                break

    if 'Ano_e_Mes' not in df_bi.columns:
        st.error("Não foi possível identificar a coluna de Ano/Mês no DataFrame BI.")
        st.stop()

    df_bi['Data'] = pd.to_datetime(df_bi['Ano_e_Mes'] + '-01', errors='coerce')
    df_bi['MŒs'] = df_bi['Data'].dt.month
    df_bi['Ano'] = df_bi['Data'].dt.year
    df_bi['MŒs_Ano'] = df_bi['Data'].dt.to_period('M').astype(str)

    if 'Valor_Vendas' in df_bi.columns:
        def converter_valor(valor):
            if pd.isna(valor):
                return 0.0
            s = str(valor).strip().replace('R$', '').replace(' ', '')
            if s == '':
                return 0.0
            if ',' in s:
                s = s.replace('.', '').replace(',', '.')
            elif '.' in s:
                if s.count('.') == 1:
                    pass
                else:
                    s = s.replace('.', '')
            try:
                return float(s)
            except:
                return 0.0
        df_bi['Valor_Vendas'] = df_bi['Valor_Vendas'].apply(converter_valor)

    # MERGE
    df_base_dedup = df_base.drop_duplicates(subset=['codigo_cliente'], keep='first')
    df_merged = df_bi.merge(
        df_base[['codigo_cliente', 'nome_cliente', 'nome_vendedor_base', 'Cliente_Coligacao',
                 'Nome_Coordenador', 'Municipio', 'Canal', 'Segmento']],
        left_on=['codigo_cliente', 'nome_vendedor_bi'],
        right_on=['codigo_cliente', 'nome_vendedor_base'],
        how='left'
    )
    for col in ['nome_cliente', 'Cliente_Coligacao', 'Nome_Coordenador', 'Municipio', 'Canal', 'Segmento']:
        if col in df_base.columns:
            fallback_map = df_base_dedup.set_index('codigo_cliente')[col].to_dict()
            df_merged[col] = df_merged[col].fillna(df_merged['codigo_cliente'].map(fallback_map))

    df_merged['nome_vendedor'] = df_merged['nome_vendedor_bi']

    fabricante_pasta = dict(zip(df_fabricantes['Nome Fabricante'], df_fabricantes['Pasta']))
    vendedor_pasta = dict(zip(df_vendedores['Vendedor'], df_vendedores['Pasta']))

    return df_base, df_bi, df_merged, df_meta_kenvue, data_dados, fabricante_pasta, vendedor_pasta

df_base, df_bi, df_merged, df_meta_kenvue, data_dados, fabricante_pasta, vendedor_pasta = load_data()
TODAS_INDUSTRIAS = sorted([i for i in df_bi['Nome_Fabricante'].dropna().unique() if str(i).strip() != ''])

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def formatar_mes_rotulo(periodo_str):
    try:
        ano, mes = periodo_str.split('-')
        meses = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',
                 7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
        return f"{meses[int(mes)]}/{ano[2:]}"
    except:
        return periodo_str

def formatar_numero_br(valor):
    if pd.isna(valor):
        return ''
    try:
        numero = float(valor)
        return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def aplicar_filtros_comuns(df, incluir_mes=True):
    df = df.copy()
    if pasta_selecionada not in ["Todas", "PVA"]:
        vendedores_pasta = [v for v in df_base['nome_vendedor_base'].unique()
                            if vendedor_pasta.get(v) == pasta_selecionada]
        df = df[df['nome_vendedor'].isin(vendedores_pasta)]
    if vendedor_selecionado != "Todos":
        df = df[df['nome_vendedor'] == vendedor_selecionado]
    if coordenador_selecionado != "Todos":
        df = df[df['Nome_Coordenador'] == coordenador_selecionado]
    if coligacao_selecionada != "Todas":
        df = df[df['Cliente_Coligacao'] == coligacao_selecionada]
    if municipio_selecionado:
        df = df[df['Municipio'].isin(municipio_selecionado)]
    if canal_selecionado:
        df = df[df['Canal'].isin(canal_selecionado)]
    if segmento_selecionado:
        df = df[df['Segmento'].isin(segmento_selecionado)]
    if incluir_mes and mes_selecionado != "Todos":
        mes_num = int(mes_selecionado.split(' - ')[0])
        anos_do_mes = df[df['MŒs'] == mes_num]['Ano'].unique()
        ano_ref = max(anos_do_mes) if len(anos_do_mes) > 0 else df['Ano'].max()
        mes_ano_ref = f"{ano_ref}-{mes_num:02d}"
        df = df[df['MŒs_Ano'] == mes_ano_ref]
    if industria_selecionada_lista:
        df = df[df['Nome_Fabricante'].isin(industria_selecionada_lista)]
    if categoria_selecionada:
        df = df[df['Categoria'].isin(categoria_selecionada)]
    if linha_selecionada:
        df = df[df['Linha_Produto'].isin(linha_selecionada)]
    return df

def calcular_janela_movel(df_historico, mes_selecionado, janela_meses):
    if mes_selecionado == "Todos":
        return df_historico.copy()
    mes_num = int(mes_selecionado.split(' - ')[0])
    anos_do_mes = df_historico[df_historico['MŒs'] == mes_num]['Ano'].unique()
    ano_ref = max(anos_do_mes) if len(anos_do_mes) > 0 else df_historico['Ano'].max()
    meses_janela = []
    for i in range(1, janela_meses + 1):
        mes = mes_num - i
        ano = ano_ref
        while mes <= 0:
            mes += 12
            ano -= 1
        meses_janela.append((ano, mes))
    cond = pd.Series(False, index=df_historico.index)
    for a, m in meses_janela:
        cond |= (df_historico['Ano'] == a) & (df_historico['MŒs'] == m)
    return df_historico[cond]

# ============================================================
# FILTROS
# ============================================================
with st.expander("🎯 Filtros", expanded=True):
    st.markdown("**Equipe de Vendas**")
    col_eq1, col_eq2, col_eq3 = st.columns(3)
    with col_eq1:
        lista_coordenadores = ["Todos"] + sorted(df_base['Nome_Coordenador'].dropna().unique().tolist())
        coordenador_selecionado = st.selectbox("Coordenador", lista_coordenadores, key='coord_top')
    with col_eq2:
        if coordenador_selecionado != "Todos":
            vendedores_base = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].dropna().unique()
        else:
            vendedores_base = df_base['nome_vendedor_base'].dropna().unique()
        lista_vendedores = ["Todos"] + sorted(vendedores_base)
        vendedor_selecionado = st.selectbox("Vendedor", lista_vendedores, key='vend_top')
    with col_eq3:
        lista_pastas = ["Todas", "PA", "PV", "PVA"]
        pasta_selecionada = st.selectbox("Pasta", lista_pastas, key='pasta_top')
        if pasta_selecionada in ["Todas", "PVA"]:
            INDUSTRIAS_PERMITIDAS = TODAS_INDUSTRIAS.copy()
        else:
            INDUSTRIAS_PERMITIDAS = [ind for ind in TODAS_INDUSTRIAS if fabricante_pasta.get(ind) == pasta_selecionada]

    st.markdown("**Produto**")
    col_prod1, col_prod2, col_prod3 = st.columns(3)
    with col_prod1:
        if pasta_selecionada in ["Todas", "PVA"]:
            INDUSTRIAS_DISPONIVEIS = TODAS_INDUSTRIAS.copy()
        else:
            INDUSTRIAS_DISPONIVEIS = [ind for ind in TODAS_INDUSTRIAS if fabricante_pasta.get(ind) == pasta_selecionada]
        industria_selecionada_lista = st.multiselect("Indústria(s)", options=INDUSTRIAS_DISPONIVEIS, key='ind_top')
    with col_prod2:
        categoria_selecionada = st.multiselect("Categoria(s)", options=sorted(df_bi['Categoria'].dropna().unique()), key='cat_top')
    with col_prod3:
        linha_selecionada = st.multiselect("Linha(s) de Produto", options=sorted(df_bi['Linha_Produto'].dropna().unique()), key='linha_top')

    st.markdown("**Localização**")
    col_loc1, col_loc2, col_loc3, col_loc4 = st.columns(4)
    with col_loc1:
        if vendedor_selecionado != "Todos":
            clientes_do_vendedor = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].unique()
            coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_vendedor)]['Cliente_Coligacao'].dropna().unique()
        elif coordenador_selecionado != "Todos":
            vendedores_do_coord = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].unique()
            clientes_do_coord = df_base[df_base['nome_vendedor_base'].isin(vendedores_do_coord)]['codigo_cliente'].unique()
            coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_coord)]['Cliente_Coligacao'].dropna().unique()
        else:
            coligacoes_filtradas = df_base['Cliente_Coligacao'].dropna().unique()
        lista_coligacoes = ["Todas"] + sorted(coligacoes_filtradas)
        coligacao_selecionada = st.selectbox("Coligação", lista_coligacoes, key='colig_top')
    with col_loc2:
        canal_selecionado = st.multiselect("Canal(is)", options=sorted(df_base['Canal'].dropna().unique()), key='canal_top')
    with col_loc3:
        segmento_selecionado = st.multiselect("Segmento(s)", options=sorted(df_base['Segmento'].dropna().unique()), key='seg_top')
    with col_loc4:
        municipio_selecionado = st.multiselect("Município(s)", options=sorted(df_base['Municipio'].dropna().unique()), key='muni_top')

    st.markdown("**Período e Metas**")
    col_per1, col_per2, col_per3 = st.columns(3)
    with col_per1:
        meses_disponiveis = sorted(df_merged['MŒs'].dropna().unique())
        meses_nomes = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
                       7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
        lista_meses = ["Todos"] + [f"{int(m):02d} - {meses_nomes.get(int(m), '')}" for m in meses_disponiveis]
        if 'mes' not in st.session_state:
            if meses_disponiveis:
                ultimo_mes = max(meses_disponiveis)
                st.session_state['mes'] = f"{int(ultimo_mes):02d} - {meses_nomes.get(int(ultimo_mes), '')}"
            else:
                st.session_state['mes'] = 'Todos'
        mes_selecionado = st.selectbox("Mês", lista_meses, index=lista_meses.index(st.session_state['mes']), key='mes_top')
        st.session_state['mes'] = mes_selecionado
    with col_per2:
        janela_meses = st.slider("Janela da Base Ativa (meses)", 3, 6, 6, key='janela_top')
    with col_per3:
        meta_ativa = st.number_input("Meta Base Ativa (%)", 0, 100, 70, key='meta_ativa_top')

# ============================================================
# APLICAR FILTROS
# ============================================================
df_filtrado = aplicar_filtros_comuns(df_merged, incluir_mes=True)
df_historico = aplicar_filtros_comuns(df_merged, incluir_mes=False)
df_relatorio_base = aplicar_filtros_comuns(df_merged, incluir_mes=False)
df_historico_janela = calcular_janela_movel(df_historico, mes_selecionado, janela_meses)

# ============================================================
# NAVEGAÇÃO
# ============================================================
st.markdown("---")
opcoes_paginas = [
    "🏠 Visão Geral",
    "👥 Performance Vendedor",
    "📍 Positivação por Município",
    "🏷️ Positivação por Segmento",
    "🔀 Oportunidades Cruzadas",
    "🟢 Softys Falcon",
    "🟠 Kenvue Perfumaria",
    "🟤 Cenoura & Bronze",
    "📋 Batalha Naval",
    "🔍 Ficha do Cliente"
]
if 'pagina_selecionada' not in st.session_state:
    st.session_state['pagina_selecionada'] = opcoes_paginas[0]
linhas = [opcoes_paginas[i:i+5] for i in range(0, len(opcoes_paginas), 5)]
for linha in linhas:
    cols = st.columns(len(linha))
    for i, pagina in enumerate(linha):
        with cols[i]:
            if st.button(pagina, key=f'nav_btn_{pagina}', use_container_width=True):
                st.session_state['pagina_selecionada'] = pagina
                st.rerun()
opcao = st.session_state['pagina_selecionada']

# ============================================================
# PÁGINA: VISÃO GERAL
# ============================================================
if opcao == "🏠 Visão Geral":
    carteira_ativa_total = df_historico_janela[df_historico_janela['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
    positivados_periodo = df_filtrado[df_filtrado['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
    pct_ativa = (positivados_periodo / carteira_ativa_total * 100) if carteira_ativa_total > 0 else 0

    st.subheader("📅 Carteira Ativa (Janela Móvel)")
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.metric("Carteira Ativa (últimos {} meses)".format(janela_meses), carteira_ativa_total)
    col_a2.metric("Positivados no Mês", positivados_periodo)
    col_a3.metric("% Positivação (Ativa)", f"{pct_ativa:.1f}%")

    if mes_selecionado != "Todos":
        mes_num = int(mes_selecionado.split(' - ')[0])
        anos_do_mes = df_historico[df_historico['MŒs'] == mes_num]['Ano'].unique()
        ano_ytd = max(anos_do_mes) if len(anos_do_mes) > 0 else df_historico['Ano'].max()
    else:
        ano_ytd = df_historico['Ano'].max()
        mes_num = df_historico['MŒs'].max()

    df_historico_ano = df_historico[df_historico['Ano'] == ano_ytd]
    df_mensal_ativos = df_historico_ano[df_historico_ano['Nome_Fabricante'].notna()]
    mensal_pos = df_mensal_ativos.groupby('MŒs_Ano')['codigo_cliente'].nunique().reset_index()
    mensal_pos.columns = ['Mês', 'Clientes Positivados']
    df_ytd = df_historico[(df_historico['Ano'] == ano_ytd) & (df_historico['MŒs'] <= mes_num)]
    ytd_total = df_ytd['codigo_cliente'].nunique()

    df_meses = pd.DataFrame({'Mês': list(mensal_pos['Mês']), 'Clientes Positivados': list(mensal_pos['Clientes Positivados'])})
    df_meses['Rótulo'] = df_meses['Mês'].apply(formatar_mes_rotulo)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_meses['Rótulo'], y=df_meses['Clientes Positivados'], text=df_meses['Clientes Positivados'],
                         textposition='outside', marker_color='#2E8B57', name='Mensal',
                         hovertemplate='Mês: %{x}<br>Clientes: %{y}'))
    fig.add_trace(go.Bar(x=['YTD'], y=[ytd_total], text=[ytd_total], textposition='outside',
                         marker_color='#D32F2F', name='YTD', hovertemplate='YTD<br>Clientes: %{y}'))
    fig.update_layout(title='Positivação Carteira Ativa (Mensal + YTD)', yaxis=dict(title='Clientes'),
                      barmode='group', legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PÁGINA: SOFTYS FALCON (COM TOP 10 CLIENTES CORRIGIDO)
# ============================================================
elif opcao == "🟢 Softys Falcon":
    df_softys = df_relatorio_base[df_relatorio_base['Nome_Fabricante'] == 'SOFTYS FALCON'].copy()

    if not df_softys.empty:
        st.subheader("🟢 Foco Estratégico: Softys Falcon")

        # Determinação do mês atual com base no filtro global
        if mes_selecionado != "Todos":
            mes_num = int(mes_selecionado.split(' - ')[0])
            anos_do_mes = df_softys[df_softys['MŒs'] == mes_num]['Ano'].unique()
            ano_ref = max(anos_do_mes) if len(anos_do_mes) > 0 else df_softys['Ano'].max()
            mes_atual_num = mes_num
        else:
            if not df_softys.empty:
                ultimo_periodo = df_softys['MŒs_Ano'].max()
                ano_ref = int(ultimo_periodo.split('-')[0])
                mes_atual_num = int(ultimo_periodo.split('-')[1])
            else:
                st.warning("Nenhum dado disponível.")
                st.stop()

        mes_atual_str = f"{ano_ref}-{mes_atual_num:02d}"

        # Meses anteriores
        meses_6m = []
        for i in range(1, 7):
            mes = mes_atual_num - i
            ano = ano_ref
            while mes <= 0:
                mes += 12
                ano -= 1
            meses_6m.append(f"{ano}-{mes:02d}")

        df_top_mes = df_softys[df_softys['MŒs_Ano'] == mes_atual_str]
        df_top_6m = df_softys[df_softys['MŒs_Ano'].isin(meses_6m)]

        # Função para gerar chave de agrupamento
        def gerar_chave_top(df):
            df = df.copy()
            df['Top_Key'] = df['Cliente_Coligacao'].astype(str).str.strip()
            # Ignorar coligações vazias ou "DIVERSOS"
            df.loc[df['Top_Key'].isin(['', 'nan', 'DIVERSOS', 'Diversos', 'diversos']), 'Top_Key'] = df['codigo_cliente'].astype(str)
            return df

        df_top_mes = gerar_chave_top(df_top_mes)
        df_top_6m = gerar_chave_top(df_top_6m)

        # Somas por chave
        soma_mes = df_top_mes.groupby('Top_Key')['Valor_Vendas'].sum().reset_index()
        soma_mes.columns = ['Top_Key', 'Mês Atual']
        soma_6m = df_top_6m.groupby('Top_Key')['Valor_Vendas'].sum().reset_index()
        soma_6m.columns = ['Top_Key', 'Total 6M']
        soma_6m['Média 6M'] = soma_6m['Total 6M'] / 6

        # Merge OUTER para incluir clientes sem venda no mês atual
        df_top = soma_6m[['Top_Key', 'Média 6M']].merge(soma_mes, on='Top_Key', how='left').fillna(0)
        df_top = df_top[df_top['Média 6M'] > 0]  # apenas clientes com venda no período 6M

        # Mapear rótulo
        df_label = df_base[['codigo_cliente', 'nome_cliente', 'Cliente_Coligacao']].drop_duplicates()
        df_label['Cliente_Coligacao'] = df_label['Cliente_Coligacao'].astype(str).str.strip()
        df_label.loc[df_label['Cliente_Coligacao'].isin(['', 'nan', 'DIVERSOS', 'Diversos', 'diversos']), 'Cliente_Coligacao'] = df_label['codigo_cliente'].astype(str)

        map_colig = df_label.drop_duplicates(subset=['Cliente_Coligacao']).set_index('Cliente_Coligacao')['nome_cliente'].to_dict()
        map_client = df_label.drop_duplicates(subset=['codigo_cliente']).set_index('codigo_cliente')['nome_cliente'].to_dict()

        def get_label(key):
            return map_colig.get(key, map_client.get(key, key))

        df_top['Cliente'] = df_top['Top_Key'].apply(get_label)
        df_top = df_top[['Cliente', 'Mês Atual', 'Média 6M']]

        # Ordenar pela média 6M decrescente
        df_top = df_top.sort_values('Média 6M', ascending=False).head(10)

        # Linha de total
        total_mes = df_top['Mês Atual'].sum()
        total_media = df_top['Média 6M'].sum()
        if total_media > 0:
            variacao_total = ((total_mes / total_media) - 1) * 100
        else:
            variacao_total = 0

        # Exibição formatada
        df_top_display = df_top.copy()
        df_top_display['Mês Atual'] = df_top_display['Mês Atual'].apply(formatar_numero_br)
        df_top_display['Média 6M'] = df_top_display['Média 6M'].apply(formatar_numero_br)
        df_top_display.loc['TOTAL'] = ['TOTAL', formatar_numero_br(total_mes), formatar_numero_br(total_media)]
        df_top_display.reset_index(drop=True, inplace=True)

        # Gráfico
        fig_top = go.Figure()
        fig_top.add_trace(go.Bar(
            x=df_top['Cliente'],
            y=df_top['Mês Atual'],
            name='Mês Atual',
            marker_color='#2E8B57',
            text=df_top['Mês Atual'].apply(formatar_numero_br),
            textposition='outside'
        ))
        fig_top.add_trace(go.Bar(
            x=df_top['Cliente'],
            y=df_top['Média 6M'],
            name='Média 6M',
            marker_color='#FFA000',
            text=df_top['Média 6M'].apply(formatar_numero_br),
            textposition='outside'
        ))
        fig_top.update_layout(
            title='TOP 10 Clientes - Mês Atual vs Média 6 Meses Anteriores',
            barmode='group',
            yaxis_title='Valor de Vendas',
            xaxis_title='Cliente'
        )
        st.plotly_chart(fig_top, use_container_width=True)
        st.dataframe(df_top_display, use_container_width=True, hide_index=True)

        # Batalha Naval Softys (mantida)
        st.markdown("**Batalha Naval Softys Falcon — Clientes que compraram**")
        df_softys_ano = df_softys[(df_softys['Ano'] == ano_ref) & (df_softys['MŒs'] <= mes_atual_num)]
        df_softys_clientes = df_softys_ano[['codigo_cliente', 'nome_cliente', 'Municipio',
                                            'Cliente_Coligacao', 'nome_vendedor', 'Categoria']].drop_duplicates()
        clientes_pivot = df_softys_clientes.pivot_table(
            index=['codigo_cliente', 'nome_cliente', 'Municipio', 'Cliente_Coligacao', 'nome_vendedor'],
            columns='Categoria', aggfunc='size', fill_value=0
        ).reset_index()
        cat_cols = [c for c in clientes_pivot.columns if c not in ['codigo_cliente', 'nome_cliente',
                                                                    'Municipio', 'Cliente_Coligacao', 'nome_vendedor']]
        clientes_pivot[cat_cols] = (clientes_pivot[cat_cols] > 0).astype(int)
        clientes_pivot['Total'] = clientes_pivot[cat_cols].sum(axis=1)
        with st.expander("Visualizar Batalha Naval", expanded=False):
            st.dataframe(clientes_pivot, use_container_width=True, hide_index=True, height=400)

        output_bn = BytesIO()
        with pd.ExcelWriter(output_bn, engine='openpyxl') as writer:
            clientes_pivot.to_excel(writer, index=False, sheet_name='Batalha Naval Softys')
        st.download_button("📥 Baixar Excel (Batalha Naval)", data=output_bn.getvalue(),
                           file_name=f'batalha_naval_softys_{datetime.now().strftime("%Y%m%d")}.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           use_container_width=True)
    else:
        st.warning("Nenhum dado da Softys Falcon para os filtros atuais.")
