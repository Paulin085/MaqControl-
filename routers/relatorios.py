# routers/relatorios.py — Exportação de relatórios
from fastapi import APIRouter, Request, Form
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import io

from crud import listar_maquinas, listar_setores
from models.maquina import TipoMaquina

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])
templates = Jinja2Templates(directory="templates")


@router.get("/", name="relatorios")
async def pg_relatorios(request: Request):
    setores = listar_setores()
    tipos   = [t.value for t in TipoMaquina]
    from crud.users import get_all_users
    usuarios = get_all_users()
    return templates.TemplateResponse(request=request,
        name="relatorios/index.html",
        context={
        "request": request,
        "setores": setores,
        "tipos": tipos,
        "usuarios": usuarios,
    })


@router.post("/exportar-excel", name="exportar_excel")
async def exportar_excel(
    setor_id: Optional[str] = Form(None),
    tipo: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    campos: list[str] = Form(default=[]),
):
    """Gera e devolve um arquivo Excel com as máquinas filtradas."""
    import pandas as pd

    maquinas  = listar_maquinas(setor_id=setor_id or None, tipo=tipo or None, status=status or None)
    setores   = listar_setores()
    setor_map = {s.id: s.nome for s in setores}

    # Campos disponíveis
    todos_campos = {
        "nome": "Nome",
        "tipo": "Tipo",
        "setor": "Setor",
        "ip": "IP",
        "anydesk": "AnyDesk",
        "processador": "Processador",
        "memoria_ram": "Memória RAM",
        "armazenamento_tipo": "Tipo Armazenamento",
        "armazenamento_capacidade": "Capacidade",
        "status": "Status",
        "ultima_manutencao": "Última Manutenção",
        "proxima_manutencao": "Próxima Manutenção",
        "data_aquisicao": "Data Aquisição",
        "data_cadastro": "Data Cadastro",
        "observacoes": "Observações",
    }

    # Se nenhum campo selecionado, exporta todos
    campos_selecionados = campos if campos else list(todos_campos.keys())

    linhas = []
    for m in maquinas:
        linha = {}
        for campo in campos_selecionados:
            if campo == "setor":
                linha["Setor"] = setor_map.get(m.setor_id, "—")
            elif campo == "status":
                linha["Status"] = m.status.value
            else:
                label = todos_campos.get(campo, campo)
                valor = getattr(m, campo, "")
                linha[label] = str(valor) if valor else ""
        linhas.append(linha)

    df = pd.DataFrame(linhas)

    # Gera o arquivo em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Máquinas")

        # Ajusta largura das colunas
        ws = writer.sheets["Máquinas"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=maqcontrol_maquinas.xlsx"}
    )


@router.post("/exportar-chamados", name="exportar_chamados")
async def exportar_chamados(
    status: Optional[str] = Form(None),
    usuario_id: Optional[str] = Form(None),
    campos: list[str] = Form(default=[])
):
    """Gera e devolve um arquivo Excel com os chamados filtrados e personalizados."""
    import pandas as pd
    from crud.crud_chamados import listar_chamados

    chamados = listar_chamados()
    if status:
        chamados = [c for c in chamados if c.status.value == status]
    if usuario_id:
        chamados = [c for c in chamados if c.usuario_id == usuario_id]

    todos_campos = {
        "id": "ID",
        "setor_loja": "Setor/Loja",
        "solicitante": "Solicitante",
        "tipo": "Tipo",
        "dificuldade": "Dificuldade",
        "descricao": "Descrição",
        "resolucao": "Resolução",
        "status": "Status",
        "data_registro": "Data de Registro"
    }

    campos_selecionados = campos if campos else list(todos_campos.keys())

    linhas = []
    for c in chamados:
        linha = {}
        for campo in campos_selecionados:
            label = todos_campos.get(campo, campo)
            if campo == "status":
                linha[label] = c.status.value
            elif campo == "tipo":
                linha[label] = c.tipo.value if hasattr(c.tipo, "value") else c.tipo
            elif campo == "dificuldade":
                linha[label] = c.dificuldade.value if hasattr(c.dificuldade, "value") else c.dificuldade
            elif campo == "data_registro":
                if hasattr(c.data_registro, "strftime"):
                    linha[label] = c.data_registro.strftime("%d/%m/%Y %H:%M")
                else:
                    linha[label] = str(c.data_registro)
            else:
                valor = getattr(c, campo, "")
                linha[label] = str(valor) if valor else ""
        linhas.append(linha)

    df = pd.DataFrame(linhas)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Chamados")
        ws = writer.sheets["Chamados"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=maqcontrol_chamados.xlsx"}
    )


@router.post("/exportar-usuarios", name="exportar_usuarios")
async def exportar_usuarios():
    """Gera e devolve um arquivo Excel com os usuários."""
    import pandas as pd
    from crud.users import get_all_users

    usuarios = get_all_users()

    linhas = []
    for u in usuarios:
        linhas.append({
            "Nome": u.name,
            "Email/Login": u.email,
            "Perfil": "Admin" if u.is_admin else "Padrão",
            "Permissões": "Acesso Total" if u.is_admin else ", ".join(u.permissions)
        })

    df = pd.DataFrame(linhas)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Usuários")
        ws = writer.sheets["Usuários"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=maqcontrol_usuarios.xlsx"}
    )
