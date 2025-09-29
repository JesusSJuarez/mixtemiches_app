from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.views.decorators.http import require_POST
from datetime import datetime
from .models import Empleado, RegistroAsistencia, Configuracion
from .forms import EmpleadoForm, ConfiguracionForm
import qrcode
import io
from openpyxl import Workbook
from django.contrib.auth.models import User
from django.contrib import messages
# --- Nuevas importaciones para manipular imágenes ---
from PIL import Image, ImageDraw, ImageFont

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
                next_url = request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('bitacora:panel_empleados')
    else:
        form = AuthenticationForm()
    
    return render(request, 'bitacora/login.html', {'form': form})

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
        'empleados_inactivos': empleados_inactivos,
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
@require_POST
def desactivar_empleado(request: HttpRequest, empleado_id: int) -> HttpResponse:
    empleado = get_object_or_404(Empleado, id=empleado_id)
    empleado.is_active = False
    empleado.save()
    return redirect('bitacora:panel_empleados')

@login_required
@require_POST
def reactivar_empleado(request: HttpRequest, empleado_id: int) -> HttpResponse:
    empleado = get_object_or_404(Empleado, id=empleado_id)
    empleado.is_active = True
    empleado.save()
    return redirect('bitacora:panel_empleados')

@login_required
@require_POST
def marcar_asistencia_panel(request: HttpRequest, empleado_id: int, accion: str) -> JsonResponse:
    empleado = get_object_or_404(Empleado, id=empleado_id)
    ahora = timezone.localtime(timezone.now())

    config = Configuracion.objects.first()
    minutos_tolerancia = config.minutos_tolerancia_entrada if config else 0
    
    if accion == 'entrada':
        ya_existe_entrada = RegistroAsistencia.objects.filter(
            empleado=empleado, 
            fecha_hora_entrada__date=ahora.date()
        ).exists()

        if ya_existe_entrada:
            return JsonResponse({'status': 'error', 'message': f"{empleado.nombre} ya tiene una entrada registrada hoy."})
        
        hora_limite = (datetime.combine(ahora.date(), empleado.hora_entrada_supuesta) + timezone.timedelta(minutes=minutos_tolerancia)).time()
        llego_tarde = ahora.time() > hora_limite
        RegistroAsistencia.objects.create(empleado=empleado, fecha_hora_entrada=ahora, llego_tarde=llego_tarde)
        
        return JsonResponse({'status': 'success', 'message': f"Entrada registrada para {empleado.nombre}."})

    elif accion == 'salida':
        ultimo_registro = RegistroAsistencia.objects.filter(empleado=empleado, fecha_hora_salida__isnull=True).order_by('-fecha_hora_entrada').first()
        if ultimo_registro:
            ultimo_registro.fecha_hora_salida = ahora
            ultimo_registro.save()
            return JsonResponse({'status': 'success', 'message': f"Salida registrada para {empleado.nombre}."})
        else:
            return JsonResponse({'status': 'error', 'message': f"No se encontró un registro de entrada abierto para {empleado.nombre}."})
    
    return JsonResponse({'status': 'error', 'message': 'Acción no válida.'})
    
@login_required
def generar_qr_empleado(request: HttpRequest, codigo_empleado_uuid: str) -> HttpResponse:
    """
    Genera una imagen de código QR que incluye el nombre del empleado debajo.
    """
    try:
        empleado = get_object_or_404(Empleado, codigo_qr_unico=codigo_empleado_uuid)
        nombre_completo = f"{empleado.nombre} {empleado.apellido}"

        url_path = reverse('bitacora:pagina_seleccion', args=[codigo_empleado_uuid])
        url_registro = request.build_absolute_uri(url_path)

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(url_registro)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        # --- Lógica robusta para encontrar una fuente y componer la imagen ---
        qr_width, qr_height = qr_img.size
        padding = 20
        font_size = 40
        font = None

        # Lista de fuentes a intentar, de más común a menos
        font_names = ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
        for font_name in font_names:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break  # Si la encuentra, salimos del bucle
            except IOError:
                continue # Si no, probamos la siguiente

        # Si no encontró ninguna, usar la fuente por defecto
        if not font:
            print("ADVERTENCIA: No se encontró ninguna fuente TrueType. Usando fuente por defecto.")
            font = ImageFont.load_default()

        # Medir el texto con la fuente que se haya cargado
        temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
        text_bbox = temp_draw.textbbox((0, 0), nombre_completo, font=font)
        text_height = text_bbox[3] - text_bbox[1]
        text_width = text_bbox[2] - text_bbox[0]

        # Calcular el tamaño del lienzo final
        canvas_height = qr_height + text_height + padding
        new_img = Image.new('RGB', (qr_width, canvas_height), 'white')

        # Pegar el QR en el nuevo lienzo
        new_img.paste(qr_img, (0, 0))

        # Dibujar el texto centrado debajo del QR
        draw = ImageDraw.Draw(new_img)
        text_x = (qr_width - text_width) / 2
        text_y = qr_height + (padding / 2)
        draw.text((text_x, text_y), nombre_completo, font=font, fill="black")

        # Guardar la imagen final en un buffer de memoria
        buffer = io.BytesIO()
        new_img.save(buffer, "PNG")
        buffer.seek(0)

        return HttpResponse(buffer, content_type="image/png")

    except Exception as e:
        print(f"Error al generar QR con nombre: {e}")
        return HttpResponse(f"Error generando QR: {e}", status=500)

# --- Vistas de Flujo de Asistencia (QR) ---

@login_required
def pagina_seleccion_accion(request: HttpRequest, codigo_empleado_uuid: str) -> HttpResponse:
    empleado = get_object_or_404(Empleado, codigo_qr_unico=codigo_empleado_uuid, is_active=True)
    context = {'empleado': empleado}
    return render(request, 'bitacora/pagina_seleccion.html', context)

@login_required
def registrar_asistencia(request: HttpRequest, codigo_empleado_uuid: str, accion: str) -> HttpResponse:
    empleado = get_object_or_404(Empleado, codigo_qr_unico=codigo_empleado_uuid)
    ahora = timezone.localtime(timezone.now())
    mensaje, es_error = "", False

    config = Configuracion.objects.first()
    minutos_tolerancia = config.minutos_tolerancia_entrada if config else 0
    
    if accion == 'entrada':
        ya_existe_entrada = RegistroAsistencia.objects.filter(
            empleado=empleado, 
            fecha_hora_entrada__date=ahora.date()
        ).exists()

        if ya_existe_entrada:
            mensaje = f"Error: {empleado.nombre} ya tiene una entrada registrada hoy."
            es_error = True
        else:
            hora_limite = (datetime.combine(ahora.date(), empleado.hora_entrada_supuesta) + timezone.timedelta(minutes=minutos_tolerancia)).time()
            llego_tarde = ahora.time() > hora_limite
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
            mensaje, es_error = f"Error: No se encontró un registro de entrada abierto para {empleado.nombre}.", True
    else:
        mensaje, es_error = "Error: Acción no válida.", True
        
    context = {'mensaje': mensaje, 'es_error': es_error}
    return render(request, 'bitacora/resultado_registro.html', context)

# --- Vistas de Reportes ---

@login_required
def reportes_view(request: HttpRequest) -> HttpResponse:
    registros = RegistroAsistencia.objects.select_related('empleado').order_by('-fecha_hora_entrada')
    
    empleado_id = request.GET.get('empleado_id')
    fecha_str = request.GET.get('fecha')

    if empleado_id:
        registros = registros.filter(empleado_id=empleado_id)
    
    if fecha_str:
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            registros = registros.filter(fecha_hora_entrada__date=fecha_obj)
        except ValueError:
            pass

    context = {
        'registros': registros,
        'todos_los_empleados': Empleado.objects.filter(is_active=True).order_by('nombre'),
    }
    return render(request, 'bitacora/reportes.html', context)

@login_required
def exportar_excel_view(request: HttpRequest) -> HttpResponse:
    registros = RegistroAsistencia.objects.select_related('empleado').order_by('-fecha_hora_entrada')
    
    empleado_id = request.GET.get('empleado_id')
    fecha_str = request.GET.get('fecha')

    if empleado_id:
        registros = registros.filter(empleado_id=empleado_id)
    
    if fecha_str:
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            registros = registros.filter(fecha_hora_entrada__date=fecha_obj)
        except ValueError:
            pass

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte de Asistencia"

    headers = ["ID Registro", "Empleado", "Fecha Entrada", "Hora Entrada", "Fecha Salida", "Hora Salida", "Llegó Tarde"]
    ws.append(headers)

    for registro in registros:
        local_entrada = timezone.localtime(registro.fecha_hora_entrada)
        fecha_salida, hora_salida = '', ''
        if registro.fecha_hora_salida:
            local_salida = timezone.localtime(registro.fecha_hora_salida)
            fecha_salida = local_salida.strftime('%d/%m/%Y')
            hora_salida = local_salida.strftime('%H:%M:%S')
        
        ws.append([
            registro.id, str(registro.empleado),
            local_entrada.strftime('%d/%m/%Y'), local_entrada.strftime('%H:%M:%S'),
            fecha_salida, hora_salida,
            "Sí" if registro.llego_tarde else "No"
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reporte_asistencia.xlsx'
    wb.save(response)
    return response

@login_required
@require_POST
def eliminar_registro_asistencia(request: HttpRequest, registro_id: int) -> HttpResponse:
    registro = get_object_or_404(RegistroAsistencia, id=registro_id)
    registro.delete()
    return redirect('bitacora:reportes')

# --- Vista de Configuración ---

@login_required
def configuracion_view(request: HttpRequest) -> HttpResponse:
    config, created = Configuracion.objects.get_or_create(id=1)

    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            
            nuevo_usuario = form.cleaned_data.get('nuevo_admin_usuario')
            nuevo_password = form.cleaned_data.get('nuevo_admin_password')

            if nuevo_usuario and nuevo_password:
                if User.objects.filter(username=nuevo_usuario).exists():
                     messages.error(request, f'El usuario "{nuevo_usuario}" ya existe.')
                else:
                    User.objects.create_superuser(username=nuevo_usuario, password=nuevo_password)
                    messages.success(request, f'¡Administrador "{nuevo_usuario}" creado con éxito!')

            messages.success(request, '¡Configuración guardada correctamente!')
            return redirect('bitacora:configuracion')
    else:
        form = ConfiguracionForm(instance=config)

    return render(request, 'bitacora/configuracion.html', {'form': form})

