from django import forms
from .models import Empleado, Configuracion
from django.contrib.auth.models import User

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido', 'puesto', 'hora_entrada_supuesta', 'hora_salida_supuesta']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition',
                'placeholder': 'Ej. Juan'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition',
                'placeholder': 'Ej. Pérez'
            }),
            'puesto': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition',
                'placeholder': 'Ej. Mesero'
            }),
            'hora_entrada_supuesta': forms.TimeInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition',
                'type': 'time'
            }),
            'hora_salida_supuesta': forms.TimeInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500 transition',
                'type': 'time'
            }),
        }
        
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
        # Aplicar estilos a todos los campos
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
        # Aplicar estilos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = common_classes
            if field_name == 'password':
                field.widget.attrs['placeholder'] = '••••••••'

    def save(self, commit=True):
        # Sobrescribimos el método save para manejar la contraseña
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        
        if password:
            user.set_password(password)
            
        if commit:
            user.save()
            
        return user