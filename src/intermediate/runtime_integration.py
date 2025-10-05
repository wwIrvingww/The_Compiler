# src/intermediate/runtime_integration.py
"""
RuntimeIntegration / RuntimeBinder
---------------------------------

Módulo puente entre:
 - la symbol table (tabla de símbolos del semantic)
 - el FrameManager / runtime_layout
 - el generador de TAC

Objetivo:
 - proporcionar una API sencilla y resistente para que el TacGenerator pida:
    * "asigna runtime info para este símbolo" (param/local/attr)
    * "dame un temporal que cargue esa variable"
    * "genera el TAC (string o nodo) para load/store"
 - encapsular llamadas a frame_manager (allocate_param, attach_runtime_info, size_of_type)
 - dar errores amigables si la API que hay en el repo difiere

USO (resumen):
    binder = RuntimeBinder(symbol_table, frame_manager, temp_allocator)
    # al entrar a function:
    binder.enter_frame("foo")
    # por cada parámetro:
    binder.register_param(frame_id="foo", sym_name="a", type_name="integer")
    # por cada var local:
    binder.register_local(frame_id="foo", sym_name="t", type_name="integer", size=4)
    # en tac_generator, para cargar variable a temporal:
    tmp = temp_alloc.new_temp()
    load_instr = binder.load_var(sym_name="a", dest_temp=tmp, frame_id="foo")
    # store:
    store_instr = binder.store_var(sym_name="a", src_temp=tmp, frame_id="foo")

NOTA:
- Este módulo no fuerza una API exacta del frame_manager ni symbol_table;
  intenta llamar a nombres comunes y si no existen, levanta RuntimeError con
  mensaje indicando qué adaptar.
- Las funciones `load_var`/`store_var` devuelven cadenas de TAC legible
  por defecto. Si tu proyecto usa nodos (ej: tac_nodes.TacNode), reemplaza
  la emisión por el nodo correspondiente.

"""

from typing import Optional, Dict, Any, Tuple


class RuntimeBinder:
    """
    Binder que conecta symbol table + frame manager + temp allocator
    para permitir que el generador de TAC conozca offsets/frames de símbolos.

    Parámetros:
      symbol_table: la tabla de símbolos del semantic (cualquier objeto que
                    tenga métodos para buscar símbolos y su metadata).
      frame_manager: objeto que maneja frames/offsets (runtime_layout.FrameManager)
      temp_allocator: objeto que genera temporales (opcional, para conveniencia)
    """

    def __init__(self, symbol_table: Any, frame_manager: Any, temp_allocator: Optional[Any] = None):
        self.symbol_table = symbol_table
        self.frame_manager = frame_manager
        self.temp_alloc = temp_allocator
        # cache runtime metadata por (frame_id, symbol_name)
        # value: dict con keys: offset, size, category, frame_id
        self._meta_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}

    # --------------------------
    # helpers para verificar APIs
    # --------------------------
    def _ensure_frame_api(self):
        fm = self.frame_manager
        missing = []
        if fm is None:
            raise RuntimeError("frame_manager es None. Pasa la instancia de FrameManager al RuntimeBinder.")
        for name in ("enter_frame", "exit_frame", "current_frame", "attach_runtime_info", "size_of_type"):
            if not hasattr(fm, name):
                missing.append(name)
        if missing:
            raise RuntimeError(f"FrameManager falta métodos esperados: {missing}. Adapta runtime_layout.py o actualiza RuntimeBinder.")

    def _ensure_symbol_table_api(self):
        st = self.symbol_table
        if st is None:
            raise RuntimeError("symbol_table es None. Pasa la instancia de symbol table.")
        # intentamos detectar nombres comunes: lookup, resolve, get
        if not any(hasattr(st, n) for n in ("lookup", "resolve", "get", "find")):
            raise RuntimeError("Symbol table no tiene métodos 'lookup/resolve/get/find'. Adapta RuntimeBinder para llamar a la función correcta.")

    # --------------------------
    # Frame lifecycle
    # --------------------------
    def enter_frame(self, frame_id: str):
        """Pide al frame_manager entrar/crear un frame con id frame_id."""
        self._ensure_frame_api()
        fm = self.frame_manager
        # prefer enter_frame, sino create_frame, sino push_frame:
        if hasattr(fm, "enter_frame"):
            return fm.enter_frame(frame_id)
        if hasattr(fm, "create_frame"):
            return fm.create_frame(frame_id)
        raise RuntimeError("FrameManager no tiene enter_frame/create_frame")

    def exit_frame(self):
        self._ensure_frame_api()
        fm = self.frame_manager
        if hasattr(fm, "exit_frame"):
            return fm.exit_frame()
        raise RuntimeError("FrameManager no tiene exit_frame")

    # --------------------------
    # Register symbols in frame (params / locals / attrs)
    # --------------------------
    def register_param(self, frame_id: str, sym_name: str, type_name: Optional[str] = None, size: Optional[int] = None, category: str = "param") -> Dict[str, Any]:
        """
        Registra un parámetro en un frame y adjunta runtime info en la symbol table.
        Devuelve un dict con metadata {'offset':..., 'size':..., 'category':..., 'frame_id':...}
        """
        self._ensure_frame_api()
        if size is None:
            # pedir tamaño por tipo si es posible
            size = self.frame_manager.size_of_type(type_name) if hasattr(self.frame_manager, "size_of_type") else 4
        try:
            # Intentar usar la API que vimos en el proyecto:
            if hasattr(self.frame_manager, "allocate_param"):
                off = self.frame_manager.allocate_param(frame_id, sym_name, type_name=type_name, size=size)
            elif hasattr(self.frame_manager, "alloc_param"):
                off = self.frame_manager.alloc_param(frame_id, sym_name, size)
            else:
                # fallback: intentar attach_runtime_info directamente (si ya asignó en otro sitio)
                off = None
            # adjuntar metadata a symbol table si existe attach_runtime_info en fm
            if hasattr(self.frame_manager, "attach_runtime_info"):
                try:
                    ok = self.frame_manager.attach_runtime_info(self.symbol_table, sym_name, frame_id, category=category, size=size)
                except TypeError:
                    # algunos attach_runtime_info tienen otra firma; intentar con menos args
                    try:
                        ok = self.frame_manager.attach_runtime_info(self.symbol_table, sym_name, frame_id)
                    except Exception:
                        ok = False
            meta = {"offset": off if off is not None else 0, "size": size, "category": category, "frame_id": frame_id}
            self._meta_cache[(frame_id, sym_name)] = meta
            return meta
        except Exception as e:
            # no queremos que una excepción bloquee toda la generación de TAC;
            # registramos el error en la cache con información parcial
            meta = {"offset": None, "size": size, "category": category, "frame_id": frame_id, "error": str(e)}
            self._meta_cache[(frame_id, sym_name)] = meta
            return meta

    def register_local(self, frame_id: str, sym_name: str, type_name: Optional[str] = None, size: Optional[int] = None, category: str = "local") -> Dict[str, Any]:
        """
        Similar a register_param pero para variables locales.
        Dependiendo de la API del frame manager, puede que exista allocate_local(...)
        """
        self._ensure_frame_api()
        if size is None:
            size = self.frame_manager.size_of_type(type_name) if hasattr(self.frame_manager, "size_of_type") else 4
        try:
            if hasattr(self.frame_manager, "allocate_local"):
                off = self.frame_manager.allocate_local(frame_id, sym_name, type_name=type_name, size=size)
            elif hasattr(self.frame_manager, "alloc_local"):
                off = self.frame_manager.alloc_local(frame_id, sym_name, size)
            else:
                off = None
            if hasattr(self.frame_manager, "attach_runtime_info"):
                try:
                    ok = self.frame_manager.attach_runtime_info(self.symbol_table, sym_name, frame_id, category=category, size=size)
                except TypeError:
                    try:
                        ok = self.frame_manager.attach_runtime_info(self.symbol_table, sym_name, frame_id)
                    except Exception:
                        ok = False
            meta = {"offset": off if off is not None else 0, "size": size, "category": category, "frame_id": frame_id}
            self._meta_cache[(frame_id, sym_name)] = meta
            return meta
        except Exception as e:
            meta = {"offset": None, "size": size, "category": category, "frame_id": frame_id, "error": str(e)}
            self._meta_cache[(frame_id, sym_name)] = meta
            return meta

    # --------------------------
    # Query runtime metadata
    # --------------------------
    def get_runtime_meta(self, sym_name: str, frame_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Devuelve metadata runtime para un símbolo. Intenta (en este orden):
          1) buscar en cache
          2) preguntar a symbol table (si expone metadata)
          3) preguntar al frame manager (si expone consulta)
        """
        # 1) cache exact match
        if frame_id is not None and (frame_id, sym_name) in self._meta_cache:
            return self._meta_cache[(frame_id, sym_name)]
        # 2) try symbol_table methods that may include runtime metadata
        st = self.symbol_table
        # We try some common names: lookup, resolve, get
        candidate = None
        for nm in ("lookup", "resolve", "get", "find"):
            if hasattr(st, nm):
                try:
                    candidate = getattr(st, nm)(sym_name)
                    break
                except Exception:
                    candidate = None
        if candidate is not None:
            # many symbol representations store runtime info on .meta or .runtime
            for key in ("meta", "metadata", "runtime", "runtime_info"):
                if hasattr(candidate, key):
                    info = getattr(candidate, key)
                    if isinstance(info, dict):
                        return info
            # if candidate is a dict itself
            if isinstance(candidate, dict):
                if "offset" in candidate or "frame_id" in candidate:
                    return candidate
        # 3) try frame_manager query API (optional)
        fm = self.frame_manager
        if hasattr(fm, "query_symbol") or hasattr(fm, "get_symbol"):
            getter = getattr(fm, "query_symbol", None) or getattr(fm, "get_symbol", None)
            try:
                info = getter(sym_name, frame_id) if getter is not None else None
                if info:
                    return info
            except Exception:
                pass
        # Not found
        return None

    # --------------------------
    # TAC helpers: generate load/store (strings)
    # --------------------------
    def load_var(self, sym_name: str, dest_temp: str, frame_id: Optional[str] = None) -> str:
        """
        Genera una instrucción TAC (string) que carga la variable `sym_name`
        a `dest_temp`. Si no hay metadata, genera un acceso global por nombre.
        """
        meta = self.get_runtime_meta(sym_name, frame_id=frame_id)
        if meta is None:
            # fallback: treat as global variable name -> load by name
            return f"{dest_temp} = {sym_name}"
        if meta.get("offset") is None:
            # metadata partial: shall load by name
            return f"{dest_temp} = {sym_name}"
        # si tenemos offset y frame, usamos convención: [frame:offset]
        frame = meta.get("frame_id", frame_id or "global")
        off = meta.get("offset")
        # produce a readable, portable TAC load instruction
        return f"{dest_temp} = LOAD {frame}[{off}]    // {sym_name}"

    def store_var(self, sym_name: str, src_temp: str, frame_id: Optional[str] = None) -> str:
        """Genera instrucción TAC para almacenar src_temp -> sym_name"""
        meta = self.get_runtime_meta(sym_name, frame_id=frame_id)
        if meta is None or meta.get("offset") is None:
            return f"{sym_name} = {src_temp}"
        frame = meta.get("frame_id", frame_id or "global")
        off = meta.get("offset")
        return f"STORE {frame}[{off}] = {src_temp}    // {sym_name}"

    # --------------------------
    # Convenience: temps
    # --------------------------
    def new_temp(self) -> str:
        if self.temp_alloc is None:
            raise RuntimeError("No temp_allocator provisto; pasa un objeto temp_allocator con método new_temp()/new()")
        # try common names
        for nm in ("new_temp", "new", "alloc", "newTemp"):
            if hasattr(self.temp_alloc, nm):
                return getattr(self.temp_alloc, nm)()
        # fallback: try attribute current naming 'new_temp' missing -> error
        raise RuntimeError("temp_allocator no expone new_temp()/new()/alloc() - adapta RuntimeBinder o pasa un temp allocator compatible.")

    # --------------------------
    # Utilities / debugging
    # --------------------------
    def dump_cache(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Devuelve la cache de metadata (útil para debugging)"""
        return dict(self._meta_cache)

