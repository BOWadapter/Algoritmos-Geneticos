import random
from collections import defaultdict
from app import db
from app.models import (
    Docente, Materia, DocenteMateria, Disponibilidad, ReservaModulo, Horario,
    Grupo, MateriaGrupo, DIAS, Turno
)

BLOQUES_POR_TURNO = 8
MAX_MATERIAS_DIA_POR_GRUPO = 4  # 4 materias por día

# -------------------- Utilitarios --------------------
def reservas_indexadas():
    """ Rslots: set (grupo_id, dia, turno, b)
        Rrangos: dict[(grupo_id, materia_id, dia)] = (ini, fin) """
    Rslots = set()
    Rrangos = {}
    for r in ReservaModulo.query.all():
        for b in range(r.bloque_inicio, r.bloque_fin + 1):
            Rslots.add((r.grupo_id, r.dia, r.turno, b))
        Rrangos[(r.grupo_id, r.materia_id, r.dia)] = (r.bloque_inicio, r.bloque_fin)
    return Rslots, Rrangos

def disponibilidad_por_docente(docente_id):
    d = Docente.query.get(docente_id)
    slots = set()
    for disp in d.disponibilidades:
        for b in range(disp.bloque_inicio, disp.bloque_fin + 1):
            slots.add((disp.dia, disp.turno, b))
    return slots

def docentes_para_materia(materia_id):
    return [dm.docente for dm in DocenteMateria.query.filter_by(materia_id=materia_id).all()]

def sesiones_requeridas():
    """ lista de tareas: (grupo_id, materia_id, turno, bloques) repetidas por sesiones_semana """
    tareas = []
    for mg in MateriaGrupo.query.all():
        m = Materia.query.get(mg.materia_id)
        for _ in range(mg.sesiones_semana):
            tareas.append({"grupo_id": mg.grupo_id, "materia_id": mg.materia_id, "turno": m.turno, "bloques": m.bloques_duracion})
    return tareas

# -------------------- Individuo --------------------
def generar_individuo():
    """ lista de tuplas: (grupo_id, materia_id, docente_id|None, dia|None, turno, ini|None, fin|None) """
    Rslots, Rrangos = reservas_indexadas()
    base = [(t["grupo_id"], t["materia_id"], None, None, t["turno"], None, None) for t in sesiones_requeridas()]

    # Preasignar reservas
    individuo = []
    for (g, m, d, dia, turno, ini, fin) in base:
        reservas_para = [(k, v) for (k, v) in Rrangos.items() if k[0] == g and k[1] == m]
        if reservas_para:
            rkey, (ini_r, fin_r) = reservas_para.pop(0)
            dia_fijo = rkey[2]
            individuo.append((g, m, None, dia_fijo, turno, ini_r, fin_r))
            Rrangos.pop(rkey, None)
        else:
            individuo.append((g, m, None, None, turno, None, None))

    uso_docente = set()                 # (docente_id, dia, turno, b)
    uso_grupo_bloques = set()           # (grupo_id, dia, turno, b)
    materias_por_grupo_dia = defaultdict(int)

    # ocupar bloques reservados (sin docente aún)
    for (g, m, d, dia, turno, ini, fin) in individuo:
        if dia and ini is not None:
            for b in range(ini, fin + 1):
                uso_grupo_bloques.add((g, dia, turno, b))
            materias_por_grupo_dia[(g, dia)] += 1

    asignado = []
    for (g, m, d, dia, turno, ini, fin) in individuo:
        # reservado: elegimos docente
        if dia and ini is not None:
            candidatos = docentes_para_materia(m)
            random.shuffle(candidatos)
            elegido = None
            for doc in candidatos:
                dslots = disponibilidad_por_docente(doc.id)
                ok = all((dia, turno, b) in dslots for b in range(ini, fin + 1))
                ok = ok and all((doc.id, dia, turno, b) not in uso_docente for b in range(ini, fin + 1))
                if ok:
                    elegido = doc.id
                    break
            asignado.append((g, m, elegido, dia, turno, ini, fin))
            if elegido:
                for b in range(ini, fin + 1):
                    uso_docente.add((elegido, dia, turno, b))
            continue

        # sin reserva: ubicar
        candidatos = docentes_para_materia(m)
        random.shuffle(candidatos)
        placed = False

        dias_barajados = DIAS[:]
        random.shuffle(dias_barajados)
        dur = Materia.query.get(m).bloques_duracion
        for dia_try in dias_barajados:
            if materias_por_grupo_dia[(g, dia_try)] >= MAX_MATERIAS_DIA_POR_GRUPO:
                continue
            inicios = list(range(1, BLOQUES_POR_TURNO - dur + 2))
            random.shuffle(inicios)
            for ini_try in inicios:
                fin_try = ini_try + dur - 1
                # no pisar reservas o clases del grupo
                if any((g, dia_try, turno, b) in Rslots for b in range(ini_try, fin_try + 1)):
                    continue
                if any((g, dia_try, turno, b) in uso_grupo_bloques for b in range(ini_try, fin_try + 1)):
                    continue
                # docente disponible
                for doc in candidatos:
                    dslots = disponibilidad_por_docente(doc.id)
                    if all((dia_try, turno, b) in dslots for b in range(ini_try, fin_try + 1)) and \
                       all((doc.id, dia_try, turno, b) not in uso_docente for b in range(ini_try, fin_try + 1)):
                        asignado.append((g, m, doc.id, dia_try, turno, ini_try, fin_try))
                        for b in range(ini_try, fin_try + 1):
                            uso_grupo_bloques.add((g, dia_try, turno, b))
                            uso_docente.add((doc.id, dia_try, turno, b))
                        materias_por_grupo_dia[(g, dia_try)] += 1
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break

        if not placed:
            asignado.append((g, m, None, None, turno, None, None))

    return asignado

def fitness(ind):
    score = 0
    Rslots, _ = reservas_indexadas()
    uso_docente = set()
    uso_grupo_bloques = set()
    materias_por_grupo_dia = defaultdict(int)

    for (g, m, d, dia, turno, ini, fin) in ind:
        if not d or not dia or ini is None:
            score -= 80  # sesión sin asignar
            continue

        if materias_por_grupo_dia[(g, dia)] >= MAX_MATERIAS_DIA_POR_GRUPO:
            score -= 40

        for b in range(ini, fin + 1):
            if (d, dia, turno, b) in uso_docente:
                score -= 25  # docente duplicado
            else:
                uso_docente.add((d, dia, turno, b))

            if (g, dia, turno, b) in uso_grupo_bloques:
                score -= 25  # choque en grupo
            else:
                uso_grupo_bloques.add((g, dia, turno, b))

            if (g, dia, turno, b) in Rslots:
                score -= 50  # pisa reserva

        materias_por_grupo_dia[(g, dia)] += 1
        score += 10  # premio por sesión válida

    return score

def mutar(ind, p=0.15):
    nuevo = []
    for (g, m, d, dia, turno, ini, fin) in ind:
        if random.random() < p:
            nuevo.append((g, m, None, None, turno, None, None))  # reubicar en generación futura
        else:
            nuevo.append((g, m, d, dia, turno, ini, fin))
    return nuevo

def generar_horario(generaciones=60, tam=30, elite=6):
    poblacion = [generar_individuo() for _ in range(tam)]
    for _ in range(generaciones):
        poblacion.sort(key=fitness, reverse=True)
        nueva = poblacion[:elite]
        while len(nueva) < tam:
            padre = random.choice(poblacion[:elite])
            nueva.append(mutar(padre, p=0.20))
        poblacion = nueva

    mejor = max(poblacion, key=fitness)

    Horario.query.delete()
    db.session.commit()
    for (g, m, d, dia, turno, ini, fin) in mejor:
        if d and dia:
            db.session.add(Horario(
                grupo_id=g, materia_id=m, docente_id=d,
                dia=dia, turno=turno, bloque_inicio=ini, bloque_fin=fin
            ))
    db.session.commit()
    return mejor, fitness(mejor)
