"""v24: NativeVS/PS call-through only. NO NullRdx.

Hypothesis: NullRdx E_NOINTERFACE / soft-forward is what leaves DirectMode
as Stereo-disabled; AddRef native path alone may keep stereo + survive packer.
"""
from pathlib import Path
import struct
import hashlib
import sys

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
b = bytearray(SRC.read_bytes())
cave = 0x6AF274
b[cave : cave + 0x200] = b"\xCC" * 0x200


def install(site: int, end: int, code: bytes, label: str, cur: int) -> int:
    b[cur : cur + len(code)] = code
    b[site:end] = b"\xE9" + struct.pack("<i", cur - (site + 5)) + b"\x90" * (end - site - 5)
    print(label, hex(site), hex(cur), len(code))
    return cur + ((len(code) + 15) // 16) * 16


cur = cave

# NativeVS
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

# NativePS
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
print("OK", hashlib.sha256(bytes(b)).hexdigest().upper())
print("cave_used", hex(cur - cave))
