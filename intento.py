import streamlit as st
import pandas as pd
import numpy as np
import io

# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="Generador de Planos SAP",
    layout="wide"
)

st.title("Generador de Planos SAP")

# ==================================================
# PROCESO
# ==================================================

proceso = st.radio(
    "Seleccione el proceso",
    [
        "Nómina",
        "Prestaciones Sociales",
        "Seguridad Social"
    ]
)

fecha = st.text_input(
    "Fecha (AAAAMMDD)",
    value="20260930"
)

# ==================================================
# PARAMETROS POR PROCESO
# ==================================================

if proceso == "Nómina":

    nombre_proceso = "NOMINA"
    segundo = "6"
    cuarto = "COMPROBANTE DE CAUSACION"
    treceavo = "NM"
    hoja_principal = "TOTAL CONTABILIZACIÓN"

    archivo_principal = st.file_uploader(
        "Archivo Nómina",
        type=["xlsx"]
    )

elif proceso == "Prestaciones Sociales":

    nombre_proceso = "PRESTACIONES SOCIALES"
    segundo = "1"
    cuarto = "COMPROBANTE DE CAUSACION"
    treceavo = "NP"
    hoja_principal = "CONTABILIZACION "

    archivo_principal = st.file_uploader(
        "Archivo Prestaciones Sociales",
        type=["xlsx"]
    )

else:

    nombre_proceso = "SEGURIDAD SOCIAL"
    segundo = "1"
    cuarto = "COMPROBANTE AUTOLIQ/PARAFISCALES"
    treceavo = "NA"
    hoja_principal = "TOTAL SS "

    archivo_principal = st.file_uploader(
        "Archivo Seguridad Social",
        type=["xlsx"]
    )

# ==================================================
# ARCHIVOS COMUNES
# ==================================================

cencos_file = st.file_uploader(
    "Validación Cencos",
    type=["xlsx"]
)

hs_file = st.file_uploader(
    "Clasificación H-S",
    type=["xlsx"]
)

conc_file = st.file_uploader(
    "Conciliación Cuentas",
    type=["xlsx"]
)

# ==================================================
# BOTON
# ==================================================

if st.button("Procesar"):

    if not all([
        archivo_principal,
        cencos_file,
        hs_file,
        conc_file
    ]):
        st.error("Debe cargar todos los archivos.")
        st.stop()

    try:

        # ==================================================
        # LECTURA
        # ==================================================

        df = pd.read_excel(
            archivo_principal,
            sheet_name=hoja_principal,
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

        df["PROCESO"] = nombre_proceso

        # ==================================================
        # LIMPIEZA
        # ==================================================

        for tabla in [df, cencos, h_s, conc_vieja]:
            tabla.fillna('', inplace=True)

        df['Id. Tercero .'] = (
            df['Id. Tercero .']
            .str.replace('.0', '', regex=False)
        )

        conc_vieja['Identificación'] = (
            conc_vieja['Identificación']
            .str.replace('.0', '', regex=False)
        )

        # ==================================================
        # MATCH TERCEROS
        # ==================================================

        df_der_aux = pd.concat([
            conc_vieja.assign(
                id_match=conc_vieja['Identificación']
            ),
            conc_vieja.assign(
                id_match=conc_vieja['Identificación'].str[:-1]
            )
        ])

        # ==================================================
        # H/S
        # ==================================================

        h_s = h_s.drop_duplicates(
            subset=['Id cuenta', 'Tipo'],
            keep='first'
        )

        # ==================================================
        # PROCESO
        # ==================================================

        resultado = (
            df
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
            .merge(
                h_s[
                    ['Id cuenta', 'Tipo', 'S/H']
                ],
                left_on=[
                    'Id Cuenta ',
                    'PROCESO'
                ],
                right_on=[
                    'Id cuenta',
                    'Tipo'
                ],
                how='left'
            )
        )

        sin_match_tercero = resultado[
            resultado['id_match'].isna()
        ]['Id. Tercero .'].dropna().unique()

        sin_match_cuenta = resultado[
            resultado['Cuenta'].isna()
        ]['Id Cuenta '].dropna().unique()

        sin_match_cencos = resultado[
            resultado['Centro de costo'].isna()
        ]['Id. C.Costos'].dropna().unique()

        # ==================================================
        # CONSTRUCCION PLANO
        # ==================================================

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
            .replace('', np.nan)
            .fillna(resultado['Id. C.Costos'])
        )

        resultado['Id cuenta'] = (
            resultado['Id cuenta']
            .replace('', np.nan)
            .fillna(resultado['Id Cuenta '])
        )

        resultado['id_match'] = (
            resultado['id_match']
            .replace('', np.nan)
            .fillna(resultado['Id. Tercero .'])
        )

        resultado['sociedad'] = '1000'
        resultado['segundo'] = segundo
        resultado['fecha'] = fecha
        resultado['cuarto'] = cuarto
        resultado['id_match2'] = resultado['id_match']

        resultado['CCOSTO_4000'] = (
            resultado['C.costo_sap']
            .where(
                resultado['C.costo_sap']
                .str.startswith('4000', na=False),
                ''
            )
        )

        resultado['CCOSTO_OTROS'] = (
            resultado['C.costo_sap']
            .where(
                ~resultado['C.costo_sap']
                .str.startswith('4000', na=False),
                ''
            )
        )

        resultado['doceavo'] = 'COMPROBANTE'
        resultado['treceavo'] = treceavo
        resultado['fecha2'] = fecha
        resultado['quinceavo'] = 'T'

        resultado['16'] = np.where(
            resultado['Id Cuenta ']
            .str.startswith(
                ('23', '25', '26'),
                na=False
            ),
            '1010201',
            ''
        )

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
                'quinceavo',
                '16'
            ]
        ]

        # ==================================================
        # MENSAJES Y VALIDACIONES
        # ==================================================

        st.success("Proceso completado")

        st.metric(
            "Registros procesados",
            len(resultado)
        )

        # --------------------------
        # TERCEROS SIN MATCH
        # --------------------------

        if len(sin_match_tercero) > 0:

            st.warning(
                f"⚠️ Se encontraron {len(sin_match_tercero)} terceros sin match."
            )

            st.write("### Terceros sin match")

            st.dataframe(
                pd.DataFrame({
                    "Id. Tercero .": sorted(sin_match_tercero)
                }),
                use_container_width=True
            )

        # --------------------------
        # CUENTAS SIN MATCH
        # --------------------------

        if len(sin_match_cuenta) > 0:

            st.warning(
                f"⚠️ Se encontraron {len(sin_match_cuenta)} cuentas sin match."
            )

            st.write("### Cuentas sin match")

            st.dataframe(
                pd.DataFrame({
                    "Id Cuenta": sorted(sin_match_cuenta)
                }),
                use_container_width=True
            )

        # --------------------------
        # CENCOS SIN MATCH
        # --------------------------

        if len(sin_match_cencos) > 0:

            st.warning(
                f"⚠️ Se encontraron {len(sin_match_cencos)} centros de costo sin match."
            )

            st.write("### Centros de costo sin match")

            st.dataframe(
                pd.DataFrame({
                    "Centro de costo": sorted(sin_match_cencos)
                }),
                use_container_width=True
            )

        # --------------------------
        # TODO OK
        # --------------------------

        if (
            len(sin_match_tercero) == 0
            and len(sin_match_cuenta) == 0
            and len(sin_match_cencos) == 0
        ):

            st.success(
                "✅ No se encontraron inconsistencias."
            )

        # ==================================================
        # VISTA PREVIA
        # ==================================================

        st.subheader("Vista previa")

        st.dataframe(
            resultado.head(20),
            use_container_width=True
        )

        # ==================================================
        # DESCARGA TXT
        # ==================================================

        txt_buffer = io.StringIO()

        resultado.to_csv(
            txt_buffer,
            sep="\t",
            index=False,
            header=False
        )

        nombre_archivo = {
            "Nómina": "Nomina_plano",
            "Prestaciones Sociales": "Prestaciones_plano",
            "Seguridad Social": "SS_plano"
        }[proceso]

        st.download_button(
            label=f"📥 Descargar {nombre_archivo}.txt",
            data=txt_buffer.getvalue(),
            file_name=f"{nombre_archivo}_{fecha}.txt",
            mime="text/plain",
            use_container_width=True
        )

    except Exception as e:

        st.error(f"Error: {str(e)}")
