from django.shortcuts import render, redirect
from django.contrib import messages
from ..forms import RegistroUsuariosForm, RegistroAdminForm, LoginForm
from ..models import RegistroUsuarios, RegistroAdmin

def registro_usuario(request):
    if request.method == 'POST':
        form = RegistroUsuariosForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de usuario exitoso.")
            return redirect('login_usuario')
    else:
        form = RegistroUsuariosForm()
    return render(request, 'evaluacionescl/registro_usuario.html', {'form': form})

def registro_admin(request):
    if request.method == 'POST':
        form = RegistroAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de administrador exitoso.")
            return redirect('login_admin')
    else:
        form = RegistroAdminForm()
    return render(request, 'evaluacionescl/registro_admin.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                usuario = RegistroUsuarios.objects.get(matricula=form.cleaned_data['matricula'])
                if usuario.check_contrasena(form.cleaned_data['contrasena']):
                    request.session['usuario_id'] = usuario.id
                    request.session['nombre_usuario'] = usuario.nombre
                    return redirect('dashboard_usuario')
                else:
                    messages.error(request, "Contraseña incorrecta.")
            except RegistroUsuarios.DoesNotExist:
                messages.error(request, "Usuario no encontrado.")
    else:
        form = LoginForm()
    return render(request, 'evaluacionescl/login_usuario.html', {'form': form})

def login_admin(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                admin = RegistroAdmin.objects.get(matricula=form.cleaned_data['matricula'])
                if admin.check_contrasena(form.cleaned_data['contrasena']):
                    request.session['admin_id'] = admin.id
                    request.session['nombre_admin'] = admin.nombre
                    return redirect('dashboard_admin')
                else:
                    messages.error(request, "Contraseña incorrecta.")
            except RegistroAdmin.DoesNotExist:
                messages.error(request, "Administrador no encontrado.")
    else:
        form = LoginForm()
    return render(request, 'evaluacionescl/login_admin.html', {'form': form})

def logout_usuario(request):
    request.session.flush()
    messages.success(request,     
    "Sesión cerrada correctamente.\n"
    "¡Gracias por participar!\n"
    "Vuelve a iniciar sesión cuando lo desees.")
    return redirect('login_usuario')
