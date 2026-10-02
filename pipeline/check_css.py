"""Check which CSS rule wins on a phone and on a desktop.

The DOM tests build the page but ignore screen-size rules, so they could not
see that the tablet rules (max-width:920px) were overriding the phone rules and
keeping the field 700px wide on phones, or that leftover button styling was
drawing boxes in the menu. This runs the real cascade -- media queries for the
width, selectors matched against the page's elements, importance, specificity
and order -- and fails the build if the wrong rule wins.

usage: check_css.py page390.html page1280.html
"""
import sys
import cssselect2
from css_cascade import cascade, computed

PHONE = {
    "#field": {"min-width": {"0", "0px"}, "aspect-ratio": {"auto"}},
    "#fieldwrap": {"overflow-x": {"visible"}},
    "#chips .chip": {"width": {"46px"}},
    "#chips .disc": {"width": {"38px"}},
    "#scoresbtn": {"border-top": {"0", "none"}, "border-left": {"0", "none"}},
    "#leadbtn": {"border-top": {"0", "none"}},
    "#gamebtn": {"background": {"none", "transparent"}},
}
DESKTOP = {
    "#chips .chip": {"width": {"60px"}},
    "#chips .disc": {"width": {"56px"}},
}

bad = 0
for path, width, want in ((sys.argv[1], 390, PHONE), (sys.argv[2], 1280, DESKTOP)):
    doc, m = cascade(open(path).read(), width)
    root = cssselect2.ElementWrapper.from_html_root(doc)
    print(f"-- {width}px")
    for sel, props in want.items():
        els = list(root.query_all(sel))
        if not els:
            print(f"MISSING  {sel}"); bad += 1; continue
        got = computed(doc, m, els[0])
        for prop, ok in props.items():
            val, src = got.get(prop, ("(unset)", ""))
            good = val in ok
            bad += not good
            print(f"{'OK' if good else 'WRONG':<8} {sel} {prop}: {val}" + ("" if good else f"   (rule that won: {src})"))
print("\nclean" if not bad else f"\n{bad} problem(s)")
sys.exit(1 if bad else 0)
