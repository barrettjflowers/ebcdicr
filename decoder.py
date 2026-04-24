#!/usr/bin/env python3
import re
import sys
import os

COPYBOOK_PATH = r"C:\Users\barrett.flowers\Desktop\temp\Project Anaconda\EBCDC\Current\TD0242.copybook"
EBCDIC_FILE_PATH = r"C:\Users\barrett.flowers\Desktop\temp\Project Anaconda\EBCDC\Current\TD0242.EBCDIC"

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
            # COMP, COMP-1, COMP-2, COMP-3 all use packed decimal
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

def render(fields, data, encoding, record_num=0):
    offset = 0
    rec_info = f"RECORD {record_num}"
    print(f"\n{rec_info:^60}")
    print(f"{'OFFSET':6} | {'FIELD NAME':30} | VALUE      | HEX    ")
    print("-" * 65)
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
        print(f"{offset:04X} | {field['name']:30} | {value:>12} | {hex_val}")
        offset += field["bytes"]

def get_record_size(fields):
    return sum(f["bytes"] for f in fields)

def kbhit():
    """Check if a key has been pressed (non-blocking on Windows)"""
    if sys.platform == 'win32':
        import msvcrt
        return msvcrt.kbhit()
    else:
        import select
        return select.select([sys.stdin], [], [], 0) != ([], [], [])

def getch():
    """Get a single keypress (Windows)"""
    if sys.platform == 'win32':
        import msvcrt
        return msvcrt.getch()
    else:
        return sys.stdin.read(1)

def main():
    global encoding_index
    
    print("EBCDIC Decoder - Interactive Mode")
    print("=" * 60)
    print("Controls:")
    print("  ENTER = next record")
    print("  r     = reload copybook")
    print("  e     = cycle encoding")
    print("  q     = quit")
    print("=" * 60)
    
    with open(EBCDIC_FILE_PATH, "rb") as f:
        data = f.read()
    
    fields = parse_copybook(COPYBOOK_PATH)
    record_size = get_record_size(fields)
    encoding = get_current_encoding()
    
    print(f"\nEncoding: {encoding}")
    print(f"Fields: {len(fields)}")
    print(f"Record size: {record_size} bytes")
    print(f"Total file size: {len(data)} bytes")
    print(f"Total records: {len(data) // record_size}")
    
    record_num = 0
    start_offset = 0
    
    encoding = get_current_encoding()
    render(fields, data[start_offset:start_offset + record_size], encoding, record_num)
    
    while True:
        try:
            if sys.platform == 'win32':
                print("\n[ENTER]ext, [r]eload, [e]ncoding, [q]uit: ", end="", flush=True)
                import msvcrt
                key = msvcrt.getch()
                key = key.decode('utf-8', errors='replace') if isinstance(key, bytes) else key
            else:
                print("\n[ENTER]ext, [r]eload, [e]ncoding, [q]uit: ", end="", flush=True)
                key = sys.stdin.read(1)
            
            if key == '\r' or key == '\n':
                # Next record
                record_num += 1
                start_offset += record_size
                if start_offset + record_size > len(data):
                    start_offset = 0
                    record_num = 0
                render(fields, data[start_offset:start_offset + record_size], get_current_encoding(), record_num)
            
            elif key == 'r':
                # Reload copybook
                fields = parse_copybook(COPYBOOK_PATH)
                record_size = get_record_size(fields)
                print(f"\nReloaded copybook: {len(fields)} fields, {record_size} bytes")
                start_offset = 0
                record_num = 0
                render(fields, data[start_offset:start_offset + record_size], get_current_encoding(), record_num)
            
            elif key == 'e':
                # Cycle encoding
                set_next_encoding()
                print(f"\nEncoding: {get_current_encoding()}")
                render(fields, data[start_offset:start_offset + record_size], get_current_encoding(), record_num)
            
            elif key == 'q':
                print("\nGoodbye!")
                break
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()