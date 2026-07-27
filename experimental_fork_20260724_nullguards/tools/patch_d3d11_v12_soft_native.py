"""v12: soft-native — keep stereo wrapper for HackerShaders; tolerate native COM.

v11 call-through returned early and skipped stereo state → alive but mono.
v12:
  - NullRdx
  - Skip AddRef only when [shader+0x30]==0 (VS + PS)
  - FUN_180177ec0: if +0x30 null, return shader ptr as-is (native)
  - FUN_180216d80: if +0x30 null, return (no stereo param inject)
  - Release: skip if [obj+0x20]==0
"""
from pathlib import Path
import struct
import hashlib
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
b = bytearray(SRC.read_bytes())
cave = 0x6AF274
b[cave : cave + 0x280] = b"\xCC" * 0x280
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

# --- NullRdx ---
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
    """Skip AddRef when +0x30 null; else original; always continue at cont."""
    code = bytearray()
    code += bytes.fromhex("4885d2")  # test rdx,rdx
    je0 = len(code)
    code += bytes.fromhex("7400")  # je cont
    code += bytes.fromhex("488b4a30")  # mov rcx,[rdx+0x30]
    code += bytes.fromhex("4885c9")  # test rcx,rcx
    je1 = len(code)
    code += bytes.fromhex("7400")  # je cont (native)
    code += bytes.fromhex("ff4218")  # inc [rdx+0x18]
    code += bytes.fromhex("488b01")  # mov rax,[rcx]
    code += bytes.fromhex("ff5008")  # call [rax+8]
    j_cont = len(code)
    code += b"\xE9" + struct.pack("<i", 0)
    code[je0 + 1] = (j_cont - (je0 + 2)) & 0xFF
    code[je1 + 1] = (j_cont - (je1 + 2)) & 0xFF
    struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
    return bytes(code)


# VS AddRef block
site, end = 0x1A4EB0, 0x1A4EC2
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
cur = install(site, end, make_addref_skip(0x1A4EC2, cur), "AddRefVS", cur)

# PS AddRef block
site, end = 0x1A50D6, 0x1A50E8
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
cur = install(site, end, make_addref_skip(0x1A50E8, cur), "AddRefPS", cur)

# --- GetShader FUN_180177ec0: after mov rbx,rdx (FO 0x1772cd / RVA 0x177ecd) ---
# Replace from mov rbx,rdx through cmp [rcx+0x22bc],1 setup... 
# Patch at FO 0x1772cd (mov rbx, rdx = 48 8b da) — overwrite following test path
# Simpler: hook at 0x1772dd (test rdx,rdx at 0x177edd) area
# Bytes at FO for RVA 0x177ecd: mov rbx,rdx
site = 0x1772CD  # mov rbx, rdx; cmp dword [rcx+0x22bc],1
assert bytes(b[site : site + 3]) == bytes.fromhex("488bda")
# replace mov rbx,rdx with jmp to cave; cave does mov rbx,rdx then native check
end = site + 5  # need 5 bytes for jmp — next is cmp [rcx+0x22bc],1 which is 7 bytes (83 b9 bc 22 00 00 01)
# Use site covering mov rbx,rdx (3) + start of cmp — actually install 5-byte jmp at 0x1772cd
# Original: 48 8B DA 83 B9 BC 22 00 00 01
assert bytes(b[site : site + 10]) == bytes.fromhex("488bda83b9bc22000001")
end = site + 10
cont = site + 10  # after cmp imm, at jne
code = bytearray()
code += bytes.fromhex("488bda")  # mov rbx, rdx
code += bytes.fromhex("4885d2")  # test rdx,rdx
je_null = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("48837a3000")  # cmp qword [rdx+0x30], 0
jne_wrapped = len(code)
code += bytes.fromhex("7500")
# native: return rdx
code += bytes.fromhex("488bc2")  # mov rax, rdx
code += bytes.fromhex("4883c430")  # add rsp, 0x30
code += bytes.fromhex("5b")  # pop rbx
code += bytes.fromhex("c3")  # ret
# continue original cmp
wrapped = len(code)
code += bytes.fromhex("83b9bc22000001")  # cmp dword [rcx+0x22bc],1
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
# null rdx -> still do original cmp
code[je_null + 1] = (wrapped - (je_null + 2)) & 0xFF
code[jne_wrapped + 1] = (wrapped - (jne_wrapped + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
cur = install(site, end, bytes(code), "GetShaderNative", cur)

# --- FUN_180216d80 early out (RVA 0x216d8a / FO 0x21618a) ---
# test rcx,rcx (3) + lea rbx,[rcx+0x28] (4) = 7 bytes; need 8 for jmp → steal 1 nop from next
site = 0x21618A
assert bytes(b[site : site + 7]) == bytes.fromhex("4885c9488d5928")
# next byte is start of mov rdi,rdx (48 8b fa) — overwrite 8 bytes, re-emit stolen 48 in cave via full mov
assert b[site + 7] == 0x48 and bytes(b[site + 7 : site + 10]) == bytes.fromhex("488bfa")
end = site + 10  # cover test+lea+mov rdi,rdx
cont = end
code = bytearray()
code += bytes.fromhex("4885c9")
je0 = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("4883793000")
jne0 = len(code)
code += bytes.fromhex("7500")
code += bytes.fromhex("488b5c2430")  # mov rbx,[rsp+0x30]
code += bytes.fromhex("4883c4205fc3")
cont_code = len(code)
code += bytes.fromhex("488d5928")  # lea rbx,[rcx+0x28]
code += bytes.fromhex("488bfa")  # mov rdi,rdx (stolen)
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)
code[je0 + 1] = (cont_code - (je0 + 2)) & 0xFF
code[jne0 + 1] = (cont_code - (jne0 + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
cur = install(site, end, bytes(code), "StereoInjectSkip", cur)

# --- Release null-guard: mov rcx,[rcx+0x20] is 48 8B 49 20 ---
def make_release_guard(site_fo: int, label: str, cur: int) -> int:
    seq = bytes(b[site_fo : site_fo + 10])
    print(label, "seq", seq.hex())
    assert seq == bytes.fromhex("488b4920488b01ff5010")
    end = site_fo + 10
    cont = end
    code = bytearray()
    code += bytes.fromhex("488b4920")  # mov rcx,[rcx+0x20]
    code += bytes.fromhex("4885c9")  # test rcx,rcx
    je0 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("488b01ff5010")
    j_cont = len(code)
    code += b"\xE9" + struct.pack("<i", 0)
    code[je0 + 1] = (j_cont - (je0 + 2)) & 0xFF
    struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
    return install(site_fo, end, bytes(code), label, cur)


cur = make_release_guard(0x1A4ED5, "ReleaseVS", cur)
cur = make_release_guard(0x1A50FF, "ReleasePS", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest()[:16], "->", DST)
print("cave_used", hex(cur - cave))
