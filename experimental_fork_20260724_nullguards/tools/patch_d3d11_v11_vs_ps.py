"""v11: native call-through for VSSetShader (+0x58) and PSSetShader (+0x48).

CustomShaderUpscale restores native Windows shaders; geo-11 AddRefs [shader+0x30].
"""
from pathlib import Path
import struct
import hashlib
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
b = bytearray(SRC.read_bytes())
cave = 0x6AF274
b[cave : cave + 0x200] = b"\xCC" * 0x200
md = Cs(CS_ARCH_X86, CS_MODE_64)


def fo_to_va(fo: int) -> int:
    return 0x180000000 + fo + 0xC00


def install(site: int, end: int, code: bytes, label: str, cur: int) -> int:
    b[cur : cur + len(code)] = code
    b[site:end] = b"\xE9" + struct.pack("<i", cur - (site + 5)) + b"\x90" * (end - site - 5)
    print(f"{label} site_fo={hex(site)} cave_fo={hex(cur)}")
    for i in md.disasm(code, fo_to_va(cur)):
        print(f"  {i.mnemonic} {i.op_str}")
    return cur + ((len(code) + 15) // 16) * 16


cur = cave

# NullRdx
site, end = 0x1A2E46, 0x1A2E4C
assert bytes(b[site:end]) == bytes.fromhex("488b02488bda")
code = bytearray()
code += bytes.fromhex("4885d2")
je = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("488b02488bda")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
null_path = len(code)
code += bytes.fromhex("4489c648c7442470000000004c8be94c89cf31dbb802400080")
j_fail = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je + 1] = (null_path - (je + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, 0x1A2E4C - (cur + j_cont + 5))
struct.pack_into("<i", code, j_fail + 1, 0x1A2E86 - (cur + j_fail + 5))
cur = install(site, end, bytes(code), "NullRdx", cur)

# VS: FO 0x1a4eb0, vtbl+0x58, epilogue pop rdi
site, end = 0x1A4EB0, 0x1A4EC2
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
code = bytearray()
code += bytes.fromhex("4885d2")
je0 = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("488b4a304885c9")
jne_a = len(code)
code += bytes.fromhex("7500")
code += bytes.fromhex("488b4b10488bd54c8bc6448bcf488b01ff5058")
code += bytes.fromhex("488b5c2450488b6c2458488b7424604883c4405fc3")
addref = len(code)
code += bytes.fromhex("488b4a30ff4218488b01ff5008")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je0 + 1] = (j_cont - (je0 + 2)) & 0xFF
code[jne_a + 1] = (addref - (jne_a + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, 0x1A4EC2 - (cur + j_cont + 5))
cur = install(site, end, bytes(code), "NativeVS", cur)

# PS: FO 0x1a50d6, vtbl+0x48, epilogue pop r14
site, end = 0x1A50D6, 0x1A50E8
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
code = bytearray()
code += bytes.fromhex("4885d2")
je0 = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("488b4a304885c9")
jne_a = len(code)
code += bytes.fromhex("7500")
code += bytes.fromhex("488b4b10488bd54c8bc6448bcf488b01ff5048")
code += bytes.fromhex("488b5c2450488b6c2458488b742460488b7c24684883c440415ec3")
addref = len(code)
code += bytes.fromhex("488b4a30ff4218488b01ff5008")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je0 + 1] = (j_cont - (je0 + 2)) & 0xFF
code[jne_a + 1] = (addref - (jne_a + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, 0x1A50E8 - (cur + j_cont + 5))
cur = install(site, end, bytes(code), "NativePS", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest()[:16], "->", DST)
print("cave_used", hex(cur - cave))
