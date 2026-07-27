from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

b = Path(
    r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D"
    r"\downloads\extracted_geo11_v0.7.10\x64\d3d11.dll"
).read_bytes()
md = Cs(CS_ARCH_X86, CS_MODE_64)
BASE = 0x180000000
DELTA = 0xC00


def dis(fo, n=0x120):
    print(f"\n=== FO {hex(fo)} RVA {hex(fo+DELTA)} ===")
    for i in md.disasm(b[fo : fo + n], BASE + fo + DELTA):
        off = i.address - (BASE + DELTA)
        mark = ""
        if off == 0x216E6C:
            mark = " <<FAULT_OFFSET"
        if off == 0x21618A:
            mark = " <<v12_patch_site"
        print(f"fo={hex(off)}: {i.mnemonic} {i.op_str}{mark}")


# Fault offset 0x216e6c as RVA => FO = 0x216e6c - 0xC00 = 0x21626c
fault_fo = 0x216E6C - DELTA
print("computed fault FO", hex(fault_fo))
dis(fault_fo - 0x40, 0xC0)
dis(0x21618A, 0x100)
# also check 0x219090 area (PS stereo)
dis(0x219090 - DELTA - 0x20, 0x80)
