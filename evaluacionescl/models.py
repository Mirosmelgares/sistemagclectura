from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class RegistroUsuarios(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    edad = models.IntegerField()
    matricula = models.CharField(max_length=20, unique=True)
    cuatrimestre = models.CharField(max_length=10)
    contrasena = models.CharField(max_length=200)

    def set_contrasena(self, contrasena):
        """Método para cifrar la contraseña antes de guardarla"""
        self.contrasena = make_password(contrasena)

    def check_contrasena(self, contrasena):
        """Método para verificar si la contraseña coincide con el valor almacenado"""
        return check_password(contrasena, self.contrasena)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class RegistroAdmin(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    matricula = models.CharField(max_length=20, unique=True)
    contrasena = models.CharField(max_length=200)

    def set_contrasena(self, contrasena):
        """Método para cifrar la contraseña antes de guardarla"""
        self.contrasena = make_password(contrasena)

    def check_contrasena(self, contrasena):
        """Método para verificar si la contraseña coincide con el valor almacenado"""
        return check_password(contrasena, self.contrasena)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class EvaluacionLectura(models.Model):
    usuario = models.ForeignKey(RegistroUsuarios, on_delete=models.CASCADE)
    tipo_texto = models.CharField(max_length=100)
    textos_leidos = models.IntegerField()
    porcentaje = models.FloatField()
    nivel_comprension = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.usuario} - {self.tipo_texto}"

from django.db import models
from django.utils import timezone
from .models import RegistroUsuarios  # Asegúrate de importar tu modelo de usuario si no usas auth.User

class EvaluacionLecturaIndividual(models.Model):
    usuario = models.ForeignKey(RegistroUsuarios, on_delete=models.CASCADE)
    tipo_texto = models.CharField(max_length=50)
    titulo_lectura = models.CharField(max_length=255)
    
    fragmento = models.TextField(default="Fragmento no disponible")  # evita el error de migración
    instruccion = models.CharField(max_length=255, default="")       # en caso de que también sea nuevo

    respuesta_usuario = models.TextField(blank=True, null=True)  # opcional para que pueda quedar vacío
    puntaje = models.IntegerField(blank=True, null=True)         # también opcional hasta evaluar
    tipo_inferencia = models.CharField(max_length=100, blank=True, null=True)

    fecha_lectura = models.DateTimeField(auto_now_add=True)  # ok si ya migraste o diste default

    def __str__(self):
        return f"{self.usuario} - {self.titulo_lectura} - {self.tipo_texto}"


class VistaAdmin(models.Model):
    usuarios_total = models.IntegerField()
    tipo_texto = models.CharField(max_length=100)
    textos_total = models.IntegerField()
    puntaje_total = models.FloatField()
    nivel_comprension_global = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.tipo_texto} - Nivel: {self.nivel_comprension_global}"
