import base64, os, re
tpl = open("template.html").read()
def datauri(m):
    p = f"img/final/{m.group(1)}.jpg"
    b = base64.b64encode(open(p, "rb").read()).decode()
    return f"data:image/jpeg;base64,{b}"
out = re.sub(r"\{\{IMG_(\w+)\}\}", datauri, tpl)
open("index.html", "w").write(out)
print("index.html:", len(out)//1024, "KB;", len(re.findall(r"data:image", out)), "imagini embedate")
