from django import forms
from .models import Empleado, Configuracion, HorarioDia
from django.contrib.auth.models import User

class EmpleadoForm(forms.ModelForm):
    # Campos auxiliares para los días de la semana
    # Los creamos dinámicamente o explícitamente para manipularlos fácil en el template
    
    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido', 'puesto', 'hora_entrada_supuesta', 'hora_salida_supuesta', 'usa_horario_variable']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition'}),
            'apellido': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition'}),
            'puesto': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition'}),
            'hora_entrada_supuesta': forms.TimeInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition', 'type': 'time'}),
            'hora_salida_supuesta': forms.TimeInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition', 'type': 'time'}),
            'usa_horario_variable': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-yellow-500 bg-gray-700 border-gray-600 rounded focus:ring-yellow-500 focus:ring-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Agregamos campos para cada día de la semana (0=Lunes, 6=Domingo)
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        # Estilos comunes
        time_widget = forms.TimeInput(attrs={'type': 'time', 'class': 'w-full bg-gray-600 border border-gray-500 text-white rounded px-2 py-1 text-sm'})
        check_widget = forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-500 bg-gray-600 border-gray-500 rounded'})

        for i, dia in enumerate(dias):
            # Campo Entrada
            self.fields[f'horario_{i}_entrada'] = forms.TimeField(required=False, widget=time_widget, label=f"Entrada {dia}")
            # Campo Salida
            self.fields[f'horario_{i}_salida'] = forms.TimeField(required=False, widget=time_widget, label=f"Salida {dia}")
            # Campo Descanso
            self.fields[f'horario_{i}_descanso'] = forms.BooleanField(required=False, widget=check_widget, label="Descanso")

        # Si estamos editando, precargar los valores
        if self.instance.pk and self.instance.usa_horario_variable:
            horarios = self.instance.horarios_dias.all()
            for h in horarios:
                self.initial[f'horario_{h.dia_semana}_entrada'] = h.hora_entrada
                self.initial[f'horario_{h.dia_semana}_salida'] = h.hora_salida
                self.initial[f'horario_{h.dia_semana}_descanso'] = h.es_dia_libre

    def save(self, commit=True):
        empleado = super().save(commit=False)
        if commit:
            empleado.save()
            
            # Gestionar horarios variables
            if empleado.usa_horario_variable:
                for i in range(7):
                    entrada = self.cleaned_data.get(f'horario_{i}_entrada')
                    salida = self.cleaned_data.get(f'horario_{i}_salida')
                    descanso = self.cleaned_data.get(f'horario_{i}_descanso')
                    
                    # Buscar o crear el horario para ese día
                    HorarioDia.objects.update_or_create(
                        empleado=empleado,
                        dia_semana=i,
                        defaults={
                            'hora_entrada': entrada,
                            'hora_salida': salida,
                            'es_dia_libre': descanso
                        }
                    )
            else:
                # Si se desactiva, podríamos borrar los horarios viejos o dejarlos ahí por si vuelve a activar
                # Por limpieza, los borramos:
                empleado.horarios_dias.all().delete()
                
        return empleado

class ConfiguracionForm(forms.ModelForm):
    # Formulario para la configuración general y AÑADIR nuevos administradores
    nuevo_admin_usuario = forms.CharField(
        label="Nuevo administrador (usuario)",
        max_length=100, 
        required=False, 
        help_text="Deja en blanco si no quieres añadir un nuevo administrador."
    )
    nuevo_admin_password = forms.CharField(
        label="Nuevo administrador (contraseña)",
        widget=forms.PasswordInput, 
        required=False
    )

    class Meta:
        model = Configuracion
        fields = ['minutos_tolerancia_entrada']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-yellow-500 focus:border-yellow-500 block w-full p-2.5"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = common_classes
            if field_name == 'nuevo_admin_password':
                 field.widget.attrs['placeholder'] = '••••••••'

    def clean(self):
        cleaned_data = super().clean()
        usuario = cleaned_data.get("nuevo_admin_usuario")
        password = cleaned_data.get("nuevo_admin_password")

        if usuario and not password:
            self.add_error('nuevo_admin_password', "La contraseña no puede estar vacía si se proporciona un usuario.")
        
        if usuario and User.objects.filter(username=usuario).exists():
            self.add_error('nuevo_admin_usuario', "Este nombre de usuario ya existe.")

        return cleaned_data

class AdminUpdateForm(forms.ModelForm):
    # Formulario para EDITAR administradores existentes
    password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
        help_text="Deja en blanco para no cambiar la contraseña."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-yellow-500 focus:border-yellow-500 block w-full p-2.5"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = common_classes
            if field_name == 'password':
                field.widget.attrs['placeholder'] = '••••••••'

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user