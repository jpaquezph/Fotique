"""Respaldos, restauración y estado de la base de datos."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

from ...util import dir_respaldos, fecha_legible
from ..theme import BORDE, FONDO, GRIS_TEXTO, RADIO, TEXTO_SUAVE
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase


class VistaRespaldos(VistaBase):
    clave = "respaldos"
    titulo = "Respaldo y mantenimiento"
    descripcion = "Exportación e importación de la base de datos"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(2, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        boton(barra, "Crear respaldo…", self._crear_respaldo, color="exito").pack(
            side="left", padx=(0, 6))
        boton(barra, "Restaurar…", self._restaurar, color="peligro").pack(
            side="left", padx=(0, 6))
        boton_secundario(barra, "Verificar integridad", self._verificar).pack(
            side="left", padx=(0, 6))
        boton_secundario(barra, "Abrir carpeta", self._abrir_carpeta).pack(
            side="left", padx=(0, 6))

        ficha = ctk.CTkFrame(contenedor, corner_radius=RADIO, fg_color=FONDO,
                             border_width=1, border_color=BORDE)
        ficha.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ficha.grid_columnconfigure(1, weight=1)
        self._datos: dict[str, ctk.CTkLabel] = {}
        self._integridad: bool | None = None  # se recalcula al verificar o restaurar
        for i, (clave, etiqueta) in enumerate([
            ("ruta", "Archivo de base de datos"),
            ("tamano", "Tamaño"),
            ("modificado", "Última modificación"),
            ("registros", "Registros"),
            ("respaldos", "Respaldos disponibles"),
            ("integridad", "Integridad"),
        ]):
            ctk.CTkLabel(ficha, text=etiqueta, font=("Segoe UI", 11, "bold"),
                         anchor="w").grid(row=i, column=0, sticky="w",
                                          padx=16, pady=((10 if i == 0 else 2), (10 if i == 5 else 2)))
            valor = ctk.CTkLabel(ficha, text="—", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
            valor.grid(row=i, column=1, sticky="ew", padx=(8, 16),
                       pady=((10 if i == 0 else 2), (10 if i == 5 else 2)))
            self._datos[clave] = valor

        columnas = [
            {"clave": "archivo", "titulo": "Archivo", "ancho": 340},
            {"clave": "fecha", "titulo": "Creado", "ancho": 170, "anchor": "center"},
            {"clave": "tamano", "titulo": "Tamaño", "ancho": 130, "anchor": "e"},
        ]
        self.tabla = Tabla(contenedor, columnas, altura=4,
                           recordar=(self.repos, "columnas.respaldos"))
        self.tabla.grid(row=2, column=0, sticky="nsew")
        ctk.CTkLabel(contenedor,
                     text="Consejo: copie la carpeta de respaldos a un disco externo "
                          "o nube de forma periódica.",
                     font=("Segoe UI", 10), text_color=TEXTO_SUAVE,
                     anchor="w").grid(row=3, column=0, sticky="ew", pady=(6, 0))

    def refrescar(self) -> None:
        ruta = Path(self.app.ruta_db)
        self._datos["ruta"].configure(text=str(ruta))
        if ruta.exists():
            stats = ruta.stat()
            self._datos["tamano"].configure(text=f"{stats.st_size / 1024:.1f} KB")
            self._datos["modificado"].configure(
                text=datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")
            )
        else:
            self._datos["tamano"].configure(text="—")
            self._datos["modificado"].configure(text="—")

        resumen = self.repos.resumen()
        self._datos["registros"].configure(
            text=f"{resumen['equipos']} equipos · {resumen['fotografos']} fotógrafos · "
            f"{resumen['clientes']} clientes · {resumen['proyectos']} proyectos · "
            f"{resumen['servicios']} servicios · {resumen['contratos']} contratos"
        )

        carpeta = dir_respaldos()
        archivos = sorted(carpeta.glob("*.db"), reverse=True)
        self._datos["respaldos"].configure(text=f"{len(archivos)} archivo(s) en {carpeta}")
        if self._integridad is None:
            self._integridad = self.app.db.verificar_integridad()
        self._datos["integridad"].configure(
            text="OK" if self._integridad else "Revisar"
        )

        filas, objetos = [], []
        for archivo in archivos:
            stats = archivo.stat()
            filas.append([
                archivo.name,
                fecha_legible(archivo.stem.split("_")[-1])
                or datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y"),
                f"{stats.st_size / 1024:.1f} KB",
            ])
            objetos.append(archivo)
        self.tabla.actualizar(filas, objetos)
        if not filas:
            self._datos["respaldos"].configure(text=f"Sin respaldos todavía · {carpeta}")

    # -- acciones ----------------------------------------------------------- #
    def _crear_respaldo(self) -> None:
        destino = filedialog.asksaveasfilename(
            parent=self, title="Crear respaldo de la base de datos",
            defaultextension=".db", initialdir=str(dir_respaldos()),
            filetypes=[("Base SQLite", "*.db"), ("SQLite", "*.sqlite")],
        )
        if not destino:
            return

        def accion():
            ruta = self.app.db.respaldar(destino)
            self.informar("Respaldo creado", f"Archivo guardado en:\n{ruta}")

        self.ejecutar(accion)

    def _restaurar(self) -> None:
        if not self.app.es_admin:  # el respaldo también reemplaza a los usuarios
            self.advertir("Sólo administradores",
                          "Restaurar un respaldo reemplaza toda la base, incluidas "
                          "las cuentas de usuario. Pídaselo a un administrador.")
            return
        origen = filedialog.askopenfilename(
            parent=self, title="Seleccionar respaldo a restaurar",
            initialdir=str(dir_respaldos()),
            filetypes=[("Base SQLite", "*.db *.sqlite"), ("Todos", "*.*")],
        )
        if not origen:
            return
        if not self.confirmar(
            "Restaurar respaldo",
            "Se reemplazará TODA la base actual por el archivo seleccionado.\n"
            "Se conserva una copia de la base actual con la extensión .anterior.",
            texto_si="Restaurar",
        ):
            return
        self._integridad = None
        self.ejecutar(lambda: self.app.db.restaurar(origen))
        # el respaldo trae sus propios usuarios: la sesión puede haber dejado de valer
        ventana = getattr(self.app, "ventana", None)
        if ventana is not None:
            ventana.validar_sesion()

    def _verificar(self) -> None:
        try:
            ok = self.app.db.verificar_integridad()
        except Exception as exc:  # noqa: BLE001
            self.advertir("Verificación fallida", str(exc))
            return
        self._integridad = ok
        self._datos["integridad"].configure(text="OK" if ok else "Revisar")
        if ok:
            self.informar("Base sana", "PRAGMA integrity_check: OK")
        else:
            self.advertir("Base dañada", "El verificador detectó inconsistencias.")

    def _abrir_carpeta(self) -> None:
        import os

        carpeta = dir_respaldos()
        os.startfile(carpeta)  # noqa: S606 - acción del usuario en Windows
