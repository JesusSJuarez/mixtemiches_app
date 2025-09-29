from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Empleado, RegistroAsistencia, Configuracion
from .forms import EmpleadoForm, ConfiguracionForm
import qrcode
import io
import openpyxl
from openpyxl.styles import Font, Alignment
from django.contrib import messages

# --- Vistas de Autenticación ---

def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect('bitacora:panel_empleados')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirección inteligente
                next_url = request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('bitacora:panel_empleados')
    else:
        form = AuthenticationForm()
    
    return render(request, 'bitacora/login.html', {'form': form, 'next': request.GET.get('next', '')})

@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('bitacora:login_view')

# --- Vistas del Panel de Administración Personalizado ---

@login_required
def panel_empleados(request: HttpRequest) -> HttpResponse:
    empleados_activos = Empleado.objects.filter(is_active=True).order_by('nombre')
    empleados_inactivos = Empleado.objects.filter(is_active=False).order_by('nombre')
    context = {
        'empleados_activos': empleados_activos,
        'empleados_inactivos': empleados_inactivos
    }
    return render(request, 'bitacora/panel_empleados.html', context)

@login_required
def agregar_empleado(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('bitacora:panel_empleados')
    else:
        form = EmpleadoForm()
    
    return render(request, 'bitacora/agregar_empleado.html', {'form': form})

@login_required
def desactivar_empleado(request: HttpRequest, empleado_id: int) -> HttpResponse:
    if request.method == 'POST':
        empleado = get_object_or_404(Empleado, id=empleado_id)
        empleado.is_active = False
        empleado.save()
    return redirect('bitacora:panel_empleados')

@login_required
def reactivar_empleado(request: HttpRequest, empleado_id: int) -> HttpResponse:
    if request.method == 'POST':
        empleado = get_object_or_404(Empleado, id=empleado_id)
        empleado.is_active = True
        empleado.save()
    return redirect('bitacora:panel_empleados')

@login_required
def marcar_asistencia_panel(request: HttpRequest, empleado_id: int, accion: str) -> JsonResponse:
    if request.method == 'POST':
        empleado = get_object_or_404(Empleado, id=empleado_id)
        ahora = timezone.localtime(timezone.now())
        
        if accion == 'entrada':
            hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            hoy_fin = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
            if RegistroAsistencia.objects.filter(empleado=empleado, fecha_hora_entrada__range=(hoy_inicio, hoy_fin)).exists():
                return JsonResponse({'status': 'error', 'message': f'Ya existe un registro de entrada para {empleado.nombre} hoy.'})

            config = Configuracion.objects.first()
            minutos_tolerancia = config.minutos_tolerancia_entrada if config else 0
            hora_entrada_con_tolerancia = (timezone.datetime.combine(ahora.date(), empleado.hora_entrada_supuesta) + timezone.timedelta(minutes=minutos_tolerancia)).time()
            llego_tarde = ahora.time() > hora_entrada_con_tolerancia

            RegistroAsistencia.objects.create(empleado=empleado, fecha_hora_entrada=ahora, llego_tarde=llego_tarde)
            return JsonResponse({'status': 'success', 'message': f'Entrada registrada para {empleado.nombre}.'})

        elif accion == 'salida':
            ultimo_registro = RegistroAsistencia.objects.filter(empleado=empleado, fecha_hora_salida__isnull=True).order_by('-fecha_hora_entrada').first()
            if ultimo_registro:
                ultimo_registro.fecha_hora_salida = ahora
                ultimo_registro.save()
                return JsonResponse({'status': 'success', 'message': f'Salida registrada para {empleado.nombre}.'})
            else:
                return JsonResponse({'status': 'error', 'message': f'No se encontró un registro de entrada abierto para {empleado.nombre}.'})

    return JsonResponse({'status': 'error', 'message': 'Petición no válida.'})

@login_required
def generar_qr_empleado(request: HttpRequest, codigo_empleado_uuid: str) -> HttpResponse:
    try:
        url_path = reverse('bitacora:pagina_seleccion', args=[codigo_empleado_uuid])
        url_registro = request.build_absolute_uri(url_path)
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
        qr.add_data(url_registro)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)
        return HttpResponse(buffer, content_type="image/png")
    except Exception as e:
        return HttpResponse(f"Error generando QR: {e}", status=500)

# --- Vistas de Registro de Asistencia (Flujo QR) ---

@login_required
def pagina_seleccion_accion(request: HttpRequest, codigo_empleado_uuid: str) -> HttpResponse:
    empleado = get_object_or_404(Empleado, codigo_qr_unico=codigo_empleado_uuid)
    return render(request, 'bitacora/pagina_seleccion.html', {'empleado': empleado})

@login_required
def registrar_asistencia(request: HttpRequest, codigo_empleado_uuid: str, accion: str) -> HttpResponse:
    empleado = get_object_or_404(Empleado, codigo_qr_unico=codigo_empleado_uuid)
    ahora = timezone.localtime(timezone.now())
    mensaje = ""
    es_error = False

    if accion == 'entrada':
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        hoy_fin = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
        if RegistroAsistencia.objects.filter(empleado=empleado, fecha_hora_entrada__range=(hoy_inicio, hoy_fin)).exists():
            mensaje = f"Error: Ya existe un registro de entrada para {empleado.nombre} hoy."
            es_error = True
        else:
            config = Configuracion.objects.first()
            minutos_tolerancia = config.minutos_tolerancia_entrada if config else 0
            hora_entrada_con_tolerancia = (timezone.datetime.combine(ahora.date(), empleado.hora_entrada_supuesta) + timezone.timedelta(minutes=minutos_tolerancia)).time()
            llego_tarde = ahora.time() > hora_entrada_con_tolerancia
            
            RegistroAsistencia.objects.create(empleado=empleado, fecha_hora_entrada=ahora, llego_tarde=llego_tarde)
            mensaje = f"Entrada registrada para {empleado.nombre} a las {ahora.strftime('%H:%M:%S')}."
            if llego_tarde:
                mensaje += " (Llegó tarde)"

    elif accion == 'salida':
        ultimo_registro = RegistroAsistencia.objects.filter(empleado=empleado, fecha_hora_salida__isnull=True).order_by('-fecha_hora_entrada').first()
        if ultimo_registro:
            ultimo_registro.fecha_hora_salida = ahora
            ultimo_registro.save()
            mensaje = f"Salida registrada para {empleado.nombre} a las {ahora.strftime('%H:%M:%S')}."
        else:
            mensaje = f"Error: No se encontró un registro de entrada abierto para {empleado.nombre}."
            es_error = True
    else:
        mensaje = "Error: Acción no válida."
        es_error = True
        
    return render(request, 'bitacora/resultado_registro.html', {'mensaje': mensaje, 'es_error': es_error})

# --- Vistas de Reportes ---

@login_required
def reportes_view(request: HttpRequest) -> HttpResponse:
    registros = RegistroAsistencia.objects.all().order_by('-fecha_hora_entrada')
    empleado_id = request.GET.get('empleado_id')
    fecha = request.GET.get('fecha')

    if empleado_id:
        registros = registros.filter(empleado__id=empleado_id)
    if fecha:
        registros = registros.filter(fecha_hora_entrada__date=fecha)
    
    context = {
        'registros': registros,
        'todos_los_empleados': Empleado.objects.filter(is_active=True).order_by('nombre')
    }
    return render(request, 'bitacora/reportes.html', context)

@login_required
def eliminar_registro_asistencia(request: HttpRequest, registro_id: int) -> HttpResponse:
    if request.method == 'POST':
        registro = get_object_or_404(RegistroAsistencia, id=registro_id)
        registro.delete()
    # Redirigir de vuelta a la página de reportes, manteniendo los filtros
    return redirect(request.META.get('HTTP_REFERER', 'bitacora:reportes'))


@login_required
def exportar_excel_view(request: HttpRequest) -> HttpResponse:
    registros = RegistroAsistencia.objects.all().order_by('-fecha_hora_entrada')
    empleado_id = request.GET.get('empleado_id')
    fecha = request.GET.get('fecha')

    if empleado_id:
        registros = registros.filter(empleado__id=empleado_id)
    if fecha:
        registros = registros.filter(fecha_hora_entrada__date=fecha)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Asistencia"

    headers = ["Empleado", "Fecha", "Hora Entrada", "Hora Salida", "Llegó Tarde"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    for registro in registros:
        hora_entrada_local = timezone.localtime(registro.fecha_hora_entrada)
        hora_salida_local = timezone.localtime(registro.fecha_hora_salida) if registro.fecha_hora_salida else None
        
        ws.append([
            f"{registro.empleado.nombre} {registro.empleado.apellido}",
            hora_entrada_local.strftime('%d/%m/%Y'),
            hora_entrada_local.strftime('%H:%M:%S'),
            hora_salida_local.strftime('%H:%M:%S') if hora_salida_local else '--',
            "Sí" if registro.llego_tarde else "No"
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reporte_asistencia.xlsx'
    wb.save(response)
    
    return response

# --- Vista de Configuración ---

@login_required
def configuracion_view(request: HttpRequest) -> HttpResponse:
    config_obj, created = Configuracion.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, instance=config_obj)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Configuración guardada correctamente!')

            nuevo_usuario = form.cleaned_data.get('nuevo_admin_usuario')
            nuevo_password = form.cleaned_data.get('nuevo_admin_password')

            if nuevo_usuario and nuevo_password:
                if User.objects.filter(username=nuevo_usuario).exists():
                     messages.error(request, f'El usuario "{nuevo_usuario}" ya existe.')
                else:
                    User.objects.create_superuser(username=nuevo_usuario, password=nuevo_password)
                    messages.success(request, f'¡Administrador "{nuevo_usuario}" creado con éxito!')
            
            return redirect('bitacora:configuracion')
    else:
        form = ConfiguracionForm(instance=config_obj)

    context = {
        'form': form,
        'usuarios': User.objects.all()
    }
    return render(request, 'bitacora/configuracion.html', context)

