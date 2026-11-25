"""Genera un recibo PNG usando únicamente la biblioteca estándar de Python."""
import struct
import zlib


# Glifos 5x7 para el alfabeto, números y signos usados en el recibo.
_FONT = {
    " ": (0,0,0,0,0,0,0), "-": (0,0,0,31,0,0,0), ".": (0,0,0,0,0,12,12),
    ":": (0,12,12,0,12,12,0), "/": (1,2,4,8,16,0,0), "$": (4,15,20,14,5,30,4),
    "0": (14,17,19,21,25,17,14), "1": (4,12,4,4,4,4,14), "2": (14,17,1,2,4,8,31),
    "3": (30,1,1,14,1,1,30), "4": (2,6,10,18,31,2,2), "5": (31,16,16,30,1,1,30),
    "6": (14,16,16,30,17,17,14), "7": (31,1,2,4,8,8,8), "8": (14,17,17,14,17,17,14),
    "9": (14,17,17,15,1,1,14),
}
_ROWS = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"]
_SHAPES = [
 (14,17,17,31,17,17,17),(30,17,17,30,17,17,30),(14,17,16,16,16,17,14),(30,17,17,17,17,17,30),
 (31,16,16,30,16,16,31),(31,16,16,30,16,16,16),(14,17,16,23,17,17,15),(17,17,17,31,17,17,17),
 (14,4,4,4,4,4,14),(7,2,2,2,18,18,12),(17,18,20,24,20,18,17),(16,16,16,16,16,16,31),
 (17,27,21,21,17,17,17),(17,25,21,19,17,17,17),(14,17,17,17,17,17,14),(30,17,17,30,16,16,16),
 (14,17,17,17,21,18,13),(30,17,17,30,20,18,17),(15,16,16,14,1,1,30),(31,4,4,4,4,4,4),
 (17,17,17,17,17,17,14),(17,17,17,17,17,10,4),(17,17,17,21,21,21,10),(17,17,10,4,10,17,17),
 (17,17,10,4,4,4,4),(31,1,2,4,8,16,31),
]
for _i, _char in enumerate(_ROWS[0]):
    _FONT[_char] = _SHAPES[_i]
    _FONT[_ROWS[1][_i]] = _SHAPES[_i]


def _png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)


def create_receipt(items, filename, order_number, timestamp):
    width, row_h, margin = 720, 52, 36
    height = 220 + row_h * len(items)
    pixels = bytearray([255, 250, 248] * width * height)

    def rect(x, y, w, h, color):
        for yy in range(max(0,y), min(height,y+h)):
            start = (yy*width + max(0,x))*3
            end = (yy*width + min(width,x+w))*3
            pixels[start:end] = bytes(color) * ((end-start)//3)

    def text(x, y, value, color=(75,55,57), scale=2):
        for char in str(value):
            glyph = _FONT.get(char, _FONT[" "])
            for gy, bits in enumerate(glyph):
                for gx in range(5):
                    if bits & (1 << (4-gx)):
                        rect(x+gx*scale,y+gy*scale,scale,scale,color)
            x += 6*scale

    rect(20,20,width-40,height-40,(255,255,255))
    text(margin,42,"RABANISTORE",(90,55,65),4)
    text(margin,82,"RECIBO " + order_number, (183,110,121),2)
    text(margin,104,timestamp,scale=1)
    y=142
    total=0
    for item in items:
        subtotal=int(item.get("unit_price",0))*int(item.get("quantity",1)); total+=subtotal
        rect(margin,y,width-margin*2,1,(234,219,213))
        text(margin,y+9,str(item.get("name","Producto"))[:35],scale=1)
        text(margin,y+24,str(item.get("shade",""))[:35],(139,119,113),1)
        text(width-190,y+12,"$"+str(subtotal), (183,110,121),2)
        y+=row_h
    rect(margin,y,width-margin*2,2,(183,110,121))
    text(margin,y+14,"TOTAL $"+str(total),(90,55,65),3)
    raw=b"".join(b"\0"+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    data=b"\x89PNG\r\n\x1a\n"+_png_chunk(b"IHDR",struct.pack(">2I5B",width,height,8,2,0,0,0))+_png_chunk(b"IDAT",zlib.compress(raw))+_png_chunk(b"IEND",b"")
    with open(filename,"wb") as file: file.write(data)
    return total
