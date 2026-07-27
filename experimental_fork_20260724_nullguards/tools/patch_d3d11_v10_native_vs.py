"""v10: survive CustomShaderUpscale restoring a native Windows VS.

geo-11 VSSetShader (RVA 0x1a5a90) AddRefs via [shader+0x30]. Native shaders
from VSGetShader have null there → AV. If +0x30 is null, call through to the
real ID3D11DeviceContext::VSSetShader and return.

Also keeps NullRdx guard (force_stereo init).
"""
from pathlib import Path
import struct
import hashlib
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

SRC = Path(sys.argv[1])
DST = Path(sys.argv[2])

b = bytearray(SRC.read_bytes())
cave = 0x6AF274
b[cave : cave + 0x200] = b"\xCC" * 0x200
md = Cs(CS_ARCH_X86, CS_MODE_64)


def fo_to_va(fo: int) -> int:
    return 0x180000000 + fo + 0xC00


def install(site: int, end: int, code: bytes, label: str, cur: int) -> int:
    b[cur : cur + len(code)] = code
    b[site:end] = b"\xE9" + struct.pack("<i", cur - (site + 5)) + b"\x90" * (end - site - 5)
    print(f"{label} site_fo={hex(site)} cave_fo={hex(cur)} len={len(code)}")
    for i in md.disasm(code, fo_to_va(cur)):
        print(f"  {i.mnemonic} {i.op_str}")
    return cur + ((len(code) + 15) // 16) * 16


cur = cave

# --- NullRdx FO 0x1a2e46 / RVA 0x1a3a46 ---
site, end = 0x1A2E46, 0x1A2E4C
assert bytes(b[site:end]) == bytes.fromhex("488b02488bda")
cont, fail = 0x1A2E4C, 0x1A2E86
code = bytearray()
code += bytes.fromhex("4885d2")
je = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("488b02488bda")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
null_path = len(code)
code += bytes.fromhex("4489c6")
code += bytes.fromhex("48c744247000000000")
code += bytes.fromhex("4c8be94c89cf31dbb802400080")
j_fail = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je + 1] = (null_path - (je + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
struct.pack_into("<i", code, j_fail + 1, fail - (cur + j_fail + 5))
cur = install(site, end, bytes(code), "NullRdx", cur)

# --- NativeVS at AddRef block FO 0x1a4eb0..0x1a4ec2 ---
# Prolog left: rbx=ctx, rbp=shader, rsi=class_instances, edi=num
site, end = 0x1A4EB0, 0x1A4EC2
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
cont_wrapped = 0x1A4EC2

code = bytearray()
code += bytes.fromhex("4885d2")  # test rdx,rdx
je0 = len(code)
code += bytes.fromhex("7400")  # je -> continue wrapped path (null shader)
code += bytes.fromhex("488b4a30")  # mov rcx,[rdx+0x30]
code += bytes.fromhex("4885c9")  # test rcx,rcx
jne_addref = len(code)
code += bytes.fromhex("7500")  # jne -> wrapped AddRef

# native call-through (matches epilogue call at 0x1a5c58)
code += bytes.fromhex("488b4b10")  # mov rcx,[rbx+0x10]
code += bytes.fromhex("488bd5")  # mov rdx,rbp
code += bytes.fromhex("4c8bc6")  # mov r8,rsi
code += bytes.fromhex("448bcf")  # mov r9d,edi
code += bytes.fromhex("488b01")  # mov rax,[rcx]
code += bytes.fromhex("ff5058")  # call [rax+0x58] VSSetShader
code += bytes.fromhex("488b5c2450")  # mov rbx,[rsp+0x50]
code += bytes.fromhex("488b6c2458")  # mov rbp,[rsp+0x58]
code += bytes.fromhex("488b742460")  # mov rsi,[rsp+0x60]
code += bytes.fromhex("4883c440")  # add rsp,0x40
code += bytes.fromhex("5f")  # pop rdi
code += bytes.fromhex("c3")  # ret

addref = len(code)
code += bytes.fromhex("488b4a30")  # mov rcx,[rdx+0x30]
code += bytes.fromhex("ff4218")  # inc dword [rdx+0x18]
code += bytes.fromhex("488b01")  # mov rax,[rcx]
code += bytes.fromhex("ff5008")  # call [rax+8]
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)

code[je0 + 1] = (j_cont - (je0 + 2)) & 0xFF
code[jne_addref + 1] = (addref - (jne_addref + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, cont_wrapped - (cur + j_cont + 5))
cur = install(site, end, bytes(code), "NativeVS", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest()[:16], "->", DST)
print("cave_used", hex(cur - cave))
