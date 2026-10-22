import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Plano Nómina", layout="wide")

st.title("Generador Plano Nómina")

fecha = st.text_input(
    "Fecha (AAAAMMDD)",
    value="20260930"
)

nomina_file = st.file_uploader(
    "Archivo Nómina",
    type=["xlsx"]
)

cencos_file = st.file_uploader(
    "Archivo Validación Cencos",
    type=["xlsx"]
)

hs_file = st.file_uploader(
    "Archivo Clasificación H-S",
    type=["xlsx"]
)

conc_file = st.file_uploader(
    "Archivo Conciliación Cuentas",
    type=["xlsx"]
)

if st.button("Procesar"):

    if not all([
        nomina_file,
        cencos_file,
        hs_file,
        conc_file
    ]):
        st.error("Debe cargar todos los archivos.")
        st.stop()

    with st.spinner("Procesando información..."):

        # ==========================
        # Lectura archivos
        # ==========================

        nomina = pd.read_excel(
            nomina_file,
            sheet_name="TOTAL CONTABILIZACIÓN",
            dtype=str
        )

        cencos = pd.read_excel(
            cencos_file,
            sheet_name="VAL. CENCOS ALFREDO",
            dtype=str
        )

        h_s = pd.read_excel(
            hs_file,
            dtype=str
        )

        conc_vieja = pd.read_excel(
            conc_file,
            dtype=str
        )

        nomina["PROCESO"] = "NOMINA"

        # ==========================
        # Limpieza
        # ==========================

        nomina['Id. Tercero .'] = (
            nomina['Id. Tercero .']
            .astype(str)
            .str.replace('.0', '', regex=False)
        )

        conc_vieja['Identificación'] = (
            conc_vieja['Identificación']
            .astype(str)
            .str.replace('.0', '', regex=False)
        )

        # ==========================
        # Match terceros
        # ==========================

        df_der_aux = pd.concat([
            conc_vieja.assign(
                id_match=conc_vieja['Identificación']
            ),
            conc_vieja.assign(
                id_match=conc_vieja['Identificación'].str[:-1]
            )
        ])

        resultado = (
            nomina
            .merge(
                df_der_aux[['id_match']].drop_duplicates(),
                left_on='Id. Tercero .',
                right_on='id_match',
                how='left'
            )
            .merge(
                conc_vieja[['Cuenta']].drop_duplicates(),
                left_on='Id Cuenta ',
                right_on='Cuenta',
                how='left'
            )
            .merge(
                cencos[
                    ['Centro de costo', 'C.costo_sap']
                ].drop_duplicates(
                    subset=['Centro de costo']
                ),
                left_on='Id. C.Costos',
                right_on='Centro de costo',
                how='left'
            )
        )

        # ==========================
        # Validaciones
        # ==========================

        sin_match_tercero = resultado[
            resultado['id_match'].isna()
        ].dropna(
            subset=['Id. Tercero .']
        )

        sin_match_cuenta = resultado[
            resultado['Cuenta'].isna()
        ].dropna(
            subset=['Id Cuenta ']
        )

        sin_match_cencos = resultado[
            resultado['Centro de costo'].isna()
        ].dropna(
            subset=['Id. C.Costos']
        )

        # ==========================
        # H/S
        # ==========================

        h_s = h_s.drop_duplicates(
            subset=['Id cuenta', 'Tipo'],
            keep='first'
        )

        resultado = resultado.merge(
            h_s[['Id cuenta', 'Tipo', 'S/H']],
            left_on=['Id Cuenta ', 'PROCESO'],
            right_on=['Id cuenta', 'Tipo'],
            how='left'
        )

        # ==========================
        # Construcción plano
        # ==========================

        resultado['valor_sap'] = (
            pd.to_numeric(
                resultado['Valor Débito PCGA'],
                errors='coerce'
            ).fillna(0)
            +
            pd.to_numeric(
                resultado['Valor Crédito PCGA'],
                errors='coerce'
            ).fillna(0)
        )

        resultado['Centro de costo'] = (
            resultado['Centro de costo']
            .fillna(resultado['Id. C.Costos'])
        )

        resultado['sociedad'] = "1000"
        resultado['segundo'] = "6"
        resultado['fecha'] = fecha
        resultado['cuarto'] = "COMPROBANTE DE CAUSACION"
        resultado['id_match2'] = resultado['id_match']

        resultado['CCOSTO_4000'] = resultado[
            'C.costo_sap'
        ].where(
            resultado['C.costo_sap']
            .str.startswith('4000', na=False),
            ''
        )

        resultado['CCOSTO_OTROS'] = resultado[
            'C.costo_sap'
        ].where(
            ~resultado['C.costo_sap']
            .str.startswith('4000', na=False),
            ''
        )

        resultado['doceavo'] = "COMPROBANTE"
        resultado['treceavo'] = "NM"
        resultado['fecha2'] = fecha
        resultado['quinceavo'] = "T"

        resultado = resultado[
            [
                'sociedad',
                'segundo',
                'Id cuenta',
                'S/H',
                'id_match',
                'fecha',
                'cuarto',
                'valor_sap',
                'id_match2',
                'CCOSTO_OTROS',
                'CCOSTO_4000',
                'doceavo',
                'treceavo',
                'fecha2',
                'quinceavo'
            ]
        ]

# Mostrar algunas estadísticas
st.success("Proceso completado correctamente")

st.write("Registros generados:", len(resultado))

# Crear archivo TXT en memoria
txt_buffer = io.StringIO()

resultado.to_csv(
    txt_buffer,
    sep="\t",
    index=False,
    header=False
)

# Botón visible de descarga
st.download_button(
    label="📥 Descargar archivo plano",
    data=txt_buffer.getvalue(),
    file_name=f"archivo_plano_{fecha}.txt",
    mime="text/plain",
    use_container_width=True
)

        
        # ==========================
        # Mensajes
        # ==========================

        st.success("Proceso completado")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Registros procesados",
            len(resultado)
        )

        col2.metric(
            "Terceros sin match",
            len(sin_match_tercero)
        )

        col3.metric(
            "Cuentas sin match",
            len(sin_match_cuenta)
        )

        col4.metric(
            "Cencos sin match",
            len(sin_match_cencos)
        )

        # ==========================
        # Archivo TXT
