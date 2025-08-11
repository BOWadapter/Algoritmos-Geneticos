# seed.py
from app import create_app, db
from app.models import (
    Grupo, Turno, Materia, MateriaGrupo, Docente, DocenteMateria,
    Disponibilidad, ReservaModulo, Horario, DIAS
)
from app.genetico import generar_horario

app = create_app()

with app.app_context():
    # Recrea el esquema desde cero (BORRA todo lo anterior)
    db.drop_all()
    db.create_all()

    # ---- Grupos (3 matutinos, 3 vespertinos) ----
    grupos = [
        Grupo(nombre="1A", turno=Turno.MATUTINO),
        Grupo(nombre="1B", turno=Turno.MATUTINO),
        Grupo(nombre="1C", turno=Turno.MATUTINO),
        Grupo(nombre="2A", turno=Turno.VESPERTINO),
        Grupo(nombre="2B", turno=Turno.VESPERTINO),
        Grupo(nombre="2C", turno=Turno.VESPERTINO),
    ]
    db.session.add_all(grupos)

    # ---- Materias (4 por turno) ----
    materias = [
        # Matutino
        Materia(nombre="Matemáticas", turno=Turno.MATUTINO, bloques_duracion=2),
        Materia(nombre="Física", turno=Turno.MATUTINO, bloques_duracion=2),
        Materia(nombre="Inglés", turno=Turno.MATUTINO, bloques_duracion=2),
        Materia(nombre="Desarrollo Humano", turno=Turno.MATUTINO, bloques_duracion=2),
        # Vespertino
        Materia(nombre="Programación", turno=Turno.VESPERTINO, bloques_duracion=2),
        Materia(nombre="Base de Datos", turno=Turno.VESPERTINO, bloques_duracion=2),
        Materia(nombre="Inglés", turno=Turno.VESPERTINO, bloques_duracion=2),
        Materia(nombre="Desarrollo Humano", turno=Turno.VESPERTINO, bloques_duracion=2),
    ]
    db.session.add_all(materias)
    db.session.commit()

    # ---- Plan por grupo: cada grupo cursa las 4 materias de su turno (3 sesiones/semana) ----
    for g in grupos:
        for m in [mat for mat in materias if mat.turno == g.turno]:
            db.session.add(MateriaGrupo(grupo_id=g.id, materia_id=m.id, sesiones_semana=3))

    # ---- Docentes ----
    d1 = Docente(nombre="Juan Pérez", correo="juan@example.com")
    d2 = Docente(nombre="Ana Gómez", correo="ana@example.com")
    d3 = Docente(nombre="Carlos Ruiz", correo="carlos@example.com")
    d4 = Docente(nombre="María López", correo="maria@example.com")
    db.session.add_all([d1, d2, d3, d4])
    db.session.flush()

    # ---- Docente-Materia (habilitaciones) ----
    asignaciones = [
        (d1, ["Matemáticas", "Programación"]),
        (d2, ["Física", "Base de Datos"]),
        (d3, ["Inglés"]),
        (d4, ["Desarrollo Humano"]),
    ]
    for docente, nombres in asignaciones:
        for nom in nombres:
            # hay materias con el mismo nombre en turnos distintos → las habilitamos en ambos turnos
            for mat in Materia.query.filter(Materia.nombre == nom).all():
                db.session.add(DocenteMateria(docente_id=docente.id, materia_id=mat.id))

    # ---- Disponibilidad: todos los docentes disponibles en ambos turnos, todos los días, bloques 1..8 ----
    for docente in [d1, d2, d3, d4]:
        for dia in DIAS:  # ["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES"]
            for turno in [Turno.MATUTINO, Turno.VESPERTINO]:
                db.session.add(Disponibilidad(
                    docente_id=docente.id, dia=dia, turno=turno,
                    bloque_inicio=1, bloque_fin=8
                ))

    # ---- Reservas fijas por grupo: Inglés (LUNES y MIERCOLES 1-2), Desarrollo Humano (MARTES 3-4) ----
    for g in grupos:
        ingles = Materia.query.filter_by(nombre="Inglés", turno=g.turno).first()
        dh = Materia.query.filter_by(nombre="Desarrollo Humano", turno=g.turno).first()
        # Inglés: LUNES y MIERCOLES, bloques 1-2
        for dia in ["LUNES", "MIERCOLES"]:
            db.session.add(ReservaModulo(
                grupo_id=g.id, materia_id=ingles.id, dia=dia, turno=g.turno,
                bloque_inicio=1, bloque_fin=2
            ))
        # Desarrollo Humano: MARTES, bloques 3-4
        db.session.add(ReservaModulo(
            grupo_id=g.id, materia_id=dh.id, dia="MARTES", turno=g.turno,
            bloque_inicio=3, bloque_fin=4
        ))

    db.session.commit()

    # ---- Ejecutar el Algoritmo Genético y guardar el horario ----
    mejor, puntaje = generar_horario(generaciones=80, tam=40, elite=8)

    # ---- Reporte rápido por consola ----
    total = Horario.query.count()
    print("✅ Seed completo.")
    print(f"→ Fitness del mejor individuo: {puntaje}")
    print(f"→ Filas en tabla 'horario': {total}")
    # muestra conteo por grupo
    for g in grupos:
        c = Horario.query.filter_by(grupo_id=g.id).count()
        print(f"   - {g.nombre} ({g.turno.value}): {c} asignaciones")
    print("\nAbre el tablero: http://127.0.0.1:5000/tablero")
