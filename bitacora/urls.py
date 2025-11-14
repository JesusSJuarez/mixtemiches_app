from django.urls import path
from . import views

app_name = 'bitacora'

urlpatterns = [
    # --- Autenticación ---
    path('', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),

    # --- Panel de Administración ---
    path('panel/empleados/', views.panel_empleados, name='panel_empleados'),
    path('panel/empleados/agregar/', views.agregar_empleado, name='agregar_empleado'),
    path('panel/empleados/desactivar/<int:empleado_id>/', views.desactivar_empleado, name='desactivar_empleado'),
    path('panel/empleados/reactivar/<int:empleado_id>/', views.reactivar_empleado, name='reactivar_empleado'),
    path('panel/empleados/qr/<uuid:codigo_empleado_uuid>/', views.generar_qr_empleado, name='generar_qr_empleado'),
    path('panel/empleados/marcar_asistencia/<int:empleado_id>/<str:accion>/', views.marcar_asistencia_panel, name='marcar_asistencia_panel'),
    path('panel/empleados/editar/<int:empleado_id>/', views.editar_empleado_view, name='editar_empleado'),
    
    path('panel/reportes/', views.reportes_view, name='reportes'),
    path('panel/reportes/exportar/', views.exportar_excel_view, name='exportar_excel'),
    path('panel/reportes/eliminar/<int:registro_id>/', views.eliminar_registro_asistencia, name='eliminar_registro'),
    
    path('panel/configuracion/', views.configuracion_view, name='configuracion'),
    # --- Nuevas rutas para gestionar administradores ---
    path('panel/configuracion/editar/<int:user_id>/', views.editar_admin_view, name='editar_admin'),
    path('panel/configuracion/eliminar/<int:user_id>/', views.eliminar_admin_view, name='eliminar_admin'),

    # --- Flujo de Escaneo QR (estas no llevan /panel/) ---
    path('seleccionar/<uuid:codigo_empleado_uuid>/', views.pagina_seleccion_accion, name='pagina_seleccion'),
    path('registrar/<uuid:codigo_empleado_uuid>/<str:accion>/', views.registrar_asistencia, name='registrar_asistencia'),
]