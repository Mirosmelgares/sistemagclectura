from django.shortcuts import render, redirect
from ..models import RegistroUsuarios

def dashboard_usuario(request):
    if 'usuario_id' not in request.session:
        return redirect('login_usuario')
    
    nombre_usuario = request.session.get('nombre_usuario', '')
    return render(request, 'evaluacionescl/dashboard_usuario.html', {'nombre': nombre_usuario})


def seleccion_tipo_texto(request):
    tipos_texto = ["Argumentativo", "Descriptivo", "Expositivo", "Narrativo"]

    if request.method == "POST":
        tipo_seleccionado = request.POST.get("tipo_texto_seleccionado")
        request.session["tipo_texto"] = tipo_seleccionado
        return redirect("mostrar_texto_pdf")

    return render(request, "evaluacionescl/seleccion_tipo_texto.html", {"tipos_texto": tipos_texto})
