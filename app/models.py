from enum import Enum
from app import db

class Turno(str, Enum):
    MATUTINO = "MATUTINO"     # 07:00–13:40 (bloques 1..8)
    VESPERTINO = "VESPERTINO" # 14:00–20:40 (bloques 1..8)

DIAS = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES"]

# ---------- Catálogos ----------
class Grupo(db.Model):
    __tablename__ = "grupo"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    turno = db.Column(db.Enum(Turno), nullable=False)
    materias = db.relationship("MateriaGrupo", back_populates="grupo", cascade="all, delete-orphan")

class Docente(db.Model):
    __tablename__ = "docente"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(120))
    materias = db.relationship("DocenteMateria", back_populates="docente", cascade="all, delete-orphan")
    disponibilidades = db.relationship("Disponibilidad", back_populates="docente", cascade="all, delete-orphan")

class Materia(db.Model):
    __tablename__ = "materia"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    turno = db.Column(db.Enum(Turno), nullable=False)           # turno al que pertenece
    bloques_duracion = db.Column(db.Integer, nullable=False, default=2)
    docentes = db.relationship("DocenteMateria", back_populates="materia", cascade="all, delete-orphan")
    grupos = db.relationship("MateriaGrupo", back_populates="materia", cascade="all, delete-orphan")

class DocenteMateria(db.Model):
    __tablename__ = "docente_materia"
    id = db.Column(db.Integer, primary_key=True)
    docente_id = db.Column(db.Integer, db.ForeignKey("docente.id"), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id"), nullable=False)
    docente = db.relationship("Docente", back_populates="materias")
    materia = db.relationship("Materia", back_populates="docentes")

# Qué materias cursa cada grupo + cuántas sesiones/semana requiere
class MateriaGrupo(db.Model):
    __tablename__ = "materia_grupo"
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey("grupo.id"), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id"), nullable=False)
    sesiones_semana = db.Column(db.Integer, nullable=False, default=1)

    grupo = db.relationship("Grupo", back_populates="materias")
    materia = db.relationship("Materia", back_populates="grupos")

class Disponibilidad(db.Model):
    __tablename__ = "disponibilidad"
    id = db.Column(db.Integer, primary_key=True)
    docente_id = db.Column(db.Integer, db.ForeignKey("docente.id"), nullable=False)
    dia = db.Column(db.String(12), nullable=False)              # LUNES..VIERNES
    turno = db.Column(db.Enum(Turno), nullable=False)
    bloque_inicio = db.Column(db.Integer, nullable=False)       # 1..8
    bloque_fin = db.Column(db.Integer, nullable=False)          # 1..8
    docente = db.relationship("Docente", back_populates="disponibilidades")

# Reservas de módulos por grupo y materia (p.ej., Inglés / Desarrollo Humano)
class ReservaModulo(db.Model):
    __tablename__ = "reserva_modulo"
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey("grupo.id"), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id"), nullable=False)
    dia = db.Column(db.String(12), nullable=False)
    turno = db.Column(db.Enum(Turno), nullable=False)
    bloque_inicio = db.Column(db.Integer, nullable=False)
    bloque_fin = db.Column(db.Integer, nullable=False)

    grupo = db.relationship("Grupo")
    materia = db.relationship("Materia")

# Resultado final
class Horario(db.Model):
    __tablename__ = "horario"
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey("grupo.id"), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id"), nullable=False)
    docente_id = db.Column(db.Integer, db.ForeignKey("docente.id"), nullable=False)
    dia = db.Column(db.String(12), nullable=False)
    turno = db.Column(db.Enum(Turno), nullable=False)
    bloque_inicio = db.Column(db.Integer, nullable=False)
    bloque_fin = db.Column(db.Integer, nullable=False)

    grupo = db.relationship("Grupo")
    materia = db.relationship("Materia")
    docente = db.relationship("Docente")
