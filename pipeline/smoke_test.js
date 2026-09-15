/* Loads the built page's script in a stub DOM to catch errors that a syntax
   check cannot see.
 *
 * This exists because `node --check` passed on a build whose drive chart module
 * had been deleted by an overlapping edit: the syntax was fine and the app was
 * dead on arrival, because a handler referenced a function that no longer
 * existed. A reference error at load time takes the whole page with it.
 */
const fs = require("fs");
const path = process.argv[2] || "index.html";
const html = fs.readFileSync(path, "utf8");
const js = html.split("<script>")[1].split("</script>")[0];

const node = () => ({
  style: {setProperty(){}}, dataset: {}, hidden: false, children: [],
  innerHTML: "", textContent: "", value: "", checked: false,
  firstChild: null, parentElement: null,
  firstElementChild: {style:{}, classList:{add(){},remove(){}},
    appendChild(c){return c}, setAttribute(){}, innerHTML:"", textContent:""},
  classList: {add(){}, remove(){}, toggle(){}, contains(){return false}},
  appendChild(c){return c}, append(){}, prepend(){}, insertBefore(){},
  removeChild(){}, remove(){}, replaceChildren(){}, after(){}, before(){},
  setAttribute(){}, getAttribute(){return null}, removeAttribute(){},
  addEventListener(){}, removeEventListener(){}, dispatchEvent(){},
  querySelector(){return null}, querySelectorAll(){return []},
  scrollIntoView(){}, focus(){}, blur(){}, click(){},
  getBoundingClientRect(){return {left:0,top:0,right:0,bottom:0,width:100,height:100};},
});

global.document = {
  createElement: node, createElementNS: node, createTextNode: t => ({textContent:t}),
  getElementById(){return node();}, querySelector(){return node();},
  querySelectorAll(){return [];},
  addEventListener(){}, removeEventListener(){},
  body: node(), documentElement: node(), head: node(),
  hidden: false, visibilityState: "visible",
};
global.window = {
  addEventListener(){}, removeEventListener(){},
  matchMedia(){return {matches:false, addEventListener(){}, addListener(){}};},
  location: {hash:"", search:"", href:"", reload(){}},
  localStorage: {getItem(){return null;}, setItem(){}, removeItem(){}},
  innerWidth: 1280, innerHeight: 800, devicePixelRatio: 2,
  scrollTo(){}, getComputedStyle(){return {getPropertyValue(){return "";}};},
};
global.location = window.location;
global.localStorage = window.localStorage;
global.navigator = {vibrate(){}, userAgent: "node", onLine: true};
global.Image = function(){ return node(); };
global.fetch = () => Promise.reject(new Error("offline in test"));
global.setInterval = () => 0; global.clearInterval = () => {};
global.setTimeout = () => 0; global.clearTimeout = () => {};
global.requestAnimationFrame = () => 0;
global.CSS = {escape: s => String(s)};
global.matchMedia = window.matchMedia;
global.history = {replaceState(){}, pushState(){}, back(){}, forward(){}};
window.history = global.history;
global.URL = URL; global.URLSearchParams = URLSearchParams;
global.performance = {now: () => 0};

try {
  new Function(js)();
  console.log("smoke test passed: script loads and initialises");
} catch (e) {
  console.error("SMOKE TEST FAILED");
  console.error("  " + e.constructor.name + ": " + e.message);
  const line = (e.stack || "").split("\n")[1] || "";
  if (line) console.error("  " + line.trim());
  process.exit(1);
}
