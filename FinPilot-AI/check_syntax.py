from pathlib import Path

html = Path(r"C:\Users\Pranav\Downloads\FinPilot-AI\FinPilot-AI\frontend\dist\index.html").read_text(encoding="utf-8")
marker = '<script type="text/babel"'
start = html.find(marker)
end = html.rfind("</script>")
script = html[start + len(marker):end]

print("Script length:", len(script))
oc = script.count("{")
cc = script.count("}")
op = script.count("(")
cp = script.count(")")
ob = script.count("[")
cb = script.count("]")

print(f"Braces ({{}}): {oc} vs {cc} (diff: {oc - cc})")
print(f"Parens (()): {op} vs {cp} (diff: {op - cp})")
print(f"Brackets ([]): {ob} vs {cb} (diff: {ob - cb})")
