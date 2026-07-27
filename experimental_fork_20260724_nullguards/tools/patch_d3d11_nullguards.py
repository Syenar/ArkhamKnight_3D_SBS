"""Patch geo-11 d3d11.dll null-deref sites by diverting to existing failure paths."""
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
# fo 0x6af274 -> rva 0x6afe74 (constant for this binary)
RVA_DELTA = 0x600


def fo_to_va(fo: int) -> int:
    return 0x180000000 + fo + RVA_DELTA


def install(site: int, end: int, code: bytes, label: str, cur: int) -> int:
    b[cur : cur + len(code)] = code
    b[site:end] = b"\xE9" + struct.pack("<i", cur - (site + 5)) + b"\x90" * (end - site - 5)
    print(f"{label} site={hex(site)} cave={hex(cur)}")
    for i in md.disasm(code, fo_to_va(cur)):
        print(f"  {i.mnemonic} {i.op_str}")
    return cur + ((len(code) + 15) // 16) * 16


cur = cave

# --- NullRdx at 0x1a2e46 / VA 0x1a3a46 ---
# If rdx==null, set up regs like a failed QI and jump to test/js at 0x1a3a86.
# Else do original mov rax,[rdx]; mov rbx,rdx and continue at 0x1a3a4c.
site, end = 0x1A2E46, 0x1A2E4C
assert bytes(b[site:end]) == bytes.fromhex("48 8b 02 48 8b da")
cont = 0x1A2E4C  # -> VA 0x1a3a4c
fail = 0x1A2E86  # -> VA 0x1a3a86 (test eax,eax / js fail path)
code = bytearray()
code += bytes.fromhex("48 85 d2")  # test rdx,rdx
je = len(code)
code += bytes.fromhex("74 00")  # je null_path
code += bytes.fromhex("48 8b 02 48 8b da")  # mov rax,[rdx]; mov rbx,rdx
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
null_path = len(code)
code += bytes.fromhex("41 89 f0")  # mov r8d,esi? NO — need mov esi,r8d first
# Correct null path:
#   mov esi, r8d
#   mov qword [rsp+0x70], 0
#   mov r13, rcx
#   mov rdi, r9
#   xor ebx, ebx
#   mov eax, 0x80004002
#   jmp fail (0x1a3a86)
code = bytearray()
code += bytes.fromhex("48 85 d2")
je = len(code)
code += bytes.fromhex("74 00")
code += bytes.fromhex("48 8b 02 48 8b da")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
null_path = len(code)
code += bytes.fromhex("41 89 c6")  # WRONG
# rebuild null path carefully
code = bytearray()
code += bytes.fromhex("48 85 d2")  # test rdx,rdx
je = len(code)
code += bytes.fromhex("74 00")
code += bytes.fromhex("48 8b 02")  # mov rax,[rdx]
code += bytes.fromhex("48 8b da")  # mov rbx,rdx
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
null_path = len(code)
code += bytes.fromhex("44 89 c6")  # mov esi, r8d
code += bytes.fromhex("48 c7 44 24 70 00 00 00 00")  # mov qword [rsp+0x70], 0
code += bytes.fromhex("4c 8b e9")  # mov r13, rcx
code += bytes.fromhex("4c 89 cf")  # mov rdi, r9
code += bytes.fromhex("31 db")  # xor ebx, ebx
code += bytes.fromhex("b8 02 40 00 80")  # mov eax, E_NOINTERFACE
j_fail = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je + 1] = (null_path - (je + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
struct.pack_into("<i", code, j_fail + 1, fail - (cur + j_fail + 5))
cur = install(site, end, bytes(code), "NullRdx", cur)

# --- AddRef: skip call if rcx null ---
site, end = 0x1A4EBC, 0x1A4EC2
assert bytes(b[site:end]) == bytes.fromhex("48 8b 01 ff 50 08")
code = bytearray(bytes.fromhex("48 85 c9 74 06 48 8b 01 ff 50 08"))
code += b"\xE9" + struct.pack("<i", end - (cur + len(code) + 5))
cur = install(site, end, bytes(code), "AddRef", cur)

# --- NullRdi: if null, jmp existing error path 0x1fd552 ---
site, end = 0x1FC906, 0x1FC90D
assert bytes(b[site:end]) == bytes.fromhex("48 8b 07 4c 8d 45 38")
cont = 0x1FC90D
skip = 0x1FC952  # VA 0x1fd552
code = bytearray()
code += bytes.fromhex("48 85 ff")  # test rdi,rdi
je = len(code)
code += bytes.fromhex("74 00")
code += bytes.fromhex("48 8b 07 4c 8d 45 38")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
null_path = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je + 1] = (null_path - (je + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
struct.pack_into("<i", code, null_path + 1, skip - (cur + null_path + 5))
cur = install(site, end, bytes(code), "NullRdi", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest()[:16], "->", DST)
