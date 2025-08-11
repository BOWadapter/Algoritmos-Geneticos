from flask import render_template, request, redirect, url_for, flash, Blueprint, jsonify
from app import db
from app.models import (
    Docente, Materia, DocenteMateria, Disponibilidad, ReservaModulo, Horario,
    Grupo, MateriaGrupo, DIAS, Turno
)
from app.genetico import generar_horario

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

# ---------- Grupos ----------
@bp.route("/grupos/nuevo", methods=["GET", "POST"])
def grupo_nuevo():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        turno = Turno(request.form["turno"])
        db.session.add(Grupo(nombre=nombre, turno=turno))
        db.session.commit()
        flash("Grupo registrado", "success")
        return redirect(url_for("main.grupo_nuevo"))
    return render_template("grupo_form.html")

@bp.route("/grupos")
def listar_grupos():
    grupos = Grupo.query.order_by(Grupo.nombre).all()
    return render_template("grupo_list.html", grupos=grupos)

@bp.route("/grupos/<int:grupo_id>/editar", methods=["GET", "POST"])
def editar_grupo(grupo_id):
    g = Grupo.query.get_or_404(grupo_id)
    if request.method == "POST":
        g.nombre = request.form["nombre"].strip()
        g.turno = Turno(request.form["turno"])
        db.session.commit()
        flash("Grupo actualizado", "success")
        return redirect(url_for("main.listar_grupos"))
    return render_template("grupo_form.html", grupo=g)

@bp.route("/grupos/<int:grupo_id>/eliminar", methods=["POST"])
def eliminar_grupo(grupo_id):
    g = Grupo.query.get_or_404(grupo_id)
    db.session.delete(g)
    db.session.commit()
    flash("Grupo eliminado", "success")
    return redirect(url_for("main.listar_grupos"))

# ---------- Materias ----------
@bp.route("/materias/nueva", methods=["GET", "POST"])
def materia_nueva():
    if request.method == "POST":
        m = Materia(
            nombre=request.form["nombre"].strip(),
            turno=Turno(request.form["turno"]),
            bloques_duracion=int(request.form["bloques"])
        )
        db.session.add(m)
        db.session.commit()
        flash("Materia registrada", "success")
        return redirect(url_for("main.materia_nueva"))
    return render_template("materia_form.html")

@bp.route("/materias")
def listar_materias():
    materias = Materia.query.order_by(Materia.turno, Materia.nombre).all()
    return render_template("materia_list.html", materias=materias)

@bp.route("/materias/<int:materia_id>/editar", methods=["GET", "POST"])
def editar_materia(materia_id):
    m = Materia.query.get_or_404(materia_id)
    if request.method == "POST":
        m.nombre = request.form["nombre"].strip()
        m.turno = Turno(request.form["turno"])
        m.bloques_duracion = int(request.form["bloques"])
        db.session.commit()
        flash("Materia actualizada", "success")
        return redirect(url_for("main.listar_materias"))
    return render_template("materia_form.html", materia=m)

@bp.route("/materias/<int:materia_id>/eliminar", methods=["POST"])
def eliminar_materia(materia_id):
    m = Materia.query.get_or_404(materia_id)
    db.session.delete(m)
    db.session.commit()
    flash("Materia eliminada", "success")
    return redirect(url_for("main.listar_materias"))

# ---------- Plan por Grupo ----------
@bp.route("/plan/nuevo", methods=["GET", "POST"])
def plan_nuevo():
    grupos = Grupo.query.order_by(Grupo.nombre).all()
    materias = Materia.query.order_by(Materia.nombre).all()
    if request.method == "POST":
        grupo_id = int(request.form["grupo_id"])
        materia_id = int(request.form["materia_id"])
        sesiones = int(request.form["sesiones_semana"])
        db.session.add(MateriaGrupo(grupo_id=grupo_id, materia_id=materia_id, sesiones_semana=sesiones))
        db.session.commit()
        flash("Materia añadida al plan del grupo", "success")
        return redirect(url_for("main.plan_nuevo"))
    return render_template("plan_form.html", grupos=grupos, materias=materias)

@bp.route("/plan")
def listar_plan():
    plan = (db.session.query(MateriaGrupo, Grupo, Materia)
            .join(Grupo, MateriaGrupo.grupo_id == Grupo.id)
            .join(Materia, MateriaGrupo.materia_id == Materia.id)
            .order_by(Grupo.nombre, Materia.nombre)
            .all())
    return render_template("plan_list.html", plan=plan)

@bp.route("/plan/<int:mg_id>/editar", methods=["GET", "POST"])
def editar_plan(mg_id):
    mg = MateriaGrupo.query.get_or_404(mg_id)
    grupos = Grupo.query.order_by(Grupo.nombre).all()
    materias = Materia.query.order_by(Materia.nombre).all()
    if request.method == "POST":
        mg.grupo_id = int(request.form["grupo_id"])
        mg.materia_id = int(request.form["materia_id"])
        mg.sesiones_semana = int(request.form["sesiones_semana"])
        db.session.commit()
        flash("Plan actualizado", "success")
        return redirect(url_for("main.listar_plan"))
    return render_template("plan_form.html", grupos=grupos, materias=materias, mg=mg)

@bp.route("/plan/<int:mg_id>/eliminar", methods=["POST"])
def eliminar_plan(mg_id):
    mg = MateriaGrupo.query.get_or_404(mg_id)
    db.session.delete(mg)
    db.session.commit()
    flash("Elemento del plan eliminado", "success")
    return redirect(url_for("main.listar_plan"))

# ---------- Docentes / Disponibilidad ----------
@bp.route("/disponibilidad/nueva", methods=["GET", "POST"])
def disponibilidad_nueva():
    materias = Materia.query.order_by(Materia.nombre).all()
    if request.method == "POST":
        d = Docente(
            nombre=request.form["docente_nombre"].strip(),
            correo=request.form.get("correo", "").strip(),
        )
        db.session.add(d)
        db.session.flush()

        for mid in request.form.getlist("materias_ids"):
            db.session.add(DocenteMateria(docente_id=d.id, materia_id=int(mid)))

        for dia in DIAS:
            for turno in [Turno.MATUTINO, Turno.VESPERTINO]:
                ini = request.form.get(f"{dia}_{turno}_ini")
                fin = request.form.get(f"{dia}_{turno}_fin")
                if ini and fin:
                    ini, fin = int(ini), int(fin)
                    if 1 <= ini <= fin <= 8:
                        db.session.add(Disponibilidad(
                            docente_id=d.id, dia=dia, turno=turno,
                            bloque_inicio=ini, bloque_fin=fin
                        ))
        db.session.commit()
        flash("Disponibilidad y materias del docente registradas", "success")
        return redirect(url_for("main.disponibilidad_nueva"))

    return render_template("disponibilidad_form.html", materias=materias, DIAS=DIAS, Turno=Turno)

@bp.route("/docentes")
def listar_docentes():
    docentes = Docente.query.order_by(Docente.nombre).all()
    return render_template("docente_list.html", docentes=docentes)

@bp.route("/docentes/<int:docente_id>/editar", methods=["GET", "POST"])
def editar_docente(docente_id):
    d = Docente.query.get_or_404(docente_id)
    materias = Materia.query.order_by(Materia.nombre).all()
    if request.method == "POST":
        d.nombre = request.form["nombre"].strip()
        d.correo = request.form.get("correo", "").strip()
        DocenteMateria.query.filter_by(docente_id=d.id).delete()
        for mid in request.form.getlist("materias_ids"):
            db.session.add(DocenteMateria(docente_id=d.id, materia_id=int(mid)))
        db.session.commit()
        flash("Docente actualizado", "success")
        return redirect(url_for("main.listar_docentes"))
    ids_actuales = {dm.materia_id for dm in d.materias}
    return render_template("docente_edit.html", docente=d, materias=materias, ids_actuales=ids_actuales)

@bp.route("/docentes/<int:docente_id>/eliminar", methods=["POST"])
def eliminar_docente(docente_id):
    d = Docente.query.get_or_404(docente_id)
    db.session.delete(d)
    db.session.commit()
    flash("Docente eliminado", "success")
    return redirect(url_for("main.listar_docentes"))

@bp.route("/disponibilidad/<int:disp_id>/eliminar", methods=["POST"])
def eliminar_disponibilidad(disp_id):
    disp = Disponibilidad.query.get_or_404(disp_id)
    docente_id = disp.docente_id
    db.session.delete(disp)
    db.session.commit()
    flash("Disponibilidad eliminada", "success")
    return redirect(url_for("main.editar_docente", docente_id=docente_id))

# ---------- Reservas ----------
@bp.route("/reservas/nueva", methods=["GET", "POST"])
def reserva_nueva():
    grupos = Grupo.query.order_by(Grupo.nombre).all()
    materias = Materia.query.order_by(Materia.nombre).all()
    if request.method == "POST":
        db.session.add(ReservaModulo(
            grupo_id=int(request.form["grupo_id"]),
            materia_id=int(request.form["materia_id"]),
            dia=request.form["dia"],
            turno=Turno(request.form["turno"]),
            bloque_inicio=int(request.form["bloque_inicio"]),
            bloque_fin=int(request.form["bloque_fin"])
        ))
        db.session.commit()
        flash("Reserva registrada", "success")
        return redirect(url_for("main.reserva_nueva"))
    return render_template("reserva_form.html", grupos=grupos, materias=materias, DIAS=DIAS, Turno=Turno)

@bp.route("/reservas")
def listar_reservas():
    reservas = (db.session.query(ReservaModulo, Grupo, Materia)
                .join(Grupo, ReservaModulo.grupo_id == Grupo.id)
                .join(Materia, ReservaModulo.materia_id == Materia.id)
                .order_by(Grupo.nombre, ReservaModulo.dia)
                .all())
    return render_template("reserva_list.html", reservas=reservas)

@bp.route("/reservas/<int:reserva_id>/eliminar", methods=["POST"])
def eliminar_reserva(reserva_id):
    r = ReservaModulo.query.get_or_404(reserva_id)
    db.session.delete(r)
    db.session.commit()
    flash("Reserva eliminada", "success")
    return redirect(url_for("main.listar_reservas"))

# ---------- Generación / Consulta de horario ----------
@bp.route("/generar", methods=["POST"])
def generar():
    mejor, puntaje = generar_horario()
    resultado = (db.session.query(Horario, Materia, Docente, Grupo)
                 .join(Materia, Horario.materia_id == Materia.id)
                 .join(Docente, Horario.docente_id == Docente.id)
                 .join(Grupo, Horario.grupo_id == Grupo.id)
                 .all())
    return render_template("resultado.html", resultado=resultado, puntaje=puntaje)

@bp.route("/horario")
def listar_horario():
    resultado = (db.session.query(Horario, Materia, Docente, Grupo)
                 .join(Materia, Horario.materia_id == Materia.id)
                 .join(Docente, Horario.docente_id == Docente.id)
                 .join(Grupo, Horario.grupo_id == Grupo.id)
                 .order_by(Grupo.nombre, Horario.dia, Horario.bloque_inicio)
                 .all())
    return render_template("resultado.html", resultado=resultado, puntaje=None)

# ---------- Tablero visual por grupo (8x5) ----------
@bp.route("/tablero")
def tablero():
    grupos = Grupo.query.order_by(Grupo.nombre).all()
    group_id = request.args.get("grupo_id", type=int)

    matriz = None
    grupo_sel = None
    BLOQUES = list(range(1, 9))
    total_asignaciones = 0

    if group_id:
        grupo_sel = Grupo.query.get_or_404(group_id)
        dias = DIAS
        matriz = {b: {d: None for d in dias} for b in BLOQUES}

        asignaciones = (db.session.query(Horario, Materia, Docente)
                        .join(Materia, Horario.materia_id == Materia.id)
                        .join(Docente, Horario.docente_id == Docente.id)
                        .filter(Horario.grupo_id == group_id)
                        .all())

        total_asignaciones = len(asignaciones)

        for h, m, d in asignaciones:
            for b in range(h.bloque_inicio, h.bloque_fin + 1):
                matriz[b][h.dia] = {
                    "materia": m.nombre,
                    "docente": d.nombre,
                    "turno": h.turno.value
                }

    return render_template("tablero.html",
                           grupos=grupos,
                           grupo_sel=grupo_sel,
                           matriz=matriz,
                           DIAS=DIAS,
                           BLOQUES=BLOQUES,
                           total_asignaciones=total_asignaciones)

# ---------- API de depuración ----------
@bp.route("/api/debug/horario/<int:grupo_id>")
def api_debug_horario(grupo_id):
    q = (db.session.query(Horario)
         .filter(Horario.grupo_id == grupo_id)
         .order_by(Horario.dia, Horario.bloque_inicio))
    items = [{
        "dia": h.dia,
        "turno": h.turno.value,
        "bloque_inicio": h.bloque_inicio,
        "bloque_fin": h.bloque_fin,
        "materia_id": h.materia_id,
        "docente_id": h.docente_id,
    } for h in q.all()]
    return jsonify({"grupo_id": grupo_id, "count": len(items), "items": items})
