from django.db import models
import uuid

# --- Modelo Configuración ---
class Configuracion(models.Model):
    """
    Modelo para guardar configuraciones globales de la app.
    """
    minutos_tolerancia_entrada = models.PositiveIntegerField(
        default=10,
        help_text="Número de minutos de tolerancia para considerar una llegada como puntual."
    )

    def __str__(self):
        return "Configuración General de la Aplicación"
    
    class Meta:
        verbose_name_plural = "Configuraciones"


# --- Modelo Empleado ---
class Empleado(models.Model):
    """
    Representa a un empleado en la base de datos.
    """
    nombre = models.CharField(max_length=100, help_text="Nombre del empleado")
    apellido = models.CharField(max_length=100, help_text="Apellido del empleado")
    puesto = models.CharField(max_length=100, blank=True, null=True, help_text="Cargo o puesto del empleado")
    email = models.EmailField(max_length=254, blank=True, null=True, unique=True, help_text="Correo electrónico (opcional)")
    
    # Horarios por defecto (se usan si no hay horario variable)
    hora_entrada_supuesta = models.TimeField(help_text="Hora de entrada programada general (ej. 09:00:00)")
    hora_salida_supuesta = models.TimeField(help_text="Hora de salida programada general (ej. 18:00:00)")
    
    # Nuevo campo para activar horarios distintos
    usa_horario_variable = models.BooleanField(
        default=False, 
        help_text="Si se marca, el sistema buscará el horario específico del día de la semana en lugar del general."
    )

    codigo_qr_unico = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True, 
        help_text="Código único para el QR del empleado. Se genera automáticamente."
    )
    is_active = models.BooleanField(default=True, help_text="Indica si el empleado está activo en la empresa")

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

# --- Nuevo Modelo: Horario por Día ---
class HorarioDia(models.Model):
    DIAS_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='horarios_dias')
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_entrada = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    es_dia_libre = models.BooleanField(default=False, help_text="Marcar si este día el empleado descansa")

    class Meta:
        unique_together = ('empleado', 'dia_semana')
        ordering = ['dia_semana']

    def __str__(self):
        return f"{self.empleado} - {self.get_dia_semana_display()}"


# --- Modelo RegistroAsistencia ---
class RegistroAsistencia(models.Model):
    """
    Representa un registro de asistencia (una jornada laboral) para un empleado.
    """
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias')
    fecha_hora_entrada = models.DateTimeField(help_text="Fecha y hora exactas de la entrada")
    fecha_hora_salida = models.DateTimeField(blank=True, null=True, help_text="Fecha y hora exactas de la salida (puede estar vacío)")
    llego_tarde = models.BooleanField(default=False, help_text="Se marca si el empleado llegó después de su hora supuesta (con tolerancia)")
    notas = models.TextField(blank=True, null=True, help_text="Notas u observaciones sobre este registro")

    def __str__(self):
        fecha = self.fecha_hora_entrada.strftime('%Y-%m-%d')
        return f"Asistencia de {self.empleado} - {fecha}"