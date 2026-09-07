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

# Esconder links do Streamlit e ajustar botões
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
    """Carrega e normaliza todos os dados do Google Sheets"""
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

    # NORMALIZAR DF_BASE
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
    missing_base = [col for col in required_base_cols if col not in df_base.columns]
    if missing_base:
        st.error(f"Colunas essenciais não encontradas no DataFrame BASE: {missing_base}")
        st.stop()

    # NORMALIZAR DF_BI
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
        elif 'valor das vendas' in col_norm:
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

def gerar_pdf_html(tabela_df, titulo):
    try:
        from weasyprint import HTML
        html_content = f"""..."""  # (mantido igual)
        # ... (código completo da função)
    except:
        return None

def aplicar_filtros_comuns(df, incluir_mes=True):
    # ... (mantido igual)

def calcular_janela_movel(df_historico, mes_selecionado, janela_meses):
    # ... (mantido igual)

# ============================================================
# FILTROS
# ============================================================
# ... (mantido igual)

# ============================================================
# APLICAR FILTROS
# ============================================================
# ... (mantido igual)

# ============================================================
# NAVEGAÇÃO
# ============================================================
# ... (mantido igual)

# ============================================================
# PÁGINA: KENVUE PERFUMARIA (CORRIGIDA)
# ============================================================
elif opcao == "🟠 Kenvue Perfumaria":
    st.subheader("🟠 Foco Estratégico: Kenvue no Canal Perfumaria")

    vendedores_kenvue = [v for v in df_base['nome_vendedor_base'].unique()
                         if vendedor_pasta.get(v) in ['PA', 'PVA']]

    df_perfumarias_ativas = df_historico_janela[
        (df_historico_janela['Canal'] == 'PERFUMARIA') &
        (df_historico_janela['nome_vendedor'].isin(vendedores_kenvue))
    ].copy()

    if not df_perfumarias_ativas.empty:
        df_kenvue_mes = df_filtrado[
            (df_filtrado['Nome_Fabricante'] == 'KENVUE') &
            (df_filtrado['Canal'] == 'PERFUMARIA') &
            (df_filtrado['nome_vendedor'].isin(vendedores_kenvue))
        ].copy()

        df_metas = df_meta_kenvue.copy()
        df_metas.columns = [str(c).strip() for c in df_metas.columns]
        col_vend_meta = next((c for c in df_metas.columns if 'vendedor' in c.lower()), None)
        col_valor_meta = next((c for c in df_metas.columns if 'meta' in c.lower()), None)
        if col_vend_meta and col_valor_meta:
            df_metas = df_metas.rename(columns={col_vend_meta: 'Vendedor', col_valor_meta: 'Meta'})
            df_metas['Vendedor'] = df_metas['Vendedor'].astype(str).str.strip()
            df_metas['Meta'] = pd.to_numeric(df_metas['Meta'], errors='coerce').fillna(0)
        else:
            df_metas = pd.DataFrame(columns=['Vendedor', 'Meta'])

        if not df_kenvue_mes.empty:
            clientes_kenvue_mes = df_kenvue_mes['codigo_cliente'].unique()
            total_perfumarias_ativas = df_perfumarias_ativas['codigo_cliente'].nunique()
            atendidos = len(clientes_kenvue_mes)
            pct_atendido = (atendidos / total_perfumarias_ativas * 100) if total_perfumarias_ativas > 0 else 0

            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Perfumarias Ativas (janela móvel)", total_perfumarias_ativas)
            col_m2.metric("Atendidas com Kenvue (mês atual)", f"{atendidos} ({pct_atendido:.1f}%)")

            realizado_por_vendedor = df_kenvue_mes.groupby('nome_vendedor')['codigo_cliente'].nunique().reset_index()
            realizado_por_vendedor.columns = ['Vendedor', 'Realizado']
            realizado_por_vendedor['Vendedor'] = realizado_por_vendedor['Vendedor'].astype(str).str.strip()

            df_meta_vendedor = df_metas.merge(realizado_por_vendedor, on='Vendedor', how='left')
            df_meta_vendedor['Realizado'] = df_meta_vendedor['Realizado'].fillna(0).astype(int)
            df_meta_vendedor['Atingimento %'] = (df_meta_vendedor['Realizado'] / df_meta_vendedor['Meta'] * 100).round(1)
            df_meta_vendedor['Atingimento %'] = df_meta_vendedor['Atingimento %'].fillna(0)
            df_meta_vendedor = df_meta_vendedor[df_meta_vendedor['Meta'] > 0]
            df_meta_vendedor = df_meta_vendedor.sort_values('Vendedor')

            # Gráfico de % de atingimento por vendedor
            fig_meta_pct = px.bar(
                df_meta_vendedor,
                x='Vendedor',
                y='Atingimento %',
                title='% de Atingimento da Meta por Vendedor',
                text='Atingimento %',
                color='Atingimento %',
                color_continuous_scale='Greens'
            )
            fig_meta_pct.update_traces(textposition='outside')
            fig_meta_pct.update_layout(yaxis_range=[0, max(120, df_meta_vendedor['Atingimento %'].max()*1.1)])
            st.plotly_chart(fig_meta_pct, use_container_width=True)

            # Tabela "Meta por Vendedor"
            vendedores_com_meta = df_meta_vendedor['Vendedor'].unique().tolist()
            lista_ken = []
            for vend in vendedores_com_meta:
                total_vend = df_perfumarias_ativas[df_perfumarias_ativas['nome_vendedor'] == vend]['codigo_cliente'].nunique()
                atend_vend = df_kenvue_mes[df_kenvue_mes['nome_vendedor'] == vend]['codigo_cliente'].nunique()
                meta_vend = df_metas[df_metas['Vendedor'] == vend]['Meta'].sum() if not df_metas.empty else 0
                pct_vend = (atend_vend / meta_vend * 100) if meta_vend > 0 else 0
                lista_ken.append({
                    'Vendedor': vend,
                    'Perfumarias Ativas': total_vend,
                    'Meta': meta_vend,
                    'Atendidas Kenvue': atend_vend,
                    '% Atingimento': round(pct_vend, 1)
                })
            df_ken_vend = pd.DataFrame(lista_ken)
            st.markdown("**Meta por Vendedor**")
            st.dataframe(df_ken_vend, use_container_width=True, hide_index=True)

            # Visão por Coordenador
            df_vend_coord = df_base[['nome_vendedor_base', 'Nome_Coordenador']].drop_duplicates()
            df_vend_coord.columns = ['Vendedor', 'Coordenador']
            df_vend_coord['Vendedor'] = df_vend_coord['Vendedor'].astype(str).str.strip()

            df_meta_coord = df_meta_vendedor.merge(df_vend_coord, on='Vendedor', how='left')
            coord_group = df_meta_coord.groupby('Coordenador').agg(
                Meta=('Meta', 'sum'),
                Realizado=('Realizado', 'sum')
            ).reset_index()
            coord_group['Atingimento %'] = (coord_group['Realizado'] / coord_group['Meta'] * 100).round(1)
            coord_group = coord_group.sort_values('Coordenador')

            fig_meta_coord = px.bar(
                coord_group,
                x='Coordenador',
                y='Atingimento %',
                title='% de Atingimento da Meta por Coordenador',
                text='Atingimento %',
                color='Atingimento %',
                color_continuous_scale='Blues'
            )
            fig_meta_coord.update_traces(textposition='outside')
            fig_meta_coord.update_layout(yaxis_range=[0, max(120, coord_group['Atingimento %'].max()*1.1)])
            st.plotly_chart(fig_meta_coord, use_container_width=True)

            st.markdown("**Meta por Coordenador**")
            st.dataframe(coord_group, use_container_width=True, hide_index=True)

            # Volume de Vendas por Coligação (Perfumaria)
            st.markdown("**Volume de Vendas por Coligação (Perfumaria)**")
            if mes_selecionado != "Todos":
                mes_num = int(mes_selecionado.split(' - ')[0])
                anos_do_mes = df_historico[df_historico['MŒs'] == mes_num]['Ano'].unique()
                ano_atual = max(anos_do_mes) if len(anos_do_mes) > 0 else df_historico['Ano'].max()
                mes_atual_str = f"{ano_atual}-{mes_num:02d}"
            else:
                mes_atual_str = df_historico['MŒs_Ano'].max() if not df_historico.empty else None

            if mes_atual_str:
                ano_atual = int(mes_atual_str.split('-')[0])
                mes_num = int(mes_atual_str.split('-')[1])
                if mes_num == 1:
                    mes_ant_num = 12
                    ano_ant = ano_atual - 1
                else:
                    mes_ant_num = mes_num - 1
                    ano_ant = ano_atual
                mes_ant_str = f"{ano_ant}-{mes_ant_num:02d}"

                df_perf_vendas = df_historico[df_historico['Canal'] == 'PERFUMARIA'].copy()
                df_vendas_mes_atual = df_perf_vendas[df_perf_vendas['MŒs_Ano'] == mes_atual_str]
                df_vendas_mes_ant = df_perf_vendas[df_perf_vendas['MŒs_Ano'] == mes_ant_str]

                if 'Valor_Vendas' in df_perf_vendas.columns:
                    vendas_atual_colig = df_vendas_mes_atual.groupby('Cliente_Coligacao')['Valor_Vendas'].sum().reset_index()
                    vendas_atual_colig.columns = ['Coligação', 'Mês Atual']
                    vendas_ant_colig = df_vendas_mes_ant.groupby('Cliente_Coligacao')['Valor_Vendas'].sum().reset_index()
                    vendas_ant_colig.columns = ['Coligação', 'Mês Anterior']
                else:
                    vendas_atual_colig = df_vendas_mes_atual.groupby('Cliente_Coligacao')['codigo_cliente'].nunique().reset_index()
                    vendas_atual_colig.columns = ['Coligação', 'Mês Atual']
                    vendas_ant_colig = df_vendas_mes_ant.groupby('Cliente_Coligacao')['codigo_cliente'].nunique().reset_index()
                    vendas_ant_colig.columns = ['Coligação', 'Mês Anterior']

                df_vol_colig = vendas_ant_colig.merge(vendas_atual_colig, on='Coligação', how='outer').fillna(0)
                df_vol_colig = df_vol_colig.sort_values('Coligação')

                fig_vol = go.Figure()
                fig_vol.add_trace(go.Bar(x=df_vol_colig['Coligação'], y=df_vol_colig['Mês Anterior'],
                                         name='Mês Anterior', marker_color='#FFA000'))
                fig_vol.add_trace(go.Bar(x=df_vol_colig['Coligação'], y=df_vol_colig['Mês Atual'],
                                         name='Mês Atual', marker_color='#2E8B57'))
                fig_vol.update_layout(title='Volume de Vendas por Coligação (Perfumaria)',
                                      barmode='group', yaxis_title='Valor de Vendas', xaxis_title='Coligação')
                st.plotly_chart(fig_vol, use_container_width=True)
                st.dataframe(df_vol_colig, use_container_width=True, hide_index=True)

            # Listas Chegamos / Não Chegamos
            clientes_nao_atendidos = [c for c in df_perfumarias_ativas['codigo_cliente'].unique()
                                      if c not in clientes_kenvue_mes]
            df_base_kenvue = df_base[df_base['nome_vendedor_base'].isin(vendedores_kenvue)]
            df_base_kenvue = df_base_kenvue.drop_duplicates(subset=['codigo_cliente'], keep='first')

            col_ken1, col_ken2 = st.columns(2)
            with col_ken1:
                st.markdown(f"✅ **Chegamos** ({atendidos})")
                df_chegamos = df_kenvue_mes[
                    ['codigo_cliente', 'nome_cliente', 'Municipio', 'Cliente_Coligacao', 'nome_vendedor']
                ].drop_duplicates()
                df_chegamos.columns = ['Código', 'Nome', 'Município', 'Coligação', 'Vendedor']
                st.dataframe(df_chegamos, use_container_width=True, hide_index=True)

                output_cheg = BytesIO()
                with pd.ExcelWriter(output_cheg, engine='openpyxl') as writer:
                    df_chegamos.to_excel(writer, index=False, sheet_name='Chegamos')
                st.download_button("📥 Baixar Excel (Chegamos)", data=output_cheg.getvalue(),
                                   file_name=f'kenvue_chegamos_{datetime.now().strftime("%Y%m%d")}.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   use_container_width=True)

            with col_ken2:
                st.markdown(f"❌ **Não chegamos** ({len(clientes_nao_atendidos)})")
                df_nao = df_base_kenvue[df_base_kenvue['codigo_cliente'].isin(clientes_nao_atendidos)][
                    ['codigo_cliente', 'nome_cliente', 'Municipio', 'Cliente_Coligacao', 'nome_vendedor_base']
                ]
                df_nao.columns = ['Código', 'Nome', 'Município', 'Coligação', 'Vendedor']
                st.dataframe(df_nao, use_container_width=True, hide_index=True)

            # Downloads restantes
            output_kenv = BytesIO()
            with pd.ExcelWriter(output_kenv, engine='openpyxl') as writer:
                df_ken_vend.to_excel(writer, index=False, sheet_name='Meta Kenvue Vendedor')
            st.download_button("📥 Baixar Excel (Meta por Vendedor)", data=output_kenv.getvalue(),
                               file_name=f'kenvue_meta_vendedor_{datetime.now().strftime("%Y%m%d")}.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                               use_container_width=True)

            output_kenc = BytesIO()
            with pd.ExcelWriter(output_kenc, engine='openpyxl') as writer:
                coord_group.to_excel(writer, index=False, sheet_name='Meta Kenvue Coordenador')
            st.download_button("📥 Baixar Excel (Meta por Coordenador)", data=output_kenc.getvalue(),
                               file_name=f'kenvue_meta_coordenador_{datetime.now().strftime("%Y%m%d")}.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                               use_container_width=True)
        else:
            st.warning("Nenhuma venda de Kenvue no mês atual para o canal Perfumaria.")
    else:
        st.warning("Nenhuma perfumaria ativa na janela móvel para os vendedores elegíveis (PA/PVA).")

# ... (demais páginas permanecem as mesmas)
