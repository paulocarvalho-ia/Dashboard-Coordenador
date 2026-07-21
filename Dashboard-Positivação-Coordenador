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
COMPILATION_DATE = "21/07/2025 10:00"  # ⚠️ Atualize manualmente a cada deploy

# ============================================================
# CONEXÃO COM GOOGLE SHEETS
# ============================================================
SHEET_ID = "100LtVtmS76bT2CJd-EIb-bHTgX3F1BVm8Er5vUa-VYQ"

@st.cache_data(ttl=300)
def load_data():
    url_base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="

    df_base = pd.read_csv(url_base + "BASE")
    df_bi = pd.read_csv(url_base + "BI")

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

    # Merge (BASE + BI)
    df_merged = df_bi.merge(
        df_base[['codigo_cliente', 'nome_cliente', 'nome_vendedor_base', 'Cliente_Coligacao', 'Nome_Coordenador']],
        left_on=['codigo_cliente', 'nome_vendedor_bi'],
        right_on=['codigo_cliente', 'nome_vendedor_base'],
        how='left'
    )
    # Fallback
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
    return df_base, df_bi, df_merged, data_dados

if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

df_base, df_bi, df_merged, data_dados = load_data()

# ============================================================
# LISTA DE INDÚSTRIAS
# ============================================================
INDUSTRIAS = sorted(df_bi['Nome_Fabricante'].dropna().unique())
INDUSTRIAS = [i for i in INDUSTRIAS if i.strip() != '']
TOTAL_INDUSTRIAS = len(INDUSTRIAS)

# ============================================================
# FILTROS (COORDENADOR, VENDEDOR OPCIONAL)
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
    for key in ['coordenador', 'vendedor', 'coligacao', 'ano', 'mes', 'industria_filtro', 'modo_gap']:
        st.session_state.pop(key, None)

# Coordenador
lista_coordenadores = ["Todos"] + sorted(df_base['Nome_Coordenador'].dropna().unique().tolist())
if 'coordenador' not in st.session_state:
    st.session_state['coordenador'] = 'Todos'
if st.session_state['coordenador'] not in lista_coordenadores:
    st.session_state['coordenador'] = 'Todos'
coordenador_selecionado = st.sidebar.selectbox(
    "Coordenador", lista_coordenadores,
    index=lista_coordenadores.index(st.session_state['coordenador']),
    key='coordenador_select'
)
st.session_state['coordenador'] = coordenador_selecionado

# Vendedor (dependente do coordenador)
if coordenador_selecionado != "Todos":
    vendedores_filtrados = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].dropna().unique()
else:
    vendedores_filtrados = df_base['nome_vendedor_base'].dropna().unique()

lista_vendedores = ["Todos"] + sorted(vendedores_filtrados.tolist())
if 'vendedor' not in st.session_state:
    st.session_state['vendedor'] = 'Todos'
if st.session_state['vendedor'] not in lista_vendedores:
    st.session_state['vendedor'] = 'Todos'
vendedor_selecionado = st.sidebar.selectbox(
    "Vendedor", lista_vendedores,
    index=lista_vendedores.index(st.session_state['vendedor']),
    key='vendedor_select'
)
st.session_state['vendedor'] = vendedor_selecionado

# Coligação
if vendedor_selecionado != "Todos":
    clientes_do_vendedor = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].unique()
    coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_vendedor)]['Cliente_Coligacao'].dropna().unique()
elif coordenador_selecionado != "Todos":
    vendedores_do_coord = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].unique()
    clientes_do_coord = df_base[df_base['nome_vendedor_base'].isin(vendedores_do_coord)]['codigo_cliente'].unique()
    coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_coord)]['Cliente_Coligacao'].dropna().unique()
else:
    coligacoes_filtradas = df_base['Cliente_Coligacao'].dropna().unique()

lista_coligacoes = ["Todas"] + sorted(coligacoes_filtradas.tolist())
if 'coligacao' not in st.session_state:
    st.session_state['coligacao'] = 'Todas'
if st.session_state['coligacao'] not in lista_coligacoes:
    st.session_state['coligacao'] = 'Todas'
coligacao_selecionada = st.sidebar.selectbox(
    "Coligação", lista_coligacoes,
    index=lista_coligacoes.index(st.session_state['coligacao']),
    key='coligacao_select'
)
st.session_state['coligacao'] = coligacao_selecionada

# Ano, Mês, Indústria e Modo GAP
anos_disponiveis = sorted(df_merged['Ano'].dropna().unique())
lista_anos = ["Todos"] + [str(int(a)) for a in anos_disponiveis]
if 'ano' not in st.session_state: st.session_state['ano'] = 'Todos'
ano_selecionado = st.sidebar.selectbox("Ano", lista_anos, index=lista_anos.index(st.session_state['ano']), key='ano_select')
st.session_state['ano'] = ano_selecionado

if ano_selecionado != "Todos":
    meses_disponiveis = sorted(df_merged[df_merged['Ano'] == int(ano_selecionado)]['Mês'].dropna().unique())
else:
    meses_disponiveis = sorted(df_merged['Mês'].dropna().unique())
meses_nomes = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
lista_meses = ["Todos"] + [f"{int(m):02d} - {meses_nomes[int(m)]}" for m in meses_disponiveis]
if 'mes' not in st.session_state: st.session_state['mes'] = 'Todos'
mes_selecionado = st.sidebar.selectbox("Mês", lista_meses, index=lista_meses.index(st.session_state['mes']), key='mes_select')
st.session_state['mes'] = mes_selecionado

st.sidebar.divider()
st.sidebar.header("🏭 Filtro por Indústria")
lista_industrias_filtro = ["Todas"] + INDUSTRIAS
if 'industria_filtro' not in st.session_state: st.session_state['industria_filtro'] = 'Todas'
industria_filtro = st.sidebar.selectbox("Indústria", lista_industrias_filtro, index=lista_industrias_filtro.index(st.session_state['industria_filtro']), key='industria_select')
st.session_state['industria_filtro'] = industria_filtro

if 'modo_gap' not in st.session_state: st.session_state['modo_gap'] = False
modo_gap = st.sidebar.checkbox("🔍 Mostrar apenas NÃO positivadas (GAP)", value=st.session_state['modo_gap'], key='modo_gap_check')
st.session_state['modo_gap'] = modo_gap

# ============================================================
# APLICAR FILTROS
# ============================================================
df_filtrado = df_merged.copy()
if coordenador_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Nome_Coordenador'] == coordenador_selecionado]
if vendedor_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['nome_vendedor'] == vendedor_selecionado]
if coligacao_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Cliente_Coligacao'] == coligacao_selecionada]
if ano_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Ano'] == int(ano_selecionado)]
if mes_selecionado != "Todos":
    mes_num = int(mes_selecionado.split(' - ')[0])
    df_filtrado = df_filtrado[df_filtrado['Mês'] == mes_num]
if industria_filtro != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Nome_Fabricante'] == industria_filtro]

# ============================================================
# CARTEIRA ATIVA (MELHORIA 1)
# ============================================================
# Clientes únicos que compraram em qualquer época (histórico completo) sob o coordenador/vendedor selecionado
df_historico = df_merged.copy()
if coordenador_selecionado != "Todos":
    df_historico = df_historico[df_historico['Nome_Coordenador'] == coordenador_selecionado]
if vendedor_selecionado != "Todos":
    df_historico = df_historico[df_historico['nome_vendedor'] == vendedor_selecionado]

carteira_ativa_total = df_historico[df_historico['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()

# Positivados no período selecionado
positivados_periodo = df_filtrado[df_filtrado['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
pct_ativa = (positivados_periodo / carteira_ativa_total * 100) if carteira_ativa_total > 0 else 0

# Clientes ativos que NÃO compraram no período
clientes_ativos_ids = df_historico[df_historico['Nome_Fabricante'].notna()]['codigo_cliente'].unique()
clientes_positivados_ids = df_filtrado[df_filtrado['Nome_Fabricante'].notna()]['codigo_cliente'].unique()
clientes_sem_venda_ativos = [c for c in clientes_ativos_ids if c not in clientes_positivados_ids]

st.subheader("📅 Carteira Ativa")
col_a1, col_a2, col_a3 = st.columns(3)
col_a1.metric("📅 Carteira Ativa Total (histórico)", carteira_ativa_total)
col_a2.metric("✅ Positivados no Período", positivados_periodo)
col_a3.metric("📈 % Positivação (Carteira Ativa)", f"{pct_ativa:.1f}%")

col_a4, _ = st.columns(2)
col_a4.metric("🔴 Clientes sem venda no período", len(clientes_sem_venda_ativos))
if len(clientes_sem_venda_ativos) > 0:
    with st.expander("👁️ Ver lista de clientes sem venda (Carteira Ativa)"):
        df_sem_venda_ativos = df_base[(df_base['codigo_cliente'].isin(clientes_sem_venda_ativos))][['codigo_cliente', 'nome_cliente', 'Cliente_Coligacao']]
        df_sem_venda_ativos.columns = ['Código', 'Nome', 'Coligação']
        st.dataframe(df_sem_venda_ativos, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# MÉTRICAS - CARTEIRA TOTAL
# ============================================================
# Base da carteira total: clientes da base dos vendedores/coordenador selecionados
if vendedor_selecionado != "Todos":
    total_clientes_base = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].nunique()
elif coordenador_selecionado != "Todos":
    vendedores_do_coord = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].unique()
    total_clientes_base = df_base[df_base['nome_vendedor_base'].isin(vendedores_do_coord)]['codigo_cliente'].nunique()
else:
    total_clientes_base = df_base['codigo_cliente'].nunique()

total_positivados = len(clientes_positivados_ids)
pct_total = (total_positivados / total_clientes_base * 100) if total_clientes_base > 0 else 0

cobertura_media = df_filtrado.groupby('codigo_cliente')['Nome_Fabricante'].nunique().mean()
cobertura_total = df_filtrado[['codigo_cliente', 'Nome_Fabricante']].dropna().drop_duplicates().shape[0]

# Clientes da carteira total sem venda no período
todos_ids_carteira = df_base['codigo_cliente'].unique()  # simplificado: todos da base
if vendedor_selecionado != "Todos":
    todos_ids_carteira = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].unique()
elif coordenador_selecionado != "Todos":
    vendedores_do_coord = df_base[df_base['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor_base'].unique()
    todos_ids_carteira = df_base[df_base['nome_vendedor_base'].isin(vendedores_do_coord)]['codigo_cliente'].unique()

clientes_sem_venda_carteira = [c for c in todos_ids_carteira if c not in clientes_positivados_ids]

st.subheader("📋 Carteira Total")
col1, col2, col3 = st.columns(3)
col1.metric("📋 Clientes na Carteira", total_clientes_base)
col2.metric("✅ Clientes Positivados", total_positivados)
col3.metric("📈 % Positivação (Carteira Total)", f"{pct_total:.1f}%")

col4, col5 = st.columns(2)
col4.metric("📊 Cobertura Média", f"{cobertura_media:.1f} ind/cliente")
col5.metric("🏭 Cobertura Total", f"{cobertura_total} coberturas")

col6, _ = st.columns(2)
col6.metric("🔴 Clientes sem venda no período (Carteira Total)", len(clientes_sem_venda_carteira))
if len(clientes_sem_venda_carteira) > 0:
    with st.expander("👁️ Ver lista de clientes sem venda (Carteira Total)"):
        df_sem_venda_total = df_base[df_base['codigo_cliente'].isin(clientes_sem_venda_carteira)][['codigo_cliente', 'nome_cliente', 'Cliente_Coligacao']]
        df_sem_venda_total.columns = ['Código', 'Nome', 'Coligação']
        st.dataframe(df_sem_venda_total, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# VISÃO MENSAL
# ============================================================
st.subheader("📅 Evolução Mensal")

df_mensal = df_merged.copy()
if coordenador_selecionado != "Todos":
    df_mensal = df_mensal[df_mensal['Nome_Coordenador'] == coordenador_selecionado]
if vendedor_selecionado != "Todos":
    df_mensal = df_mensal[df_mensal['nome_vendedor'] == vendedor_selecionado]
if coligacao_selecionada != "Todas":
    df_mensal = df_mensal[df_mensal['Cliente_Coligacao'] == coligacao_selecionada]
if ano_selecionado != "Todos":
    df_mensal = df_mensal[df_mensal['Ano'] == int(ano_selecionado)]
if industria_filtro != "Todas":
    df_mensal = df_mensal[df_mensal['Nome_Fabricante'] == industria_filtro]

base_fixa = total_clientes_base  # usa a mesma base da carteira total

evolucao_list = []
meses_ordenados = sorted(df_mensal['Mês_Ano'].dropna().unique())
for mes in meses_ordenados:
    df_mes = df_mensal[df_mensal['Mês_Ano'] == mes]
    clientes_pos = df_mes[df_mes['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
    cobertura_mes = df_mes.groupby('codigo_cliente')['Nome_Fabricante'].nunique()
    cobertura_media_mes = cobertura_mes.mean() if len(cobertura_mes) > 0 else 0
    cobertura_total_mes = df_mes[['codigo_cliente', 'Nome_Fabricante']].dropna().drop_duplicates().shape[0]
    evolucao_list.append({
        'Mês_Ano': mes,
        'Clientes_Positivados': clientes_pos,
        '%_Positivação': round((clientes_pos / base_fixa * 100), 1) if base_fixa > 0 else 0,
        'Cobertura_Media': round(cobertura_media_mes, 2),
        'Cobertura_Total': cobertura_total_mes
    })

evolucao = pd.DataFrame(evolucao_list)
if len(evolucao) > 0:
    col1, col2 = st.columns(2)
    with col1:
        fig_evo = go.Figure()
        fig_evo.add_trace(go.Bar(x=evolucao['Mês_Ano'], y=evolucao['%_Positivação'], text=[f'{v:.1f}%' for v in evolucao['%_Positivação']],
                                 textposition='outside', marker=dict(color=evolucao['%_Positivação'], colorscale='Greens', showscale=False)))
        fig_evo.update_layout(title='% de Positivação por Mês', xaxis_title="", yaxis_title="% Positivação", yaxis_range=[0,105],
                              xaxis=dict(type='category', categoryorder='array', categoryarray=meses_ordenados))
        st.plotly_chart(fig_evo, use_container_width=True)
    with col2:
        fig_evo2 = go.Figure()
        fig_evo2.add_trace(go.Scatter(x=evolucao['Mês_Ano'], y=evolucao['Cobertura_Media'], mode='lines+markers+text',
                                      text=[f'{v:.2f}' for v in evolucao['Cobertura_Media']], textposition='top center',
                                      line=dict(color='blue', width=3), marker=dict(size=10)))
        fig_evo2.update_layout(title='Cobertura Média por Mês', xaxis_title="", yaxis_title="Cobertura Média",
                               yaxis_range=[0, max(evolucao['Cobertura_Media'])*1.2 if len(evolucao)>0 else 1],
                               xaxis=dict(type='category', categoryorder='array', categoryarray=meses_ordenados))
        st.plotly_chart(fig_evo2, use_container_width=True)
    st.dataframe(evolucao, use_container_width=True, hide_index=True)
else:
    st.warning("Sem dados para evolução mensal.")

st.divider()

# ============================================================
# RELATÓRIO BATALHA NAVAL (NOME ALTERADO)
# ============================================================
st.subheader("📋 Relatório Batalha Naval")

matriz = df_filtrado.pivot_table(index='codigo_cliente', columns='Nome_Fabricante', aggfunc='size', fill_value=0)
mapa_nomes = df_filtrado[['codigo_cliente', 'nome_cliente']].drop_duplicates('codigo_cliente')
mapa_nomes_dict = dict(zip(mapa_nomes['codigo_cliente'], mapa_nomes['nome_cliente']))

matriz_bin = (matriz > 0).astype(int)
matriz_bin['Nome_Cliente'] = matriz.index.map(lambda x: mapa_nomes_dict.get(x, 'N/A'))
matriz_bin['Total_Indústrias'] = matriz_bin.drop(columns=['Nome_Cliente']).sum(axis=1)
matriz_bin = matriz_bin.reset_index().rename(columns={'codigo_cliente': 'Código'})

colunas_fabricantes = [c for c in matriz_bin.columns if c not in ['Código', 'Nome_Cliente', 'Total_Indústrias']]
matriz_bin = matriz_bin[['Código', 'Nome_Cliente'] + colunas_fabricantes + ['Total_Indústrias']]

st.metric("📊 Total de Clientes no Relatório", len(matriz_bin))

col1, col2, col3 = st.columns(3)
with col1:
    csv = matriz_bin.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar CSV", data=csv, file_name=f'positivacao_{datetime.now().strftime("%Y%m%d")}.csv', mime='text/csv', use_container_width=True)
with col2:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        matriz_bin.to_excel(writer, index=False, sheet_name='Batalha Naval')
    st.download_button("📥 Baixar Excel", data=output.getvalue(), file_name=f'batalha_naval_{datetime.now().strftime("%Y%m%d")}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
with col3:
    html_pdf = f"""
    <html><head><meta charset="UTF-8"><style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ text-align: center; color: #1a3a4a; font-size: 18px; }}
        h2 {{ text-align: center; color: #666; font-size: 12px; font-weight: normal; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 8px; }}
        th {{ background-color: #1a3a4a; color: white; padding: 6px 4px; text-align: center; }}
        td {{ padding: 4px; text-align: center; border: 1px solid #ddd; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .positivo {{ background-color: #0F5220; color: white; }}
        .negativo {{ background-color: #8B0000; color: white; }}
        .footer {{ text-align: center; font-size: 10px; color: #999; margin-top: 20px; }}
    </style></head><body>
        <h1>Relatório Batalha Naval</h1>
        <h2>4 Elos Distribuidora Ltda. - Centro de Custo 622 | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</h2>
        <table><thead><tr><th>Código</th><th>Cliente</th>"""
    for col in colunas_fabricantes:
        html_pdf += f"<th>{col}</th>"
    html_pdf += "<th>Total</th></tr></thead><tbody>"
    for _, row in matriz_bin.iterrows():
        html_pdf += "<tr>"
        html_pdf += f"<td>{row['Código']}</td><td style='text-align:left;'>{row['Nome_Cliente']}</td>"
        for col in colunas_fabricantes:
            valor = row[col]
            classe = "positivo" if valor == 1 else "negativo"
            html_pdf += f"<td class='{classe}'>{valor}</td>"
        html_pdf += f"<td><strong>{row['Total_Indústrias']}</strong></td></tr>"
    html_pdf += f"</tbody></table><div class='footer'>4 Elos Distribuidora Ltda. - Centro de Custo 622 | Total: {len(matriz_bin)} clientes | Cobertura Total: {matriz_bin['Total_Indústrias'].sum()} coberturas</div></body></html>"
    st.download_button("📥 Baixar PDF (HTML)", data=html_pdf.encode('utf-8'), file_name=f'batalha_naval_{datetime.now().strftime("%Y%m%d")}.html', mime='text/html', use_container_width=True)
    st.caption("💡 Abra o arquivo HTML e salve como PDF (Ctrl+P)")

with st.expander("👁️ Visualizar tabela"):
    st.dataframe(matriz_bin, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# FICHA DO CLIENTE
# ============================================================
st.subheader("🔍 Ficha do Cliente")

try:
    df_clientes_unicos = df_filtrado[['codigo_cliente', 'nome_cliente']].drop_duplicates().dropna()
    df_clientes_unicos['cliente_label'] = df_clientes_unicos['codigo_cliente'].astype(str) + ' - ' + df_clientes_unicos['nome_cliente'].astype(str)
    lista_clientes = sorted(df_clientes_unicos['cliente_label'].unique())
except:
    lista_clientes = []

if lista_clientes:
    cliente_sel = st.selectbox("Selecione um cliente:", lista_clientes, key='ficha_cliente')
    if cliente_sel:
        codigo = cliente_sel.split(' - ')[0].strip()
        df_cliente = df_filtrado[df_filtrado['codigo_cliente'].astype(str).str.strip() == codigo]
        if not df_cliente.empty:
            st.write(f"**Código:** {codigo}")
            st.write(f"**Nome:** {df_cliente['nome_cliente'].iloc[0]}")
            st.write(f"**Coligação:** {df_cliente['Cliente_Coligacao'].iloc[0]}")
            st.write(f"**Vendedor:** {df_cliente['nome_vendedor'].iloc[0]}")
            st.write(f"**Coordenador:** {df_cliente['Nome_Coordenador'].iloc[0]}")

            st.write("**Positivação por Indústria e Mês:**")
            meses_disp = sorted(df_cliente['Mês_Ano'].dropna().unique())
            if meses_disp:
                tabela = []
                for ind in INDUSTRIAS:
                    linha = {'Indústria': ind}
                    for m in meses_disp:
                        linha[m] = '✅' if ((df_cliente['Nome_Fabricante'] == ind) & (df_cliente['Mês_Ano'] == m)).any() else '❌'
                    linha['Total'] = sum(1 for m in meses_disp if linha[m] == '✅')
                    tabela.append(linha)
                df_tab = pd.DataFrame(tabela)
                st.dataframe(df_tab, use_container_width=True, hide_index=True)
                pos_industrias = sum(1 for l in tabela if l['Total'] > 0)
                st.metric("Indústrias Positivadas", f"{pos_industrias} de {TOTAL_INDUSTRIAS}")
                st.metric("Cobertura Total do Cliente", df_cliente[['codigo_cliente', 'Nome_Fabricante']].dropna().drop_duplicates().shape[0])
            else:
                st.warning("Nenhum dado mensal.")
        else:
            st.warning("Cliente não encontrado.")
else:
    st.warning("Nenhum cliente encontrado.")

# ============================================================
# RODAPÉ
# ============================================================
st.divider()
col1, col2 = st.columns(2)
col1.caption(f"📅 Dashboard compilado em: {COMPILATION_DATE}")
col2.caption(f"📊 Dados carregados em: {data_dados}")
