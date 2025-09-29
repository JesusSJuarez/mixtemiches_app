from django.contrib import admin
from .models import Empleado, RegistroAsistencia, Configuracion

admin.site.register(Empleado)
admin.site.register(RegistroAsistencia)
admin.site.register(Configuracion)