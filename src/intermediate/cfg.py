from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from src.intermediate.tac_nodes import TACOP

@dataclass
class BasicBlock:
    id: int
    start: int
    end: int
    labels: List[str] = field(default_factory=list)
    succ: List[int] = field(default_factory=list)
    pred: List[int] = field(default_factory=list)

@dataclass
class CFG:
    blocks: List[BasicBlock]
    label2block: Dict[str, int]

def build_cfg(tac: List[TACOP]) -> CFG:
    # 1) Mapa label -> índice de instrucción
    label_at: Dict[str, int] = {}
    for i, ins in enumerate(tac):
        if ins.op == "label" and ins.result:
            label_at[ins.result] = i

    # 2) Bloques líderes
    leaders: Set[int] = set()
    if tac:
        leaders.add(0)

    def add_leader(idx: int):
        if 0 <= idx < len(tac):
            leaders.add(idx)

    for i, ins in enumerate(tac):
        if ins.op == "goto":
            tgt = label_at.get(ins.arg1)
            if tgt is not None: add_leader(tgt)
            add_leader(i + 1)
        elif ins.op == "if-goto":
            tgt = label_at.get(ins.arg2)
            if tgt is not None: add_leader(tgt)
            add_leader(i + 1)
        elif ins.op == "return":
            add_leader(i + 1)

    # 3) Construir bloques contiguos
    leaders_sorted = sorted(leaders)
    blocks: List[BasicBlock] = []
    label2block: Dict[str, int] = {}

    for bidx, start in enumerate(leaders_sorted):
        end = (leaders_sorted[bidx+1] - 1) if bidx+1 < len(leaders_sorted) else (len(tac) - 1)
        labels = []
        for i in range(start, end + 1):
            if tac[i].op == "label" and tac[i].result:
                labels.append(tac[i].result)
        block = BasicBlock(id=bidx, start=start, end=end, labels=labels)
        blocks.append(block)
        for L in labels:
            label2block[L] = bidx

    # 4) Conectar edges
    def add_edge(frm: int, to: Optional[int]):
        if to is None: return
        if 0 <= to < len(blocks):
            if to not in blocks[frm].succ:
                blocks[frm].succ.append(to)
            if frm not in blocks[to].pred:
                blocks[to].pred.append(frm)

    for b in blocks:
        if b.start > b.end: 
            continue
        last = tac[b.end]
        if last.op == "goto":
            add_edge(b.id, label2block.get(last.arg1))
        elif last.op == "if-goto":
            add_edge(b.id, label2block.get(last.arg2))          # rama verdadera
            add_edge(b.id, b.id + 1 if b.id + 1 < len(blocks) else None)  # caída
        elif last.op == "return":
            pass  # no sucesores
        else:
            add_edge(b.id, b.id + 1 if b.id + 1 < len(blocks) else None)

    return CFG(blocks=blocks, label2block=label2block)
