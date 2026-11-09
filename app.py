import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Transporte e Mobilidade Urbana",
    layout="wide",
    page_icon="🚌"
)

@st.cache_data
def carregar_dados_transporte(caminho_arquivo):
    xls = pd.ExcelFile(caminho_arquivo)
    df_raw = pd.read_excel(xls, sheet_name="BR GR UF MU")

    racas = ["Branca"] * 6 + ["Preta ou Parda"] * 6 + ["Indígena"] * 6
    modais = [
        "A pé", "Bicicleta", "Motocicleta ou Mototaxi", 
        "Automóvel, taxi ou assemelhados", "Transporte coletivo", "Outros"
    ] * 3
    
    col_names = ["Localidade"] + [f"{r} - {m}" for r, m in zip(racas, modais)]

    df_clean = df_raw.iloc[2:].copy()
    df_clean.columns = col_names
    df_clean = df_clean.dropna(subset=["Localidade"])
    df_clean["Localidade"] = df_clean["Localidade"].astype(str).str.strip()

    for col in col_names[1:]:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    df_long = df_clean.melt(
        id_vars=["Localidade"],
        var_name="Raca_Modal",
        value_name="Percentual"
    )

    df_long[["Raça", "Meio de Transporte"]] = df_long["Raca_Modal"].str.split(" - ", expand=True)
    df_long.drop(columns=["Raca_Modal"], inplace=True)

    def categorizar_modal(modal):
        if modal in ["Transporte coletivo"]:
            return "Público (Ônibus/Metrô)"
        elif modal in ["Automóvel, taxi ou assemelhados", "Motocicleta ou Mototaxi"]:
            return "Particular (Carro/Moto)"
        elif modal in ["A pé", "Bicicleta"]:
            return "Ativo (Bicicleta/Pé)"
        return "Outros"

    df_long["Tipo de Modal"] = df_long["Meio de Transporte"].apply(categorizar_modal)
    
    return df_long

caminho_arquivo = "Tabela_13_Meio_de_transporte.xlsx"

try:
    df_transporte = carregar_dados_transporte(caminho_arquivo)

    st.sidebar.header("🔍 Filtros de Análise")

    localidades_disponiveis = df_transporte["Localidade"].unique().tolist()
    localidade_selecionada = st.sidebar.selectbox(
        "Selecione a Região Metro / UF / Localidade:",
        options=localidades_disponiveis,
        index=0 
    )

    modais_disponiveis = df_transporte["Meio de Transporte"].unique().tolist()
    modais_selecionados = st.sidebar.multiselect(
        "Selecione o Meio de Transporte:",
        options=modais_disponiveis,
        default=modais_disponiveis
    )

    tipos_modais = df_transporte["Tipo de Modal"].unique().tolist()
    tipos_selecionados = st.sidebar.multiselect(
        "Selecione a Categoria de Modal:",
        options=tipos_modais,
        default=tipos_modais
    )

    df_filtrado = df_transporte[
        (df_transporte["Localidade"] == localidade_selecionada) &
        (df_transporte["Meio de Transporte"].isin(modais_selecionados)) &
        (df_transporte["Tipo de Modal"].isin(tipos_selecionados))
    ]

    st.title("🚗 Transporte e Mobilidade Urbana")
    st.markdown(f"Análise dos modais de transporte mais utilizados por cor ou raça em **{localidade_selecionada}**.")

    st.markdown("---")

    st.subheader("Mediana de Uso por Cor / Raça (KPIs)")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

    mediana_branca = df_filtrado[df_filtrado["Raça"] == "Branca"]["Percentual"].median()
    mediana_preta = df_filtrado[df_filtrado["Raça"] == "Preta ou Parda"]["Percentual"].median()
    mediana_indigena = df_filtrado[df_filtrado["Raça"] == "Indígena"]["Percentual"].median()

    col_kpi1.metric(
        label="Mediana (População Branca)",
        value=f"{mediana_branca:.1f}%" if pd.notnull(mediana_branca) else "N/A"
    )
    col_kpi2.metric(
        label="Mediana (População Preta/Parda)",
        value=f"{mediana_preta:.1f}%" if pd.notnull(mediana_preta) else "N/A"
    )
    col_kpi3.metric(
        label="Mediana (População Indígena)",
        value=f"{mediana_indigena:.1f}%" if pd.notnull(mediana_indigena) else "N/A"
    )

    st.markdown("---")

    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.subheader("Distribuição de Uso")
        fig_box = px.box(
            df_filtrado,
            x="Raça",
            y="Percentual",
            color="Raça",
            points="all",
            title=f"Distribuição do Tempo/Uso por Raça ({localidade_selecionada})",
            labels={"Percentual": "Percentual (%)", "Raça": "Cor / Raça"},
            color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c"]
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with col_graf2:
        st.subheader("Proporção dos Tipos de Modal")
        df_tipo_modal = df_filtrado.groupby("Tipo de Modal")["Percentual"].sum().reset_index()
        
        fig_pie = px.pie(
            df_tipo_modal,
            values="Percentual",
            names="Tipo de Modal",
            hole=0.4,
            title="Proporção: Público vs Particular vs Ativo",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    st.subheader("Cidades / Localidades com Maior Mobilidade Ativa (Bicicleta)")
    df_bicicleta = df_transporte[df_transporte["Meio de Transporte"] == "Bicicleta"]
    df_rank_bike = df_bicicleta.groupby("Localidade")["Percentual"].mean().reset_index()
    df_rank_bike = df_rank_bike[~df_rank_bike["Localidade"].isin(["Brasil", "Norte", "Nordeste", "Sudeste", "Sul", "Centro-oeste"])]
    df_top_bikes = df_rank_bike.sort_values(by="Percentual", ascending=False).head(10)

    fig_rank = px.bar(
        df_top_bikes,
        x="Percentual",
        y="Localidade",
        orientation="h",
        title="Top 10 Cidades/UFs com Maior Uso de Bicicleta",
        labels={"Percentual": "Média Percentual (%)", "Localidade": "Cidade / UF"},
        color="Percentual",
        color_continuous_scale="Viridis"
    )
    fig_rank.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_rank, use_container_width=True)

    st.markdown("---")

    st.subheader("📰 Conteúdo Adicional & Notícias")
    st.markdown("Explores matérias e artigos sobre sustentabilidade e os desafios da mobilidade urbana no Brasil.")

    col_art1, col_art2, col_art3 = st.columns(3)

    with col_art1:
        st.image("https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=600&q=80", caption="Caos no Trânsito Urbano")
        st.markdown("**Desafios do Caos no Trânsito nas Metrópoles**")
        st.caption("Estudo aponta as perdas econômicas e sociais do excesso de veículos particulares nas grandes vias.")

    with col_art2:
        st.image("https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=600&q=80", caption="Mobilidade Sustentável")
        st.markdown("**Mobilidade Sustentável e Malha Cicloviária**")
        st.caption("Como investimentos em ciclovias e transporte ativo melhoram a qualidade de vida e o meio ambiente.")

    with col_art3:
        st.image("https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=600&q=80", caption="Transporte Público Integrado")
        st.markdown("**A Importância da Integração no Transporte Público**")
        st.caption("Análise sobre o impacto da tarifa zero e corredores exclusivos de ônibus na redução das desigualdades.")

except Exception as e:
    st.error(f"Erro ao carregar e processar os dados: {e}")
    st.info("Verifique se o arquivo 'Tabela_13_Meio_de_transporte.xlsx' está no mesmo diretório do projeto.")