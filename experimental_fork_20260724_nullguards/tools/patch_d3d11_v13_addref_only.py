"""v13: NullRdx + soft AddRef skip on VS/PS only.

Keeps stereo wrapper paths intact (unlike v11 native call-through).
Omits v12 GetShaderNative / StereoInjectSkip (those crashed or killed stereo).
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
    print(f"{label} site_fo={hex(site)} cave_fo={hex(cur)} n={len(code)}")
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


def make_addref_skip(cont: int, cur: int) -> bytes:
    code = bytearray()
    code += bytes.fromhex("4885d2")  # test rdx,rdx
    je0 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("488b4a30")  # mov rcx,[rdx+0x30]
    code += bytes.fromhex("4885c9")
    je1 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("ff4218")  # inc [rdx+0x18]
    code += bytes.fromhex("488b01")
    code += bytes.fromhex("ff5008")  # AddRef
    j_cont = len(code)
    code += b"\xE9" + struct.pack("<i", 0)
    code[je0 + 1] = (j_cont - (je0 + 2)) & 0xFF
    code[je1 + 1] = (j_cont - (je1 + 2)) & 0xFF
    struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
    return bytes(code)


site, end = 0x1A4EB0, 0x1A4EC2
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
cur = install(site, end, make_addref_skip(0x1A4EC2, cur), "AddRefVS", cur)

site, end = 0x1A50D6, 0x1A50E8
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
cur = install(site, end, make_addref_skip(0x1A50E8, cur), "AddRefPS", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest().upper(), "->", DST)
print("cave_used", hex(cur - cave))
