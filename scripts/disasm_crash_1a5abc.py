from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

p = Path(
    r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D"
    r"\downloads\extracted_geo11_v0.7.10\x64\d3d11.dll"
)
b = p.read_bytes()
md = Cs(CS_ARCH_X86, CS_MODE_64)
DELTA = 0xC00
BASE = 0x180000000


def dis(fo, n=0xA0):
    print(f"\n=== FO {hex(fo)} ===")
    for i in md.disasm(b[fo : fo + n], BASE + fo + DELTA):
        off = i.address - (BASE + DELTA)
        mark = " <<FAULT" if off == 0x1A5ABC else ""
        print(f"{hex(i.address)} fo={hex(off)}: {i.mnemonic} {i.op_str}{mark}")


dis(0x1A4EB0, 0x200)
dis(0x1A50D6, 0x120)
dis(0x1A5A90, 0x80)
