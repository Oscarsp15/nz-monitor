"""Filtro de 'última actividad': frontera de palabra + descarte de otra base."""


def test_references_table_frontera_y_base():
    from netezza.service import _references_table as ref

    T, DB = "INSUMOSMODELOSDR", "DESA_MODELOS"

    # referencias válidas a ESTA tabla en ESTA base
    assert ref("SELECT MAX(x) FROM InsumosModelosDR WHERE f=1", T, DB)
    assert ref("Insert Into DBO.INSUMOSMODELOSDR (a,b)", T, DB)
    assert ref("SELECT * FROM DESA_MODELOS.DBO.INSUMOSMODELOSDR", T, DB)

    # nombres PARECIDOS (no deben contar)
    assert not ref("SELECT COUNT(*) FROM DESA_MODELOS.DBO.INSUMOSMODELOSDR_", T, DB)
    assert not ref("Insert Into DBO.INSUMOSMODELOSDR_NBK_INDUSTRIA (a)", T, DB)
    assert not ref("GENERATE STATISTICS ON INSUMOSMODELOSDR_ (cols.0-49)", T, DB)

    # OTRA base (no debe contar al mirar DESA_MODELOS)
    assert not ref("SELECT COUNT(1) FROM PROD_MODELOS.DBO.INSUMOSMODELOSDR", T, DB)
