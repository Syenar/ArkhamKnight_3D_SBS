"""v22: AddRef soft-skip + InjectSkip (+0x30==0 only). NO NullRdx.

NullRdx's E_NOINTERFACE fail path likely leaves DirectMode as 'Stereo disabled'.
"""
from pathlib import Path
import struct
import hashlib
import sys

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
b = bytearray(SRC.read_bytes())
cave = 0x6AF274
b[cave : cave + 0x180] = b"\xCC" * 0x180


def install(site, end, code, label, cur):
    b[cur : cur + len(code)] = code
    b[site:end] = b"\xE9" + struct.pack("<i", cur - (site + 5)) + b"\x90" * (end - site - 5)
    print(label, hex(site), hex(cur), len(code))
    return cur + ((len(code) + 15) // 16) * 16


cur = cave


def addref_skip(cont, cur):
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


def inject_skip(site, label, cur):
    assert bytes(b[site : site + 10]) == bytes.fromhex("4885c9488d5928488bfa")
    end = site + 10
    cont = end
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
    struct.pack_into("<i", code, j_cont + 1, cont - (cur + j_cont + 5))
    return install(site, end, bytes(code), label, cur)


cur = inject_skip(0x21618A, "InjectVS", cur)
cur = inject_skip(0x21849A, "InjectPS", cur)

DST.write_bytes(bytes(b))
print("OK", hashlib.sha256(bytes(b)).hexdigest().upper())
