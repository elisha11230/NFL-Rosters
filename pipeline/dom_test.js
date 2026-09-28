/* Loads the built page in jsdom, a real DOM, and reports every error.
 *
 * The stub-DOM smoke test missed a broken page because its getElementById
 * returns a fake element for any id. A real document returns null for an id
 * that is not there, and code that assumes otherwise throws.
 */
const {JSDOM, VirtualConsole} = require("jsdom");
const fs = require("fs");
const path = process.argv[2];
const hash = process.argv[3] || "";
const html = fs.readFileSync(path, "utf8");
const errors = [];

// Conflict markers are checked before anything runs, with a message that says
// what they are, because the browser's own error ("Unexpected token '<<'") does
// not.
const marker = html.split("\n").findIndex(l => /^(<{7}|>{7}) /.test(l) || l === "=".repeat(7));
if(marker >= 0){
  console.error("DOM TEST FAILED: git conflict markers at line " + (marker + 1) + ".");
  console.error("  The file holds two versions stitched together. Rebuild it rather than editing.");
  process.exit(1);
}
const vc = new VirtualConsole();
vc.on("jsdomError", e => errors.push("jsdom: " + (e.message || e)));
vc.on("error", e => errors.push("console.error: " + e));
const dom = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true,
  url: "https://example.test/" + hash, virtualConsole: vc,
  beforeParse(w){
    w.fetch = () => Promise.reject(new Error("offline in test"));
    w.matchMedia = () => ({matches:false, addEventListener(){}, addListener(){}});
    w.scrollTo = () => {};
    w.HTMLElement.prototype.scrollIntoView = function(){};
    w.addEventListener("error", ev => errors.push("window: " + (ev.error ? ev.error.stack.split("\n").slice(0,3).join(" | ") : ev.message)));
  },
});
setTimeout(() => {
  const d = dom.window.document;
  const count = sel => d.querySelectorAll(sel).length;
  console.log("page " + (hash || "(home)"));
  console.log("  chips on field:", count(".chip"), "| team rail logos:", count("#rail img, #rail button"),
              "| sections:", count(".sect"));
  // An empty page is the failure that matters, so test for it directly.
  if(!count(".chip")) errors.push("no player chips rendered: the page is blank");
  if(errors.length){ console.log("  ERRORS:"); errors.forEach(e => console.log("   ", e)); process.exit(1); }
  console.log("  no errors");
  process.exit(0);
}, 1500);
