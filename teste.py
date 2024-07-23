#pip install streamlit pandas plotly-express

import pandas as pd
import os, sys
import re
import decimal
import warnings
import pymssql
import unidecode
import locale
import psycopg2, csv
import streamlit as st
import plotly.express as px

from decimal import *
from datetime import date, time, timedelta, datetime
from psycopg2.extras import RealDictCursor
from collections import OrderedDict

locale.setlocale(locale.LC_TIME, 'pt_BR')
getcontext().prec = 40
warnings.simplefilter(action = 'ignore', category = UserWarning)

dataInicio: date = datetime.strptime('2024-01-01', r'%Y-%m-%d')
dataFim: date = datetime.strptime('2024-04-30', r'%Y-%m-%d')
mostrarValorZero: int = 1
mostrarCusto: int = 1
tenant: str = 'usr102228nhpdr'

# Configurar o layout da pÃ¡gina
st.set_page_config(layout="wide")

try:
  conexaoSQL = psycopg2.connect(
    host = "localhost",
    dbname = "econt",
    user = "postgres",
    password = "mabel",
    port = 5432
  )
except:
  print(f"Verifique dados de conexÃ£o com o servidor")
  exit(1)

#cursor = conexao.cursor(cursor_factory = RealDictCursor)
consulta = f"""
select 
pessoas.nome_completo as pessoa_nome, 
pessoas.tipo as pessoa_tipo, 
pessoas.cidade as pessoa_cidade, 
pessoas.acronimo_estado as pessoa_estado, 
titulos.value::numeric(40, 2) as titulo_valor, 
titulos.title_number as titulo_numero, 
titulos.release_type as titulo_tipo, 
titulos.issue_date as titulo_emissao

from {tenant}.title_releases titulos

inner join public.vwPerson(
  tenant := '{tenant}',
  param_pessoa_id := ('{{' || titulos.person_id::text || '}}')::int8[],
  param_endereco_id := ('{{' || titulos.address_id::text || '}}')::int8[]
) pessoas
  on pessoas.id_person = titulos.person_id

where titulos.issue_date between %s and %s
order by titulos.id desc
"""

df1 = pd.read_sql_query(
  sql = consulta,
  con = conexaoSQL,
  params = (dataInicio, dataFim)
)

#dfEmissao = df1.groupby(['titulo_emissao'])['titulo_valor'].sum().reset_index()
#print(dfEmissao)

# Troca o tipo de dados da coluna
df1['titulo_emissao'] = pd.to_datetime(df1['titulo_emissao'])
df1.sort_values('titulo_emissao')
#Cria uma nova coluna, composta por ano + mÃªs da data, calculada com funÃ§Ã£o anÃ´nima
df1['ano_mes'] = df1['titulo_emissao'].apply(lambda x: f'{x.year:04d}' + '-' + f'{x.month:02d}')
filtroMes = st.sidebar.selectbox('Escolha o mÃªs de emissÃ£o', df1['ano_mes'].unique())
filtroUF = st.sidebar.selectbox('Escolha o estado', df1['pessoa_estado'].unique())
#filtroDia = st.sidebar.selectbox('Esolha o dia de emissÃ£o', df1['titulo_emissao'].unique())
#dfFiltrado = df1[df1['titulo_emissao'] == filtroDia]
dfFiltrado = df1[df1['ano_mes'] == filtroMes]
dfFiltrado = dfFiltrado[dfFiltrado['pessoa_estado'] == filtroUF]

col1, col2 = st.columns(2)
col3, col4, col5 = st.columns(3)

#Passando um dataframe agrupado, resolve o problema de ficar gerando bloquinhos/linhas no meio das barras.
#essas linhas no meio das barras sÃ£o os dados soltos
graf1 = px.bar(
  dfFiltrado.groupby(
    by = ['titulo_emissao', 'titulo_tipo']).sum().reset_index(), 
    x = 'titulo_emissao', 
    y = 'titulo_valor', 
    color = 'titulo_tipo', 
    title = 'Faturamento por dia'
)
#graf2 = px.pie(dfFiltrado, values = 'titulo_valor', names = 'pessoa_estado', title = 'Faturamento por UF')
graf2 = px.bar(dfFiltrado, x = 'pessoa_estado', y = 'titulo_valor', color = 'titulo_tipo', title = 'Faturamento por UF')

dfTotalPessoa = dfFiltrado.groupby(['pessoa_nome'])['titulo_valor'].sum().reset_index()

df3Pessoas = dfTotalPessoa.nlargest(5, ['titulo_valor'], keep = 'last').reset_index()
df3Pessoas.sort_values(by = ['titulo_valor'], ascending = False)
df3Pessoas = df3Pessoas.drop(columns = ['index'])

filtro = df3Pessoas
# ~ quer dizer "NOT"
dfOutrasPessoas = dfFiltrado[~dfFiltrado['pessoa_nome'].isin(df3Pessoas['pessoa_nome'])]
valorOutros = dfOutrasPessoas['titulo_valor'].sum()
dados = {
  'pessoa_nome': ['Outros'],
  'titulo_valor': [valorOutros]
}
dfOutrasPessoas = pd.DataFrame(
  data = dados
)

#dfOutrasPessoas = pd.concat([df3Pessoas, dfOutrasPessoas])
#print(dfOutrasPessoas)
#graf3 = px.bar(df3Pessoas, x = 'pessoa_nome', y = 'titulo_valor', color = 'titulo_tipo', title = 'Faturamento por pessoa')
graf3 = px.pie(
  df3Pessoas.merge(dfOutrasPessoas, how = 'outer'), 
  title = 'Faturamento por pessoa', 
  names = 'pessoa_nome', 
  values = 'titulo_valor'
)
col1.plotly_chart(graf1, use_container_width = True)
tab1, tab2 = col2.tabs(['GrÃ¡fico por UF', 'GrÃ¡fico por pessoa'])
with tab1:
  st.plotly_chart(graf2, use_container_width = True)
with tab2:
  st.plotly_chart(graf3, use_container_width = True)


#st.write(dfFiltrado)
st.write(dfTotalPessoa)
st.dataframe(
  df3Pessoas, 
  column_config = {
    'pessoa_nome': st.column_config.TextColumn(
      'Pessoa', 
      help = 'RazÃ£o social',
      width = 300
    ),
    'titulo_valor': st.column_config.NumberColumn(
      'Soma dos tÃ­tulos', 
      help = 'Valor do tÃ­tulo',
      format = 'R$ %.2f'
    ),
  }
)
st.write(dfOutrasPessoas)

map_data = pd.DataFrame(
  {
    'lat': {
      '0': -19.8516758,
      '1': -19.85495
    },
    'lon': {
      '0': -44.5784332,
      '1': -44.5983913
    }
  },
  columns=['lat', 'lon']
)

st.map(map_data)
#st.write(df3Pessoas.merge(dfOutrasPessoas, how = 'outer'))
conexaoSQL.close()
