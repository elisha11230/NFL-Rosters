"""Which CSS rule wins, element by element, at a given screen width.

No layout, just the cascade: media queries evaluated for the width, selectors
matched against the page's real elements, then importance, specificity and
source order decide each property. That is exactly where "the tablet rule came
later and won on phones" lives.

usage: cascade.py page.html width
"""
import re, sys, json
import tinycss2, cssselect2, html5lib
from xml.etree import ElementTree as ET

def media_ok(prelude, width):
    q = tinycss2.serialize(prelude).strip().lower()
    if not q: return True
    for part in q.split(","):                       # any comma clause may match
        ok = True
        for cond in re.findall(r"\(([^)]*)\)", part):
            m = re.match(r"\s*(max|min)-width\s*:\s*([\d.]+)px", cond)
            if m:
                v = float(m.group(2))
                ok &= (width <= v) if m.group(1) == "max" else (width >= v)
            elif "prefers-reduced-motion" in cond or "prefers-color-scheme" in cond:
                ok = False
            elif "hover" in cond or "pointer" in cond:
                ok &= ("none" not in cond and "coarse" not in cond)
        if "print" in part: ok = False
        if ok: return True
    return False

def rules(nodes, width, out, order):
    for n in nodes:
        if n.type == "qualified-rule":
            decls = [d for d in tinycss2.parse_declaration_list(n.content, skip_whitespace=True, skip_comments=True)
                     if d.type == "declaration"]
            out.append((tinycss2.serialize(n.prelude).strip(), decls, order[0])); order[0] += 1
        elif n.type == "at-rule" and n.lower_at_keyword == "media" and n.content is not None:
            if media_ok(n.prelude, width):
                rules(tinycss2.parse_rule_list(n.content, skip_whitespace=True, skip_comments=True), width, out, order)

def cascade(html, width):
    css = html.split("<style>", 1)[1].split("</style>", 1)[0]
    flat = []; rules(tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True), width, flat, [0])
    doc = html5lib.parse(html, treebuilder="etree", namespaceHTMLElements=False)
    matcher = cssselect2.Matcher()
    for sel, decls, order in flat:
        try:
            for cs in cssselect2.compile_selector_list(sel):
                matcher.add_selector(cs, (decls, order, sel))
        except Exception:
            pass
    return doc, matcher

def computed(doc, matcher, el_wrapper):
    win = {}
    for spec, order, pseudo, payload in matcher.match(el_wrapper):
        if pseudo: continue
        decls, o, sel = payload
        for d in decls:
            imp = bool(d.important)
            key = (imp, spec, o)
            name = d.lower_name
            val = tinycss2.serialize(d.value).strip()
            for nm in expand(name, val):
                if nm[0] not in win or key >= win[nm[0]][0]:
                    win[nm[0]] = (key, nm[1], sel)
    return {k: (v[1], v[2]) for k, v in win.items()}

def expand(name, val):
    """Just enough shorthand expansion for borders and padding."""
    if name == "border":
        return [(f"border-{s}", val) for s in ("top","right","bottom","left")]
    if name == "padding":
        p = val.split(); p = (p * 4)[:4] if len(p) == 1 else (p + p)[:4] if len(p) == 2 else (p + [p[1]])[:4] if len(p) == 3 else p[:4]
        return [(f"padding-{s}", x) for s, x in zip(("top","right","bottom","left"), p)]
    return [(name, val)]

if __name__ == "__main__":
    html = open(sys.argv[1]).read(); width = int(sys.argv[2])
    doc, m = cascade(html, width)
    root = cssselect2.ElementWrapper.from_html_root(doc)
    want = json.loads(sys.argv[3])
    for sel, props in want.items():
        els = list(root.query_all(sel))
        if not els: print(f"{sel:<26} (no such element)"); continue
        got = computed(doc, m, els[0])
        for p in props:
            v = got.get(p)
            print(f"{sel:<26} {p:<14} {v[0] if v else '(unset)':<34} from: {v[1][:44] if v else ''}")
