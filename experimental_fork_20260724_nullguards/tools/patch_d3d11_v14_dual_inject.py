"""v14: v13 AddRef skips + early-out stereo inject for VS AND PS native shaders.

Stock crash: AddRef null at RVA 0x1a5abc.
After AddRef skip: stereo inject AV at RVA 0x216e6c (VS) / 0x21917c (PS)
when force_stereo=2 and shader lacks wrapper fields.
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
    code += bytes.fromhex("4885d2")
    je0 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("488b4a30")
    code += bytes.fromhex("4885c9")
    je1 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("ff4218488b01ff5008")
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


def make_inject_skip(site: int, label: str, cur: int) -> int:
    """At function entry: test rcx / lea rbx,[rcx+0x28] / mov rdi,rdx (10 bytes).

    If rcx null OR [rcx+0x30]==0 → epilogue return (skip stereo inject).
    Else restore original 10 bytes and continue.
    """
    assert bytes(b[site : site + 10]) == bytes.fromhex("4885c9488d5928488bfa")
    end = site + 10
    cont = end
    code = bytearray()
    code += bytes.fromhex("4885c9")  # test rcx,rcx
    je0 = len(code)
    code += bytes.fromhex("7400")  # je ret
    code += bytes.fromhex("4883793000")  # cmp qword [rcx+0x30],0
    je1 = len(code)
    code += bytes.fromhex("7400")  # je ret
    # original prolog then continue
    code += bytes.fromhex("4885c9488d5928488bfa")
    j_cont = len(code)
    code += b"\xE9" + struct.pack("<i", 0)
    ret = len(code)
    # epilogue matching nearby returns: mov rbx,[rsp+0x30]; add rsp,0x20; pop rdi; ret
    # From disasm of similar: sub rsp,0x20 at entry for PS twin.
    # VS FUN at 0x21618a - need correct epilogue. Check bytes before site.
    code += bytes.fromhex("488b5c2430")  # mov rbx,[rsp+0x30]
    code += bytes.fromhex("4883c420")  # add rsp,0x20
    code += bytes.fromhex("5f")  # pop rdi
    code += bytes.fromhex("c3")  # ret
    code[je0 + 1] = (ret - (je0 + 2)) & 0xFF
    code[je1 + 1] = (ret - (je1 + 2)) & 0xFF
    struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
    return install(site, end, bytes(code), label, cur)


# Verify prolog bytes for both inject functions
assert bytes(b[0x21618A : 0x21618A + 10]) == bytes.fromhex("4885c9488d5928488bfa")
assert bytes(b[0x21849A : 0x21849A + 10]) == bytes.fromhex("4885c9488d5928488bfa")

cur = make_inject_skip(0x21618A, "InjectSkipVS", cur)
cur = make_inject_skip(0x21849A, "InjectSkipPS", cur)

# Release null-guards (same as v12)
def make_release_guard(site_fo: int, label: str, cur: int) -> int:
    assert bytes(b[site_fo : site_fo + 10]) == bytes.fromhex("488b4920488b01ff5010")
    end = site_fo + 10
    cont = end
    code = bytearray()
    code += bytes.fromhex("488b4920")
    code += bytes.fromhex("4885c9")
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
print("OK", hashlib.sha256(bytes(b)).hexdigest().upper(), "->", DST)
print("cave_used", hex(cur - cave))
