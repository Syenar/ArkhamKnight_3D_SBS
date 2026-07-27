import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

dll = Path(
    r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D"
    r"\downloads\extracted_geo11_v0.7.10\x64\d3d11.dll"
)
b = dll.read_bytes()
pe = struct.unpack_from("<I", b, 0x3C)[0]
coff = pe + 4
nsec = struct.unpack_from("<H", b, coff + 2)[0]
opt = coff + 20
magic = struct.unpack_from("<H", b, opt)[0]
assert magic == 0x20B
dd_count = struct.unpack_from("<I", b, opt + 108)[0]
sec_off = opt + 112 + dd_count * 8
print("sections", nsec, "sec_off", hex(sec_off))
secs = []
for i in range(nsec):
    o = sec_off + i * 40
    name = b[o : o + 8].split(b"\0", 1)[0].decode("ascii", "replace")
    vs, va, rsz, raw = struct.unpack_from("<IIII", b, o + 8)
    secs.append((name, va, vs, raw, rsz))
    print(f"{name:8} VA={va:08x} VS={vs:08x} RAW={raw:08x} RSZ={rsz:08x}")


def rva_to_fo(rva: int) -> int | None:
    for name, va, vs, raw, rsz in secs:
        if va <= rva < va + max(vs, rsz):
            return raw + (rva - va)
    return None


for rva in (0x15AE58, 0x1A5ABC, 0x216E6C, 0x21917C, 0x1A4EBC):
    fo = rva_to_fo(rva)
    print(f"RVA {rva:08x} -> FO {fo and hex(fo)}")

md = Cs(CS_ARCH_X86, CS_MODE_64)
rva = 0x15AE58
fo = rva_to_fo(rva)
print("\nDisasm around fault")
for i in md.disasm(b[fo - 0x20 : fo + 0x40], 0x180000000 + rva - 0x20):
    off = i.address - 0x180000000
    m = " <<" if off == rva else ""
    print(f"RVA {off:08x}: {i.mnemonic} {i.op_str}{m}")
