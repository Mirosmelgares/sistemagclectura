import os
import random
import fitz
import spacy
import torch
import numpy as np
from torch.nn.functional import softmax
from transformers import BertTokenizer, BertForSequenceClassification
from django.shortcuts import render, redirect
from django.conf import settings
from ..models import RegistroUsuarios, EvaluacionLecturaIndividual, EvaluacionLectura

# Cargar modelo NLP y BERT
nlp = spacy.load("es_core_news_md")
model_path = "trained_model"
model = BertForSequenceClassification.from_pretrained(model_path)
tokenizer = BertTokenizer.from_pretrained(model_path)
if torch.cuda.is_available():
    model.to('cuda')

CLASS_NAMES = [
    "asociativa", "elaborativa", "predictiva",
    "no_inferencia_parafrasis", "no_inferencia_sinsentido"
]

import re
import fitz

def extraer_texto_limpio(pdf_path):
    doc = fitz.open(pdf_path)
    texto = "\n".join(pagina.get_text("text") for pagina in doc)

    # Eliminar URLs
    texto = re.sub(r'https?://\S+|www\.\S+', '', texto)

    # Eliminar líneas con palabras como Referencias o Bibliografía
    texto = re.sub(r'(?i)^.*\b(Referencias|Bibliografía)\b.*$', '', texto, flags=re.MULTILINE)

    # Eliminar citas tipo (Apellido, Año)
    texto = re.sub(r'\([A-Z][a-z]+,\s*\d{4}\)', '', texto)

    # Eliminar referencias estilo científico tipo “2016;569-70:1545-52.”
    texto = re.sub(r'\d{4};\d+-\d+:\d+-\d+\.?', '', texto)

    # Eliminar nombres largos en mayúsculas (encabezados o instituciones)
    texto = re.sub(r'^[A-Z\s]{5,}$', '', texto, flags=re.MULTILINE)

    # Eliminar números de página sueltos
    texto = re.sub(r'^\s*\d+\s*$', '', texto, flags=re.MULTILINE)

    # Compactar texto, quitar saltos innecesarios
    texto = re.sub(r'\n+', '\n', texto)
    texto = re.sub(r'\s{2,}', ' ', texto).strip()

    return texto



import random
import spacy
nlp = spacy.load("es_core_news_md")

def segmentar_texto(texto, min_palabras=50, max_palabras=80):
    doc = nlp(texto)
    oraciones = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    fragmentos = []
    bloque = []
    total_palabras = 0

    for oracion in oraciones:
        palabras = len(oracion.split())
        if total_palabras + palabras <= max_palabras:
            bloque.append(oracion)
            total_palabras += palabras
        else:
            if total_palabras >= min_palabras:
                fragmentos.append(" ".join(bloque))
            bloque = [oracion]
            total_palabras = palabras

    if bloque and total_palabras >= min_palabras:
        fragmentos.append(" ".join(bloque))

    return random.choice(fragmentos) if fragmentos else ""


def calcular_puntaje(inf):
    return {
        "asociativa": 2,
        "elaborativa": 3,
        "predictiva": 3,
        "no_inferencia_parafrasis": 1,
        "no_inferencia_sinsentido": 0
    }.get(inf, 0)

def calcular_porcentaje(prom):
    return (prom / 3) * 100 if prom is not None else 0

from time import time

def mostrar_texto_pdf(request):
    tipo_texto = request.session.get("tipo_texto")
    usuario_id = request.session.get("usuario_id")
    if not tipo_texto or not usuario_id:
        return redirect("seleccion_tipo_texto")

    usuario = RegistroUsuarios.objects.get(id=usuario_id)

    # 1. Verificar si hay una lectura pendiente
    pendiente = EvaluacionLecturaIndividual.objects.filter(
        usuario=usuario,
        tipo_texto=tipo_texto,
        fragmento="pendiente"
    ).order_by("-fecha_lectura").first()

    if pendiente:
        texto_seleccionado = pendiente.titulo_lectura
    else:
        carpeta = os.path.join(settings.MEDIA_ROOT, "bancotext", tipo_texto)
        archivos = [f for f in os.listdir(carpeta) if f.endswith(".pdf")]

        leidos = EvaluacionLecturaIndividual.objects.filter(
            usuario=usuario,
            tipo_texto=tipo_texto
        ).values_list("titulo_lectura", flat=True)

        no_leidos = [a for a in archivos if a not in leidos]

        if not no_leidos:
            return render(request, "evaluacionescl/no_textos_disponibles.html", {
                "mensaje": "Has leído todos los textos de esta categoría."
            })

        texto_seleccionado = random.choice(no_leidos)

        EvaluacionLecturaIndividual.objects.create(
            usuario=usuario,
            tipo_texto=tipo_texto,
            titulo_lectura=texto_seleccionado,
            fragmento="pendiente",
            instruccion="pendiente"
        )

    ruta = f"{settings.MEDIA_URL}bancotext/{tipo_texto}/{texto_seleccionado}"

    return render(request, "evaluacionescl/mostrar_texto_pdf.html", {
        "ruta_texto": ruta,
        "titulo": texto_seleccionado,
        "timestamp": int(time())  # ← aquí va esto
    })


def mostrar_fragmento(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login_usuario")

    usuario = RegistroUsuarios.objects.get(id=usuario_id)

    evaluacion = EvaluacionLecturaIndividual.objects.filter(
        usuario=usuario,
        fragmento__in=["pendiente", None]
    ).order_by("-fecha_lectura").first()

    # Si no hay evaluación pendiente, buscar la última sin responder
    if not evaluacion:
        evaluacion = EvaluacionLecturaIndividual.objects.filter(
            usuario=usuario,
            respuesta_usuario__isnull=True
        ).order_by("-fecha_lectura").first()

    if not evaluacion:
        return render(request, "evaluacionescl/no_fragmento.html", {
            "mensaje": "Aún no has seleccionado un texto para evaluar. Por favor, elige una categoría primero."
        })

    # Si ya se generó un fragmento antes, lo usamos tal cual
    if evaluacion.fragmento != "pendiente" and evaluacion.fragmento.strip():
        return render(request, "evaluacionescl/fragmento_lectura.html", {
            "fragmento": evaluacion.fragmento,
            "instruccion": evaluacion.instruccion,
            "evaluacion_id": evaluacion.id
        })

    # Si aún no tiene fragmento, generamos uno
    titulo = evaluacion.titulo_lectura
    tipo_texto = evaluacion.tipo_texto
    pdf_path = os.path.join(settings.MEDIA_ROOT, "bancotext", tipo_texto, titulo)

    if not os.path.exists(pdf_path):
        return render(request, "error.html", {"mensaje": "No se encontró el archivo del texto."})

    texto_limpio = extraer_texto_limpio(pdf_path)
    fragmento = segmentar_texto(texto_limpio)
    if not fragmento:
        return render(request, "error.html", {"mensaje": "No se pudo segmentar el texto correctamente."})

    instrucciones = [
        "Escribe lo que entendiste del siguiente fragmento:",
        "¿A qué se refiere el siguiente fragmento?:",
        "Escribe con tus palabras la idea del siguiente fragmento:"
    ]
    instruccion = random.choice(instrucciones)

    evaluacion.fragmento = fragmento
    evaluacion.instruccion = instruccion
    evaluacion.save()

    return render(request, "evaluacionescl/fragmento_lectura.html", {
        "fragmento": fragmento,
        "instruccion": instruccion,
        "evaluacion_id": evaluacion.id
    })



def classify_inference(sentence, inference):
    model.eval()
    with torch.no_grad():
        inputs = tokenizer.encode_plus(sentence, inference, return_tensors="pt", truncation=True, padding=True)
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
        logits = model(**inputs).logits
        probs = softmax(logits, dim=1).cpu().numpy()[0]
        return CLASS_NAMES[probs.argmax()], probs

from django.contrib import messages  # Asegúrate de tener esto importado

def guardar_respuesta(request):
    if request.method == "POST":
        eval_id = request.POST.get("evaluacion_id")
        respuesta = request.POST.get("respuesta", "").strip()

        evaluacion = EvaluacionLecturaIndividual.objects.get(id=eval_id)

        if evaluacion.respuesta_usuario:
            messages.warning(request, "Esta evaluación ya fue respondida.")
            return redirect("resultados_usuario")

        # Clasificación y puntaje
        evaluacion.respuesta_usuario = respuesta
        clase, _ = classify_inference(evaluacion.fragmento, respuesta)
        if not clase:
            clase = "no_inferencia_sinsentido"
        evaluacion.puntaje = calcular_puntaje(clase)
        evaluacion.tipo_inferencia = clase
        evaluacion.save()

        # Recalcular resumen
        usuario = evaluacion.usuario
        tipo = evaluacion.tipo_texto
        lecturas = EvaluacionLecturaIndividual.objects.filter(
            usuario=usuario,
            tipo_texto=tipo,
            puntaje__isnull=False
        )

        total = lecturas.count()
        puntos = sum([l.puntaje for l in lecturas])
        promedio = puntos / total if total > 0 else 0
        porcentaje = calcular_porcentaje(promedio)

        if porcentaje >= 89:
            nivel = "Alto"
        elif porcentaje >= 67:
            nivel = "Medio"
        elif porcentaje >= 34:
            nivel = "Bajo"
        else:
            nivel = "Deficiente"

        resumen, creado = EvaluacionLectura.objects.get_or_create(
            usuario=usuario,
            tipo_texto=tipo,
            defaults={
                "textos_leidos": total,
                "porcentaje": porcentaje,
                "nivel_comprension": nivel
            }
        )

        if not creado:
            resumen.textos_leidos = total
            resumen.porcentaje = porcentaje
            resumen.nivel_comprension = nivel
            resumen.save()

        return redirect("resultados_usuario")

    return redirect("dashboard_usuario")

def resultados_usuario(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login_usuario")

    usuario = RegistroUsuarios.objects.get(id=usuario_id)
    tipos = ["Argumentativo", "Descriptivo", "Expositivo", "Narrativo"]
    resultados = []

    for tipo in tipos:
        lecturas = EvaluacionLecturaIndividual.objects.filter(usuario=usuario, tipo_texto=tipo)
        total = lecturas.count()
        if total:
            suma = sum([e.puntaje for e in lecturas if e.puntaje is not None])
            promedio = suma / total
            porcentaje = calcular_porcentaje(promedio)
            if porcentaje >= 89:
                nivel = f"Alto (Comprensión profunda) - {int(porcentaje)}%"
            elif porcentaje >= 67:
                nivel = f"Medio (Comprensión adecuada) - {int(porcentaje)}%"
            elif porcentaje >= 34:
                nivel = f"Bajo (Comprensión superficial) - {int(porcentaje)}%"
            else:
                nivel = f"Deficiente (No comprensión) - {int(porcentaje)}%"
        else:
            nivel = "Sin evaluar"

        resultados.append({"tipo": tipo, "cantidad": total, "nivel": nivel})

    # Última inferencia del usuario
    ultima_eval = EvaluacionLecturaIndividual.objects.filter(usuario=usuario).order_by("-fecha_lectura").first()
        # Última inferencia del usuario
    ultima_eval = EvaluacionLecturaIndividual.objects.filter(
        usuario=usuario,
        tipo_inferencia__isnull=False
    ).order_by("-fecha_lectura").first()

    inferencia_limpia = "Sin evaluar"  # Valor por defecto

    if ultima_eval and ultima_eval.tipo_inferencia:
        tipo = ultima_eval.tipo_inferencia
        if tipo == "no_inferencia_sinsentido":
            inferencia_limpia = "No inferencia: sin sentido"
        elif tipo == "no_inferencia_parafrasis":
            inferencia_limpia = "No inferencia: paráfrasis"
        else:
            inferencia_limpia = tipo.capitalize()


    return render(request, "evaluacionescl/tabla_resultados.html", {
        "resultados": resultados,
        "ultima_inferencia": inferencia_limpia
    })


def ver_grafica_tipo(request, tipo_texto):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login_usuario")

    usuario = RegistroUsuarios.objects.get(id=usuario_id)
    lecturas = EvaluacionLecturaIndividual.objects.filter(usuario=usuario, tipo_texto=tipo_texto).order_by('titulo_lectura', '-fecha_lectura')

    if not lecturas.exists():
        return render(request, "evaluacionescl/no_fragmento.html", {"mensaje": "No hay lecturas evaluadas de este tipo todavía."})

    titulos, porcentajes, tipos_inferencia, tooltips = [], [], [], []
    vistos = set()

    for l in lecturas:
        if l.titulo_lectura not in vistos:
            vistos.add(l.titulo_lectura)
            titulos.append(l.titulo_lectura)
            porcentaje = calcular_porcentaje(l.puntaje) if l.puntaje is not None else 0
            porcentajes.append(porcentaje)
            tooltips.append(f"{int(porcentaje)}%" if l.puntaje is not None else "Sin evaluar")

            tipo = l.tipo_inferencia
        # Limpieza y asignación segura
        if tipo == "no_inferencia_sinsentido":
                tipo = "No inferencia: sin sentido"
        elif tipo == "no_inferencia_parafrasis":
                tipo = "No inferencia: paráfrasis"
        elif tipo:
                tipo = tipo.capitalize()
        else:
                tipo = "No inferencia: sin sentido"  # Por defecto si está vacío o None


        tipos_inferencia.append(tipo)

    return render(request, "evaluacionescl/grafica_texto_tipo.html", {
        "tipo": tipo_texto,
        "titulos": titulos,
        "porcentajes": porcentajes,
        "tipos_inferencia": tipos_inferencia,
        "tooltips": tooltips
    })
