from django.db import models
import uuid

# --- Modelo Configuración ---
# Almacena configuraciones globales de la aplicación para que sean editables.
class Configuracion(models.Model):
    """
    Modelo para guardar configuraciones globales de la app, como la tolerancia de retardo.
    Se debe crear una única instancia de este modelo.
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
# Almacena la información de cada empleado de la empresa.
class Empleado(models.Model):
    """
    Representa a un empleado en la base de datos.
    """
    # ... (el resto del modelo Empleado se mantiene igual, no es necesario repetirlo)
    nombre = models.CharField(max_length=100, help_text="Nombre del empleado")
    apellido = models.CharField(max_length=100, help_text="Apellido del empleado")
    puesto = models.CharField(max_length=100, blank=True, null=True, help_text="Cargo o puesto del empleado")
    email = models.EmailField(max_length=254, blank=True, null=True, unique=True, help_text="Correo electrónico (opcional)")
    hora_entrada_supuesta = models.TimeField(help_text="Hora de entrada programada (ej. 09:00:00)")
    hora_salida_supuesta = models.TimeField(help_text="Hora de salida programada (ej. 18:00:00)")
    codigo_qr_unico = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True, 
        help_text="Código único para el QR del empleado. Se genera automáticamente."
    )
    is_active = models.BooleanField(default=True, help_text="Indica si el empleado está activo en la empresa")

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

# --- Modelo RegistroAsistencia ---
# Guarda cada uno de los registros de entrada y salida de los empleados.
class RegistroAsistencia(models.Model):
    """
    Representa un registro de asistencia (una jornada laboral) para un empleado.
    """
    # ... (el resto del modelo RegistroAsistencia se mantiene igual)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias')
    fecha_hora_entrada = models.DateTimeField(help_text="Fecha y hora exactas de la entrada")
    fecha_hora_salida = models.DateTimeField(blank=True, null=True, help_text="Fecha y hora exactas de la salida (puede estar vacío)")
    llego_tarde = models.BooleanField(default=False, help_text="Se marca si el empleado llegó después de su hora supuesta (con tolerancia)")
    notas = models.TextField(blank=True, null=True, help_text="Notas u observaciones sobre este registro")

    def __str__(self):
        fecha = self.fecha_hora_entrada.strftime('%Y-%m-%d')
        return f"Asistencia de {self.empleado} - {fecha}"
