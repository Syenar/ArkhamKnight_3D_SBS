"""v25: AddRef skip + InjectSkip(+0x30==0) + null-guard at 0x1a8180 loop.

No NullRdx (avoids Stereo-disabled). Survives packer where v22 died at 0x1a8180,
while still allowing stereo inject for wrapped game shaders.
"""
from pathlib import Path
import struct
import hashlib
import sys

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
b = bytearray(SRC.read_bytes())
cave = 0x6AF274
b[cave : cave + 0x280] = b"\xCC" * 0x280


def install(site: int, end: int, code: bytes, label: str, cur: int) -> int:
    b[cur : cur + len(code)] = code
    b[site:end] = b"\xE9" + struct.pack("<i", cur - (site + 5)) + b"\x90" * (end - site - 5)
    print(label, hex(site), hex(cur), len(code))
    return cur + ((len(code) + 15) // 16) * 16


cur = cave


def addref_skip(cont: int, cur: int) -> bytes:
    code = bytearray()
    code += bytes.fromhex("4885d2")
    je0 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("488b4a304885c9")
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
cur = install(site, end, addref_skip(0x1A4EC2, cur), "AddRefVS", cur)
site, end = 0x1A50D6, 0x1A50E8
assert bytes(b[site:end]) == bytes.fromhex("4885d2740d488b4a30ff4218488b01ff5008")
cur = install(site, end, addref_skip(0x1A50E8, cur), "AddRefPS", cur)


def inject_skip(site: int, label: str, cur: int) -> int:
    assert bytes(b[site : site + 10]) == bytes.fromhex("4885c9488d5928488bfa")
    end = site + 10
    code = bytearray()
    code += bytes.fromhex("4885c9")
    je0 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("4883793000")
    je1 = len(code)
    code += bytes.fromhex("7400")
    code += bytes.fromhex("4885c9488d5928488bfa")
    j_cont = len(code)
    code += b"\xE9" + struct.pack("<i", 0)
    ret = len(code)
    code += bytes.fromhex("488b5c24304883c4205fc3")
    code[je0 + 1] = (ret - (je0 + 2)) & 0xFF
    code[je1 + 1] = (ret - (je1 + 2)) & 0xFF
    struct.pack_into("<i", code, j_cont + 1, end - (cur + j_cont + 5))
    return install(site, end, bytes(code), label, cur)


cur = inject_skip(0x21618A, "InjectVS", cur)
cur = inject_skip(0x21849A, "InjectPS", cur)

# Guard vector loop at FO 0x1a7557 (RVA 0x1a8180 crash when rcx null)
# Original through near-je empty: mov rcx/rax, sub, sar, test rax, je 0x1a77cf
site, end = 0x1A7557, 0x1A7575
assert bytes(b[site:end]) == bytes.fromhex(
    "498b88d8000000498b80e0000000482bc148c1f8024885c00f845a020000"
)
code = bytearray()
code += bytes.fromhex("498b88d8000000")  # mov rcx,[r8+0xd8]
code += bytes.fromhex("498b80e0000000")  # mov rax,[r8+0xe0]
code += bytes.fromhex("4885c9")  # test rcx,rcx
je0 = len(code)
code += bytes.fromhex("7400")
code += bytes.fromhex("482bc148c1f8024885c0")  # sub/sar/test rax
je1 = len(code)
code += bytes.fromhex("7400")
j_cont = len(code)
code += b"\xE9" + struct.pack("<i", 0)  # jmp 0x1a7575
j_empty = len(code)
code += b"\xE9" + struct.pack("<i", 0)  # jmp 0x1a77cf
code[je0 + 1] = (j_empty - (je0 + 2)) & 0xFF
code[je1 + 1] = (j_empty - (je1 + 2)) & 0xFF
struct.pack_into("<i", code, j_cont + 1, 0x1A7575 - (cur + j_cont + 5))
struct.pack_into("<i", code, j_empty + 1, 0x1A77CF - (cur + j_empty + 5))
cur = install(site, end, bytes(code), "LoopGuard", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest().upper())
print("cave_used", hex(cur - cave))
