from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database.connection import Base


class Venta(Base):
    """Registro de ventas / cargas de hacienda."""
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    categoria = Column(String(50), nullable=False)   # terneros, terneras, vacas, novillos, toros
    cantidad = Column(Integer, nullable=False)
    kgs = Column(Float, nullable=True)
    precio_total = Column(Float, nullable=False)
    notas = Column(Text, nullable=True)


class Mortandad(Base):
    """Registro de bajas / muertes."""
    __tablename__ = "mortandad"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    categoria = Column(String(50), nullable=False)   # ternero, ternera, vaca, toro, novillo, vaquilla
    descripcion = Column(Text, nullable=True)        # causa / observaciones
    numero_caravana = Column(Integer, nullable=True)
    potrero = Column(String(100), nullable=True)


class TrabajoCorral(Base):
    """Trabajos sanitarios y de manejo a corral."""
    __tablename__ = "trabajos_corral"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    categoria = Column(String(50), nullable=True)        # Sanidad, Reproducción / Servicio, Manejo / Organización, Otro
    tipo_trabajo = Column(String(100), nullable=False)  # aftosa, tactos, vitaminas, pesaje, ricobendazol, etc.
    animales = Column(Text, nullable=True)               # descripción de los animales trabajados
    resultado = Column(Text, nullable=True)              # resultados / observaciones
    notas = Column(Text, nullable=True)


class TipoTrabajoCatalogo(Base):
    """Catálogo editable de tipos de trabajo a corral, agrupados por categoría."""
    __tablename__ = "tipos_trabajo_catalogo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    categoria = Column(String(50), nullable=False)   # Sanidad, Reproducción / Servicio, Manejo / Organización, Otro
    activo = Column(Boolean, nullable=False, default=True)


class Gasto(Base):
    """Gastos del campo."""
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    tipo = Column(String(100), nullable=False)   # sanidad, alimentos, personal, combustible, maquinaria, etc.
    descripcion = Column(Text, nullable=True)
    monto = Column(Float, nullable=False)
    proveedor = Column(String(100), nullable=True)
    notas = Column(Text, nullable=True)


class Potrero(Base):
    """Potreros / lotes del campo."""
    __tablename__ = "potreros"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    numero = Column(String(20), nullable=True)       # número o código del potrero
    hectareas = Column(Float, nullable=True)
    notas = Column(Text, nullable=True)

    asignaciones = relationship("AsignacionPotrero", back_populates="potrero", cascade="all, delete-orphan")


class AsignacionPotrero(Base):
    """Asignación de hacienda a un potrero."""
    __tablename__ = "asignaciones_potrero"

    id = Column(Integer, primary_key=True, index=True)
    potrero_id = Column(Integer, ForeignKey("potreros.id"), nullable=False)
    fecha_entrada = Column(Date, nullable=False)
    fecha_salida = Column(Date, nullable=True)
    categoria = Column(String(50), nullable=False)
    cantidad = Column(Integer, nullable=False)
    notas = Column(Text, nullable=True)

    potrero = relationship("Potrero", back_populates="asignaciones")


class MovimientoPotrero(Base):
    """Movimiento de un lote de hacienda de un potrero a otro.

    Registra el traslado de `cantidad` cabezas de una `categoria` desde un
    potrero de origen hacia uno de destino. Puede ser directo o hacerse
    después de un trabajo a corral (vinculado opcionalmente vía
    `trabajo_corral_id`). Al registrarse, ajusta las asignaciones activas del
    potrero de origen (FIFO) y crea una nueva asignación en el destino.
    """
    __tablename__ = "movimientos_potrero"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    origen_potrero_id = Column(Integer, ForeignKey("potreros.id"), nullable=False)
    destino_potrero_id = Column(Integer, ForeignKey("potreros.id"), nullable=False)
    categoria = Column(String(50), nullable=False)
    cantidad = Column(Integer, nullable=False)
    tipo = Column(String(30), nullable=False, default="directo")  # directo | post-corral
    trabajo_corral_id = Column(Integer, ForeignKey("trabajos_corral.id"), nullable=True)
    notas = Column(Text, nullable=True)

    origen = relationship("Potrero", foreign_keys=[origen_potrero_id])
    destino = relationship("Potrero", foreign_keys=[destino_potrero_id])
    trabajo = relationship("TrabajoCorral")


class MovimientoInventario(Base):
    """Movimientos de inventario (compras, ajustes de hacienda)."""
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    categoria = Column(String(50), nullable=False)
    cantidad = Column(Integer, nullable=False)        # positivo = entrada, negativo = salida
    tipo_movimiento = Column(String(30), nullable=False)  # compra, ajuste, nacimiento, destete
    monto = Column(Float, nullable=True)              # costo de compra si aplica
    notas = Column(Text, nullable=True)


class Reproduccion(Base):
    """Registros reproductivos: tactos, partos, destetes."""
    __tablename__ = "reproduccion"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    tipo = Column(String(50), nullable=False)   # tacto, parto, destete, entrada_toros, salida_toros
    total_animales = Column(Integer, nullable=True)
    prenadas = Column(Integer, nullable=True)
    vacias = Column(Integer, nullable=True)
    terneros_machos = Column(Integer, nullable=True)
    terneras_hembras = Column(Integer, nullable=True)
    notas = Column(Text, nullable=True)


class IndiceReproductivo(Base):
    """Índices reproductivos históricos por temporada (KPIs anuales).

    Cada registro resume una temporada de servicio: total de vientres tactados,
    preñadas, destetados y muertos entre parto y destete. Los porcentajes
    (% preñez, % destete) se calculan a partir de estos valores crudos.
    """
    __tablename__ = "indices_reproductivos"

    id = Column(Integer, primary_key=True, index=True)
    temporada = Column(String(20), nullable=False)   # "Primavera" / "Otoño"
    anio = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)          # total de vientres tactados / en servicio
    prenadas = Column(Integer, nullable=False)
    destete = Column(Integer, nullable=True)         # terneros destetados
    muertos_parto_destete = Column(Integer, nullable=True)
    notas = Column(Text, nullable=True)
