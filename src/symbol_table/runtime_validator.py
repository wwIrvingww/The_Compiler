# src/symbol_table/runtime_validator.py
"""
Validación ligera de consistencia entre SymbolTable y FrameManager.

Reglas principales usadas por los tests:
 - El FrameManager (o sus frames) es la fuente primaria para offsets/sizes.
 - Se detectan overlaps dentro de un mismo frame.
 - Si el SymbolTable contiene metadata de runtime (offset/size), se compara con lo del FrameManager
   y se reporta discrepancia. Si no contiene metadata, no se considera error (se asume que
   FrameManager es la fuente de verdad).
 - Se aceptan distintas implementaciones/atributos en FrameManager:
     - fm.all_frames() -> dict
     - fm._frames (map id->Frame)
     - fm.frames (map id->dict)
   Y distintas formas de exponer la información de cada Frame:
     - frame.summary() -> dict(name -> slot-dict)
     - frame.symbols -> dict(name -> slot or Slot object)
"""
from __future__ import annotations
import json
from typing import Dict, Any, List, Tuple

def _frames_map_from_fm(fm) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Normaliza la representación de frames a:
      { frame_id: { symbol_name: { offset:int|None, size:int|None, category:str|None, type_name:str|None } } }
    Funciona con distintas formas comunes de exponer FrameManager/Frame internamente.
    """
    # 1) if API present
    if hasattr(fm, "all_frames"):
        try:
            # all_frames() puede devolver ya la forma esperada; si no, lo normalizaremos abajo
            raw = fm.all_frames()
            # ensure it's a dict mapping
            if isinstance(raw, dict):
                # attempt to normalize each frame entry if necessary using the same logic below
                normalized = {}
                for fid, val in raw.items():
                    # if val already looks like symbol->slot mapping, keep it
                    if isinstance(val, dict) and all(
                        isinstance(s, dict) and ("offset" in s or "size" in s or "category" in s)
                        for s in val.values() if s is not None
                    ):
                        normalized[fid] = val
                    else:
                        # fallback to processing via frames_src-like logic by wrapping val
                        normalized[fid] = {}  # will be normalized by the generic path below
                # If normalized contains empties, fall through to generic extraction below using fm._frames
                try:
                    # Prefer actual internal frames map if available for richer metadata
                    frames_src = getattr(fm, "_frames", None) or getattr(fm, "frames", None)
                    if frames_src:
                        # let the generic logic below handle frames_src
                        pass
                    else:
                        # if we don't have internal map, return the raw (best-effort)
                        return raw
                except Exception:
                    return raw
        except Exception:
            # ignore and try other ways
            pass

    frames_src = None
    if hasattr(fm, "_frames"):
        frames_src = getattr(fm, "_frames")
    elif hasattr(fm, "frames"):
        frames_src = getattr(fm, "frames")
    else:
        # no frames known on fm, but maybe all_frames exists and returned something earlier; try that
        try:
            maybe = fm.all_frames() if hasattr(fm, "all_frames") else {}
            if isinstance(maybe, dict):
                # If it's already the expected shape, return it
                # If nested, we'll normalize below, so reassign frames_src to maybe
                frames_src = maybe
            else:
                return {}
        except Exception:
            return {}

    def _slot_to_dict(slot) -> Dict[str, Any]:
        if slot is None:
            return {"offset": None, "size": None, "category": None, "type_name": None}
        if isinstance(slot, dict):
            return {
                "offset": slot.get("offset"),
                "size": slot.get("size"),
                "category": slot.get("category"),
                "type_name": slot.get("type_name") or slot.get("type"),
            }
        # assume tuple/list: (offset, size, category) or object with attrs
        try:
            # tuple/list case
            if isinstance(slot, (list, tuple)):
                off = slot[0] if len(slot) > 0 else None
                size = slot[1] if len(slot) > 1 else None
                cat = slot[2] if len(slot) > 2 else None
                return {"offset": off, "size": size, "category": cat, "type_name": None}
            # object-like
            return {
                "offset": getattr(slot, "offset", None),
                "size": getattr(slot, "size", None),
                "category": getattr(slot, "category", None),
                "type_name": getattr(slot, "type_name", getattr(slot, "type", None)),
            }
        except Exception:
            return {"offset": None, "size": None, "category": None, "type_name": None}

    frames: Dict[str, Dict[str, Dict[str, Any]]] = {}
    # frames_src may be a dict mapping frame_id -> Frame-like or already mapping frame_id->symbolmap
    for fid, frame in (frames_src.items() if isinstance(frames_src, dict) else []):
        # If frame already a simple dict mapping name->slot-dict (flat), try a defensive normalization
        if isinstance(frame, dict):
            # decide whether it's already in the final form or is a nested summary
            if any(k in frame for k in ("params", "locals")):
                # nested summary style
                s = frame
                syms_map: Dict[str, Dict[str, Any]] = {}
                params = s.get("params", {}) or {}
                locals_ = s.get("locals", {}) or {}
                for name, slot in params.items():
                    syms_map[name] = _slot_to_dict(slot)
                for name, slot in locals_.items():
                    syms_map[name] = _slot_to_dict(slot)
                # include any other entries that look like slots
                for name, slot in frame.items():
                    if name in ("params", "locals"):
                        continue
                    if isinstance(slot, dict) and ("offset" in slot or "size" in slot):
                        syms_map[name] = _slot_to_dict(slot)
                frames[fid] = syms_map
                continue
            else:
                # Might already be flat symbol->slot mapping; normalize each slot
                syms_map = {name: _slot_to_dict(slot) for name, slot in frame.items()}
                frames[fid] = syms_map
                continue

        # If Frame has summary() method, try to use it and normalize nested params/locals
        if hasattr(frame, "summary"):
            try:
                s = frame.summary()
                if isinstance(s, dict):
                    if "params" in s or "locals" in s:
                        syms_map: Dict[str, Dict[str, Any]] = {}
                        params = s.get("params", {}) or {}
                        locals_ = s.get("locals", {}) or {}
                        for name, slot in params.items():
                            syms_map[name] = _slot_to_dict(slot)
                        for name, slot in locals_.items():
                            syms_map[name] = _slot_to_dict(slot)
                        # also include other possible slot-like fields
                        for name, slot in s.items():
                            if name in ("params", "locals"):
                                continue
                            if isinstance(slot, dict) and ("offset" in slot or "size" in slot):
                                syms_map[name] = _slot_to_dict(slot)
                        frames[fid] = syms_map
                        continue
                    # if it's already a flat mapping, normalize and return
                    if all(isinstance(v, dict) and ("offset" in v or "size" in v) for v in s.values()):
                        frames[fid] = {name: _slot_to_dict(slot) for name, slot in s.items()}
                        continue
                # fallback: try to treat s as flat mapping
                if isinstance(s, dict):
                    frames[fid] = {name: _slot_to_dict(slot) for name, slot in s.items()}
                    continue
            except Exception:
                # ignore and continue to other heuristics
                pass

        # If Frame has 'symbols' mapping, normalize that
        syms_map: Dict[str, Dict[str, Any]] = {}
        if hasattr(frame, "symbols"):
            try:
                raw_symbols = getattr(frame, "symbols")
                if isinstance(raw_symbols, dict):
                    for name, slot in raw_symbols.items():
                        syms_map[name] = _slot_to_dict(slot)
                    frames[fid] = syms_map
                    continue
            except Exception:
                pass

        # Last attempt: try to inspect common attributes on frame object (params/locals)
        try:
            syms_map = {}
            if hasattr(frame, "params"):
                try:
                    for name, slot in getattr(frame, "params").items():
                        syms_map[name] = _slot_to_dict(slot)
                except Exception:
                    pass
            if hasattr(frame, "locals"):
                try:
                    for name, slot in getattr(frame, "locals").items():
                        syms_map[name] = _slot_to_dict(slot)
                except Exception:
                    pass
            if syms_map:
                frames[fid] = syms_map
                continue
        except Exception:
            pass

        # If nothing matched, place an empty mapping (so validator will gracefully report "estructura no es un mapping")
        frames[fid] = {}

    return frames

def _symbol_exists_in_table(st, name: str) -> Tuple[bool, Any]:
    """
    Best-effort check if symbol exists in symbol table. Returns (found, symbol_obj_or_none).
    Tries common shapes: st.lookup(name), st.get(name), st.symbols dict, st._symbols.
    """
    if st is None:
        return (False, None)
    # try common APIs
    for attr in ("lookup", "get", "resolve"):
        if hasattr(st, attr):
            try:
                sym = getattr(st, attr)(name)
                if sym:
                    return True, sym
            except Exception:
                pass
    # try direct dicts
    if hasattr(st, "symbols") and isinstance(getattr(st, "symbols"), dict):
        mp = getattr(st, "symbols")
        if name in mp:
            return True, mp[name]
    if hasattr(st, "_symbols") and isinstance(getattr(st, "_symbols"), dict):
        mp = getattr(st, "_symbols")
        if name in mp:
            return True, mp[name]
    # last attempt: maybe SymbolTable stores attribute 'table' etc.
    for attr in ("table", "_table"):
        if hasattr(st, attr) and isinstance(getattr(st, attr), dict):
            mp = getattr(st, attr)
            if name in mp:
                return True, mp[name]
    return (False, None)

def validate_runtime_consistency(symbol_table, frame_manager) -> List[str]:
    """
    Valida la consistencia entre frame_manager y symbol_table.
    Devuelve lista de mensajes de error (vacía si no hay problemas).
    """
    errors: List[str] = []
    frames = _frames_map_from_fm(frame_manager)

    # Recorremos frames y slots; verificamos overlaps y existencia en symbol table.
    for fid, symmap in frames.items():
        # Normalize to dict(name->slotdict)
        if not isinstance(symmap, dict):
            errors.append(f"[{fid}] estructura de frame no es un mapping esperado.")
            continue

        # Build list of (start,end,name) for overlap detection
        ranges: List[Tuple[int,int,str]] = []
        for name, slot in symmap.items():
            # 🔹 Ignorar campos internos del frame (no son símbolos)
            if name in {"name", "alignment", "param_offset_cursor", "local_offset_cursor"}:
                continue

            # slot may be a dict or other; assume dict-like
            if slot is None:
                offset = None; size = None; category = None; type_name = None
            elif isinstance(slot, dict):
                offset = slot.get("offset")
                size = slot.get("size")
                category = slot.get("category")
                type_name = slot.get("type_name") or slot.get("type")
            else:
                offset = getattr(slot, "offset", None)
                size = getattr(slot, "size", None)
                category = getattr(slot, "category", None)
                type_name = getattr(slot, "type_name", getattr(slot, "type", None))

            # If offset/size are missing, report (but continue).
            if offset is None or size is None:
                errors.append(f"[{fid}] símbolo '{name}' tiene offset/size inválido: offset={offset} size={size}")
                continue

            try:
                start = int(offset)
                length = int(size)
            except Exception:
                errors.append(f"[{fid}] símbolo '{name}' offset/size no numéricos: offset={offset} size={size}")
                continue
            if length <= 0:
                errors.append(f"[{fid}] símbolo '{name}' tiene size no positiva: {length}")
                continue

            end = start + length - 1
            ranges.append((start, end, name))

            # verify symbol exists in symbol table (best-effort)
            found, sym_obj = _symbol_exists_in_table(symbol_table, name)
            if not found:
                errors.append(f"[{fid}] símbolo '{name}' definido en frame pero no encontrado en SymbolTable")

            # if symbol_table has runtime metadata, compare (best-effort)
            if found and sym_obj is not None:
                # try to find metadata inside sym_obj
                meta_offset = None
                meta_size = None
                # common places: sym_obj.offset / sym_obj.metadata dict / sym_obj.runtime
                if hasattr(sym_obj, "offset") and getattr(sym_obj, "offset") is not None:
                    meta_offset = getattr(sym_obj, "offset")
                elif hasattr(sym_obj, "metadata") and isinstance(getattr(sym_obj, "metadata"), dict):
                    md = getattr(sym_obj, "metadata")
                    meta_offset = md.get("offset", md.get("addr", None))
                    meta_size   = md.get("size", None)
                elif isinstance(sym_obj, dict):
                    meta_offset = sym_obj.get("offset")
                    meta_size = sym_obj.get("size")

                # if we have metadata, compare
                if meta_offset is not None:
                    try:
                        if int(meta_offset) != start:
                            errors.append(f"[{fid}] símbolo '{name}' offset mismatch: frame={start} table={meta_offset}")
                    except Exception:
                        pass
                if meta_size is not None:
                    try:
                        if int(meta_size) != length:
                            errors.append(f"[{fid}] símbolo '{name}' size mismatch: frame={length} table={meta_size}")
                    except Exception:
                        pass

        # overlap detection (sort by start)
        ranges.sort(key=lambda t: t[0])
        for i in range(1, len(ranges)):
            prev_s, prev_e, prev_name = ranges[i-1]
            cur_s, cur_e, cur_name = ranges[i]
            if cur_s <= prev_e:
                errors.append(f"[{fid}] overlap entre '{prev_name}' ({prev_s}-{prev_e}) y '{cur_name}' ({cur_s}-{cur_e})")

    return errors

def dump_runtime_info_json(frame_manager) -> str:
    """
    Retorna JSON serializado con la información de frames normalizada
    (útil para el IDE o logging).
    """
    frames = _frames_map_from_fm(frame_manager)
    # Force simple serializable values (ints or null)
    out = {}
    for fid, symmap in frames.items():
        out[fid] = {}
        for name, slot in symmap.items():
            if slot is None:
                out[fid][name] = {"offset": None, "size": None, "category": None, "type_name": None}
            elif isinstance(slot, dict):
                out[fid][name] = {
                    "offset": slot.get("offset"),
                    "size": slot.get("size"),
                    "category": slot.get("category"),
                    "type_name": slot.get("type_name") or slot.get("type"),
                }
            else:
                out[fid][name] = {
                    "offset": getattr(slot, "offset", None),
                    "size": getattr(slot, "size", None),
                    "category": getattr(slot, "category", None),
                    "type_name": getattr(slot, "type_name", getattr(slot, "type", None)),
                }
    return json.dumps(out, indent=2)
