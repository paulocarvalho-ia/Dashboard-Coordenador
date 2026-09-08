import streamlit as st
import pandas as pd
from urllib.parse import quote

st.set_page_config(page_title="Diagnóstico", layout="wide")

SHEET_ID = "100LtVtmS76bT2CJd-EIb-bHTgX3F1BVm8Er5vUa-VYQ"

@st.cache_data(ttl=300)
def load_raw():
    url_base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="
    try:
        df_base = pd.read_csv(url_base + quote("BASE"))
        df_bi = pd.read_csv(url_base + quote("BI"))
        return df_base, df_bi
    except Exception as e:
        st.error(f"Erro: {e}")
        return None, None

df_base, df_bi = load_raw()

if df_bi is None:
    st.stop()

st.subheader("Aba BI - primeiras linhas")
st.dataframe(df_bi.head())

st.subheader("Colunas da aba BI")
st.write(list(df_bi.columns))

st.subheader("Verificando valores de 'Valor Venda' (ou similar) e meses")
# Tenta identificar coluna de valor e mês
col_valor = [c for c in df_bi.columns if 'valor' in c.lower() and ('venda' in c.lower() or 'vendas' in c.lower())]
col_mes = [c for c in df_bi.columns if 'ano' in c.lower() and 'mes' in c.lower()]

if col_valor and col_mes:
    col_valor = col_valor[0]
    col_mes = col_mes[0]
    st.write(f"Coluna valor: {col_valor}")
    st.write(f"Coluna mês: {col_mes}")

    # Filtrar Softys Falcon (se coluna fabricante existir)
    col_fab = [c for c in df_bi.columns if 'fabricante' in c.lower()]
    if col_fab:
        df_softys = df_bi[df_bi[col_fab[0]].str.upper() == 'SOFTYS FALCON'].copy()
    else:
        df_softys = df_bi.copy()

    st.subheader("Linhas Softys Falcon (primeiras 5)")
    st.dataframe(df_softys.head())

    # Mostrar meses únicos
    meses_unicos = sorted(df_softys[col_mes].astype(str).unique())
    st.write("Meses únicos (valores originais):", meses_unicos)

    # Mostrar soma por mês crua (valores como texto)
    if len(df_softys) > 0:
        st.subheader("Soma por mês (valores crus, sem conversão)")
        # Apenas agrupa e soma se os valores forem numéricos; senão, mostra contagem
        try:
            df_softys[col_valor] = pd.to_numeric(df_softys[col_valor].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce')
            soma_mes = df_softys.groupby(col_mes)[col_valor].sum().reset_index()
            st.dataframe(soma_mes)
        except:
            st.warning("Não foi possível converter valores automaticamente.")
            st.dataframe(df_softys[[col_mes, col_valor]].head(20))
else:
    st.error("Não foi possível identificar colunas de valor e mês automaticamente.")
