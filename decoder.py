#!/usr/bin/env python3
import re
import struct

COPYBOOK_PATH = r"C:\Users\barrett.flowers\Desktop\temp\Project Anaconda\EBCDC\Current\TD0242.copybook"
EBCDIC_FILE_PATH = r"C:\Users\barrett.flowers\Desktop\temp\Project Anaconda\EBCDC\Current\TD0242.EBCDIC"

#COPYBOOK_PATH = r"/Users/barrettjflowers/Dev/EBCDIC-decode/Copy Books (Verified)/TA2244.copybook"
#EBCDIC_FILE_PATH = r"/Users/barrettjflowers/Dev/EBCDIC-decode/ebcdicr/test_ta2244.ebcdc"

ENCODINGS = ["cp037", "cp1047", "cp1140"]
encoding_index = 0

def get_current_encoding():
    return ENCODINGS[encoding_index]

def set_next_encoding():
    global encoding_index
    encoding_index = (encoding_index + 1) % len(ENCODINGS)

def set_prev_encoding():
    global encoding_index
    encoding_index = (encoding_index - 1) % len(ENCODINGS)

def parse_copybook(path):
    fields = []
    level_re = re.compile(r"^\s*(\d+)\s+(\S+)\s+(?:PIC\s+)?(.+?)\.$")
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            m = level_re.match(line)
            if m:
                name = m.group(2)
                pic = m.group(3).strip()
                fields.append(parse_field(name, pic))
    return fields

def parse_field(name, pic):
    pic = pic.upper().replace(" ", "")
    field_type = "X"
    digits = 0
    scale = 0
    is_comp = "COMP" in pic
    is_comp3 = "COMP-3" in pic
    
    if "X(" in pic:
        field_type = "X"
        match = re.search(r"X\((\d+)\)", pic)
        if match:
            digits = int(match.group(1))
    elif "V" in pic:
        v_pos = pic.find("V")
        before_v = pic[:v_pos]
        if is_comp:
            field_type = "P"
        m = re.search(r"9\((\d+)\)", before_v)
        digits = int(m.group(1)) if m else 0
        after_v = pic[v_pos+1:]
        scale_matches = re.findall(r"9\((\d+)\)", after_v)
        if scale_matches:
            scale = int(scale_matches[0])
        else:
            scale = len(re.findall(r"9(?!\()", after_v))
    elif "9(" in pic:
        if is_comp:
            field_type = "P"
        else:
            field_type = "N"
        match = re.search(r"S?9\((\d+)\)", pic)
        digits = int(match.group(1)) if match else 0
    
    if field_type == "P":
        total_digits = digits + scale
        byte_len = (total_digits + 1) // 2
    else:
        byte_len = digits
    return {"name": name, "type": field_type, "bytes": byte_len, "digits": digits, "scale": scale}

def decode_comp3(data):
    if not data:
        return "0"
    digits = []
    for b in data[:-1]:
        digits.append((b >> 4) & 0x0F)
        digits.append(b & 0x0F)
    last_byte = data[-1]
    digits.append((last_byte >> 4) & 0x0F)
    sign = last_byte & 0x0F
    val = int("".join(map(str, digits)))
    if sign in (0x0D,):
        val = -val
    return str(val)

def decode_display(data, encoding):
    try:
        return data.decode(encoding).strip()
    except:
        return data.hex()

def render(fields, data, encoding):
    offset = 0
    print(f"{'OFFSET':6} | {'FIELD NAME':20} | VALUE      | HEX    ")
    print("-" * 60)
    for field in fields:
        if offset + field["bytes"] > len(data):
            break
        raw = data[offset:offset + field["bytes"]]
        hex_val = "0x" + raw.hex()
        ftype = field["type"]
        if ftype == "P":
            value = decode_comp3(raw)
            if field["scale"] > 0 and value != "0" and value != "-0":
                s = field["scale"]
                if value.startswith("-"):
                    value = "-" + value[1:].zfill(s + len(value) - 1)
                    value = value[:-s] + "." + value[-s:]
                else:
                    value = value.zfill(s + len(value))
                    value = value[:-s] + "." + value[-s:]
        elif ftype == "N":
            value = decode_display(raw, encoding)
        else:
            value = decode_display(raw, encoding)
        print(f"{offset:04X} | {field['name']:20} | {value:>12} | {hex_val}")
        offset += field["bytes"]

def main():
    global encoding_index
    with open(EBCDIC_FILE_PATH, "rb") as f:
        data = f.read()
    fields = parse_copybook(COPYBOOK_PATH)
    encoding = get_current_encoding()
    print(f"Encoding: {encoding}")
    print(f"Fields: {len(fields)}")
    render(fields, data, encoding)

if __name__ == "__main__":
    main()
