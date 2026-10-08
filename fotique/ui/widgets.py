"""Componentes reutilizables de la interfaz (tablas, diálogos, campos)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Callable, Optional, Sequence

import tkinter as tk

import customtkinter as ctk
from tkinter import ttk

from ..domain.errors import DatosInvalidosError, FotiqueError
from .fechas import SelectorFecha
from .logo import aplicar_icono
from .theme import (
    ACENTO,
    BORDE,
    BORDE_FUERTE,
    BOTONES,
    FONDO,
    FUENTE_BOTON,
    FUENTE_DIALOGO,
    FUENTE_ETIQUETA,
    FUENTE_NORMAL,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    GRIS_TEXTO,
    RADIO,
    RESALTE,
    SEMINEGRITA,
    ROJO,
    TEXTO,
    TEXTO_BOTON,
    TEXTO_BOTON_INACTIVO,
    TEXTO_SUAVE,
    ancho_par,
    area_de_trabajo,
    colores_etiquetas,
    colores_tema,
    estilos_filas,
)

# --------------------------------------------------------------------------- #
# Conversiones de campos
# --------------------------------------------------------------------------- #


def parsear_fecha(texto: str) -> Optional[date]:
    """``30/09/2026`` o ``2026-09-30`` ➜ ``date`` (vacío ➜ ``None``)."""
    valor = (texto or "").strip()
    if not valor:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    raise DatosInvalidosError(f"Fecha inválida: {valor}. Use dd/mm/aaaa.")


def parsear_monto(texto: str) -> float:
    """Soporta ``1500000``, ``1.500.000,00`` y ``1,500,000.00``."""
    valor = (texto or "").strip().replace("$", "").replace(" ", "")
    if not valor:
        return 0.0
    negativo = valor.startswith("-")
    valor = valor.lstrip("-")
    if "," in valor and "." in valor:
        if valor.rfind(",") > valor.rfind("."):
            valor = valor.replace(".", "").replace(",", ".")  # 1.500.000,00
        else:
            valor = valor.replace(",", "")  # 1,500,000.00
    elif "," in valor:
        valor = valor.replace(",", ".")
    elif "." in valor:
        partes = valor.split(".")
        if len(partes) > 2 or (len(partes[1]) == 3 and len(partes[0]) <= 3):
            valor = valor.replace(".", "")  # 1.500.000
    try:
        monto = float(valor)
    except ValueError as exc:
        raise DatosInvalidosError(f"Importe inválido: {texto}") from exc
    return -monto if negativo else monto


# --------------------------------------------------------------------------- #
# Tabla (ttk.Treeview)
# --------------------------------------------------------------------------- #


class Tabla(ctk.CTkFrame):
    """Tabla con encabezados fijos, doble clic y selección de objeto."""

    def __init__(
        self,
        master: Any,
        columnas: Sequence[dict],
        *,
        doble_click: Optional[Callable[[Any], None]] = None,
        altura: int = 12,
        estilo: str = "Fotique.Treeview",
        lineas_verticales: bool = True,
        recordar: Optional[tuple[Any, str]] = None,
    ):
        """``recordar=(repos, clave)`` deja reordenar y ocultar las columnas
        (arrastrando el encabezado o con el botón «Columnas») y guarda la
        elección en la configuración bajo ``clave``."""
        super().__init__(master, fg_color=FONDO, border_width=1,
                         border_color=BORDE, corner_radius=RADIO)
        self.columnas = list(columnas)
        self._objetos: dict[str, Any] = {}
        self._doble_click = doble_click
        self._lineas_verticales = lineas_verticales
        self._recordar = recordar
        self._arrastrada: Optional[str] = None

        claves = [c["clave"] for c in self.columnas]
        self._orden = list(claves)
        self._ocultas: set[str] = set()
        self.tree = ttk.Treeview(
            self,
            columns=claves,
            show="headings",
            selectmode="browse",
            height=altura,
            style=estilo,
        )
        for col in self.columnas:
            self.tree.heading(col["clave"], text=col["titulo"])
            self.tree.column(
                col["clave"],
                width=col.get("ancho", 120),
                minwidth=col.get("min", 60),
                anchor=col.get("anchor", "w"),
                stretch=col.get("stretch", True),
            )
        self._colorear_etiquetas()

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                            style="Fotique.Vertical.TScrollbar")
        # Con «Columnas» la barra horizontal comparte la fila con el botón.
        pie = self if recordar is None else ctk.CTkFrame(self, fg_color="transparent")
        hsb = ttk.Scrollbar(pie, orient="horizontal", command=self.tree.xview,
                            style="Fotique.Horizontal.TScrollbar")
        # Las líneas de la grilla se redibujan cada vez que la tabla se desplaza.
        self._lineas_v: list[tk.Frame] = []
        self._lineas_h: list[tk.Frame] = []
        self._trazo_pendiente: Optional[str] = None

        def al_desplazar(barra: ttk.Scrollbar, *posicion: str) -> None:
            barra.set(*posicion)
            self._pedir_trazo()

        self.tree.configure(yscrollcommand=lambda *p: al_desplazar(vsb, *p),
                            xscrollcommand=lambda *p: al_desplazar(hsb, *p))

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(8, 0))
        if recordar is None:
            hsb.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))
        else:
            pie.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
            elegir = boton_secundario(pie, "Columnas", self.elegir_columnas,
                                      ancho=84, alto=22)
            elegir.configure(font=FUENTE_PEQUE)
            elegir.pack(side="right", padx=(8, 0))
            hsb.pack(side="left", fill="x", expand=True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._al_doble_clic)
        self.tree.bind("<Return>", self._al_doble_clic)
        self.tree.bind("<Configure>", self._pedir_trazo, add="+")
        # al arrastrar el borde de un encabezado cambia el ancho de la columna
        self.tree.bind("<B1-Motion>", self._pedir_trazo, add="+")
        self.tree.bind("<ButtonRelease-1>", self._pedir_trazo, add="+")
        if recordar is not None:
            self.tree.bind("<ButtonPress-1>", self._tomar_encabezado, add="+")
            self.tree.bind("<B1-Motion>", self._arrastrar_encabezado, add="+")
            self.tree.bind("<ButtonRelease-1>", self._soltar_encabezado, add="+")
            self._cargar_columnas()

    # -- orden y visibilidad de las columnas ------------------------------- #
    def orden_columnas(self) -> list[str]:
        """Claves de todas las columnas en el orden elegido (incluye las ocultas)."""
        return list(self._orden)

    def columnas_ocultas(self) -> list[str]:
        return [c for c in self._orden if c in self._ocultas]

    def columnas_visibles(self) -> list[str]:
        return [c for c in self._orden if c not in self._ocultas]

    def ordenar_columnas(self, orden: Sequence[str], ocultas: Sequence[str] = ()) -> None:
        """Fija el orden y qué columnas se ocultan. Las claves desconocidas se
        ignoran, las que falten van al final y siempre queda una a la vista."""
        claves = [c["clave"] for c in self.columnas]
        elegidas = [c for c in dict.fromkeys(orden) if c in claves]
        self._orden = elegidas + [c for c in claves if c not in elegidas]
        self._ocultas = {c for c in ocultas if c in claves}
        if not self.columnas_visibles():
            self._ocultas.clear()
        self.tree.configure(displaycolumns=self.columnas_visibles())
        self._pedir_trazo()

    def _encabezado_en(self, evento) -> Optional[str]:
        if self.tree.identify_region(evento.x, evento.y) != "heading":
            return None
        indice = int(self.tree.identify_column(evento.x).lstrip("#") or 0) - 1
        visibles = self.columnas_visibles()
        return visibles[indice] if 0 <= indice < len(visibles) else None

    def _tomar_encabezado(self, evento) -> None:
        self._arrastrada = self._encabezado_en(evento)

    def _arrastrar_encabezado(self, _evento) -> None:
        if self._arrastrada is not None:
            self.tree.configure(cursor="fleur")

    def _soltar_encabezado(self, evento) -> None:
        arrastrada, self._arrastrada = self._arrastrada, None
        self.tree.configure(cursor="")
        destino = self._encabezado_en(evento)
        if arrastrada is None or destino is None or destino == arrastrada:
            return
        orden = self.orden_columnas()
        posicion = orden.index(destino)
        orden.remove(arrastrada)
        orden.insert(posicion, arrastrada)
        self.ordenar_columnas(orden, self._ocultas)
        self._guardar_columnas()

    def _cargar_columnas(self) -> None:
        repos, clave = self._recordar
        try:
            guardado = json.loads(repos.config(clave, "") or "{}")
        except ValueError:
            guardado = {}
        if isinstance(guardado, dict):
            self.ordenar_columnas(guardado.get("orden") or [], guardado.get("ocultas") or [])

    def _guardar_columnas(self) -> None:
        repos, clave = self._recordar
        repos.set_config(clave, json.dumps({
            "orden": self.orden_columnas(), "ocultas": self.columnas_ocultas()}))

    def elegir_columnas(self) -> None:
        """Abre el diálogo de orden y visibilidad y guarda lo elegido."""
        elegido = DialogoColumnas(
            self, [(c["clave"], c["titulo"]) for c in self.columnas],
            self.orden_columnas(), self.columnas_ocultas()).mostrar()
        if elegido is not None:
            self.ordenar_columnas(*elegido)
            self._guardar_columnas()

    def _colorear_etiquetas(self) -> None:
        for nombre, color in colores_etiquetas().items():
            self.tree.tag_configure(nombre, foreground=color)
        for nombre, opciones in estilos_filas().items():
            self.tree.tag_configure(nombre, **opciones)

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "tree"):  # los tags de ttk no siguen el modo solos
            self._colorear_etiquetas()
            self._pedir_trazo()

    # -- grilla ----------------------------------------------------------- #
    # ttk.Treeview (Tk 8.6) no dibuja líneas entre celdas: se superponen marcos
    # de 1 px sobre los bordes de las columnas y de las filas visibles.
    def _pedir_trazo(self, _evento=None) -> None:
        if self._trazo_pendiente is None:
            self._trazo_pendiente = self.after_idle(self._trazar)

    def _linea(self, reserva: list, indice: int, color: str) -> tk.Frame:
        if indice == len(reserva):
            reserva.append(tk.Frame(self.tree, bd=0, highlightthickness=0))
        reserva[indice].configure(bg=color)
        return reserva[indice]

    def _trazar(self) -> None:
        self._trazo_pendiente = None
        if not self.tree.winfo_exists():
            return
        color = colores_tema()["borde"]
        ancho, alto = self.tree.winfo_width(), self.tree.winfo_height()

        anchos = [self.tree.column(c, "width") for c in self.columnas_visibles()]
        x = -round(self.tree.xview()[0] * sum(anchos))
        usadas = 0
        for ancho_columna in anchos[:-1] if self._lineas_verticales else ():
            x += ancho_columna
            if 0 < x < ancho:
                self._linea(self._lineas_v, usadas, color).place(
                    x=x - 1, y=0, width=1, height=alto)
                usadas += 1
        for sobrante in self._lineas_v[usadas:]:
            sobrante.place_forget()

        usadas = 0
        hijos = self.tree.get_children()
        if hijos:
            primero = min(round(self.tree.yview()[0] * len(hijos)), len(hijos) - 1)
            caja = self.tree.bbox(hijos[primero])
            if caja:
                y, alto_fila = caja[1], caja[3]
                for _ in hijos[primero:]:
                    y += alto_fila
                    if y >= alto:
                        break
                    self._linea(self._lineas_h, usadas, color).place(
                        x=0, y=y - 1, width=ancho, height=1)
                    usadas += 1
        for sobrante in self._lineas_h[usadas:]:
            sobrante.place_forget()

    # -- datos ------------------------------------------------------------ #
    def actualizar(
        self,
        filas: Sequence[Sequence[str]],
        objetos: Sequence[Any],
        etiquetas: Optional[Sequence[str]] = None,
    ) -> None:
        # La selección se conserva por posición: los iid cambian en cada carga.
        seleccion = self.id_seleccionado()
        indice = self.tree.index(seleccion) if seleccion else None
        self.tree.delete(*self.tree.get_children())
        self._objetos.clear()
        for i, valores in enumerate(filas):
            tags = etiquetas[i] if etiquetas and i < len(etiquetas) and etiquetas[i] else ()
            if isinstance(tags, str):
                tags = (tags,)
            iid = self.tree.insert("", "end", values=list(valores), tags=tags)
            self._objetos[iid] = objetos[i]
        hijos = self.tree.get_children()
        if indice is not None and hijos:
            self.tree.selection_set(hijos[min(indice, len(hijos) - 1)])
        self._pedir_trazo()

    def limpiar(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._objetos.clear()
        self._pedir_trazo()

    # -- selección -------------------------------------------------------- #
    def id_seleccionado(self) -> Optional[str]:
        seleccion = self.tree.selection()
        return seleccion[0] if seleccion else None

    def seleccionado(self) -> Any:
        iid = self.id_seleccionado()
        return self._objetos.get(iid) if iid else None

    def seleccionados(self) -> list[Any]:
        return [self._objetos[i] for i in self.tree.selection() if i in self._objetos]

    def vacio(self) -> bool:
        return not self.tree.get_children()

    def enfocar_primero(self) -> None:
        hijos = self.tree.get_children()
        if hijos:
            self.tree.selection_set(hijos[0])
            self.tree.focus(hijos[0])

    def _al_doble_clic(self, _evento=None) -> None:
        if self._doble_click is None:
            return
        objeto = self.seleccionado()
        if objeto is not None:
            self._doble_click(objeto)


# --------------------------------------------------------------------------- #
# Botones, tarjetas y barras
# --------------------------------------------------------------------------- #


def boton(
    master: Any,
    texto: str,
    comando: Optional[Callable[[], Any]],
    *,
    color: str = "primario",
    ancho: int = 118,
    alto: int = 32,
    estado: str = "normal",
) -> ctk.CTkButton:
    """Botón de acción de color pleno; ``color`` es una variante de ``theme.BOTONES``."""
    relleno, hover = BOTONES[color]
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho_par(master, ancho), height=alto,
        fg_color=relleno, hover_color=hover, text_color=TEXTO_BOTON,
        text_color_disabled=TEXTO_BOTON_INACTIVO, font=FUENTE_BOTON, state=estado,
    )


def boton_secundario(master: Any, texto: str, comando: Optional[Callable[[], Any]],
                     *, ancho: int = 118, alto: int = 32) -> ctk.CTkButton:
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho_par(master, ancho), height=alto,
        fg_color=FONDO, hover_color=RESALTE, text_color=TEXTO,
        border_width=1, border_color=BORDE_FUERTE, font=FUENTE_BOTON,
    )


class Tarjeta(ctk.CTkFrame):
    """Tarjeta de resumen con número grande y leyenda."""

    def __init__(self, master: Any, titulo: str, valor: Any = "0",
                 *, color: Optional[tuple] = None, relleno: Optional[tuple] = None,
                 compacta: bool = False):
        """``color`` tiñe borde y texto; ``relleno`` pinta la tarjeta de un color
        sólido con texto claro. ``compacta`` la hace más baja."""
        if relleno:
            color = TEXTO_BOTON
        super().__init__(master, corner_radius=RADIO, height=54 if compacta else 96,
                         fg_color=relleno or FONDO,
                         border_width=0 if relleno else 2 if color else 1,
                         border_color=color or BORDE)
        self.grid_propagate(False)
        self.pack_propagate(False)
        self._color = color or TEXTO
        self._relleno = relleno
        self._actual = (str(valor), self._color)
        self._titulo = ctk.CTkLabel(self, text=titulo.upper(), height=16,
                                    font=(SEMINEGRITA, 9 if compacta else 10),
                                    text_color=color or GRIS_TEXTO, anchor="w")
        self._valor = ctk.CTkLabel(self, text=str(valor), height=24,
                                   font=("Segoe UI", 17 if compacta else 24, "bold"),
                                   text_color=color or TEXTO, anchor="w")
        margen = (5, 0) if compacta else (12, 0)
        self._titulo.pack(fill="x", padx=14, pady=margen)
        self._valor.pack(fill="x", padx=14, pady=(0 if compacta else 2, 0))

    def set_valor(self, valor: Any, color: Optional[tuple] = None) -> None:
        nuevo = (str(valor), color or self._color)
        if nuevo != self._actual:  # redibujar un CTkLabel es caro: solo si cambió
            self._actual = nuevo
            self._valor.configure(text=nuevo[0], text_color=nuevo[1])

    def set_relleno(self, relleno: tuple) -> None:
        """Cambia el color de una tarjeta sólida (p. ej. resultado en rojo)."""
        if relleno != self._relleno:
            self._relleno = relleno
            self.configure(fg_color=relleno)


class BarraBotones(ctk.CTkFrame):
    """Barra de herramientas con acciones a la izquierda y búsqueda a la derecha."""

    def __init__(self, master: Any, *, busqueda: bool = True,
                 placeholder: str = "Buscar…",
                 al_buscar: Optional[Callable[[str], None]] = None):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(99, weight=1)
        self._indice = 0
        self._al_buscar = al_buscar
        if busqueda:
            self._buscador = ctk.CTkEntry(
                self, width=230, height=32, placeholder_text=placeholder,
                font=FUENTE_NORMAL,
            )
        else:
            self._buscador = None

    def agregar(self, texto: str, comando: Optional[Callable[[], Any]],
                *, color: str = "primario") -> ctk.CTkButton:
        btn = boton(self, texto, comando, color=color)
        btn.grid(row=0, column=self._indice, padx=(0, 8), pady=2, sticky="w")
        self._indice += 1
        return btn

    def espaciador(self) -> None:
        self.grid_columnconfigure(self._indice, weight=1)
        self._indice += 1

    def terminar_busqueda(self) -> None:
        if self._buscador is None:
            return
        self._buscador.grid(row=0, column=99, padx=(8, 0), pady=2, sticky="e")
        if self._al_buscar:
            self._buscador.bind("<KeyRelease>", lambda e: self._al_buscar(self.texto()))

    def texto(self) -> str:
        return self._buscador.get() if self._buscador else ""


# --------------------------------------------------------------------------- #
# Diálogos
# --------------------------------------------------------------------------- #


class Dialogo(ctk.CTkToplevel):
    """Base modal con formulario en dos columnas y botones Aceptar/Cancelar."""

    def __init__(self, master: Any, titulo: str, *, ancho: int = 560, alto: int = 560):
        super().__init__(master)
        self.withdraw()
        self.title(titulo)
        aplicar_icono(self)
        # Nunca más alto que la pantalla (el formulario tiene barra de
        # desplazamiento) y centrado, para que los botones queden a la vista.
        escala = self._get_window_scaling()
        x0, y0, ancho_area, alto_area = area_de_trabajo(self)
        ancho = int(min(ancho, ancho_area / escala - 20))
        alto = int(min(alto, alto_area / escala - 44))  # deja lugar a la barra de título
        x = x0 + int((ancho_area - ancho * escala) / 2)
        y = y0 + int(max(0, (alto_area - alto * escala) / 2 - 20 * escala))
        self.geometry(f"{ancho}x{alto}+{max(x0, x)}+{y}")
        self.resizable(False, False)
        self.transient(master)
        self.resultado: Any = None
        self._fila = 0
        self._campos: dict[str, Any] = {}
        self._objetos_selector: dict[str, dict[str, Any]] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Los diálogos son una tarjeta: superficie blanca y título mediano.
        self.configure(fg_color=FONDO)
        self._cabecera = ctk.CTkLabel(self, text=titulo, font=FUENTE_DIALOGO,
                                      anchor="w", text_color=TEXTO)
        self._cabecera.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))

        self.form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.form.grid(row=1, column=0, sticky="nsew", padx=8)
        self.form.grid_columnconfigure(1, weight=1)

        self._pie = ctk.CTkFrame(self, fg_color="transparent")
        self._pie.grid(row=2, column=0, sticky="ew", padx=16, pady=(6, 16))

    # -- campos ----------------------------------------------------------- #
    def _etiqueta(self, texto: str) -> ctk.CTkLabel:
        label = ctk.CTkLabel(self.form, text=texto, font=FUENTE_NORMAL, anchor="w")
        label.grid(row=self._fila, column=0, sticky="w", padx=10, pady=6, ipady=6)
        return label

    def campo_texto(self, clave: str, etiqueta: str, valor: str = "",
                    placeholder: str = "", ancho: int = 330) -> ctk.CTkEntry:
        self._etiqueta(etiqueta)
        entrada = ctk.CTkEntry(self.form, width=ancho, font=FUENTE_NORMAL,
                               placeholder_text=placeholder)
        entrada.insert(0, valor or "")
        entrada.grid(row=self._fila, column=1, sticky="ew", padx=10, pady=6, ipady=4)
        self._fila += 1
        self._campos[clave] = entrada
        return entrada

    def campo_password(self, clave: str, etiqueta: str) -> ctk.CTkEntry:
        entrada = self.campo_texto(clave, etiqueta)
        entrada.configure(show="\u2022")
        return entrada

    def campo_fecha(self, clave: str, etiqueta: str, valor: Optional[date] = None,
                    *, opcional: bool = True) -> SelectorFecha:
        """Fecha elegida desde un calendario (``opcional`` permite dejarla vacía)."""
        self._etiqueta(etiqueta)
        selector = SelectorFecha(self.form, valor, opcional=opcional)
        selector.grid(row=self._fila, column=1, sticky="w", padx=10, pady=6)
        self._fila += 1
        self._campos[clave] = selector
        return selector

    def campo_combo(self, clave: str, etiqueta: str, valores: Sequence[str],
                    valor: str = "") -> ctk.CTkComboBox:
        """Lista de sugerencias en la que también se puede escribir un valor nuevo."""
        self._etiqueta(etiqueta)
        combo = ctk.CTkComboBox(self.form, values=list(valores), width=330,
                                font=FUENTE_NORMAL)
        combo.set(valor or "")
        combo.grid(row=self._fila, column=1, sticky="w", padx=10, pady=6)
        self._fila += 1
        self._campos[clave] = combo
        return combo

    def campo_monto(self, clave: str, etiqueta: str, valor: float = 0.0) -> ctk.CTkEntry:
        texto = "" if not valor else f"{valor:.2f}".replace(",", "")
        entrada = self.campo_texto(clave, etiqueta, texto, placeholder="0.00", ancho=160)
        return entrada

    def campo_selector(self, clave: str, etiqueta: str, valores: Sequence[str],
                       valor: Optional[str] = None) -> ctk.CTkOptionMenu:
        self._etiqueta(etiqueta)
        valores = list(valores) or ["—"]
        menu = ctk.CTkOptionMenu(self.form, values=valores, width=330,
                                 font=FUENTE_NORMAL, dynamic_resizing=False)
        menu.set(valor if valor in valores else valores[0])
        menu.grid(row=self._fila, column=1, sticky="w", padx=10, pady=6, ipady=2)
        self._fila += 1
        self._campos[clave] = menu
        return menu

    def campo_check(self, clave: str, etiqueta: str, valor: bool = False) -> ctk.CTkCheckBox:
        self._etiqueta(etiqueta)
        caja = ctk.CTkCheckBox(self.form, text="", font=FUENTE_NORMAL)
        if valor:
            caja.select()
        caja.grid(row=self._fila, column=1, sticky="w", padx=10, pady=6)
        self._fila += 1
        self._campos[clave] = caja
        return caja

    def campo_area(self, clave: str, etiqueta: str, valor: str = "",
                   altura: int = 140) -> ctk.CTkTextbox:
        label = ctk.CTkLabel(self.form, text=etiqueta, font=FUENTE_NORMAL, anchor="nw")
        label.grid(row=self._fila, column=0, sticky="nw", padx=10, pady=6, ipady=6)
        area = ctk.CTkTextbox(self.form, height=altura, font=FUENTE_NORMAL)
        area.insert("1.0", valor or "")
        area.grid(row=self._fila, column=1, sticky="ew", padx=10, pady=6)
        self._fila += 1
        self._campos[clave] = area
        return area

    def separador(self, texto: str) -> None:
        label = ctk.CTkLabel(self.form, text=texto, font=FUENTE_ETIQUETA,
                             anchor="w", text_color=ACENTO)
        label.grid(row=self._fila, column=0, columnspan=2, sticky="w",
                   padx=10, pady=(14, 2))
        self._fila += 1

    def nota(self, texto: str) -> None:
        label = ctk.CTkLabel(self.form, text=texto, font=FUENTE_PEQUE,
                             anchor="w", text_color=GRIS_TEXTO, wraplength=440,
                             justify="left")
        label.grid(row=self._fila, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
        self._fila += 1

    # -- lectura ---------------------------------------------------------- #
    def texto(self, clave: str) -> str:
        widget = self._campos[clave]
        if isinstance(widget, ctk.CTkTextbox):
            return widget.get("1.0", "end-1c").strip()
        if isinstance(widget, (ctk.CTkOptionMenu,)):
            return widget.get()
        if isinstance(widget, SelectorFecha):
            return widget.get()
        if isinstance(widget, ctk.CTkCheckBox):
            return "1" if widget.get() else "0"
        return widget.get().strip()

    def fecha(self, clave: str) -> Optional[date]:
        return parsear_fecha(self.texto(clave))

    def poner_fecha(self, clave: str, valor: Optional[date]) -> None:
        self._campos[clave].set(valor)

    def monto(self, clave: str) -> float:
        return parsear_monto(self.texto(clave))

    def es_verdadero(self, clave: str) -> bool:
        widget = self._campos[clave]
        return bool(widget.get()) if isinstance(widget, ctk.CTkCheckBox) else bool(self.texto(clave))

    def valor_selector(self, clave: str) -> str:
        return self._campos[clave].get()

    def objeto_selector(self, clave: str, objetos: Sequence[Any],
                        clave_atributo: str = "id") -> Any:
        """Devuelve el objeto asociado al ítem seleccionado del ``OptionMenu``."""
        texto = self._campos[clave].get()
        for objeto in objetos:
            if str(getattr(objeto, clave_atributo)) == texto:
                return objeto
        return None

    def campo_selector_objetos(
        self,
        clave: str,
        etiqueta: str,
        objetos: Sequence[Any],
        etiquetador: Callable[[Any], str] = str,
        seleccion: Any = None,
        vacio: str = "— Ninguno —",
        opcional: bool = False,
    ) -> ctk.CTkOptionMenu:
        """Selector cuyo valor visible es una etiqueta y cuyo objeto se recupera con :meth:`objeto`.

        Con ``opcional`` la primera opción es ``vacio`` y devuelve ``None``.
        """
        mapa: dict[str, Any] = {}
        valores: list[str] = [vacio] if opcional and objetos else []
        for objeto in objetos:
            base = etiquetador(objeto)
            texto, n = base, 2
            while texto in mapa:
                texto = f"{base} ({n})"
                n += 1
            mapa[texto] = objeto
            valores.append(texto)
        self._objetos_selector[clave] = mapa
        if not valores:
            valores = [vacio]
        menu = self.campo_selector(clave, etiqueta, valores)
        if seleccion is not None:
            for texto, objeto in mapa.items():
                if objeto is seleccion or getattr(objeto, "id", None) == getattr(
                    seleccion, "id", None
                ):
                    menu.set(texto)
                    break
        return menu

    def objeto(self, clave: str) -> Any:
        """Objeto elegido en un selector creado con :meth:`campo_selector_objetos`."""
        mapa = self._objetos_selector.get(clave, {})
        return mapa.get(self._campos[clave].get())

    # -- acciones --------------------------------------------------------- #
    def botones(self, texto_ok: str = "Guardar",
                al_aceptar: Optional[Callable[[], Any]] = None) -> None:
        self._al_aceptar = al_aceptar
        cancelar = boton_secundario(self._pie, "Cancelar", self.cancelar, ancho=110)
        cancelar.pack(side="right", padx=(8, 0))
        ok = boton(self._pie, texto_ok, self.aceptar, ancho=130)
        ok.pack(side="right")
        self.bind("<Escape>", lambda e: self.cancelar())
        self.bind("<Return>", lambda e: self.aceptar())

    def aceptar(self) -> None:
        if getattr(self, "_al_aceptar", None) is None:
            self.resultado = True
            self.destroy()
            return
        try:
            resultado = self._al_aceptar()
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            DialogoMensaje.error(self, "Datos inválidos", str(exc))
            return
        if resultado is not False:
            self.resultado = resultado
            self.destroy()

    def cancelar(self) -> None:
        self.resultado = None
        self.destroy()

    def mostrar(self) -> Any:
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window(self)
        return self.resultado


class DialogoColumnas(Dialogo):
    """Orden y visibilidad de las columnas de una tabla.

    ``columnas`` son los pares ``(clave, título)`` en el orden predeterminado.
    Devuelve ``(orden, ocultas)``.
    """

    def __init__(self, master: Any, columnas: Sequence[tuple[str, str]],
                 orden: Sequence[str], ocultas: Sequence[str] = ()):
        super().__init__(master, "Columnas", ancho=460, alto=600)
        self._titulos = dict(columnas)
        self._orden = [c for c in orden if c in self._titulos]
        self._visible = {clave: ctk.BooleanVar(self, value=clave not in ocultas)
                         for clave in self._titulos}
        self.nota("Tilde las columnas que quiere ver y acomódelas con las flechas. "
                  "En la tabla también puede arrastrar los encabezados.")
        self._lista = ctk.CTkFrame(self.form, fg_color="transparent")
        self._lista.grid(row=self._fila, column=0, columnspan=2, sticky="ew", padx=10)
        self._lista.grid_columnconfigure(0, weight=1)
        self._fila += 1
        self._armar()
        boton_secundario(self._pie, "Restablecer", self._restablecer,
                         ancho=120).pack(side="left")
        self.botones("Guardar", self._guardar)

    def _armar(self) -> None:
        for hijo in self._lista.winfo_children():
            hijo.destroy()
        ultima = len(self._orden) - 1
        for i, clave in enumerate(self._orden):
            ctk.CTkCheckBox(self._lista, text=self._titulos[clave], font=FUENTE_NORMAL,
                            variable=self._visible[clave]).grid(
                row=i, column=0, sticky="w", pady=4)
            subir = boton_secundario(self._lista, "▲", lambda i=i: self._mover(i, -1),
                                     ancho=36, alto=28)
            subir.grid(row=i, column=1, padx=(8, 4), pady=4)
            bajar = boton_secundario(self._lista, "▼", lambda i=i: self._mover(i, 1),
                                     ancho=36, alto=28)
            bajar.grid(row=i, column=2, pady=4)
            if i == 0:
                subir.configure(state="disabled")
            if i == ultima:
                bajar.configure(state="disabled")

    def _mover(self, indice: int, paso: int) -> None:
        destino = indice + paso
        if 0 <= destino < len(self._orden):
            self._orden[indice], self._orden[destino] = (
                self._orden[destino], self._orden[indice])
            self._armar()

    def _restablecer(self) -> None:
        self._orden = list(self._titulos)
        for variable in self._visible.values():
            variable.set(True)
        self._armar()

    def _guardar(self) -> tuple[list[str], list[str]]:
        ocultas = [c for c in self._orden if not self._visible[c].get()]
        if len(ocultas) == len(self._orden):
            raise DatosInvalidosError("Deje al menos una columna a la vista.")
        return list(self._orden), ocultas


def ejecutar_protegido(
    parent: Any,
    accion: Callable[[], Any],
    refrescar: Optional[Callable[[], Any]] = None,
) -> Any:
    """Ejecuta una operación de negocio mostrando errores como diálogo."""
    try:
        resultado = accion()
    except FotiqueError as exc:
        DialogoMensaje.error(parent, "Operación no válida", str(exc))
        return None
    except Exception as exc:  # noqa: BLE001 - último recurso para el usuario
        DialogoMensaje.error(parent, "Error inesperado", f"{type(exc).__name__}: {exc}")
        return None
    if refrescar:
        refrescar()
    return resultado


class DialogoMensaje(ctk.CTkToplevel):
    """Diálogo pequeño de información, error o confirmación."""

    def __init__(self, master: Any, titulo: str, mensaje: str,
                 *, tipo: str = "info", texto_si: str = "Aceptar"):
        super().__init__(master)
        self.withdraw()
        self.title(titulo)
        aplicar_icono(self)
        self.resizable(False, False)
        self.transient(master)
        self.resultado = False
        self.configure(fg_color=FONDO)

        ancho = max(360, min(640, 12 + len(mensaje)))
        self.geometry(f"{ancho}x170")
        color = ROJO if tipo == "error" else ACENTO
        ctk.CTkLabel(self, text=titulo, font=FUENTE_SUBTITULO, text_color=color,
                     anchor="w").pack(fill="x", padx=18, pady=(18, 4))
        ctk.CTkLabel(self, text=mensaje, font=FUENTE_NORMAL, anchor="w",
                     justify="left", wraplength=ancho - 40).pack(
            fill="both", expand=True, padx=18, pady=4
        )
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=18, pady=(4, 16))

        if tipo == "confirmar":
            boton_secundario(pie, "Cancelar", lambda: self._cerrar(False)).pack(
                side="right", padx=(8, 0)
            )
            boton(pie, texto_si, lambda: self._cerrar(True)).pack(
                side="right")
        else:
            boton(pie, "Aceptar", lambda: self._cerrar(True)).pack(
                side="right")
        self.bind("<Escape>", lambda e: self._cerrar(False))

    def _cerrar(self, valor: bool) -> None:
        self.resultado = valor
        self.destroy()

    @classmethod
    def info(cls, master: Any, titulo: str, mensaje: str) -> None:
        cls(master, titulo, mensaje, tipo="info").mostrar()

    @classmethod
    def error(cls, master: Any, titulo: str, mensaje: str) -> None:
        cls(master, titulo, mensaje, tipo="error").mostrar()

    @classmethod
    def confirmar(cls, master: Any, titulo: str, mensaje: str,
                  texto_si: str = "Eliminar") -> bool:
        return bool(cls(master, titulo, mensaje, tipo="confirmar",
                        texto_si=texto_si).mostrar())

    def mostrar(self) -> bool:
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window(self)
        return self.resultado
